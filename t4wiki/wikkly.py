import time
from io import StringIO

from tinymarkup.context import Context
from tinymarkup.macro import MacroLibrary
from wikklytext.macro import ( WikklyMacro as Macro, WikklySource,
                               LanguageMacro, ClassMacro, )
from wikklytext.to_html import HTMLCompiler, to_html, to_inline_html

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

    def html_element(self, document_title):
        return '<p><b style="color:red">INCLUDE: {document_title}</b></p>'

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

    def html_element(self, filename):
        if self.environment == "block":
            return f'<figure><img src="{filename}" /></figure>'
        else:
            return f'<img src="{filename}" />'

class BildRechts(Macro):
    name = "bildrechts"

    def html_element(self, filename):
        return f'<img src="{filename}" />'

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
