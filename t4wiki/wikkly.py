import time
from io import StringIO

from tinymarkup.context import Context
from wikklytext.macro import ( WikklyMacro as Macro, WikklySource,
                               MacroLibrary, LanguageMacro, ClassMacro, )
from tinymarkup.writer import HTMLWriter
from wikklytext.to_html import HTMLCompiler, to_html, to_inline_html

from ll.xist import xsc
from ll.xist.ns import html

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

class NamedLanguageMacro(Macro):
    name = "lang"

    def tag_params(self, lang):
        return { "lang": lang }

class toc(Macro):
    environments = { "block" }

    def html_element(self):
        return "<!--INHALT-->"

class subdued(ClassMacro):
    pass

class small(ClassMacro):
    pass

class red(ClassMacro):
    pass

class footnote(ClassMacro):
    pass

class box(ClassMacro):
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
    def html_element(self, value):
        return f"<code>transcode this: {value}</code>"

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
            return html.figure(
                html.img(src=filename,
                         class_="rounded preview-image preview-1800"),
                html.figcaption(info, class_="figure-caption"),
                class_="figure t4wiki-figure")
        else:
            return html.img(src=filename,
                            class_="rounded preview-image preview-1800")

class BildRechts(Macro):
    name = "bildrechts"

    def html_element(self, filename, info=""):
        return html.img(src=filename,
                        title=info,
                        class_="rounded float-end preview-image preview-300")

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
        return '<div><b>DOWNLOADS</b></div>'

class poem(Macro):
    environments = { "block" }
    def html_element(self, poem):
        return '<pre>{poeam}</pre>'


macro_library = MacroLibrary()
macro_library.register_module(globals())

class Context(Context):
    def __init__(self):
        super().__init__(macro_library)
