
from flask import url_for
from t4 import sql

from .utils import get_site_url
from .db import dbobject, query_one, cursor, execute_with_template

class has_title_and_namespace:
    @property
    def full_title(self):
        if hasattr(self, "title"):
            title = self.title
        else:
            title = self.main_title

        if self.namespace:
            return f"{title} ({self.namespace})"
        else:
            return title

class Article(dbobject, has_title_and_namespace):
    __schema__ = "wiki"
    __relation__ = "article"
    __view__ = "article_info"

    @staticmethod
    def id_by_title(title):
        return query_one(sql.select( ("article_id",),
                                     ("wiki.article_title",),
                                     ArticleTitle.title_where(title), ))

    def form_url(self, form):
        return url_for(f"articles.{form}_form") + f"?id={self.id}"

    @property
    def href(self):
        return get_site_url() + "/" + self.full_title

    @property
    def id_where(self):
        return sql.where("article_id = %i" % self.id)

    @property
    def source(self):
        source, = query_one("SELECT source "
                            "  FROM wiki.article WHERE id = %i" % self.id)
        return source

    @property
    def user_info(self):
        source, = query_one("SELECT user_info "
                            "  FROM wiki.article WHERE id = %i" % self.id)
        return source

    @property
    def user_info_source(self):
        source, = query_one("SELECT user_info_source "
                            "  FROM wiki.article WHERE id = %i" % self.id)
        return source

class ArticleForView(Article, has_title_and_namespace):
    __view__ = "article_for_view"

class IncludedArticle(dbobject, has_title_and_namespace):
    # article_id, included_as

    @classmethod
    def query_recursively_for(IncludedArticle, article_id:int):
        cursor = execute_with_template(
            "recursive_include_query.sql", ( article_id, ))
        return [ IncludedArticle(cursor.description, tpl)
                 for tpl in cursor.fetchall() ]

class ResolvedArticleLink(dbobject):
    __view__ = "article_link_resolved"

class ResolvedArticleTeaser(dbobject, has_title_and_namespace):
    __view__ = "article_teaser_on_resolved"

class ArticleTitle(dbobject, has_title_and_namespace):
    __schema__ = "wiki"
    __relation__ = "article_title"

    @staticmethod
    def title_where(title):
        return sql.where("""(\
             CASE WHEN namespace IS NULL THEN title
                  WHEN namespace IS NOT NULL
                             THEN title || ' (' || namespace || ')'
             END)::citext = """, sql.string_literal(title))

    @classmethod
    def select_by_fulltitle(ArticleTitle, title):
        return ArticleTitle.select_one(ArticleTitle.title_where(title))

class ArticleMainTitle(ArticleTitle):
    __view__ = "article_main_title"

class FulltextEntry(dbobject, has_title_and_namespace):
    pass
