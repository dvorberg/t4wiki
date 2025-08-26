import io, re, unicodedata, importlib
from typing import NamedTuple, List

from flask import current_app as app

from t4 import sql
from t4.typography import normalize_whitespace

from tinymarkup.language import Language
from tinymarkup.compiler import CompilerDuplexer
from tinymarkup.writer import TSearchWriter

from . import model
from . import html_markup
from .exceptions import TitleUnavailable
from .context import Context, get_languages
from .db import insert_from_dict, execute, query_one
from .utils import title2path

title_re = re.compile(r"""
  (?:
    (?P<language>[a-z]{2,3}):)?
    (?P<title>.*?)
    \s*
    (?:
          \((?P<namespace>[^\(\),]*)\)
        | \((?P<ptitle>[^\(\),]*),\s* (?P<pnamespace>[^\(,]*)\)
    )?$
    """, re.VERBOSE)
class Title(NamedTuple):
    lang: Language
    title: str
    namespace: str

    @classmethod
    def parse(Title, title, ignore_namespace=False):
        if isinstance(title, Title):
            return title

        title = normalize_whitespace(title)

        match = title_re.match(title)
        d = match.groupdict()
        lang = d["language"]
        title = d["title"]
        namespace = d["namespace"]

        if d["ptitle"]:
            title = "%(title)s (%(ptitle)s)" % d
            namespace = d["pnamespace"]

        if ignore_namespace:
            if namespace:
                title = f"{title} ({namespace})"
            namespace = None

        if lang is not None:
            lang = get_languages().by_iso(lang)

        return Title(lang, title, namespace)

    @classmethod
    def from_db(Title, article_title, ignore_lang=False):
        if ignore_lang:
            lang = None
        else:
            lang = get_languages().by_iso(article_title.language)

        return Title(lang, article_title.title, article_title.namespace)

    def normalized(self):
        ret = []
        if self.lang:
            ret.append(f"{self.lang.iso}:")
        ret.append(self.title)
        if self.namespace:
            ret.append(f" ({self.namespace})")
        return "".join(ret)

    __str__ = normalized

    def __repr__(self):
        return f"{self.__class__.__name__}<{str(self)}>"

    @property
    def full_title(self):
        if self.namespace:
            return f"{self.title} ({self.namespace})"
        else:
            return self.title

    @property
    def path(self):
        return title2path(self.full_title)

    def __eq__(self, other):
        def low(s):
            if s is None:
                return ""
            else:
                return s.lower()

        return ( self.lang == other.lang
                 and self.title.lower() == other.title.lower()
                 and low(self.namespace) == low(other.namespace))

    def to_tsvector(self, default_language, weight="A"):
        """
        Return a string containing an SQL expressiong for a tsvector
        to store this title in the database.
        """
        if type(default_language) is str:
            default_language = get_languages().by_iso(default_language)

        output = io.StringIO()
        writer = TSearchWriter(output, self.lang or default_language)
        writer.write(self.title, weight=weight)
        if self.namespace:
            writer.write(self.namespace, weight=weight)
        writer.end_document()

        return output.getvalue()

def normalize_title(title, ignore_namespace=False):
    return parse_title(title, ignore_namespace).normalized()

def normalize_source(source):
    source = source.replace("\r", "")
    return unicodedata.normalize("NFC", source)

def format_by_suffix(suffix):
    if suffix.startswith("."):
        suffix = suffix[1:]

    return { "mwiki": "wikitext",
             "wikkly": "wikkly" }[suffix]

def tools_by_format(source_format):
    """
    Return a tuple as ( parser class, compiler class, ) that will turn
    “source format” into “target format”.
    """
    match source_format:
        case "wikkly":
            from wikklytext.parser import WikklyParser as Parser
            from wikklytext.to_tsearch import TSearchCompiler
            from wikklytext.to_html import HTMLCompiler

            from .wikkly import macro_library

            return Parser, HTMLCompiler, TSearchCompiler, macro_library
        case "wikitext":
            from tinywikitext.parser import WikiTextParser as Parser
            from tinywikitext.to_tsearch import TSearchCompiler
            from tinywikitext.to_html import HTMLCompiler

            from .wikitext import macro_library

            return Parser, HTMLCompiler, TSearchCompiler, macro_library
        case "html":
            # articles_blueprint.title_form calls us to check if the format
            # string is valid. markup.compile_article() will re-route html
            # to extract_article_from_html() rather than using these None
            # values.
            return None, None, None, None
        case _:
            raise NotImplementedError(source_format)


