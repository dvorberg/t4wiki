from tinywikitext.macro import RAWMacro, TagMacro, LinkMacro, MacroLibrary
from tinymarkup.utils import html_start_tag

from .macrotools import block_level_figure, float_right_image

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
        if "thumb" in params:
            params = list(params)
            params.remove("thumb")
            description = " ".join(params)
            return float_right_image(source, description)
        else:
            description = " ".join(params)
            return block_level_figure(source, description)

image = Bild
Image = Bild

class Kategorie(LinkMacro):
    def html(self, source, *params):
        return None

class Category(Kategorie):
    pass

from tinywikitext.macro import macro_library
macro_library.register_module(globals(), True)
