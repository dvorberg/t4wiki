import io, re
from typing import NamedTuple, List

from t4 import sql
from t4.typography import normalize_whitespace

from tinymarkup.language import Language
from tinymarkup.compiler import CompilerDuplexer

from . import model
from .exceptions import TitleUnavailable
from .context import Context, get_languages
from .db import insert_from_dict, execute, query_one

title_re = re.compile(r"(?:([a-z]{2,3}):)?(.*?)\s*(?:\((.*)\))?$")
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
        lang, title, namespace = match.groups()

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

    def __eq__(self, other):
        def low(s):
            if s is None:
                return ""
            else:
                return s.lower()

        return ( self.lang == other.lang
                 and self.title.lower() == other.title.lower()
                 and low(self.namespace) == low(other.namespace))

def normalize_title(title, ignore_namespace=False):
    return parse_title(title, ignore_namespace).normalized()


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
        case _:
            raise NotImplementedError(source_format)


class CompiledArticle(NamedTuple):
    current_html: str
    current_tsearch: str
    article_links: List[str]
    article_includes: List[str]
    macro_info: dict

def compile_article(titles, source, format, root_language, user_info):
    """
    Returns a CompiledArticle named tuple created from the input
    or raises a tinymarkup.exceptions.MarkupError.
    """
    Parser, HTMLCompiler, TSearchCompiler, macro_library = tools_by_format(
        format)

    context = Context(macro_library, user_info)
    context.root_language = root_language

    html_out = io.StringIO()
    tsearch_out = io.StringIO()

    html_compiler = HTMLCompiler(context, html_out)
    tsearch_compiler = TSearchCompiler(context, tsearch_out)

    # Initialize the tsearch output by adding the titles
    # weightes "A".
    for title in titles:
        lang, title, namespace = Title.parse(title, ignore_namespace=True)
        tsearch_compiler.writer.write(title, lang or root_language, "A")

    duplexer = CompilerDuplexer(html_compiler, tsearch_compiler)
    duplexer.duplex(Parser(), source)

    return CompiledArticle(  html_out.getvalue(),
                             tsearch_out.getvalue(),
                             context.article_links,
                             context.article_includes,
                             context.macro_info, )

def update_titles_for(id, titles, root_language):
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



def store_article(id, titles, ignore_namespace,
                  root_language, source, format, uuid=None):
    """
    INSERT or UPDATE an article in the database and all the
    depending tables.
    """
    if len(titles) < 1:
        raise ValueError("Article must have at least one title.")

    titles = [ Title.parse(title, ignore_namespace) for title in titles ]

    # Verify that no other articles claim any of the titles we want to
    # use.
    result = article_ids_by_titles(titles)
    foreign = []
    for article_title in result:
        if id is None or article_title.article_id != id:
            foreign.append(article_title)

    if len(foreign) > 0:
        raise TitleUnavailable("An article with that title or alias "
                               "already exists.", foreign)

    if id is None:
        user_info = {}
    else:
        user_info = get_user_info(id)

    html, tsearch, links, includes, macro_info = compile_article(
        titles, source, format, root_language, user_info)

    article = { "ignore_namespace": ignore_namespace,
                "root_language": root_language.iso,
                "source": source,
                "format": format,
                "current_html": html,
                "macro_info": sql.json_literal(macro_info),
                "tsvector": sql.expression(tsearch) }

    # Article contents
    if id is None:
        if uuid is not None:
            article["uuid"] = uuid

        id = insert_from_dict("wiki.article", article)
    else:
        execute(sql.update("wiki.article",
                           sql.where("id = ", int(id)),
                           article))

    # Titles
    update_titles_for(id, titles, root_language)

    # Links
    execute("DELETE FROM wiki.article_link WHERE article_id = %i" % id)
    for link in links:
        insert_from_dict( "wiki.article_link",
                          { "article_id": id, "target_title": link },
                          retrieve_id=False)

    # Includes
    execute("DELETE FROM wiki.article_include WHERE article_id = %i" % id)
    for include in includes:
        insert_from_dict( "wiki.article_include",
                          { "article_id": id, "wants_to_include": include },
                          retrieve_id=False)


    return id

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
