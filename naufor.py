# -*- coding: cp1251 -*-
"""������ �������� �������������� ��� ������
   - https://www.naufor.ru/
"""
__author__ = 'ok_kir'
__version__ = '0.00.5'

# ================================================================================
import csv
import os
from time import perf_counter
from functools import wraps
from multiprocessing import Pool

import requests
from bs4 import BeautifulSoup
import xlsxwriter

# --------------------------------------------------------------------------------
# ��������� ������
HOST = r"https://www.naufor.ru"  # ����� �������� �������� ���
URL_PAGE = r"https://www.naufor.ru/tree.asp?n=13092"  # ����� �������� ��������
REQUEST_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:92.0) Gecko/20100101 Firefox/92.0',
    'Accept': '*/*'
}  # ��������� ��� ������������ ������ ��������
PATH_FOR_SAVE = 'members.csv'
PATH_FOR_LOAD = 'members.csv'
ENTERPRISES = []  # ������ ������������� ��������
TABLE_HEADERS = ('��������', '���������� � ���������', '����� ���������')
NUMBER_OF_ALL_PROC = 42  # ����� ��������� ��� ������������� ��������


# --------------------------------------------------------------------------------
class ParsingError(Exception):
    """Site Parsing Exception Class"""

    def __init__(self, *args):
        if args:
            self.msg = args[0]
        else:
            self.msg = None

    def __str__(self):
        if self.msg:
            return f"[!] ParsingError: {self.msg}"
        else:
            return "[!] ParsingError encountered - check your parsing logic and addresses"


# --------------------------------------------------------------------------------
# ����������� � ������� ��� ������������ � ������ ������
def timer(func):
    """��������� ��� ��������� ������� ������ �������"""

    @wraps(func)
    def wrapper(*args):
        start_timer = perf_counter()
        return_value = func(*args)
        stop_timer = perf_counter()
        print(f"[*] ����� ������ '{func.__name__}': {stop_timer - start_timer}")
        return return_value

    return wrapper


# --------------------------------------------------------------------------------
def get_html(url, params=None):
    """��������� ����������� �������� �� ���������� url

    :param url: ����� �������� ��� ��������.
    :param params: �������������� �������� ��� ������� ���������� ���������� �������
    :return: ���� ���������� � ����� ���� �������� ������������ ������, ����� ������������ None
    """

    r = requests.get(url, headers=REQUEST_HEADERS, params=params)
    # [*] - ��� ��� ���� ������ �������� ������ �� ��������� ���������� (��� �������� ���. ���������� �� ����), ��
    # ��������� ������� �������� �� ������������ ������ (����� ����������� �� `r.ok`)
    if r.status_code == 200:
        # ������������ ���������� ������ � ������ � ���������� ��������� �� ����� ��� utf-8 (�� ���������)
        return r.text
    return None


def get_all_companies(html, host=HOST):
    """��������� ������ ���� �������� �������������� ���.

    :param html: ���������������� html ���.
    :param host: ����� �������� �������� �����
    :return: ������������ ������� ���� �������� �������������� ��� � �������� �� ��������� ��������.
    """
    soup = BeautifulSoup(html, 'lxml')
    # ��������� ��� ��� �� html �������� �������� �������� ����������
    # � ���� ������ <a> � ������� <link-ajax>
    links = soup.find_all('a', class_='link-ajax')
    companies = {}
    for link in links:
        name = link.get_text(strip=True)  # ��� �������� ��������� ���
        href = host + link.get('href').strip()  # ����� �������� � ��������� ����������� � ��������
        companies[name] = href
    return companies


def get_verification_data(html):
    """��������� ���������� � ����������� ��������

    :param html: ���������������� html ���
    :return: ������������ ������ � ����������� � ����������� ��������
    """
    string_begin = '6 �������� � ����������� ���������������� ������������ � ����� ����������� ����� ���������'
    string_end = '7 �������� � ���������� ���������������� ������������ � �����'

    soup = BeautifulSoup(html, 'lxml')
    res_text = soup.text
    index_begin = res_text.find(string_begin) + len(string_begin)
    index_end = res_text.find(string_end, index_begin)
    info = res_text[index_begin: index_end].replace('* * *', '').replace('\n\n\n', '\n').strip('\n')

    # ���� ������ ������� ������ �� �������� ����� ������ - �������� ��� �� ����
    if len(info) == info.count('\n'):
        info = '�������� ��� �� ����'
    return info


