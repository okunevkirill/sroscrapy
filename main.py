from sroscrapy import naufor
from sroscrapy.testing import timer


@timer
def start_naufor():
    scraper = naufor.NauforScrapper()
    scraper.run()


if __name__ == '__main__':
    start_naufor()
