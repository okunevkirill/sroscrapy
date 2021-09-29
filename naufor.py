# -*- coding: utf-8 -*-
"""Модуль парсинга профучастников СРО НАУФОР
   - https://www.naufor.ru/
"""
__author__ = 'ok_kir'
__version__ = '0.00.4'

# ================================================================================
import csv
import os
from time import perf_counter
from functools import wraps

import requests
from bs4 import BeautifulSoup
import xlsxwriter

# --------------------------------------------------------------------------------
# Константы модуля
HOST = r"https://www.naufor.ru"  # Адрес основной страницы СРО
URL_PAGE = r"https://www.naufor.ru/tree.asp?n=13092"  # Адрес страницы парсинга
REQUEST_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:92.0) Gecko/20100101 Firefox/92.0',
    'Accept': '*/*'
}  # Заголовки для эмулирования работы браузера
PATH_FOR_SAVE = 'members.csv'
PATH_FOR_LOAD = 'members.csv'
ENTERPRISES = []  # Список отслеживаемых компаний
TABLE_HEADERS = ('Компания', 'Информация о проверках', 'Адрес источника')


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
# Ограничения и функции для тестирования и оценки модуля
def timer(func):
    """Декоратор для получения времени работы функции"""

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
    """Получение содержимого страницы по указанному url

    :param url: Адрес страницы для парсинга.
    :param params: Дополнительный параметр для анализа нескольких однотипных страниц
    :return: Если информация с сайта была получена возвращается строка, иначе возвращается None
    """

    r = requests.get(url, headers=REQUEST_HEADERS, params=params)
    # [*] - Так как весь скрипт работает только на получение информации (без передачи доп. параметров на сайт), то
    # использую строгую проверку на корректность ответа (иначе использовал бы `r.ok`)
    if r.status_code == 200:
        # Конвертируем полученные данные в строку с кодировкой указанной на сайте или utf-8 (по умолчанию)
        return r.text
    return None


def get_all_companies(html, host=HOST):
    """Получение списка всех компаний профучастников СРО.

    :param html: Конвертированный html код.
    :param host: Адрес основной страницы сайта
    :return: Возвращается словарь всех компаний профучастников СРО с адресами на результат проверки.
    """
    soup = BeautifulSoup(html, 'lxml')
    # Пользуюсь тем что на html странице перечень компаний реализован
    # в виде ссылок <a> с классом <link-ajax>
    links = soup.find_all('a', class_='link-ajax')
    companies = {}
    for link in links:
        name = link.get_text(strip=True)  # Имя компании участницы СРО
        href = host + link.get('href').strip()  # Адрес страницы с подробной информацией о компании
        companies[name] = href
    return companies


def get_verification_data(html):
    """Получения информации о результатах проверки

    :param html: Конвертированный html код
    :return: Возвращается строка с информацией о результатах проверки
    """
    string_begin = '6 Сведения о проведенных саморегулируемой организацией в сфере финансового рынка проверках'
    string_end = '7 Сведения о применении саморегулируемой организацией в сфере'

    soup = BeautifulSoup(html, 'lxml')
    res_text = soup.text
    index_begin = res_text.find(string_begin) + len(string_begin)
    index_end = res_text.find(string_end, index_begin)
    info = res_text[index_begin: index_end].replace('* * *', '').replace('\n\n\n', '\n').strip('\n')

    # Если строка состоит только из символов конца строки - проверок СРО не было
    if len(info) == info.count('\n'):
        info = 'Проверок СРО не было'
    return info


def check_entry_company(all_company, enterprises):
    """Сортировка компаний и отсев не указанных для отслеживания

    :param all_company: Словарь всех компаний профучастников СРО
    :param enterprises: Список интересующих нас компаний - участников СРО
    :return: словарь с именем компании в качестве ключа, значения - адрес
    """
    res = {}
    # ToDo - Можно сделать параллельный скроллинг (существенно ускорит скрипт)
    for member in enterprises:
        res[member] = None  # [*] - Устанавливаем для отслеживания компаний отсутствующих в списке членов СРО
        for firm in all_company:
            if firm.lower().find(member.lower()) != -1:
                res[member] = all_company[firm]
    return res


