
from .db import dbobject

class Article(dbobject):
    __schema__ = "wiki"
    __relation__ = "article"
    __view__ = "article_info"

class ArticleTitle(dbobject):
    __schema__ = "wiki"
    __relation__ = "article_title"
