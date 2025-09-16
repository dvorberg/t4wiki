import os.path as op, re, string, datetime, io, json, time, tomllib, pathlib
import sys, subprocess, urllib.parse, mimetypes, unicodedata, traceback
from PIL import Image

from flask import (current_app as app, url_for, send_file,
                   g, request, session, abort, redirect, make_response)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.exceptions import Unauthorized

from ll.xist import xsc
from ll.xist.ns import html

from citeproc.source.bibtex import BibTeX as BibTeXLibrary
from citeproc import CitationStylesStyle, CitationStylesBibliography
from citeproc import formatter as citeproc_formatter
from citeproc import Citation, CitationItem

from t4 import sql
from t4.typography import normalize_whitespace
from t4.passwords import slug

from iridophore.flask import SkinnedBlueprint as Blueprint

from tinymarkup.exceptions import MarkupError
from tinymarkup.utils import html_start_tag

from .ptutils import test
from .utils import (gets_parameters_from_request, get_languages,
                    get_site_url, rget,
                    OrderByHandler, PaginationHandler, FilterFormHandler)
from .form_feedback import FormFeedback, NullFeedback
from . import model
from .db import insert_from_dict, commit, query_one, execute, cursor
from .markup import (Title, tools_by_format, compile_article,
                     update_titles_for, update_links_for, update_includes_for,
                     normalize_source, )
from .authentication import login_required, role_required
from . import html_markup

bp = Blueprint("articles", __name__, url_prefix="/articles")