def get_dataframe(members):
    """Функция формирования единого набора данных - результат всего парсинга

    :param members:
    :return:
    """
    res = {
        'name': [],
        'href': [],
        'info': []
    }

    for member in members.keys():
        url = members.get(member)
        if url is None:
            res['name'].append(member)
            res['href'].append("")
            res['info'].append("Компании нет в списках членов СРО")
            continue

        res['name'].append(member)
        res['href'].append(url)
        html = get_html(url)
        if html is None:
            # Ответ от сайта != 200
            res['info'].append("Не удалось обновить информацию - проверьте адрес")
        else:
            content = get_verification_data(html)
            res['info'].append(content)
    return res


# --------------------------------------------------------------------------------
# Функции для работы с файлами
def read_data_file(path=PATH_FOR_LOAD):
    members = []
    with open(path, 'r', encoding='utf-8') as csv_file:
        reader = csv.DictReader(csv_file, delimiter=';')
        for line in reader:
            members.append(line[TABLE_HEADERS[0]].strip())
    return members


def save_file_xlsx(dataframe, path="Результаты.xlsx"):
    """Сохранение в xlsx файл"""

    workbook = xlsxwriter.Workbook(path)
    worksheet = workbook.add_worksheet("НАУФОР")
    # ----------------------------------------
    # Добавление форматирования для xlsx
    worksheet.set_default_row(40)   # Высота строк
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
    # Формирование заголовков
    worksheet.write('A1', TABLE_HEADERS[0], heading_format)
    worksheet.write('B1', TABLE_HEADERS[1], heading_format)
    worksheet.write('C1', TABLE_HEADERS[2], heading_format)
    # ----------------------------------------
    # Ширина столбцов
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
    """Основная функция парсинга СРО НАУФОР

    :param url:
    :return:
    """

    # Формирование списка интересующих компаний
    # Если файл ранее существовал, то формируем список из него, иначе - используем глобальный список
    if os.path.exists(PATH_FOR_LOAD) and os.path.isfile(PATH_FOR_LOAD):
        enterprises = read_data_file()
        print("[*] - Список компаний загружен из файла")
    else:
        enterprises = ENTERPRISES
        print("[*] - Список компаний взят из скрипта")
    # --------------------------------------------------
    try:
        soup = get_html(url)
        if soup is None:
            raise ParsingError("HTTP status code is not 200")
        else:
            print("[*] - Ответ от сайта получен")

        companies = get_all_companies(soup)
        if not companies:
            raise ParsingError("Failed to get the list of SRO members")
        else:
            print("[*] - Список членов СРО сформирован")

        members = check_entry_company(companies, enterprises=enterprises)
        if not members:
            raise ParsingError("The list of companies to search is empty")
        else:
            print("[*] - Список искомых компаний был сформирован")

        dataframe = get_dataframe(members)
        save_file_xlsx(dataframe)
    except ParsingError:
        print("[!] Проверти ИД для скрипта")


# --------------------------------------------------------------------------------
print("[!] - Начало работы скрипта", "=" * 50, sep="\n")
main_for_parse()
print("[!] - Окончание работы скрипта", "=" * 50, sep="\n")

