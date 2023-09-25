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
from .context import get_languages
from .utils import guess_language
from .authentication import login_required, role_required
from . import markup
from . import model
from . import db

bp = Blueprint("wiki", __name__, url_prefix="/wiki")

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


fulltext_query_tmpl = '''\
set search_path = wiki, public;

CREATE TEMPORARY VIEW the_query AS
    SELECT websearch_to_tsquery(%(tsearch_config)s, %(query)s) AS query;

CREATE TEMPORARY VIEW search_result AS
    SELECT article_id, title, namespace, rank,
           ts_headline(%(tsearch_config)s, current_html, query,
                       'MaxWords=100') AS headline
      FROM
      (
        SELECT id, current_html,
               ts_rank_cd('{0.1, 0.2, 0.4, 1.0}', tsvector, query, 0) AS rank,
               the_query.query
          FROM article, the_query
         WHERE the_query.query @@ tsvector
      ) AS foo
      LEFT JOIN article_title ON id = article_id AND is_main_title
      GROUP BY article_id, title, namespace, rank, headline;
'''


@bp.route("/")
@bp.route("/<path:article_title>")
@role_required("Reader")
def article_view(article_title=None):
    if article_title is None:
        article_title = ""

    # Everything after ? (even when quoted!) is removed from the path.
    article_title = request.full_path[len(bp.url_prefix)+1:] # Remove "/wiki/"

    template = app.skin.load_template("article_view.pt")

    article_title = normalize_whitespace(article_title)

    if article_title == "":
        article_title = app.config["MAIN_ARTICLE"]

    cc = db.cursor()
    lang = guess_language(article_title)
    if lang is None:
        config = "simple"
    else:
        config = lang.tsearch_configuration
    cc.execute(fulltext_query_tmpl, { "query": article_title,
                                      "tsearch_config": config })

    def full_text_search(query):
        cc.execute(query)
        return [ model.FulltextEntry(cc.description, tpl)
                 for tpl in cc.fetchall() ]


    result = model.Article.id_by_title(article_title)
    if result is None or "search" in request.args:
        # No article found with that title. Present a search result only.

        title = markup.Title.parse(article_title)
        if title.namespace:
            query_namespace = title.namespace
            where = cc.mogrify("WHERE namespace = %s",
                               ( query_namespace, )).decode("utf-8")
        else:
            where = ""
            query_namespace = ""

        search_result = full_text_search(f"SELECT title, namespace, headline"
                                         f"  FROM search_result "
                                         f"  {where}"
                                         f" ORDER BY rank DESC")
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
            "SELECT json_object_agg(target, fulltitle)::text "
            "  FROM article_link_resolved "
            " WHERE article_id IN (%s)" % article_ids_s)

        linking_here = list(model.ResolvedArticleTeaser.select(
            sql.where("resolved_fulltitle =",
                      sql.string_literal(main_article.full_title)),
            sql.orderby("main_title, namespace")))

        if len(linking_here) == 0:
            where = ""
        else:
            ids = [str(article.article_id) for article in linking_here]
            ids.append(str(article.id))

            where = " WHERE article_id NOT IN (%s)" % ",".join(ids)

        search_result = full_text_search(f"SELECT title, namespace, headline"
                                         f"  FROM search_result "
                                         f"  {where}"
                                         f" ORDER BY rank DESC"
                                         f" LIMIT 10")
        full_text_count, = db.query_one(f"SELECT COUNT(*) FROM search_result "
                                        f" {where}")

        return template(article=main_article,
                        included=included,
                        linking_here=linking_here,
                        meta_info_js=meta_info_js,
                        link_info=link_info,
                        file_info_json=file_info_json,
                        title_to_id_js=title_to_id_js,
                        query=article_title,
                        search_result=search_result,
                        full_text_count=full_text_count)
