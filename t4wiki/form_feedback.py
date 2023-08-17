import html

from .utils import rget
import t4.res
from t4.typography import parse_german_date

from ll.xist import xsc
from ll.xist import parse as xist_parse
from ll.xist.ns import html as xist_html_ns


# Dummy
def _(s): return s

class FieldFeedback:
    def __init__(self, feedback, *args, **kw): # is_valid=False
        self._feedback = feedback
        self._is_valid = kw.get("is_valid", False)
        self._args = args
        self._kw = kw

    @property
    def field_class(self):
        """
        Return `is-valid` or `is-invalid` depending on this feedback’s
        validity.
        """
        # These string should be custumizable.
        if self.is_valid:
            return "is-valid"
        else:
            return "is-invalid"

    cls = field_class

    @property
    def is_valid(self):
        return self._is_valid

    @property
    def is_invalid(self):
        return (not self._is_valid)

    def __str__(self):
        return self._feedback.format(*self._args, **self._kw)

    @property
    def html(self):
        if self.is_invalid:
            return '<div class="invalid-feedback">%s</div>' % (
                html.escape(str(self)), )
        else:
            return ''

class FieldException(FieldFeedback):
    def __init__(self, exception):
        FieldFeedback.__init__(self,
                               str(exception),
                               is_valid=False)
        self._exception = exception

class NotValidated:
    cls = ""
    field_class = ""
    html = ""

    def __str__(self):
        return ""

    @property
    def field_class(self):
        return ""

    @property
    def is_invalid(self):
        return False

    @property
    def input_class(self):
        return ""

class DefaultFieldFeedback(FieldFeedback):
    def __init__(self, is_valid):
        FieldFeedback.__init__(self, "", is_valid=is_valid)

not_empty_message = "Dieses feld darf nicht leer sein."
class FormFeedback:
    form_class = "has-validation"

    def __init__(self, errors=None, default_to=True):
        """
        @default_to: True -> Default to `is_valid`
                     False -> Default to `is_invalid`
                     None -> Return an NotValidated object.
        """
        self._feedbacks = {}
        self.default_to = default_to

        if errors is None:
            pass
        elif isinstance(dict, errors) or isinstance(FormFeedback, errors):
            for field_name, feedback in errors.items():
                self._feedbacks[field_name] = feedback
        else:
            raise TypeError("FormFeedback must be initialized either with a "
                            "dict or None as first parameter.")

    def __setitem__(self, field_name, error):
        if type(error) == str:
            self._feedbacks[field_name] = FieldFeedback(error)
        elif isinstance(error, Exception):
            self._feedbacks[field_name] = FieldException(error)
        elif isinstance(error, FieldFeedback):
            self._feedbacks[field_name] = error
        else:
            raise TypeError(("A validation result must be either a string "
                             "or an instance of field_validation_result. "
                             "Got: %s") % repr(error))

    def __contains__(self, field_name):
        return ( field_name in self._feedbacks )

    def __getitem__(self, field_name):
        return self.on(field_name)

    def __getattr__(self, field_name):
        return self.on(field_name)

    def on(self, field_name):
        if not field_name in self:
            if self.default_to is None:
                return NotValidated()
            else:
                return DefaultFieldFeedback(self.default_to)
        else:
            return self._feedbacks[field_name]


    def keys(self):
        return self._feedbacks.keys()

    def values(self):
        return self._feedbacks.values()

    def items(self):
        return self._feedbacks.items()

    def get(self, name, default=None):
        return self._feedbacks.get(name)

    def is_valid(self):
        for feedback in self._feedbacks.values():
            if not feedback.is_valid:
                return False

        return True

    def __bool__(self):
        return self.is_valid()

    def give(self, field_name, feedback, *args, **kw): # is_valid=False,
        self[field_name] = FieldFeedback(feedback, *args, **kw)

    def validate_not_empty(self, field_name):
        value = rget(field_name, "")
        if value.strip() == "":
            self.give(field_name, _(not_empty_message))
            #_("This field must not be empty."))

    def validate_email(self, field_name):
        value = rget(field_name, "")
        if not t4.res.email_re.match(value):
            #msg = _("Not a valid email address: „{}“").format(value)
            msg = _("Keine gültige e-Mail Adresse: „{}“").format(value)
            self.give(field_name, msg)

    def validate_html(self, field_name):
        value = rget(field_name, "")

        try:
            node = xist_parse.tree(
                xist_parse.String(value.encode("utf-8")),
                xist_parse.Expat(),
                xist_parse.NS(xist_html_ns),
                xist_parse.Node(pool=xsc.Pool(xist_html_ns)))
        except Exception as e:
            self.give(field_name, str(e))


    def validate_login(self, field_name="login"):
        value = rget(field_name, "")
        if not t4.res.login_re.match(value):
            #msg = _("Not a valid user name: „{}“").format(value)
            msg = _("Kein gültiger Benutzername: „{}“").format(value)
            self.give(field_name, msg)

    def ensure_int(self, field_name, required=True):
        value = rget(field_name, "")

        if (value is None or value.strip() == "") and not required:
            return None

        try:
            return int(value)
        except ValueError:
            msg = _("Bitte geben Sie eine Ganzzahl ein statt „{}“").format(
                value)
            self.give(field_name, msg)
            return None
    validate_int = ensure_int

    def ensure_uint(self, field_name, required=True):
        value = rget(field_name, "")

        if (value is None or value.strip() == "") and not required:
            return None

        try:
            if int(value) < 0:
                raise ValueError
            return value
        except ValueError:
            msg = _("Bitte geben Sie eine Ganzzahl ein statt „{}“").format(
                value)
            self.give(field_name, msg)
            return None
    valudate_uint = ensure_uint

    def ensure_german_date(self, field_name, required=True):
        value = rget(field_name, "")
        if value.strip() == "":
            if required:
                self.give(field_name, _(not_empty_message))

            return None

        try:
            return parse_german_date(value)
        except ValueError:
            self.give(field_name,
                      _("Bitte geben Sie ein Datum ein (tt.mm.jjjj)."))
            return None

    validate_german_date = ensure_german_date


    def normalize_bibref(self, field_name, required=True):
        # , normalize_bibref, BibleReferenceParseError
        if required:
            self.validate_not_empty(field_name)

        value = rget(field_name, "")
        if value:
            try:
                value = normalize_bibref(value)
            except BibleReferenceParseError:
                self.give(field_name, "Keine gültige Bibelstelle.")
                return None
            else:
                return value

    validate_bibref = normalize_bibref



class NullFeedback(FormFeedback):
    form_class = ""

    def __getitem__(self, key):
        return NotValidated()

    def is_valid(self):
        return True

    def give(self, field_name, feedback, *args, **kw):
        raise NotImplemented()

    def on(self, field_name):
        return NotValidated()