def check_entry_company(all_company, enterprises):
    """���������� �������� � ����� �� ��������� ��� ������������

    :param all_company: ������� ���� �������� �������������� ���
    :param enterprises: ������ ������������ ��� �������� - ���������� ���
    :return: ������ ������� � ������� �������� � 0 ������� � �������� � 1
    """
    res = ([], [])
    for idx, member in enumerate(enterprises):
        res[0].append(member)
        res[1].append(None)  # [*] - ������������� ��� ������������ �������� ������������� � ������ ������ ���
        for firm in all_company:
            if firm.lower().find(member.lower()) != -1:
                res[1][idx] = all_company[firm]
    return res


def parsing_info(url):
    if url is None:
        return "�������� ��� � ������� ������ ���"

    html = get_html(url)
    if html is None:
        # ����� �� ����� != 200
        return "�� ������� �������� ���������� - ��������� �����"
    else:
        content = get_verification_data(html)
        return content


def get_dataframe(info_members):
    """������� ������������ ������� ������ ������ - ��������� ����� ��������

    :param info_members: ������ ������� � ������� �������� � 0 ������� � �������� � 1
    :return: ������� � ����������� � ������ ���
    """

    res = {'name': info_members[0], 'href': info_members[1]}
    with Pool(NUMBER_OF_ALL_PROC) as prc:
        temp = prc.map(parsing_info, info_members[1])
    res['info'] = temp

    return res


# --------------------------------------------------------------------------------
# ������� ��� ������ � �������
def read_data_file(path=PATH_FOR_LOAD):
    members = []
    with open(path, 'r', encoding='cp1251') as csv_file:
        reader = csv.DictReader(csv_file, delimiter=';')
        for line in reader:
            members.append(line[TABLE_HEADERS[0]].strip())
    return members


def save_file_xlsx(dataframe, path="����������.xlsx"):
    """���������� � xlsx ����"""

    workbook = xlsxwriter.Workbook(path)
    worksheet = workbook.add_worksheet("������")
    # ----------------------------------------
    # ���������� �������������� ��� xlsx
    worksheet.set_default_row(40)  # ������ �����
    heading_format = workbook.add_format(
        {
            'bold': True,
            'font_color': 'black',
            'font_size': '14',
            'valign': 'vcenter',
            'align': 'center'
        }
    )
    text_format = workbook.add_format(
        {
            'align': 'left',
            'valign': 'vcenter'
            # 'text_wrap': 'True'
        }
    )
    # ----------------------------------------
    # ������������ ����������
    worksheet.write('A1', TABLE_HEADERS[0], heading_format)
    worksheet.write('B1', TABLE_HEADERS[1], heading_format)
    worksheet.write('C1', TABLE_HEADERS[2], heading_format)
    # ----------------------------------------
    # ������ ��������
    worksheet.set_column('A:A', 30)
    worksheet.set_column('A:B', 40)
    worksheet.set_column('C:C', 50)
    # ----------------------------------------
    row, col = 1, 0
    for index in range(len(dataframe["name"])):
        name, info, href = dataframe["name"][index], dataframe["info"][index], dataframe["href"][index]
        worksheet.write(row, col, name, text_format)
        worksheet.write(row, col + 1, info, text_format)
        worksheet.write(row, col + 2, href, text_format)
        row += 1
    workbook.close()


# --------------------------------------------------------------------------------
@timer
def main_for_parse(url=URL_PAGE):
    """�������� ������� �������� ��� ������

    :param url:
    :return:
    """

    # ������������ ������ ������������ ��������
    # ���� ���� ����� �����������, �� ��������� ������ �� ����, ����� - ���������� ���������� ������
    if os.path.exists(PATH_FOR_LOAD) and os.path.isfile(PATH_FOR_LOAD):
        enterprises = read_data_file()
        print("[*] - ������ �������� �������� �� �����")
    else:
        enterprises = ENTERPRISES
        print("[*] - ������ �������� ���� �� �������")
    # --------------------------------------------------
    try:
        soup = get_html(url)
        if soup is None:
            raise ParsingError("HTTP status code is not 200")
        else:
            print("[*] - ����� �� ����� �������")

        companies = get_all_companies(soup)
        if not companies:
            raise ParsingError("Failed to get the list of SRO members")
        else:
            print("[*] - ������ ������ ��� �����������")

        info_members = check_entry_company(companies, enterprises=enterprises)
        # print(info_members)
        if not info_members[0]:  # ���� �������� ���
            raise ParsingError("The list of companies to search is empty")
        else:
            print("[*] - ������ ������� �������� �����������")

        dataframe = get_dataframe(info_members)
        save_file_xlsx(dataframe)
    except ParsingError:
        print("[!] �������� �� ��� �������")


# --------------------------------------------------------------------------------
print("[!] - ������ ������ �������", "=" * 50, sep="\n")
main_for_parse()
print("[!] - ��������� ������ �������", "=" * 50, sep="\n")

