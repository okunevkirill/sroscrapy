# -*- coding: utf-8 -*-
""" The module is designed for parsing the site of professional members
    of a self-regulatory organization in the Russian financial market NAUFOR.
   site: https://www.naufor.ru/
"""

__author__ = 'ok_kir'
__version__ = '0.00.7'

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
# Connection constants
HOST = r"https://www.naufor.ru"  # SRO main page address
URL_PAGE = r"https://www.naufor.ru/tree.asp?n=13092"  # Parsing page URL
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:92.0) Gecko/20100101 Firefox/92.0",
    "Accept": "*/*"
}
# ---------------------------------------------
# Constants for files
PATH_INP_COMPANIES = "inp_lst_companies.csv"
TABLE_HEADERS = ('Компания', 'Информация о проверках', "Дата последней проверки", 'Адрес источника')
MSG_NO_COMPANY = "Компании нет в списках членов СРО"
MSG_NO_URL = "Не удалось обновить информацию - проверьте адрес"
# ---------------------------------------------
# Xlsx formatting constants
XLSX_HEADING = {'bold': True, 'font_color': 'black', 'font_size': '14', 'valign': 'vcenter', 'align': 'center',
                'text_wrap': 'True', 'border': 2}
XLSX_DEFAULT = {'align': 'left', 'valign': 'vcenter', 'text_wrap': 'True'}
XLSX_MARKER = {"bg_color": 'red', 'align': 'left', 'valign': 'vcenter'}
# ---------------------------------------------
# Constants for multithreading
NUMBER_OF_ALL_PROC = 42  # Number of worker processes for parallel parsing


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
            return f"[!] ParsingError - {self.msg}"
        else:
            return "[!] ParsingError encountered - check your parsing logic and addresses"


# --------------------------------------------------------------------------------
# Functions for testing and evaluating a module

def timer(func):
    """Decorator for getting the running time of a function"""

    @wraps(func)
    def wrapper(*args):
        start_timer = perf_counter()
        return_value = func(*args)
        stop_timer = perf_counter()
        print(f"[*] Время работы '{func.__name__}': {stop_timer - start_timer}")
        return return_value

    return wrapper


# --------------------------------------------------------------------------------
def get_html(url, params=None):
    """Retrieving the page content at the specified url

    :param url: Parsing page address
    :param params: Additional parameter for the analysis of several pages of the same type
    :return: If information from the site was received, the html code is returned, otherwise None is returned
    """

    r = requests.get(url, headers=BROWSER_HEADERS, params=params)
    if r.status_code == 200:
        return r.text
    return None


def get_all_companies(html, host=HOST):
    """Obtaining a list of all companies of professional SRO participants

    :param html: html code
    :param host: Site main page address
    :return: A dictionary of all professional SRO members is returned with addresses based on the results of the check
    """

    soup = BeautifulSoup(html, 'lxml')

    links = soup.find_all('a', class_='link-ajax')
    companies = {}
    for link in links:
        name = link.get_text(strip=True)
        href = host + link.get('href').strip()
        companies[name] = href
    return companies


def get_verification_data(html):
    """Obtaining information about the results of the check

    :param html: html code
    :return: A tuple with information about checks and the date of the last check
    """

    soup = BeautifulSoup(html, 'lxml')
    res = ''
    flag_info = False
    date = ''
    for string in soup.find_all('tr'):
        info = string.get_text()
        if info.find('6 Сведения') != -1:
            flag_info = True
        elif flag_info and info.find('7 Сведения') != -1:
            break

        if info.strip().replace('\n', '').replace('\t', '').replace('\r', '') == '':
            info = 'Проверок СРО не было'

        if flag_info:
            res += info.replace('* * *', '').replace('\n\n\n', '')
            if info.find('Дата окончания') != -1:
                date = info.replace('Дата окончания', '').strip().strip('\n')

    return res, date


def check_entry_company(all_company, enterprises):
    """Sorting companies and filtering out those not listed for tracking

    :param all_company: Dictionary of all companies of professional SRO participants
    :param enterprises: List of required companies
    :return: A tuple of lists with company names in column 0 and addresses in 1
    """
    res = ([], [])
    for idx, member in enumerate(enterprises):
        res[0].append(member)
        res[1].append(None)  # [*] - We install to track companies that are not on the list of SRO members
        for firm in all_company:
            if firm.lower().find(member.lower()) != -1:
                res[1][idx] = all_company[firm]
    return res


def parsing_info(url):
    if url is None:
        return MSG_NO_COMPANY, ''

    html = get_html(url)
    if html is None:
        # Reply from the site != 200
        return MSG_NO_URL, ''
    else:
        content, date = get_verification_data(html)
        return content, date


