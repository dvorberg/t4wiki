import re
from io import StringIO

from ll.xist import xsc, parse, xfind
from ll.xist.ns import html

from tinymarkup.language import Language
from tinymarkup.writer import TSearchWriter
from tinymarkup.exceptions import UnknownLanguage

from .utils import get_languages

def dom_tree(source):
    return parse.tree( parse.String(source.encode("utf-8")),
                       parse.Tidy(encoding="utf-8"),
                       parse.NS(html),
                       parse.Node(pool=xsc.Pool(html)) )

def body_contents(dom_tree) -> xsc.Frag:
    result = dom_tree.walknodes(html.body)
    body = next(result)

    ret = xsc.Frag()
    for child in body:
        ret.append(child)
    return ret


weights = {}
for weight, clss in ( ("B", ( html.h1, html.h2, )),
                      ("C", ( html.h3, html.h4, html.h5, html.h6,
                              html.caption, html.th,
                              html.b, html.strong, html.em, ), ) ):
    for cls in clss:
        weights[cls] = weight

def weight(element):
    return weights.get(element.__class__, "D")

word_re = re.compile("\w+")

def tsearch(dom_tree:xsc.Frag, root_language) -> str:
    languages = get_languages()
    output = StringIO()
    writer = TSearchWriter(output, root_language)

    def walk(node):
        if isinstance(node, xsc.Text):
            for word in word_re.findall(node.string()):
                writer.word(word)

        elif isinstance(node, xsc.Element):
            lang = str(node.attrs.get("lang"))
            if lang:
                try:
                    language = languages.by_iso(lang)
                except UnknownLanguage:
                    language = Language(lang, "simple")

                writer.push_language(language)

            writer.push_weight(weight(node))

            for child in node:
                walk(child)

            writer.pop_weight()
            if lang: writer.pop_language()

            if isinstance(node, html.p):
                writer.tsvector_break()

        elif isinstance(node, xsc.Frag):
            for child in node:
                walk(child)

    walk(dom_tree)
    writer.end_document()

    return output.getvalue()

absolute_link_re = re.compile(r"^([a-zA-Z0-9]+:|/)", re.IGNORECASE)
def wiki_links(dom_tree:xsc.Frag) -> list[str]:
    for a in dom_tree.walknodes(html.a):
        href = str(a.attrs.href)
        if not absolute_link_re.match(href):
            yield href
