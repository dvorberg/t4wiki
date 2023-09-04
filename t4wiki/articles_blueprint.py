import re, string, datetime, io, json, time

from flask import (current_app as app, Blueprint,
                   g, request, session, abort, redirect, make_response)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.exceptions import Unauthorized

from ll.xist import xsc
from ll.xist.ns import html

from t4 import sql
from t4.typography import normalize_whitespace

from tinymarkup.utils import html_start_tag

from .ptutils import test
from .utils import gets_parameters_from_request, guess_language, get_languages
from .form_feedback import FormFeedback, NullFeedback
from . import markup
from . import model
from . import db

bp = Blueprint("articles", __name__, url_prefix="/articles")

class LinkMan(object):
    def __init__(self, active_form, article):
        self.active_form = active_form
        self.article = article

    def cls(self, form):
        if self.article is None:
            if form == "title" and self.active_form == "title":
                return "active"
            else:
                return "disabled"
        elif form == self.active_form:
            return "active"
        else:
            return ""

    def href(self, form):
        if self.article is None:
            return None
        else:
            if form == "view":
                return self.article.href()
            else:
                return self.article.form_url(form)


@bp.route("/title_form.cgi", methods=("GET", "POST"))
@gets_parameters_from_request
def title_form(id:int=None):
    template = app.skin.load_template("article_forms/title_form.pt")

    if request.method == "POST":
        feedback = FormFeedback()
    else:
        feedback = NullFeedback()
        if id is None:
            article = model.Article.empty()
            aliases = ""
        else:
            article = model.Article.select_by_primary_key(id)
            titles = model.ArticleTitle.select(
                sql.where("NOT is_main_title").and_(article.id_where),
                sql.orderby("title, namespace"))
            aliases = "\n".join([ t.full_title for t in titles ])

    languages = sorted(get_languages().values(), key=lambda l: l.ui_name or "")

    return template(linkman=LinkMan('title', article),
                    aliases=aliases,
                    feedback=feedback,
                    languages=languages)

@bp.route("/source_form.cgi", methods=("GET", "POST"))
@gets_parameters_from_request
def source_form(id:int):
    template = app.skin.load_template("article_forms/source_form.pt")
    article = model.Article.select_by_primary_key(id)

    if request.method == "POST":
        feedback = FormFeedback()
    else:
        feedback = NullFeedback()

    return template(linkman=LinkMan('source', article), feedback=feedback)


@bp.route("/meta_info_form.cgi", methods=("GET", "POST"))
@gets_parameters_from_request
def meta_info_form(id:int):
    template = app.skin.load_template("article_forms/meta_info_form.pt")
    article = model.Article.select_by_primary_key(id)

    if request.method == "POST":
        feedback = FormFeedback()
    else:
        feedback = NullFeedback()

    return template(linkman=LinkMan('meta_info', article), feedback=feedback)

@bp.route("/files_form.cgi", methods=("GET", "POST"))
@gets_parameters_from_request
def files_form(id:int):
    template = app.skin.load_template("article_forms/files_form.pt")
    article = model.Article.select_by_primary_key(id)

    if request.method == "POST":
        feedback = FormFeedback()
    else:
        feedback = NullFeedback()

    return template(linkman=LinkMan('files', article), feedback=feedback)