class CompiledArticle(NamedTuple):
    current_html: str
    current_tsearch: str
    article_links: List[str]
    article_includes: List[str]
    macro_info: dict

def compile_article(source, format,
                    root_language, user_info) -> CompiledArticle:
    """
    Since for HTML the input language and one of the target languages
    are identical, it is treated specially below.
    """
    if format == "html":
        return extract_article_from_html(
            source, format, root_language, user_info)
    else:
        return compile_article_from_markup(
            source, format, root_language, user_info)

def compile_article_from_markup(source, format,
                                root_language, user_info) -> CompiledArticle:
    """
    Returns a CompiledArticle named tuple created from the input
    or raises a tinymarkup.exceptions.MarkupError.
    """
    Parser, HTMLCompiler, TSearchCompiler, macro_library = tools_by_format(
        format)

    context_class_name = app.config.get("T4WIKI_CONTEXT_CLASS", None)
    if context_class_name is not None:
        module_name, class_name = context_class_name.rsplit(".", 1)
        module = importlib.import_module(module_name)
        Context = getattr(module, class_name)

    context = Context(macro_library, user_info)
    context.root_language = root_language

    html_out = io.StringIO()
    tsearch_out = io.StringIO()

    html_compiler = HTMLCompiler(context, html_out)
    tsearch_compiler = TSearchCompiler(context, tsearch_out)

    duplexer = CompilerDuplexer(html_compiler, tsearch_compiler)
    duplexer.duplex(Parser(), source)

    tsearch = tsearch_out.getvalue()

    if not tsearch:
        # We can’t have a NULL value here.
        tsearch = "to_tsvector('simple', '')"

    return CompiledArticle(  html_out.getvalue(),
                             tsearch,
                             context.article_links,
                             context.article_includes,
                             context.macro_info, )

def extract_article_from_html(source, format,
                              root_language, user_info) -> CompiledArticle:
    """
    Input HTML is tidied and the contents of the <body>-tag are returned.
    """
    doc = html_markup.dom_tree(source)
    body = html_markup.body_contents(doc)

    return CompiledArticle(body.string(), # html
                           html_markup.tsearch(body, root_language), # tsearch
                           list(html_markup.wiki_links(body)), # links
                           [], # includes
                           {}) # macro_info



def update_titles_for(id, titles, root_language):
    tsvectors = []
    execute("DELETE FROM wiki.article_title WHERE article_id = %i" % id)
    for index, title in enumerate(titles):
        insert_from_dict( "wiki.article_title",
                          {
                              "article_id": id,
                              "title": title.title,
                              "namespace": title.namespace,
                              "language": (title.lang or root_language).iso,
                              "is_main_title": bool(index == 0)
                          }, retrieve_id=False)
        tsvectors.append(title.to_tsvector(root_language))

    tsvector = "||".join(tsvectors)
    model.Article.update_db(id, titles_tsvector=sql.expression(tsvector))

def update_links_for(id, links):
    execute("DELETE FROM wiki.article_link WHERE article_id = %i" % id)
    for link in links:
        insert_from_dict( "wiki.article_link",
                          { "article_id": id, "target_title": link },
                          retrieve_id=False)

def update_includes_for(id, includes):
    execute("DELETE FROM wiki.article_include WHERE article_id = %i" % id)
    for include in includes:
        insert_from_dict( "wiki.article_include",
                          { "article_id": id, "wants_to_include": include },
                          retrieve_id=False)

def get_user_info(id):
    info, = query_one("SELECT user_info FROM wiki.article "
                      " WHERE id = %s", ( int(id), ))
    return info

def article_ids_by_titles(titles):
    """
    Return model.ArticleTitle objects matching the “titles”.
    """
    titles = [ Title.parse(title) for title in titles ]

    def where_for(title):
        where = sql.where("title = ", sql.string_literal(title.title))
        if title.namespace:
            where = where.and_(sql.where("namespace =",
                                         sql.string_literal(title.namespace)))
        return where

    where = sql.where.or_(*[where_for(title) for title in titles])

    return model.ArticleTitle.select(where)
