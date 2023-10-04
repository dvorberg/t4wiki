import os.path as op, functools

from flask import url_for
from t4 import sql

from .utils import get_site_url, title2path
from .db import dbobject, query_one, cursor, execute_with_template, execute

class has_title_and_namespace:
    @property
    def full_title(self):
        if hasattr(self, "_full_title"):
            return self._full_title

        if hasattr(self, "title"):
            title = self.title
        else:
            title = self.main_title

        if self.namespace:
            return f"{title} ({self.namespace})"
        else:
            return title

    @full_title.setter
    def full_title(self, t):
        self._full_title = t

    @property
    def href(self):
        return "/" + title2path(self.full_title)

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
        return f"{get_site_url()}/articles/{form}_form.cgi?id={self.id}"

    @property
    def href(self):
        if not getattr(self, "id"):
            return None
        else:
            return super().href

    @property
    def id_where(self):
        return sql.where("article_id = %i" % self.id)

    @property
    def source(self):
        source, = query_one("SELECT source "
                            "  FROM wiki.article WHERE id = %i" % self.id)
        return source

    # @property
    # def bibtex(self):
    #     source, = query_one("SELECT bibtex "
    #                         "  FROM wiki.article_rendition "
    #                         " WHERE id = %i" % self.id)
    #     return source

    @property
    def bibtex_source(self):
        source, = query_one("SELECT bibtex_source "
                            "  FROM wiki.article WHERE id = %i" % self.id)
        return source

    @property
    def user_info(self):
        if not hasattr(self, "_user_info"):
            self._user_info, = query_one(
                "SELECT user_info "
                "  FROM wiki.article WHERE id = %i" % self.id)
        return self._user_info

    @user_info.setter
    def user_info(self, i):
        self._user_info = i

    @property
    def user_info_source(self):
        source, = query_one("SELECT user_info_source "
                            "  FROM wiki.article WHERE id = %i" % self.id)
        return source

class ArticleForView(Article):
    __view__ = "article_for_view"

class ArticleForRedo(Article):
    __view__ = "article_for_redo"

class ArticleForRecentChangesList(Article):
    __view__ = "article_for_recent_changes_list"

class IncludedArticle(dbobject):
    # article_id, included_as

    @classmethod
    def query_recursively_for(IncludedArticle, article_id:int):
        cursor = execute_with_template(
            "recursive_include_query.sql", ( article_id, ))
        return [ IncludedArticle(cursor.description, tpl)
                 for tpl in cursor.fetchall() ]

class ResolvedArticleLink(dbobject, has_title_and_namespace):
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
    def select_by_full_title(ArticleTitle, title):
        return ArticleTitle.select_one(ArticleTitle.title_where(title))

class FulltextEntry(dbobject, has_title_and_namespace):
    pass

class Upload(dbobject):
    __schema__ = "uploads"
    __relation__ = "upload"
    __view__ = "upload_info"

    preview_sizes = ( 300, 600, 1800, )

    @property
    def data(self):
        if hasattr(self, "_data"):
            return self._data
        else:
            data, = query_one("SELECT data "
                              "  FROM uploads.upload "
                              " WHERE id = %i" % self.id)
            return data

    @data.setter
    def data(self, _data):
        self._data = _data

    @property
    def ext(self):
        if not hasattr(self, "_ext"):
            name, ext = op.splitext(self.filename)
            self._ext = ext.lower()
        return self._ext

    @ext.setter
    def ext(self, ext):
        self._ext = ext

    @property
    def preview_ext(self):
        if not hasattr(self, "_preview_ext"):
            if self.ext == ".png":
                self._preview_ext = ".png"
            else:
                self._preview_ext = ".jpg"

        return self._preview_ext

    @preview_ext.setter
    def preview_ext(self, p):
        self._preview_ext = p

    @property
    def preview_dir_name(self):
        return "%i_%i_%s" % ( self.article_id, self.id, self.slug, )

    def preview_url_for(self, size):
        assert size in self.preview_sizes, ValueError
        return "%s/previews/%s/preview%i%s" % ( get_site_url(),
                                                self.preview_dir_name,
                                                size,
                                                self.preview_ext, )
