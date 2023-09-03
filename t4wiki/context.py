from flask import current_app as app
from tinymarkup.context import Context

from ll.xist.ns import html

from .utils import citextset, get_languages

class Context(Context):
    def __init__(self, macro_library, user_info):
        super().__init__(macro_library, get_languages())
        self.user_info = user_info
        self.article_links = citextset()
        self.article_includes = citextset()
        self.macro_info = {}

    def html_link_element(self, target, text):
        self.article_links.add(target)
        return super().html_link_element(target, text)
