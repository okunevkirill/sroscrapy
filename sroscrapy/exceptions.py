"""
Custom exceptions raised by <sroscrapy>
"""


class SroScraperError(Exception):
    def __init__(self, *args):
        self.msg = args[0] if args else None

    def __str__(self):
        if self.msg:
            return f"[!] :: {self.__class__.__name__} encountered - {self.msg}"
        else:
            return f"[!] :: {self.__class__.__name__} encountered - Check parsing logic and package logic"


class FileDataError(SroScraperError):
    def __str__(self):
        if self.msg is None:
            self.msg = "Check the path to the file and headers in it"
        return super().__str__()


class URLError(SroScraperError):
    def __str__(self):
        if self.msg is None:
            self.msg = "Check the site is working or the path is correct"
        return super().__str__()


if __name__ == "__main__":
    raise SroScraperError
