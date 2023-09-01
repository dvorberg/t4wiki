class WikiException(Exception):
    pass

class TitleUnavailable(WikiException):
    def __init__(self, message, existing_titles):
        super().__init__(message)
        self.existing_titles = existing_titles
