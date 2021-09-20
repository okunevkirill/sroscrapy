"""Модуль парсинга профучастников СРО НАУФОР
   - https://www.naufor.ru/
"""
__author__ = 'ok_kir'
__version__ = '0.00.2'

# ================================================================================
import requests
from bs4 import BeautifulSoup
import csv
# import pandas

# --------------------------------------------------------------------------------
# Константы модуля

HOST = 'https://www.naufor.ru'  # Адрес основной страницы СРО
GL_URL = HOST + r'/tree.asp?n=13092'  # Адрес страницы парсинга [!] ToDO - можно получать его с основной страницы
REQUEST_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:92.0) Gecko/20100101 Firefox/92.0',
    'Accept': '*/*'
}  # Заголовки для эмулирования работы браузера
PATH_FOR_SAVE = r'./members.csv'

ENTERPRISES = {'датабанк ао', 'сургутгазстрой ук ооо', 'стоунхедж ук ооо'}  # Список отслеживаемых компаний


# --------------------------------------------------------------------------------
def get_html(url, params=None):
    """Получение содержимого страницы по указанному url

    :param url: Адрес страницы для парсинга.
    :param params:
    :return: Если информация с сайта была получена возвращается строка.
             Иначе возвращается None
    """

    r = requests.get(url, headers=REQUEST_HEADERS, params=params)
    # Проверяем корректность запроса (Если код == 200 информация получена)
    if r.status_code == 200:
        # Конвертируем полученные данные в строку с кодировкой указанной на сайте или utf-8
        return r.text
    return None


def get_all_company(html, host=HOST):
    """Получение списка всех компаний профучастников СРО.

    :param html: Конвертированный html код.
    :param host:
    :return: Возвращается словарь всех компаний профучастников СРО с адресами на результат проверки.
    """
    soup = BeautifulSoup(html, 'lxml')
    # Пользуюсь тем что на html странице перечень компаний реализован
    # в виде ссылок <a> с классом <link-ajax>
    links = soup.find_all('a', class_='link-ajax')
    company = {}
    for link in links:
        name = link.get_text(strip=True)  # Имя компании участницы СРО
        href = host + link.get('href').strip()  # Адрес страницы с подробной информацией о компании
        temp = link.get('href')
        company[name] = href
    return company


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
    info = res_text[index_begin: index_end].replace('* * *', '').replace('\n\n\n', '\n')

    # Если строка состоит только из символов конца строки - проверок СРО не было
    if len(info) == info.count('\n'):
        info = 'Проверок СРО не было'
    return info


def check_entry_company(company):
    """Сортировка компаний и отсев не указанных для отслеживания

    :param company: Словарь всех компаний профучастников СРО
    :return: словарь с именем компании в качестве ключа, значения - адрес
    """
    members = {}
    # ToDo - Можно использовать бинарный поиск (на сайте идёт упорядочивание по алфавиту).
    # ToDo - Можно сделать параллельный скроллинг (существенно ускорит скрипт)
    for member in ENTERPRISES:
        for firm in company:
            if firm.lower().find(member) != -1:  # if firm.lower() == member.lower() # Более жёсткое условие
                members[firm] = company[firm]
    return members


# --------------------------------------------------------------------------------
def save_file(data, path=PATH_FOR_SAVE):
    """Сохранение файла с результатами проверки

    :param data:
    :param path:
    :return:
    """

    with open(path, 'w', newline='') as csv_file:
        writer = csv.writer(csv_file, delimiter=';')
        writer.writerow(['Компания', 'Информация о проверках', 'Адрес источника'])

        for company in data.keys():
            writer.writerow([company, data[company]['content'], data[company]['href']])


def main_for_parse(url=GL_URL):
    """Основная функция парсинга СРО НАУФОР

    :param url:
    :return:
    """
    soup = get_html(url)
    if soup is not None:
        result = {}
        company = get_all_company(soup)
        members = check_entry_company(company)
        for name in members.keys():
            url = members.get(name)
            html = get_html(url)
            if html is not None:
                content = get_verification_data(html)
                result[name] = {
                    'href': url,
                    'content': content
                }
            else:
                # Ответ от сайта != 200
                result[name] = 'Не удалось обновить информацию - проверьте адрес'
        save_file(result)
        # print(*result.items(), sep='\n')
    else:
        # Ответ от сайта != 200
        print('[!] Проверти доступа к сайту или корректность парсинга в скрипте.')


# --------------------------------------------------------------------------------
print('[*] Начало работы скрипта', '=' * 50, sep='\n')
main_for_parse()
print('[*] Окончание работы скрипта', '=' * 50, sep='\n')
