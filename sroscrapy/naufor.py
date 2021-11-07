from multiprocessing import Pool

from sroscrapy.exceptions import *
from sroscrapy.kernel import Scrapper, Website, FileData


class NauforScrapper(Scrapper):
    START_PHRASE = "6 Сведения"
    END_PHRASE = "7 Сведения"
    DATE_PHRASE = "Дата окончания"

    def __init__(self, raw_data_path: str = None, path_to_the_result: str = None):
        self._website = Website(name="НАУФОР", url="https://www.naufor.ru")
        self._file_data = FileData(raw_data_path=raw_data_path, path_to_the_result=path_to_the_result)

    def set_website_url_search(self):
        """
        Установка основного пути парсинга
        """
        soup = self.get_soup_page(self._website.url)
        try:
            url_search = soup.find('a', string="Реестр членов НАУФОР")['href']
        except AttributeError:
            raise URLError
        self._website.url_search = self._website.get_absolute_url(self._website.url, url_search)

    def _get_verification_data(self, soup):
        result = ''
        flag_info = False
        date = ''
        for string in soup.find_all('tr'):
            info = string.get_text()
            if flag_info and self.END_PHRASE in info:
                break

            if not info.strip():
                info = "Проверок СРО не было"
            if flag_info:
                result += info.replace('* * *', '').replace('\n\n\n', '')
                if self.DATE_PHRASE in info:
                    date = info.replace(self.DATE_PHRASE, '').strip()

            if self.START_PHRASE in info:
                flag_info = True
        return result, date

    def _get_all_participants(self, soup):
        """
        Получение списка всех участников СРО
        """
        links = soup.find_all('a', class_='link-ajax')
        participants = {}
        for link in links:
            name = link.get_text(strip=True)
            href = self._website.get_absolute_url(self._website.url, link.get('href').strip())
            participants[name] = href
        if not participants:
            raise URLError
        return participants

    def _parsing_child(self, url):
        """
        Парсинг дочерних страниц с информацией и датой
        """
        if url is None:
            return "Компании нет в списках членов СРО", ""
        soup = self.get_soup_page(url)
        if soup is None:
            return "Не удалось обновить информацию - проверьте адрес", ""
        else:
            content, date = self._get_verification_data(soup)
            return content, date

    def _set_company_info(self, companies):
        links = [item.href for item in companies]
        with Pool(self._number_of_processes) as prc:
            content = prc.map(self._parsing_child, links)
        for idx, company in enumerate(companies):
            info, date = content[idx]
            company.info = info
            if company.is_date_matches(date):
                company.change_date = True
            company.date = date

    def start_parsing(self):
        """
        Парсинг основной страницы поиска
        """
        # Получение списка отслеживаемых компаний
        companies = self._file_data.get_data_from_csv()
        self.set_website_url_search()
        print(self._website)
        # --------------------
        # Получение всех участников СРО с адресами доп страниц
        soup = self.get_soup_page(self._website.url_search)
        if soup is None:
            raise URLError("HTTP status code is not 200")
        else:
            print("[*] :: Response from search URL received")

        participants = self._get_all_participants(soup)
        # --------------------
        # Установка href для отслеживаемых компаний
        for name, href in participants.items():
            for company in companies:
                if company.is_name_matches(name):
                    company.href = href
        # --------------------
        # Изменение на месте информации о компании
        self._set_company_info(companies)
        # --------------------
        self._file_data.save_dataframe_xlsx(companies=companies, worksheet_name=self._website.name)

    def run(self):
        print("[!] - Start parsing", "=" * 42, sep="\n")
        try:
            self.start_parsing()
        except SroScraperError as err:
            print(err)
        print("[!] - End of parsing", "=" * 42, sep="\n")


if __name__ == "__main__":
    import os

    temp = NauforScrapper(raw_data_path=f"..{os.sep}companies.csv",
                          path_to_the_result=f"..{os.sep}scraping_result.xlsx")
    temp.run()
