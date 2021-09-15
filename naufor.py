"""Модуль парсинга профучастников СРО НАУФОР
   - https://www.naufor.ru/
"""
__author__ = "ok_kir"
__version__ = "0.00.1"

# ================================================================================
import requests
from bs4 import BeautifulSoup

# --------------------------------------------------------------------------------
# Глобальные переменные
MAIN_URL = 'https://www.naufor.ru/'
# ToDO - можно в дальнейшем получать данный адрес с основной страницы (могут изменить)
GL_URL = MAIN_URL + 'tree.asp?n=13092'  # Адрес основной страницы парсинга
# ToDo - реализовать загрузку предприятий из файла
ENTERPRISES = {'датабанк ао', 'сургутгазстрой ук ооо', 'стоунхедж ук ооо'}  # Список отслеживаемых компаний


# --------------------------------------------------------------------------------
def get_html(url: str):
    """Получение содержимого страницы по указанному url

    :param url: Адрес страницы для парсинга.
    :return: Если информация с сайта была получена возвращается строка.
             Иначе возвращается None
    """

    r = requests.get(url)
    # Проверяем корректность запроса (Если код == 200 информация получена)
    if r.status_code == 200:
        # Конвертируем полученные данные в строку с кодировкой указанной на сайте или utf-8
        return r.text
    return None


def get_all_company(html):
    """Получение списка всех компаний профучастников СРО.

    :param html: Конвертированный html код.
    :return: Возвращается словарь всех компаний профучастников СРО с адресами на результат проверки.
    """
    soup = BeautifulSoup(html, 'lxml')
    # Пользуюсь тем что на html странице перечень компаний реализован
    # в виде ссылок <a> с классом <link-ajax>
    links = soup.find_all('a', class_='link-ajax')
    company = {}
    for link in links:
        name = link.get_text().strip()
        href = MAIN_URL + link.get('href').strip()
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
    info = res_text[index_begin: index_end].replace('\n\n\n', '\n')
    return info


def check_enterprises(company):
    """Сортировка компаний и отсев не указанных для отслеживания

    :param company: Словарь всех компаний профучастников СРО
    :return: словарь с именем компании в качестве ключа, значения - адрес
    """
    member_company = {}
    # ToDo - Можно использовать бинарный поиск - т.к. на сайте идёт упорядочивание по алфавиту
    for firm in ENTERPRISES:
        for item in company:
            if item.lower() == firm.lower():  # if item.find(firm) != -1: # Альтернативный поиск
                member_company[item] = company[item]
    return member_company


# --------------------------------------------------------------------------------
print('[!] Начало работы скрипта', '=' * 50, sep='\n')
gl_soup = get_html(GL_URL)
if gl_soup is not None:
    result = {}
    gl_company = get_all_company(gl_soup)
    gl_member = check_enterprises(gl_company)
    for gl_name in gl_member.keys():
        gl_url = gl_member.get(gl_name)
        gl_html = get_html(gl_url)
        if gl_html is not None:
            gl_info = get_verification_data(gl_html)
            result[gl_name] = {
                'href': gl_url,
                'info': gl_info
            }
    print(*result.items(), sep='\n')
else:
    print('[!] Проверти доступа к сайту или корректность адреса в скрипте')

print('-' * 50)
print('[!] Окончание работы скрипта', '=' * 50, sep='\n')
