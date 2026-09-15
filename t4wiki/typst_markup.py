import subprocess, tempfile, pathlib, re

from sqlclasses import sql

from ll.xist.ns import html

from flask import current_app as app
from tinymarkup.exceptions import MarkupError

from .utils import get_languages
from . import db, html_markup

citekey_re = re.compile(r"@(\w+)"
                        r"|#cite\(label\([\"'](\w+)[\"']\)\)"
                        r"|#cite\(<(\w+)>\)")
def typst_to_t4wiki_html(source, root_language, user_info):
    # Find references and citations in the typst source.
    # keys = set([ a or b or c for (a,b,c) in citekey_re.findall(source) ])
    # strings = [ sql.string_literal(key) for key in keys ]
    # query = sql.select( ("string_agg(bibtex_source, '\n\n')",),
    #                     ("wiki.article",),
    #                     sql.where("bibtex_key IN (",
    #                               sql.comma_separated(strings),
    #                               ")") )
    # cursor = db.execute(query)
    # bibtex_source, = cursor.fetchone()

    keys = set([ a or b or c for (a,b,c) in citekey_re.findall(source) ])
    fake_entries = [ "@book{%s, title={%s}}" % ( key, key, )
                     for key in keys ]
    bibtex_source = "\n\n".join(fake_entries)
    
    # Load out preamble for the typst file.
    definitions = app.skin.read("preamble.typ")
    
    with tempfile.TemporaryDirectory(delete=(not app.debug)) as tmpdirname:
        tmpdir = pathlib.Path(tmpdirname)
        sourcefile_path = pathlib.Path(tmpdir, "source.typ")

        if bibtex_source:
            bibfile_path = pathlib.Path(tmpdir, "db.bib")
            with bibfile_path.open("w") as fp:
                fp.write(bibtex_source)
        
        with sourcefile_path.open("w") as fp:
            def p(*args, **kw):
                print(*args, file=fp)
                
            fp.write(definitions)
            p()
            p('#set text(lang: "%s")' % root_language.iso)
            p()
            for lang in get_languages():
                p('#let de(body) = wikilang("%s", body)' % lang)
            p()
            
            fp.write(source)

            if bibtex_source:
                p()
                p('#bibliography("db.bib")')
                p()

        
        result = subprocess.run(
            "typst compile --features html -f html source.typ -",
            capture_output=True,
            shell=True,
            cwd=tmpdirname,
            encoding="utf-8")

        if result.returncode == 0:
            raw_html = result.stdout
        else:
            raise MarkupError("Typst failed:\n" + result.stderr)

    doc = html_markup.dom_tree(raw_html)
    body = html_markup.body_contents(doc)

    for role in ("doc-endnotes", "doc-bibliography"):
        idx = None
        for counter, kid in enumerate(body):
            if type(kid) is html.section and str(kid["role"]) == role:
                idx = counter
                break

        if idx is not None:
            del body[idx]
            
    return  body

