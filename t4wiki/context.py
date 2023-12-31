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
        # Remove the anchor when adding the linked document
        # to the internal list.
        document_name = target.split("#", 1)[0]
        self.article_links.add(document_name)

        return super().html_link_element(target, text)