bp.skin.add_mjs_import("files_form", "article_forms/files_form.mjs")
bp.skin.add_mjs_import("codejar", "article_forms/codejar/codejar.mjs")
bp.skin.add_mjs_import("cursor", "article_forms/codejar/cursor.mjs")
bp.skin.add_mjs_import("prismjs", "article_forms/prism/prism.mjs")
bp.skin.add_mjs_import("syntax_highlighting",
                       "article_forms/syntax_highlighting.mjs")

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
               full_title=None,
               aliases="",
               ignore_namespace:bool=False,
               lang=None,
               format=None,
               followup="view"):
    template = app.skin.load_template("article_forms/title_form.pt")

    if request.method == "POST":
        feedback = FormFeedback()

        feedback.validate_not_empty("full_title")

        main_title = Title.parse(full_title, ignore_namespace)

        # Check titles with the database.
        titles = aliases.split("\n")
        titles = set([ Title.parse(title, ignore_namespace)
                       for title in titles if title.strip() != ""])
        titles.discard(main_title)
        titles = [main_title] + list(titles)

        for idx, title in enumerate(titles):
            where = sql.where("full_title = ",
                              sql.string_literal(title.full_title))
            if id:
                where = where.and_(sql.where("article_id <> %i" % id))

            result = model.ArticleTitle.select(where)
            result = list(result)

            if len(result) > 0:
                other = result[0].full_title
                msg = (f"“{title}” is already used by an article named "
                       f"“{other}”.")
                if idx == 0:
                    feedback.give( "full_title", msg )
                else:
                    feedback.give( "aliases", msg )

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
                        "format": format,
                        "mtime": sql.expression("NOW()"), }
            if id:
                model.Article.update_db(id, **article)
            else:
                id = insert_from_dict("wiki.article", article)

            update_titles_for(id, titles, root_language)

            commit()

            if followup == "view":
                return redirect(get_site_url() + "/" + main_title.path)
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

        def title_string(t):
            if t.language == article.root_language:
                return t.full_title
            else:
                return t.language + ":" + t.full_title
        aliases = "\n".join([ title_string(t) for t in titles ])

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

        source = normalize_source(source)

        titles = model.ArticleTitle.select(
            sql.where("article_id = %i" % article.id))
        titles = [ Title.from_db(title) for title in titles ]

        try:
            html, tsearch, links, includes, macro_info = compile_article(
                source,
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

            article.update_db(source=source,
                              current_html=html,
                              main_tsvector=sql.expression(tsearch),
                              mtime=sql.expression("NOW()"),
                              macro_info=sql.json_literal(macro_info))

            update_links_for(id, links)
            update_includes_for(id, includes)

            commit()
            return redirect(article.href)

    else:
        feedback = NullFeedback()

    return template(linkman=LinkMan('source', article), feedback=feedback)


def render_bibtex_html(library:BibTeXLibrary, lang):
    here = op.dirname(__file__)
    bib_style = CitationStylesStyle( op.join(here, "bibliography.csl"),
                                     locale=lang, validate=True )
    entry = list(library.values())[0]
    key = entry["key"]
    bibliography = CitationStylesBibliography(
        bib_style, library, citeproc_formatter.html)
    bibliography.register(Citation([CitationItem(key)]))

    return "".join(bibliography.bibliography()[0]).replace("..", ".")


def read_bibtex_templates():
    here = pathlib.Path(__file__)
    template_path = pathlib.Path(here.parent, "skin",
                                 "article_forms", "bibtex_templates")

    filenames = template_path.glob("*.bib")
    templates = []
    for fp in sorted(filenames, key=lambda p: p.stem):
        templates.append(f'<pre data-type="{fp.stem}">{fp.open().read()}</pre>')

    return "\n".join(templates)

comment_re = re.compile(r"%.*$", re.MULTILINE)
key_re = re.compile(r"@\w+\{(\w+),")
def find_bibtex_key(source):
    """
    The citeproc BiBTeX code converts keys lower case. That makes
    sense.  I’d like to retain case on my keys, because being a human
    and not a computer, I find them easier to remember that way.
    """
    source = comment_re.sub("", source)
    match = key_re.search(source)
    if match is None:
        raise KeyError("No BibTeX key in %s" % repr(source))
    else:
        return match.group(1)

def bibtex_tsvector(language, bibtex_html):
    frag = html_markup.dom_tree(bibtex_html)
    tsvector = html_markup.tsearch(frag, language, "B")
    return f"setweight({tsvector}, 'B')"


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
                               bibjson=None,
                               bibtex_html=None )

            commit()
            return redirect(article.href)

        try:
            library = BibTeXLibrary(io.StringIO(bibtex_source))

            if len(library) < 1:
                feedback.give("bibtex_source",
                              "No valid BibTeX entry found in source.")
            elif len(library) > 1:
                feedback.give("bibtex_source",
                              "You can’t enter more than one entry here.")

        except Exception as ex:
            traceback.print_exception(ex)
            feedback.give("bibtex_source",
                          f"Error parsing the BibTeX "
                          f"within citeproc library: ‘{repr(ex)}’.")

        if feedback.is_valid():
            entry = list(library.values())[0]

            key = entry["key"]

            if key == "citekey":
                feedback.give("bibtex_source",
                              "Not a valid citekey: “citekey”.")

            # Verify key uniqueness.
            result = query_one("SELECT full_title "
                               "  FROM wiki.article "
                               "  LEFT JOIN wiki.article_title "
                               "    ON article_id = id "
                               " WHERE id <> %s "
                               "   AND bibtex_key = %s"
                               " LIMIT 1",
                               ( id, key, ))

            if result is not None:
                full_title, = result
                href = f"{get_site_url()}/{full_title}"
                feedback.give(
                    "bibtex_source",
                    xsc.Frag( f'A BibTeX entry for “{key}” already exists '
                              f'in article “',
                              html.a(full_title, href=href, target="_new"),
                              "”."))

            try:
                bibtex_html=render_bibtex_html(library, article.root_language)
            except Exception as ex:
                traceback.print_exception(ex)

                feedback.give(
                    "bibtex_source",
                    f"Error parsing or rendering the BibTeX "
                    f"within citeproc library: {str(ex)}")

        if feedback.is_valid():
            tsvector = bibtex_tsvector(article.root_language, bibtex_html)

            article.update_db( bibtex_source=bibtex_source,
                               bibtex_key=find_bibtex_key(bibtex_source),
                               bibtex_html=bibtex_html,
                               bibtex_tsvector=sql.expression(tsvector),
                               bibjson=sql.jsonb_literal(entry) )
            commit()
            return redirect(article.href)
    else:
        feedback = NullFeedback()

    return template(linkman=LinkMan('bibtex', article), feedback=feedback,
                    templates=read_bibtex_templates())

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
                               user_info=sql.jsonb_literal(user_info),
                               mtime=sql.expression("NOW()"), )
            commit()
            return redirect(article.href)
    else:
        feedback = NullFeedback()

    return template(linkman=LinkMan('user_info', article), feedback=feedback)


