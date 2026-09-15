import subprocess, tempfile, pathlib

from flask import current_app as app
from tinymarkup.exceptions import MarkupError

from .utils import get_languages

def typst_to_t4wiki_html(source, root_language, user_info):
    definitions = app.skin.read("t4wiki.typ")
    
    with tempfile.TemporaryDirectory(delete=(not app.debug)) as tmpdirname:
        tmpdir = pathlib.Path(tmpdirname)
        sourcefile_path = pathlib.Path(tmpdir, "source.typ")

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

        
        result = subprocess.run(
            "typst compile --features html -f html source.typ -",
            capture_output=True,
            shell=True,
            cwd=tmpdirname,
            encoding="utf-8")

        if result.returncode == 0:
            return result.stdout
        else:
            raise MarkupError("Typst failed:\n" + result.stderr)
