import os.path as op, re, string, datetime, io, json, time, tomllib, pathlib
import subprocess
from PIL import Image

from flask import (current_app as app, Blueprint, url_for,
                   g, request, session, abort, redirect, make_response)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.exceptions import Unauthorized

from ll.xist import xsc
from ll.xist.ns import html

import bibtexparser.bparser

from t4 import sql
from t4.typography import normalize_whitespace

from tinymarkup.exceptions import MarkupError
from tinymarkup.utils import html_start_tag

from .ptutils import test
from .utils import (gets_parameters_from_request, guess_language, get_languages,
                    get_site_url)
from .form_feedback import FormFeedback, NullFeedback
from . import model
from .db import insert_from_dict, commit, query_one, execute
from .markup import Title, tools_by_format, update_titles_for, compile_article
from .authentication import login_required, role_required

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
        if self.article is None or self.article.id is None:
            return None
        else:
            if form == "view":
                return self.article.href()
            else:
                return self.article.form_url(form)

@bp.route("/title_form.cgi", methods=("GET", "POST"))
@role_required("Writer")
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
            # Update the article.
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

    languages = [ l for l in get_languages().values()
                  if l.ui_name is not None ]
    languages = sorted(languages, key=lambda l: l.ui_name or "")

    if id:
        delete_link = f'{url_for("articles.delete")}?id={id}'
    else:
        delete_link = None

    return template(linkman=LinkMan('title', article),
                    aliases=aliases,
                    feedback=feedback,
                    languages=languages,
                    delete_link=delete_link)

@bp.route("/source_form.cgi", methods=("GET", "POST"))
@role_required("Writer")
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
            # Make a backup of the current article.
            execute("INSERT INTO archive.article_revision "
                    "    SELECT * FROM wiki.current_article_revision "
                    "     WHERE id = %s", (id,))

            article.update_db( source=source,
                               current_html=html,
                               tsvector=sql.expression(tsearch) )
            commit()
            return redirect(article.href)

    else:
        feedback = NullFeedback()

    return template(linkman=LinkMan('source', article), feedback=feedback)


@bp.route("/bibtex_form.cgi", methods=("GET", "POST"))
@role_required("Writer")
@gets_parameters_from_request
def bibtex_form(id:int, bibtex_source=None):
    template = app.skin.load_template("article_forms/bibtex_form.pt")
    article = model.Article.select_by_primary_key(id)

    if request.method == "POST":
        feedback = FormFeedback()

        if bibtex_source.strip() == "":
            article.update_db( bibtex_source="",
                               bibtex_key=None,
                               bibtex=None )

            commit()
            return redirect(article.href)

        parser = bibtexparser.bparser.BibTexParser()
        library = parser.parse(bibtex_source)
        if len(library.entries) < 1:
            feedback.give("bibtex_source",
                          "No valid BibTeX entry found in source.")
        elif len(library.entries) > 1:
            feedback.give("bibtex_source",
                          "You can’t enter more than one entry here.")
        else:
            entry = library.entries[0]
            key = entry["ID"]

            # Verify key uniqueness.
            result = query_one("SELECT fulltitle "
                               "  FROM wiki.article "
                               "  LEFT JOIN wiki.article_main_title "
                               "    ON article_id = id "
                               " WHERE id <> %s "
                               "   AND bibtex_key = %s"
                               " LIMIT 1",
                               ( id, key, ))
            if result is not None:
                fulltitle, = result
                href = f"{get_site_url()}/fulltitle"
                feedback.give(
                    "bibtex_source",
                    xsc.Frag( f'A BibTeX entry for “{key}” already exists '
                              f'in article “',
                              html.a(fulltitle, href=href, target="_new"),
                              "”."))

        if feedback.is_valid():
            article.update_db( bibtex_source=bibtex_source,
                               bibtex_key=key,
                               bibtex=sql.jsonb_literal(entry) )
            commit()
            return redirect(article.href)
    else:
        feedback = NullFeedback()

    return template(linkman=LinkMan('bibtex', article), feedback=feedback)

@bp.route("/user_info_form.cgi", methods=("GET", "POST"))
@role_required("Writer")
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


def make_grey_image(greypath):
    img = Image.new(mode="L", size=(200,200), color=128)
    img.save(greypath)

preview_sizes = ( 300, 600, 1800, )
def create_previews_for(upload:model.Upload):
    preview_dir = pathlib.Path(app.config["PREVIEW_PATH"],
                               upload.preview_dir_name)
    if not preview_dir.exists():
        # Create the preview dir.
        preview_dir.mkdir()
    else:
        # Clear the preview dir.
        for pp in preview_dir.glob("*"):
            pp.unlink()

    if upload.ext in { ".jpg", ".png", ".pdf" }:
        create_image_previews_for(preview_dir, upload)
    else:
        # Create default grey images.
        greypath = pathlib.Path(preview_dir, "grey.jpg")
        make_grey_image(greypath)
        for size in preview_sizes:
            outfilepath = pathlib.Path(preview_dir,
                                       "preview%i.jpg" % (size))
            outfilepath.hardlink_to(greypath)


def create_image_previews_for(preview_dir, upload):
    original_path = pathlib.Path(preview_dir, "original" + upload.ext)
    with original_path.open("wb") as fp:
        fp.write(upload.data)

    if upload.ext != ".pdf":
        pil_image = Image.open(original_path)
        width, height = pil_image.size
        upload.update_db( width=width, height=height )
    else:
        width, height = 1000000, 1000000

    for size in preview_sizes:
        ext = upload.ext

        if ext == ".pdf":
            ext = ".jpg"

        outfilepath = pathlib.Path(preview_dir,
                                   "preview%i%s" % (size, ext))

        if width < size and height < size:
            # No point in making this preview.
            outfilepath.hardlink_to(original_path)
        else:
            cmd = [ "convert",
                    str(original_path) + "[0]",
                    "-thumbnail",
                    "%ix%i" % ( size, size, ),
                    str(outfilepath) ]

            print(cmd)
            done = subprocess.run(cmd)

            if done.returncode != 0:
                make_grey_image(outfilepath)

    original_path.unlink()

def create_previews_for_all():
    for upload in model.Upload.select():
        create_previews_for(upload)

    # To store image dimensions:
    commit()

@bp.route("/files_form.cgi", methods=("GET", "POST"))
@role_required("Writer")
@gets_parameters_from_request
def files_form(id:int):
    template = app.skin.load_template("article_forms/files_form.pt")
    article = model.Article.select_by_primary_key(id)

    if request.method == "POST":
        feedback = FormFeedback()
    else:
        feedback = NullFeedback()

    return template(linkman=LinkMan('files', article), feedback=feedback)

@bp.route("/delete.cgi")
@role_required("Writer")
@gets_parameters_from_request
def delete(id:int):
    execute("DELETE FROM wiki.article WHERE id = %i" % id)
    commit()
    return redirect(get_site_url())