def get_dataframe(info_members):
    """The function of forming a single data set based on the analysis results

    :param info_members: A tuple of lists with company names in column 0 and addresses in 1
    :return: Dictionary with information about SRO members for writing in xlsx
    """

    res = {'name': info_members[0], 'href': info_members[1]}
    with Pool(NUMBER_OF_ALL_PROC) as prc:
        content = prc.map(parsing_info, info_members[1])
    res['info'] = [x[0] for x in content]
    res['date'] = [x[1] for x in content]

    return res


# --------------------------------------------------------------------------------
# Functions for working with files
def read_data_file(path=PATH_INP_COMPANIES):
    """The function of reading the initial data for the script to work

    :param path: The path to the file
    :return: A tuple from the list of required companies and the dates of the last checks
    """
    members, date = [], []
    with open(path, 'r', encoding='cp1251') as csv_file:
        reader = csv.DictReader(csv_file, delimiter=';')
        try:
            for line in reader:
                members.append(line[TABLE_HEADERS[0]].strip())
                date.append(line[TABLE_HEADERS[2]].strip())
        except KeyError:
            raise ParsingError("Check the headers in the raw data file")
    return members, date


def save_file_xlsx(dataframe, inp_date, path="Результаты.xlsx"):
    """The function of creating an xlsx file with the result of the script

    :param dataframe: Dictionary with information about SRO members
    :param inp_date: Initial data about the date of the last check (from a csv file)
    :param path: Result file save address
    :return: None
    """

    workbook = xlsxwriter.Workbook(path)
    worksheet = workbook.add_worksheet("НАУФОР")
    # ----------------------------------------
    # Добавление форматирования для xlsx
    worksheet.set_default_row(40)  # Высота строк
    heading_format = workbook.add_format(XLSX_HEADING)
    default_format = workbook.add_format(XLSX_DEFAULT)
    marker_format = workbook.add_format(XLSX_MARKER)
    # ----------------------------------------
    # Формирование заголовков
    worksheet.write('A1', TABLE_HEADERS[0], heading_format)
    worksheet.write('B1', TABLE_HEADERS[1], heading_format)
    worksheet.write('C1', TABLE_HEADERS[2], heading_format)
    worksheet.write('D1', TABLE_HEADERS[3], heading_format)
    # ----------------------------------------
    # Ширина столбцов
    worksheet.set_column('A:A', 20)
    worksheet.set_column('A:B', 30)
    worksheet.set_column('C:C', 20)
    worksheet.set_column('D:D', 45)
    # ----------------------------------------
    row, col = 1, 0
    for index in range(len(dataframe["name"])):
        name, info, date, href = dataframe["name"][index], dataframe["info"][index], dataframe["date"][index], \
                                 dataframe["href"][index]

        worksheet.write(row, col, name, default_format)
        if info in (MSG_NO_URL, MSG_NO_COMPANY):
            worksheet.write(row, col + 1, info, marker_format)
        else:
            worksheet.write(row, col + 1, info, default_format)

        if date != inp_date[index].strip():
            worksheet.write(row, col + 2, date, marker_format)
        else:
            worksheet.write(row, col + 2, date, default_format)
        worksheet.write(row, col + 3, href, default_format)
        row += 1
    workbook.close()


# --------------------------------------------------------------------------------
@timer
def main_for_parse(url=URL_PAGE):
    """The main function of parsing SRO NAUFOR

    :param url: Parsing page URL
    :return: None
    """

    try:
        if os.path.exists(PATH_INP_COMPANIES) and os.path.isfile(PATH_INP_COMPANIES):
            enterprises, inp_date = read_data_file()
            if not enterprises:
                raise ParsingError("Check the configuration of the company listing file")
            print("[*] - Список компаний был загружен из файла")

        else:
            raise ParsingError("Check file path and file name")
        # ---------------------------------------------
        soup = get_html(url)
        if soup is None:
            raise ParsingError("HTTP status code is not 200")
        else:
            print("[*] - Ответ от сайта получен")
        # ---------------------------------------------
        companies = get_all_companies(soup)
        if not companies:
            raise ParsingError("Failed to get the list of SRO members")
        else:
            print("[*] - Список членов СРО сформирован")
        # ---------------------------------------------
        info_members = check_entry_company(companies, enterprises=enterprises)
        if not info_members[0]:  # If there are no companies
            raise ParsingError("The list of companies to search is empty")
        else:
            print("[*] - Список искомых компаний сформирован")

        dataframe = get_dataframe(info_members)
        save_file_xlsx(dataframe, inp_date)
    except ParsingError as err:
        print("[!] - Check the data for the script")
        print("-" * 50, err, "-" * 50, sep='\n')


# --------------------------------------------------------------------------------
if __name__ == '__main__':
    print("[!] - Начало работы скрипта", "=" * 50, sep="\n")
    main_for_parse()
    print("[!] - Окончание работы скрипта", "=" * 50, sep="\n")