def make_grey_image(greypath):
    img = Image.new(mode="L", size=(200,200), color=128)
    img.save(greypath)

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
        for size in model.Upload.preview_sizes:
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

    for size in model.Upload.preview_sizes:
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

            done = subprocess.run(cmd)

            if done.returncode != 0:
                make_grey_image(outfilepath)

    original_path.unlink()

def create_previews_for_all():
    for upload in model.Upload.select():
        create_previews_for(upload)

    # To store image dimensions:
    commit()

separator_re = re.compile(r"[/\\:]")
def sanitize_filename(filename):
    filename = filename.replace("..", "_") # For security.
    # Remove path separators from the filename, just in case.
    parts = separator_re.split(filename)
    filename = parts[-1]

    return filename

@bp.route("/files_form.cgi", methods=("GET", "POST"))
@role_required("Writer")
@gets_parameters_from_request
def files_form(id:int):
    template = app.skin.load_template("article_forms/files_form.pt")
    article = model.Article.select_by_primary_key(id)

    errors = xsc.Frag()

    if request.method == "POST":
        for file in request.files.getlist("files"):
            # When there is no file, the Browser sends am empty one.
            if file.filename != "":
                filename = sanitize_filename(file.filename)

                name, ext = op.splitext(filename)
                ext = ext.lower()

                count, = query_one("SELECT COUNT(*) FROM uploads.upload "
                                   " WHERE article_id = %s "
                                   "   AND filename = %s", (id, filename,))
                if count > 0:
                    errors.append(f"A file named “{filename}” already exists "
                                  f"for this article.")
                else:
                    upload = { "article_id": id,
                               "filename": filename,
                               "data": file.read(),
                               "slug": slug(20),
                               "is_download": ext == ".pdf"
                              }
                    upload_id = insert_from_dict("uploads.upload", upload)

                    upload["id"] = upload_id
                    upload = model.Upload.from_dict(upload)

                    create_previews_for(upload)

        commit()

    uploads = model.Upload.select( sql.where("article_id = %i" % id),
                                   sql.orderby("sortrank" ) )

    return template(linkman=LinkMan('files', article),
                    uploads=uploads,
                    errors=errors)

@bp.route("/delete.cgi")
@role_required("Writer")
@gets_parameters_from_request
def delete(id:int):
    execute("DELETE FROM wiki.article WHERE id = %i" % id)
    commit()
    return redirect(get_site_url())

@bp.route("/modify_upload.cgi", methods=("POST",))
@role_required("Writer")
@gets_parameters_from_request
def modify_upload(article_id:int, upload_id:int, name, value):
    assert name in { "title", "description", "filename", "is_download",
                     "gallery", "sortrank" }, ValueError

    if name == "sortrank":
        value = float(value)
    elif name in { "gallery", "is_download" }:
        value = bool(value == "on")
    elif name == "filename":
        value = sanitize_filename(value)

        # Verify no other upload (in this article_id) has that filename.
        count, = query_one(sql.select(
            ("COUNT(*)",),
            ("uploads.upload",),
            sql.where("article_id = %i " % article_id,
                      "AND id <> %i " % upload_id,
                      "AND filename =", sql.string_literal(value))))
        if count > 0:
            return make_response(f"A file named “{value}” already exists.",
                                 409) # 409 => “Conflict”

    data = { name: value }
    command = sql.update(model.Upload.__relation__,
                         sql.where("article_id = %i" % article_id,
                                   " AND id = %i" % upload_id),
                         data)
    execute(command)
    commit()

    return make_response("Ok", 200)

@bp.route("/delete_upload.cgi")
@role_required("Writer")
@gets_parameters_from_request
def delete_upload(article_id:int, upload_id:int):
    execute("DELETE FROM uploads.upload WHERE id = %i AND article_id = %i" % (
        upload_id, article_id))
    commit()

    return redirect(url_for("articles.files_form") + "?id=%i" % article_id)


@bp.route("/update_sortranks.cgi")
@role_required("Writer")
@gets_parameters_from_request
def update_sortranks(article_id:int):
    with cursor() as cc:
        cc.execute("SELECT id FROM uploads.upload "
                   " WHERE article_id = %s "
                   " ORDER BY sortrank", (article_id,))

        for idx, (id,) in enumerate(cc.fetchall()):
            cc.execute("UPDATE uploads.upload "
                       "   SET sortrank = %s::FLOAT "
                       " WHERE id = %s" % ( idx+1, id, ))
    commit()

    return redirect(url_for("articles.files_form") + "?id=%i" % article_id)


