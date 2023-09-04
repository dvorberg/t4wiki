import re, string, datetime, io, json, time, tomllib

from flask import (current_app as app, Blueprint, url_for,
                   g, request, session, abort, redirect, make_response)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.exceptions import Unauthorized

from ll.xist import xsc
from ll.xist.ns import html

from t4 import sql
from t4.typography import normalize_whitespace

from tinymarkup.exceptions import MarkupError
from tinymarkup.utils import html_start_tag

from .ptutils import test
from .utils import (gets_parameters_from_request, guess_language, get_languages,
                    get_site_url)
from .form_feedback import FormFeedback, NullFeedback
from . import model
from .db import insert_from_dict, commit
from .markup import Title, tools_by_format, update_titles_for, compile_article

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
def title_form(id:int=None,
               main_title=None,
               aliases="",
               ignore_namespace:bool=False,
               lang=None,
               format=None,
               followup="view"):
    template = app.skin.load_template("article_forms/title_form.pt")

    if request.method == "POST":
        feedback = FormFeedback()

        feedback.validate_not_empty("main_title")

        main_title = Title.parse(main_title, ignore_namespace)

        # Check titles with the database.
        titles = aliases.split("\n")
        titles = set([ Title.parse(title, ignore_namespace)
                       for title in titles if title.strip() != ""])
        titles.discard(main_title)
        titles = [main_title] + list(titles)

        for idx, title in enumerate(titles):
            where = sql.where("article_fulltitle.fulltitle  =",
                              sql.string_literal(title.full_title))
            if id:
                where = where.and_(sql.where(
                    "article_fulltitle.article_id <> %i" % id))

            result = model.ArticleMainTitle.select(
                sql.left_join("wiki.article_fulltitle",
                              "article_fulltitle.article_id = "
                              "  article_main_title.article_id"),
                where)
            result = list(result)

            if len(result) > 0:
                other = result[0].fulltitle
                msg = (f"“{title}” is already used by an article named "
                       f"“{other}”.")
                if idx == 0:
                    feedback.give( "main_title", msg )
                else:
                    feedback.give( "aliases", msg)

                break

        # This is an internal check.
        # No need to report an error through feedback,
        # because this is a radio button set and the user can’t
        # correct the language mapping from here.
        root_language = get_languages().by_iso(lang)

        # Same here: We check if we know about that format
        # before writing it to the db.
        tools_by_format(format)


        if feedback.is_valid():
            article = { "ignore_namespace": ignore_namespace,
                        "root_language": lang,
                        "format": format, }
            if id:
                model.Article.update_db(id, **article)
            else:
                id = insert_from_dict("wiki.article", article)

            update_titles_for(id, titles, root_language)

            commit()

            if followup == "view":
                return redirect(get_site_url() + "/" + str(main_title))
            elif followup == "source":
                return redirect(url_for("articles.source_form") + f"?id={id}")
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
def source_form(id:int, source=None):
    template = app.skin.load_template("article_forms/source_form.pt")
    article = model.Article.select_by_primary_key(id)

    if request.method == "POST":
        feedback = FormFeedback()

        titles = model.ArticleTitle.select(
            sql.where("article_id = %i" % article.id))
        titles = [ Title.from_db(title) for title in titles ]

        try:
            html, tsearch, links, includes, macro_info = compile_article(
                titles,
                source.replace("\r", ""),
                article.format,
                get_languages().by_iso(article.root_language),
                article.user_info)
        except MarkupError as exc:
            feedback.give("source", str(exc))
        else:
            article.update_db( source=source,
                               current_html=html,
                               tsvector=sql.expression(tsearch) )
            commit()
            return redirect(article.href)

    else:
        feedback = NullFeedback()

    return template(linkman=LinkMan('source', article), feedback=feedback)


@bp.route("/user_info_form.cgi", methods=("GET", "POST"))
@gets_parameters_from_request
def user_info_form(id:int, user_info_source=None):
    template = app.skin.load_template("article_forms/user_info_form.pt")
    article = model.Article.select_by_primary_key(id)

    if request.method == "POST":
        feedback = FormFeedback()

        try:
            user_info = tomllib.loads(user_info_source)
        except tomllib.TOMLDecodeError as exc:
            feedback.give("user_info_source", str(exc))
        else:
            article.update_db( user_info_source=user_info_source,
                               user_info=sql.jsonb_literal(user_info) )
            commit()
            return redirect(article.href)
    else:
        feedback = NullFeedback()

    return template(linkman=LinkMan('user_info', article), feedback=feedback)

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
