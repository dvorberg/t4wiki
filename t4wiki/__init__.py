from ll.xist import xsc
xsc.Node.__html__ = xsc.Node.string
# Chameleon will check for object.__html__() and use it instead of
# str(object) if available. Above modification lets me any ll.xist.Node
# as if it were a string with regard to Chameleon templates.


# Chameleon benutzt bei Objekten, die eine __html__() methode haben,
# obj.__html__() Statt str(obj), was ja dann zu obj.__str__() wird.
# xsc.Node.__str__() liefert aber den *textlichen Inhalt* der Knoten zurück,
# nicht die HTML-Repräsentation, die ich gerne hätte. Das macht aber
# Node.string(). Damit ich nicht Node.string() immer irgendwo aufrufen muss,
# sondern einfach meine Funktionen in den Page Templates verwenden möchte,
# hier dieser kleine Kunstgriff.
# Die __html__()-Funktion ist dokumentiert:
# https://chameleon.readthedocs.io/en/latest/reference.html
#
# So könnte man da noch eingreifen:
#def xsc__html__(self):
#    return self.string()
#xsc.Node.__html__ = xsc__html__
#

import os, re
debug = os.getenv("DEBUG") is not None
debug_sql = os.getenv("DEBUG_SQL") is not None

from werkzeug import serving

quoted_question_mark_re = re.compile("%3[fF]")
from urllib.parse import unquote
def my_unquote(s):
    ret = unquote(s)
    ret = quoted_question_mark_re.sub("?", ret)
    return ret
serving.unquote = my_unquote

def init_app(app):
    app.debug = debug
    app.debug_sql = debug_sql

    from .db import init_app
    init_app(app)