# temp = {'name': ['�������� ��', '��������� �� ���', '�������������� �� ���', '���� ��� ����� �� ���', '����� ���� ���', '��������� �� ���', '������������ �������������� ����������� ���', '����������� ��������'], 'href': ['https://www.naufor.ru/compcard.asp?compid=5228', 'https://www.naufor.ru/compcard.asp?compid=6819', 'https://www.naufor.ru/compcard.asp?compid=6192', 'https://www.naufor.ru/compcard.asp?compid=6122', 'https://www.naufor.ru/compcard.asp?compid=3348', 'https://www.naufor.ru/compcard.asp?compid=7066', 'https://www.naufor.ru/compcard.asp?compid=6026', ''], 'info': ['6.1 ���� ������ � ���� ��������� ��������\n���� ������\n01.11.2016\n���� ���������\n30.11.2016\n6.2 ��������� ���������� ��������\n������ ���������� ������\n6.3 ������� ��������\n�������� ���������� ���������� �� � ��������������� �������������� ������������� ������������ ���������� � ��������������� ����\n6.4 ��������� �������� (���������, ���������� � ���� ����������� �������� (��� �������)\n�������� ��������� ���������� ���������� �� � ��������������� �������������� ������������� ������������ ���������� � ����������\n\n6.1 ���� ������ � ���� ��������� ��������\n���� ������\n07.06.2021\n���� ���������\n05.08.2021\n6.2 ��������� ���������� ��������\n������ ���������� ������\n6.3 ������� ��������\n�������� ���������� ���������� ����������� ������� � ���������� ���������� ������, ���������� � ������������ ������� �������� ������ �� 2021 ���\n6.4 ��������� �������� (���������, ���������� � ���� ����������� �������� (��� �������)\n�������� ��������� ����������� ��������� ������ "�������������� ������� � ������", �������� ��������� ���������� ����������� �������� �� ���������� ����� � �������� ��������� ���������� �������� �������� �� ���������� �����.', '�������� ��� �� ����', '6.1 ���� ������ � ���� ��������� ��������\n���� ������\n11.03.2020\n���� ���������\n09.04.2020\n6.2 ��������� ���������� ��������\n������ ���������� ������\n6.3 ������� ��������\n�������� ���������� ���������� ���������� ������������ ����������� �������� ������ �������������� ������ ������ � ����� ���������� ��������� 1 "�������������� ��������� ���������" � ��������� 3 "���������� ������� ����������� ��������"\n6.4 ��������� �������� (���������, ���������� � ���� ����������� �������� (��� �������)\n��������� �� ��������', '6.1 ���� ������ � ���� ��������� ��������\n���� ������\n19.02.2020\n���� ���������\n19.03.2020\n6.2 ��������� ���������� ��������\n������ ���������� ������\n6.3 ������� ��������\n�������� ���������� ���������� ���������� ������������ ����������� �������� ������ �������������� ������ ������ � ����� ���������� ��������� 1 "�������������� ��������� ���������" � ��������� 3 "���������� ������� ����������� ��������".\n6.4 ��������� �������� (���������, ���������� � ���� ����������� �������� (��� �������)\n��������� �� ��������', '6.1 ���� ������ � ���� ��������� ��������\n���� ������\n28.10.2019\n���� ���������\n26.11.2019\n6.2 ��������� ���������� ��������\n������ ���������� ������\n6.3 ������� ��������\n�������� ���������� �������� ��������� ���������� �������� �������� �� ���������� ����� �� �������� ������� � ������� ������������� �������� ������� � ������ ����� �������� � ��������� �������; �������� ��������� ���������� ����������� �������� �� ���������� ����� �� �������� ������� � ������� ����������� ��������������� ������� �������; �������� ��������� ���������� ������������ �������� �� ���������� ����� �� �������� ��������, ��������� � ���������� ������������ �������� � ������� ����� \n6.4 ��������� �������� (���������, ���������� � ���� ����������� �������� (��� �������)\n��������� �� ��������', '�������� ��� �� ����', '6.1 ���� ������ � ���� ��������� ��������\n���� ������\n29.04.2019\n���� ���������\n28.05.2019\n6.2 ��������� ���������� ��������\n������ ���������� ������\n6.3 ������� ��������\n���������� ����������� ��������� ������ ������� ����������� ��������� ������ ������� ������� ��������������� ����� � ��������� ��������������� ���\n6.4 ��������� �������� (���������, ���������� � ���� ����������� �������� (��� �������)\n��������� �� ��������', '�������� ��� � ������� ������ ���']}
# save_file_xlsx(temp, 'temp.xlsx')
