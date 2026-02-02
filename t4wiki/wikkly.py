import time
from io import StringIO

from wikklytext.macro import ( WikklyMacro as Macro, WikklySource,
                               MacroLibrary, LanguageMacro, ClassMacro, )
from tinymarkup.writer import HTMLWriter
from tinymarkup.exceptions import MacroError
from wikklytext.to_html import HTMLCompiler, to_html, to_inline_html

from ll.xist import xsc
from ll.xist.ns import html

import transbeta

from .macrotools import block_level_figure, float_right_image

class German(LanguageMacro):
    name = "de"

class English(LanguageMacro):
    name = "en"

class Latin(LanguageMacro):
    name = "la"

class Greek(LanguageMacro):
    name = "gr"

class Spanish(LanguageMacro):
    name = "es"

class French(LanguageMacro):
    name = "fr"

class NamedLanguageMacro(Macro):
    name = "lang"

    def tag_params(self, lang):
        return { "lang": lang }

class toc(Macro):
    environments = { "block" }

    def html_element(self):
        return '<div class="t4wiki-toc"></div>'

class subdued(ClassMacro):
    pass

class small(ClassMacro):
    pass

class red(ClassMacro):
    pass

class footnote(ClassMacro):
    pass

class box(ClassMacro):
    def html_element(self, contents:WikklySource, class_:str|None=None):
        name = self.get_name()
        if class_:
            class_ = class_.strip()
            kw = {"class_": f"{name} {name}-{class_}"}
        else:
            kw = {}
        return self.start_tag(**kw) + contents.html() + self.end_tag

class sidebox(box):
    pass

class noinclude(ClassMacro):
    pass

class include(Macro):
    environments = { "block" }

    def html_element(self, document_title, writer:HTMLWriter):
        self.context.article_includes.add(document_title)
        writer.open("div",
                    class_="t4wiki-include",
                    data_article_title=document_title)
        writer.close("div")

class flashcard(Macro):
    environments = { "block" }

    def html_element(self, titel, inhalt):
        return ""

class bselk(Macro):
    environments = { "inline" }

    def html_element(self, value):
        return f"BSELK {value}"

class hebrew(Macro):
    environments = { "block", "inline", }

    def html_element(self, source, writer:HTMLWriter):
        if self.environment == "block":
            tag = "p"
        else:
            tag = "span"

        writer.open(tag, lang="he")
        writer.print(transbeta.cjhebrew_to_unicode(source))
        writer.close(tag)


class blockquote(Macro):
    environments = { "block" }
    def html_element(self, contents:WikklySource):
        return f'<blockquote>{contents}</blockquote>'

class anchor(Macro):
    def html_element(self, name):
        return f'<a name="{name}"></a>'

class Bild(Macro):
    name = "bild"

    def html_element(self, filename, info=""):
        if self.environment == "block":
            return block_level_figure(filename, info)
        else:
            return float_right_image(filename)

class BildRechts(Macro):
    name = "bildrechts"

    def html_element(self, filename, info=""):
        return float_right_image(filename, info)

class HTMLMacro(Macro):
    name = "html"
    environment = { "block" }

    def html_element(self, html:str):
        # tidy me??
        return html

class striped(ClassMacro):
    def tag_params(self):
        return { "class": "table table-striped" }

class bibtex(Macro):
    environments = { "block" }

    def html_element(self, contents):
        return '<pre>' + contents + '</pre>'

class clear(Macro):
    environments = { "block" }

    def html_element(self):
        return '<div style="clear:both"></div>'

class downloads(Macro):
    environments = { "block" }
    def html_element(self):
        if getattr(self.context, "downloads_macro_used", False):
            raise MacroError("The <<downloads>> macro may only be used once "
                             "per article.")
        self.context.downloads_macro_used = True
        return '<div class="t4wiki-downloads"></div>'

class poem(Macro):
    environments = { "block" }
    def html_element(self, poem):
        poem = poem.strip()
        return f'<div class="poem">{poem}</div>'


macro_library = MacroLibrary()
macro_library.register_module(globals())
