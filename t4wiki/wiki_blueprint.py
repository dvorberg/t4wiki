import sys, os, re, string, datetime, io, json, time
from typing import List

from flask import (current_app as app,
                   g, request, session, abort, redirect, make_response)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.exceptions import Unauthorized

from ll.xist import xsc
from ll.xist.ns import html

from t4 import sql
from t4.typography import normalize_whitespace

from iridophore.flask import SkinnedBlueprint as Blueprint
from tinymarkup.utils import html_start_tag

from .context import get_languages
from .utils import guess_language, gets_parameters_from_request, rget
from .authentication import login_required, role_required, get_user
from . import markup
from . import model
from . import db
from . import ptutils



# This ought not to be done here. “Double quoting” the “?” character
# is neccessary for URLs to pass through the Apache reverse proxy safely.
# It must be double quoted when creating URLs and unquoted before URL
# processing.
from werkzeug import serving

quoted_question_mark_re = re.compile("%3[fF]")
from urllib.parse import unquote
def my_unquote(s):
    ret = unquote(s)
    ret = quoted_question_mark_re.sub("?", ret)
    return ret
serving.unquote = my_unquote


class Blueprint(Blueprint):
    def register(self, app, options):
        super().register(app, options)

        app.debug_sql = app.debug and (os.getenv("DEBUG_SQL") is not None)

bp = Blueprint("wiki", __name__, url_prefix="/wiki")

bp.skin.add_mjs_import("t4wiki", "t4wiki.mjs")
bp.skin.add_mjs_import("articles", "articles.mjs")
bp.skin.add_mjs_import("searchbar", "searchbar.mjs")

@bp.skin.template_globals
def template_globals():
    return { "test": ptutils.test,
             "ptutils": ptutils,
             "user": get_user(),
             "rget": rget,
            }

@bp.route("/t4wiki_languages.css")
@login_required
def languages_css():
    ret = []
    for language in get_languages().values():
        iso = language.iso
        ret.append( (".t4wiki article[lang=%s] { *[lang]:not([lang=%s]) { "
                     "font-style: italic; } "
                     "}") % ( iso, iso, ))
    response = make_response("\n".join(ret), 200)
    response.headers["Content-Type"] = "text/css"

    if False: #debug:
        response.headers["Pragma"] = "no-cache"
    else:
        response.headers["Cache-Control"] = "max-age=6048000" # 10 weeks

    return response


create_query_view = '''\
set search_path = wiki, public;

CREATE TEMPORARY VIEW the_query AS
    SELECT {} AS query;
'''

create_result_view = '''\
set search_path = wiki, public;

CREATE TEMPORARY VIEW search_result AS
    SELECT id AS article_id,
           ts_rank_cd('{0.1, 0.2, 0.4, 1.0}', tsvector, query, 0) AS rank,
           ts_headline(current_html, query) AS headline
      FROM article, the_query
     WHERE tsvector @@ query;
'''

def full_text_search(query, *clauses, lang=None):
    if lang is None:
        lang = guess_language(query)

    if lang is None:
        config = "simple"
    else:
        config = lang.tsearch_configuration

    cc = db.cursor()
    command = create_query_view.format(
        "websearch_to_tsquery(%(tsearch_config)s, %(query)s)")
    cc.execute(command, { "query": query, "tsearch_config": config })

    return run_query(cc, *clauses)


def title_search(article_id, *clauses):
    titles = model.ArticleTitle.select(
        sql.where("article_id = %i" % article_id))

    parts = []
    params = []
    for title in titles:
        parts.append('websearch_to_tsquery(%s, %s)')
        params.append(title.language_object.tsearch_configuration)
        params.append('"' + title.title.replace('"', ' ') + '"')

    cc = db.cursor()
    command = create_query_view.format(" || ".join(parts))
    cc.execute(command, params)

    return run_query(cc, *clauses)

def run_query(cc, *clauses):
    cc.execute(create_result_view)

    db.execute(sql.select(
        ("search_result.article_id", "title", "namespace", "rank", "headline",),
        ("search_result",),
        sql.left_join("article_title",
                      "search_result.article_id = article_title.article_id"
                      "      AND is_main_title"),
        sql.orderby("rank DESC"),
        *clauses), cc=cc)

    return [ model.FulltextEntry(cc.description, tpl)
             for tpl in cc.fetchall() ]


