from tinywikitext.macro import RAWMacro, TagMacro, LinkMacro, MacroLibrary
from tinymarkup.utils import html_start_tag

class bibtex(RAWMacro):
    environments = { "block" }

    def html(self, source, **params):
        return f'<pre>\n{repr(params)}\n\n{source.strip()}</pre>'

class pre(RAWMacro):
    environments = { "block" }

    def html(self, source, **params):
        return f'<pre>{source.strip()}</pre>'

class poem(RAWMacro):
    environments = { "block" }

    def html(self, source, **params):
        return f'<pre>\n{repr(params)}\n\n{source.strip()}</pre>'

class DPL(RAWMacro):
    environments = { "block" }

    def html(self, source, **params):
        """
        I don’t even know whats this does.
        """
        return None

class gallery(RAWMacro):
    environments = { "block" }

    def html(self, source, **params):
        return None

class ref(TagMacro):
    environments = { "inline" }

    def start_tag(self, *args, **kw):
        return html_start_tag("span", class_="subdued") + "("

    def end_tag(self):
        return ")</span>"

class Bild(LinkMacro):
    def html(self, source, *params):
        return f'<pre>Bild:{repr(source)} + {repr(params)}</pre>\n'

class Image(Bild):
    pass

class image(Bild):
    pass

class Kategorie(LinkMacro):
    def html(self, source, *params):
        return None

class Category(Kategorie):
    pass

from tinywikitext.macro import macro_library
macro_library.register_module(globals(), True)
