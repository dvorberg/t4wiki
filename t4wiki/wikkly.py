import time
from io import StringIO

from tinymarkup.context import Context
from tinymarkup.macro import MacroLibrary
from wikklytext.macro import ( WikklyMacro as Macro,
                              ClassMacro, LanguageMacro, )
from wikklytext.to_html import HTMLCompiler, to_html, to_inline_html

# Bootstrap tables need the “table” CSS class and I don’t believe in
# coding bootstrap specifics into my wikkly converter. So it came down to
# this:
old_open = HTMLCompiler.open
def open(self, tag, **params):
    if tag == "table" and not "class" in params:
        params["class"] = "table"
    old_open(self, tag, **params)
HTMLCompiler.open = open


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

    def block_html(self, lang, contents:to_html):
        return f'<div lang="{lang}">{contents}</div>'

    def inline_html(self, lang, contents:to_inline_html):
        return f'<span lang="{lang}">{contents}</span>'


class toc(Macro):
    def block_html(self):
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
    def block_html(self, document_title):
        return '<p><b style="color:red">INCLUDE: {document_title}</b></p>'

class flashcard(Macro):
    def block_html(self, titel, inhalt):
        return ""

class bselk(Macro):
    def inline_html(self, value):
        return "BSELK {value}"

class hebrew(Macro):
    def inline_html(self, value):
        return f"<code>transcode this: {value}</code>"

class blockquote(Macro):
    def block_html(self, contents:to_html):
        return f'<blockquote>{contents}</blockquote>'

class anchor(Macro):
    def inline_html(self, name):
        return f'<a name="{name}"></a>'

    block_html = inline_html

class Bild(Macro):
    name = "bild"

    def block_html(self, filename):
        return f'<figure><img src="{filename}" /></figure>'

class BildRechts(Macro):
    name = "bildrechts"

    def block_html(self, filename):
        return f'<figure><img src="{filename}" /></figure>'

    def inline_html(self, filename):
        return f'<img src="{filename}" />'

class HTMLMacro(Macro):
    name = "html"

    def block_html(self, html:str):
        # tidy me??
        return html

    inline_html = block_html

class striped(ClassMacro):
    def tag_params(self):
        return { "class": "table table-striped" }

class bibtex(Macro):
    def block_html(self, contents):
        return '<pre>' + contents + '</pre>'

class clear(Macro):
    def block_html(self):
        return '<div style="clear:both"></div>'

class downloads(Macro):
    def block_html(self):
        return '<div><b>DOWNLOADS</b></div>'

class poem(Macro):
    def block_html(self, poem):
        return '<pre>{poeam}</pre>'


macro_library = MacroLibrary()
macro_library.register_module(globals())

class Context(Context):
    def __init__(self):
        super().__init__(macro_library)