# temp = {'name': ['Датабанк АО', 'СтоунХедж УК ООО', 'Сургутгазстрой УК ООО', 'Евро Фин Траст УК ООО', 'ЗЕНИТ Банк ПАО', 'Доминвест УК ООО', 'ВербаКапитал Инвестиционное партнерство ООО', 'Неизвестная компания'], 'href': ['https://www.naufor.ru/compcard.asp?compid=5228', 'https://www.naufor.ru/compcard.asp?compid=6819', 'https://www.naufor.ru/compcard.asp?compid=6192', 'https://www.naufor.ru/compcard.asp?compid=6122', 'https://www.naufor.ru/compcard.asp?compid=3348', 'https://www.naufor.ru/compcard.asp?compid=7066', 'https://www.naufor.ru/compcard.asp?compid=6026', ''], 'info': ['6.1 Дата начала и дата окончания проверки\nДата начала\n01.11.2016\nДата окончания\n30.11.2016\n6.2 Основание проведения проверки\nПриказ Президента НАУФОР\n6.3 Предмет проверки\nПроверка соблюдения требований РФ о противодействии неправомерному использования инсайдерской информации и манипулированию рынк\n6.4 Результат проверки (нарушения, выявленные в ходе проведенной проверки (при наличии)\nВыявлены нарушения соблюдения требований РФ о противодействии неправомерному использованию инсайдерской информации и манипулиро\n\n6.1 Дата начала и дата окончания проверки\nДата начала\n07.06.2021\nДата окончания\n05.08.2021\n6.2 Основание проведения проверки\nПриказ Президента НАУФОР\n6.3 Предмет проверки\nПроверка соблюдения требований действующих базовых и внутренних стандартов НАУФОР, включенных в приоритетные области контроля НАУФОР на 2021 год\n6.4 Результат проверки (нарушения, выявленные в ходе проведенной проверки (при наличии)\nВыявлены нарушения внутреннего стандарта НАУФОР "Информирование клиента о рисках", базового стандарта совершения управляющим операций на финансовом рынке и базового стандарта совершения брокером операций на финансовом рынке.', 'Проверок СРО не было', '6.1 Дата начала и дата окончания проверки\nДата начала\n11.03.2020\nДата окончания\n09.04.2020\n6.2 Основание проведения проверки\nПриказ Президента НАУФОР\n6.3 Предмет проверки\nПроверка соблюдения внутренних стандартов деятельности управляющих компаний паевых инвестиционных фондов НАУФОР в части соблюдения Стандарта 1 "Предотвращение конфликта интересов" и Стандарта 3 "Управление рисками управляющей компании"\n6.4 Результат проверки (нарушения, выявленные в ходе проведенной проверки (при наличии)\nНарушений не выявлено', '6.1 Дата начала и дата окончания проверки\nДата начала\n19.02.2020\nДата окончания\n19.03.2020\n6.2 Основание проведения проверки\nПриказ Президента НАУФОР\n6.3 Предмет проверки\nПроверка соблюдения внутренних стандартов деятельности управляющих компаний паевых инвестиционных фондов НАУФОР в части соблюдения Стандарта 1 "Предотвращение конфликта интересов" и Стандарта 3 "Управление рисками управляющей компании".\n6.4 Результат проверки (нарушения, выявленные в ходе проведенной проверки (при наличии)\nНарушений не выявлено', '6.1 Дата начала и дата окончания проверки\nДата начала\n28.10.2019\nДата окончания\n26.11.2019\n6.2 Основание проведения проверки\nПриказ Президента НАУФОР\n6.3 Предмет проверки\nПроверка соблюдения базового стандарта совершения брокером операций на финансовом рынке по вопросам условий и порядка использования денежных средств и ценных бумаг клиентов в интересах брокера; базового стандарта совершения управляющим операций на финансовом рынке по вопросам условий и порядка определения инвестиционного профиля клиента; базового стандарта совершения депозитарием операций на финансовом рынке по вопросам процедур, связанных с отражением депозитарных операций в системе учета \n6.4 Результат проверки (нарушения, выявленные в ходе проведенной проверки (при наличии)\nНарушений не выявлено', 'Проверок СРО не было', '6.1 Дата начала и дата окончания проверки\nДата начала\n29.04.2019\nДата окончания\n28.05.2019\n6.2 Основание проведения проверки\nПриказ Президента НАУФОР\n6.3 Предмет проверки\nСоблюдение внутреннего стандарта НАУФОР порядка определения стоимости чистых активов паевого инвестиционного фонда и стоимости инвестиционного пая\n6.4 Результат проверки (нарушения, выявленные в ходе проведенной проверки (при наличии)\nНарушений не выявлено', 'Компании нет в списках членов СРО']}
# save_file_xlsx(temp, 'temp.xlsx')
