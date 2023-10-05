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
