import werkzeug

from tinymarkup.context import Context
from tinymarkup.macro import MacroLibrary
from tinymarkup.language import Languages

from ll.xist.ns import html

from .utils import citextset, get_languages

class Context(Context):
    def __init__(self, macro_library=MacroLibrary(), user_info=None):
        try:
            languages = get_languages()
        except RuntimeError: # Raised by Werkzeug if outside app context.
            languages = Languages()

        super().__init__(macro_library, languages)
        self.user_info = user_info
        self.article_links = citextset()
        self.article_includes = citextset()
        self.macro_info = {}

    def html_link_element(self, target, text):
        # Remove the anchor when adding the linked document
        # to the internal list.
        document_name = target.split("#", 1)[0]
        self.article_links.add(document_name)

        return html.a(text, href=document_name, class_="t4wiki-link")