@bp.route("/")
@bp.route("/<path:article_title>")
@role_required("Reader")
def article_view(article_title=None):
    t = time.time()

    if article_title is None:
        article_title = ""

    template = app.skin.load_template("article_view.pt")

    article_title = normalize_whitespace(article_title)

    if article_title == "":
        article_title = app.config["PORTAL_ARTICLES"][0]

    result = model.Article.id_by_title(article_title)
    if result is None or "search" in request.args:
        # No article found with that title. Present a search result only.

        title = markup.Title.parse(article_title)
        if title.namespace:
            query_namespace = title.namespace
            where = sql.where("namespace = ",
                              sql.string_literal(query_namespace))
        else:
            where = None
            query_namespace = ""

        search_result = full_text_search(article_title, where)
        if result:
            regular_result = model.Article.select_by_primary_key(result[0])
        else:
            regular_result = None

        return template(article=None,
                        query=article_title,
                        query_namespace=query_namespace,
                        search_result=search_result,
                        regular_result=regular_result)
    else:
        article_id, = result
        included_articles = model.IncludedArticle.query_recursively_for(
            article_id)

        included_article_ids = [ a.article_id for a in included_articles ]
        article_ids = [article_id] + included_article_ids
        # For SQL:
        article_ids_s = ",".join([str(id) for id in article_ids])

        articles = model.ArticleForView.select(
            sql.where("id in (", article_ids_s, ")"))

        included = []
        meta_info_js = []
        for article in articles:
            if article.id == article_id:
                main_article = article
            else:
                included.append(article)

            meta_info_js.append( ('%i: { '
                                  '"user_info": (%s), '
                                  '"macro_info": (%s) '
                                  '}') % ( article.id,
                                           article.user_info,
                                           article.macro_info, ) )
        meta_info_js = "{ %s }"  % ", ".join(meta_info_js)

        title_to_id_js = "{ %s }" % ", ".join([ '"%s": %i' % ( ia.included_as,
                                                               ia.article_id, )
                                                for ia in included_articles ])

        file_info_json, = db.query_one(
            "SELECT json_object_agg(article_id, uploads_info)::TEXT"
            "  FROM uploads.upload_info_for_view "
            " WHERE article_id IN (%s)" % article_ids_s)
        if not file_info_json:
            file_info_json = "{}"

        link_info, = db.query_one(
            "SELECT json_object_agg(target, full_title)::text "
            "  FROM article_link_resolved "
            " WHERE article_id IN (%s)" % article_ids_s)

        linking_here = list(model.ResolvedArticleTeaser.select(
            sql.where("resolved_full_title =",
                      sql.string_literal(main_article.full_title)),
            sql.orderby("main_title")))

        if len(linking_here) == 0:
            where = None
        else:
            ids = [str(article.article_id) for article in linking_here]
            ids.append(str(article.id))
            where = sql.where(
                "search_result.article_id NOT IN (%s)" % ",".join(ids))

        return template(article=main_article,
                        included=included,
                        linking_here=linking_here,
                        meta_info_js=meta_info_js,
                        link_info=link_info,
                        file_info_json=file_info_json,
                        title_to_id_js=title_to_id_js,
                        query=article_title)

ids_re = re.compile(r"(\d+,?)+")
@bp.route("/article_fulltext_search")
@role_required("Reader")
@gets_parameters_from_request
def article_fulltext_search(article_id:int, linking_here):
    template = app.skin.load_template("article_fulltext_search_result.pt")

    ignore_ids = [ article_id, ]
    if linking_here != "":
        ignore_ids += [ int(id) for id in linking_here.split(",") ]

    where = sql.where("search_result.article_id NOT IN (%s)" % (
        ",".join([str(i) for i in ignore_ids]),))

    result = title_search(article_id, where, sql.limit(100))
    count = db.count("search_result", where)

    return template(search_result=result, full_text_count=count)