@bp.route("/download_upload.cgi")
@role_required("Writer")
@gets_parameters_from_request
def download_upload(id:int):
    with cursor() as cc:
        cc.execute("SELECT filename, data FROM uploads.upload "
                   " WHERE id = %s ", (id,))

        filename, data = cc.fetchone()

    response = make_response(bytes(data), 200)
    mimetype, subtype = mimetypes.guess_type(filename)
    if not mimetype:
        mimetype = "application/octet-stream"

    return send_file(io.BytesIO(bytes(data)),
                     download_name = filename,
                     as_attachment = True,
                     mimetype=mimetype)

@bp.route("/all.cgi", methods=("GET", "POST"))
@role_required("Writer")
@gets_parameters_from_request
def all():
    template = app.skin.load_template("article_list.pt")

    def rget_empty_as_none(key, default):
        ret = rget(key, default=None)
        if ret:
            return ret
        else:
            return None

    orderby = OrderByHandler(
        [ ("main_title, namespace", "Title",),
          ("mtime DESC", "Modification time", "mtime",),
         ], "articles_orderby")

    filter = FilterFormHandler("article_filter",
                               ( "namespace", rget_empty_as_none, None, ))

    if request.method == "GET":
        namespace = rget("namespace")
        if namespace:
            filter.namespace = namespace


    if filter.namespace is None:
        where = sql.where("1=1")
    else:
        where = sql.where("namespace = ", sql.string_literal(filter.namespace))

    count = model.ArticleForList.count(where)

    pagesize = int(count/19)
    if pagesize < 50:
        pagesize = 50

    print("pagesize =", repr(pagesize))

    pagination = PaginationHandler(pagesize=pagesize, count=count)
    articles = model.ArticleForList.select(
        where, orderby.sql_clause(), *pagination.sql_clauses())

    if orderby.active.id == "mtime":
        title = "Recent Changes"
    else:
        title = "Articles"

        if filter.namespace:
            title = f"{title} ({filter.namespace})"

    return template(title=title, articles=articles,
                    orderby=orderby, filter=filter, pagination=pagination)

def redo_html():
    for article in model.ArticleForRedo.select(sql.orderby("full_title")):
        print(article.full_title, end="")
        sys.stdout.flush()

        root_language = get_languages().by_iso(article.root_language)

        user_info = tomllib.loads(article.user_info_source)

        titles = [ Title(get_languages().by_iso(d["lang"]),
                         d["title"], d["namespace"])
                   for d in article.titles ]

        # Compile the source to HTML and tsearch.
        html, tsearch, links, includes, macro_info = compile_article(
            article.source,
            article.format,
            root_language,
            user_info)

        update_links_for(article.id, links)
        update_includes_for(article.id, includes)

        # Get the titles from the database to update their tsvector.
        titles_tsvector = "||".join([title.to_tsvector(root_language)
                                     for title in titles])

        # Update the database.
        article.update_db(user_info=sql.jsonb_literal(user_info),
                          current_html=html,
                          main_tsvector=sql.expression(tsearch),
                          macro_info=sql.jsonb_literal(macro_info),
                          titles_tsvector=sql.expression(titles_tsvector))
        print()
        sys.stdout.flush()
    commit()

def redo_bibtex():
    articles = model.ArticleForBibTeXRedo.select(
        sql.where("bibtex_source IS NOT NULL"), sql.orderby("full_title"))

    for article in articles:
        print(article.full_title, end="")
        sys.stdout.flush()

        try:
            library = BibTeXLibrary(io.StringIO(article.bibtex_source))
            entry = list(library.values())[0]
            key = find_bibtex_key(article.bibtex_source)
            html = render_bibtex_html(library, article.root_language)
            tsvector = bibtex_tsvector(article.root_language, html)
        except Exception as ex:
            print(" ", ex)
            print()
            raise
            #sys.exit(255)
        else:
            article.update_db( bibtex_key=key,
                               bibtex_html=html,
                               bibjson=sql.jsonb_literal(entry),
                               bibtex_tsvector=sql.expression(tsvector) )
        print()
        sys.stdout.flush()

    commit()
