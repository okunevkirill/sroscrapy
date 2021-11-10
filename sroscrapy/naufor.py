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

    def _set_website_url_search(self):
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
        info, date = "", ""
        is_needed_info, is_date = False, False
        for inner_html in soup.find_all(["th", "td"]):
            text = inner_html.get_text().strip()
            if is_date:  # На данной итерации формируется дата окончания последней проверки (может перезаписываться)
                date = text
                is_date = False
            if text.startswith("* * *"):
                continue
            elif text.startswith(self.END_PHRASE):  # Вся необходимая информация получена
                break
            if is_needed_info:
                info += text + "\n"
                if self.DATE_PHRASE in text:  # На следующей итерации формируется дата окончания проверки
                    is_date = True
            if text.startswith(self.START_PHRASE):  # Со следующей итерации будет необходимая информация
                is_needed_info = True
        if not info.strip():
            info = self._file_data.MSG_NO_CHECKS_SRO
        return info, date

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

    def _get_content_about_company(self, url):
        """
        Получение информации о компании
        """
        if url is None:
            return self._file_data.MSG_NO_COMPANY, ""
        soup = self.get_soup_page(url)
        if soup is None:
            return self._file_data.MSG_NO_URL, ""
        else:
            info, date = self._get_verification_data(soup)
            return info, date

    def _get_companies_info(self, companies):
        links = [item.href for item in companies]
        with Pool(self._number_of_processes) as prc:
            companies_info = prc.map(self._get_content_about_company, links)
        return companies_info

    def _start_parsing(self):
        """
        Парсинг основной страницы поиска
        """
        # Получение списка отслеживаемых компаний
        companies = self._file_data.get_data_from_csv()
        self._set_website_url_search()
        print(self._website)
        print("-" * 42)
        # --------------------
        # Получение всех участников СРО с адресами доп страниц
        soup = self.get_soup_page(self._website.url_search)
        if soup is None:
            raise URLError("HTTP status code is not 200")
        else:
            print("[*] :: Response from search URL received")

        participants = self._get_all_participants(soup)
        print("[*] :: The list of all SRO participants has been formed")
        # --------------------
        # Установка href для отслеживаемых компаний
        for name, href in participants.items():
            for company in companies:
                if company.is_name_matches(name):
                    company.href = href
        # --------------------
        # Получение информации о компании и дате проверок
        companies_info = self._get_companies_info(companies)
        for index, company in enumerate(companies):
            info, date = companies_info[index]
            company.info = info
            if not company.is_date_matches(date):
                # Если было дата из файла не соотв. дате на сайте - нужно отразить
                company.change_date = True
            company.date = date
        # --------------------
        # Сохранение файла
        self._file_data.save_dataframe_xlsx(companies=companies, worksheet_name=self._website.name)

    def run(self):
        print("[!] :: Start parsing", "=" * 42, sep="\n")
        try:
            self._start_parsing()
        except SroScraperError as err:
            print(err)
        print("[!] :: End of parsing", "=" * 42, sep="\n")


if __name__ == "__main__":
    import os

    temp = NauforScrapper(raw_data_path=f"..{os.sep}companies.csv",
                          path_to_the_result=f"..{os.sep}scraping_result.xlsx")
    temp.run()
