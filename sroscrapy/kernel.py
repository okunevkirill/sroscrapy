# -*- coding: utf-8 -*-
"""
Basic entities for <sroscrapy>
"""
import csv

import requests
from bs4 import BeautifulSoup
import xlsxwriter

from sroscrapy.exceptions import *


# --------------------------------------------------------------
class Company:
    def __init__(self, name: str, date: str, href: str = None, info: str = None, date_changed: bool = False):
        self.name = name
        self.date = date
        self.href = href
        self.info = info
        self.change_date = date_changed

    def __repr__(self):
        return f"<class: '{self.__class__.__name__}'> Name: '{self.name}. Date: '{self.date}'"

    def is_name_matches(self, name: str):
        return self.name.lower() == name.lower().strip()

    def is_date_matches(self, date):
        return self.date == date.strip().replace(',', '.')


# --------------------------------------------------------------
class FileData:
    MSG_NO_COMPANY = "Компании нет в списках членов СРО"
    MSG_NO_URL = "Не удалось обновить информацию - проверьте адрес"
    MSG_NO_CHECKS_SRO = "Проверок СРО не было"
    _encoding = "cp1251"
    _table_headers = ('Компания', 'Информация о проверках', "Дата последней проверки", 'Адрес источника')

    def __init__(self, raw_data_path: str, path_to_the_result: str):
        self.raw_data_path = raw_data_path if raw_data_path else "companies.csv"
        self.path_to_the_result = path_to_the_result if path_to_the_result else "scraping_result.xlsx"

    def get_data_from_csv(self, delimiter=";"):
        """
        Возвращает список компаний требующих анализа
        """
        companies = []
        try:
            with open(self.raw_data_path, 'r', encoding=self._encoding) as csv_file:
                reader = csv.DictReader(csv_file, delimiter=delimiter)
                for line in reader:
                    name = line[self._table_headers[0]].strip()
                    date = line[self._table_headers[2]].strip()
                    companies.append(Company(name=name, date=date))
        except (FileNotFoundError, KeyError):
            raise FileDataError
        if not companies:
            raise FileDataError
        return companies

    def save_dataframe_xlsx(self, companies, worksheet_name: str = 'Лист1'):
        workbook = xlsxwriter.Workbook(self.path_to_the_result)
        worksheet = workbook.add_worksheet(worksheet_name)
        # ----------------------------------------
        # Adding formatting for xlsx
        worksheet.set_default_row(40)  # Height of lines
        heading_format = workbook.add_format(
            {'bold': True, 'font_color': 'black', 'font_size': '14', 'valign': 'vcenter',
             'align': 'center', 'text_wrap': 'True', 'border': 2}
        )
        default_format = workbook.add_format({'align': 'left', 'valign': 'vcenter', 'text_wrap': 'True', 'border': 1})
        marker_format_red = workbook.add_format(
            {"bg_color": '#ef8959', 'align': 'left', 'valign': 'vcenter', 'border': 1})
        marker_format_green = workbook.add_format(
            {"bg_color": '#57bf45', 'align': 'left', 'valign': 'vcenter', 'border': 1})
        # ----------------------------------------
        # Forming headers
        worksheet.write('A1', self._table_headers[0], heading_format)
        worksheet.write('B1', self._table_headers[1], heading_format)
        worksheet.write('C1', self._table_headers[2], heading_format)
        worksheet.write('D1', self._table_headers[3], heading_format)
        # ----------------------------------------
        # Column width
        worksheet.set_column('A:A', 20)
        worksheet.set_column('A:B', 30)
        worksheet.set_column('C:C', 20)
        worksheet.set_column('D:D', 45)
        # ----------------------------------------
        row, col = 1, 0
        for company in companies:
            name = company.name
            date = company.date
            href = company.href
            info = company.info

            worksheet.write(row, col, name, default_format)
            if info in (self.MSG_NO_COMPANY, self.MSG_NO_URL):
                worksheet.write(row, col + 1, info, marker_format_red)
            elif info == self.MSG_NO_CHECKS_SRO:
                worksheet.write(row, col + 1, info, marker_format_green)
            else:
                worksheet.write(row, col + 1, info, default_format)

            if company.change_date:
                worksheet.write(row, col + 2, date, marker_format_red)
            else:
                worksheet.write(row, col + 2, date, default_format)
            worksheet.write(row, col + 3, href, default_format)
            row += 1
        workbook.close()


# --------------------------------------------------------------
class Scrapper:
    _http_headers = {
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:92.0) Gecko/20100101 Firefox/92.0",
        "Accept": "*/*"
    }
    _response_time = 4
    _html_parser = "lxml"
    _number_of_processes = 42

    def get_soup_page(self, url: str, params=None):
        """
        Получение древа объектов типа soup
        :param url: Адрес страницы для парсинга
        :param params: Дополнительные параметры при работе со скроллингом
        :return: {bs.BeautifulSoup} Древо объектов типа soup
        """
        try:
            req = requests.get(url, headers=self._http_headers, params=params, timeout=self._response_time)
        except requests.RequestException:
            return None
        if req.status_code != 200:
            return None
        return BeautifulSoup(req.text, self._html_parser)

    def run(self):
        raise NotImplementedError(f"Define a run method in the {self.__class__.__name__}")


# --------------------------------------------------------------
class Website:
    def __init__(self, name: str, url: str, url_search: str = None):
        self.name = name
        self.url = url
        self.url_search = url_search

    def __str__(self):
        return f"<class: '{self.__class__.__name__}'>\nName for the site: '{self.name}'\n" \
               f"URL: '{self.url}'\nSearch URL: '{self.url_search}'"

    @staticmethod
    def get_absolute_url(host_url, source):
        return source if source.startswith("https://") else f"{host_url}{source}"


# --------------------------------------------------------------
if __name__ == "__main__":
    temp_1 = Scrapper()
    temp_1.run()
