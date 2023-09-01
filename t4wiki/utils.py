import sys, os, os.path as op, fnmatch, shutil, types, functools, inspect, re
import subprocess, threading, collections
from collections.abc import MutableSet, Hashable
from urllib.parse import urlencode, quote_plus

from flask import g, current_app, request, session, redirect as flask_redirect

from t4 import sql
from t4.web import set_url_param
from t4.title_to_id import title_to_id
from t4.typography import improve_typography

from ll.xist import xsc
from ll.xist.ns import html

def redirect(url, **kw):
    if kw:
        if "?" in url:
            a, b = url.split("?", 1)
            url = a
            params = "?" + b + "&" + urlencode(kw, quote_via=quote_plus)
        else:
            params = "?" + urlencode(kw, quote_via=quote_plus)
    else:
        params = ""

    if url.startswith("/"):
        url = get_site_url() + url

    return flask_redirect(url + params)

def get_www_url(path, **kw):
    if kw:
        params = "?" + urlencode(kw, quote_via=quote_plus)
    else:
        params = ""

    return current_app.config["SITE_URL"] + params

def get_site_url(**kw):
    return get_www_url("/", **kw)

def rget(key, default=None):
    if key in request.args:
        return request.args[key]
    else:
        return request.form.get(key, default)

class RCheckedDefault: pass
def rchecked(key, default=RCheckedDefault):
    """
    Also see dbobject.rchecked()
    """
    if request.method == "POST":
        return (key in request.form)
    else:
        if default is RCheckedDefault:
            return None
        else:
            return default

def call_from_request(function, *args, **kw):
    # Assemble parameters from the current request.
    signature = inspect.signature(function)

    empty = inspect.Parameter.empty
    for name, param in signature.parameters.items():
        if name in kw:
            continue

        if param.default is not empty:
            kw[name] = param.default

        if issubclass(param.annotation, list):
            value = request.form.getlist(name)
            kw[name] = value
        else:
            value = rget(name, empty)
            if value is not empty:
                value = rget(name)

                # If an annotation has been supplied,
                # cast the value.
                if param.annotation is not empty:
                    try:
                        value = param.annotation(value)
                    except ValueError as e:
                        raise ValueError("%s: %s" % ( name, str(e), ))

                kw[name] = value

    return function(*args, **kw)

def gets_parameters_from_request(func):
    @functools.wraps(func)
    def wraped_for_parameters_from_request(*args, **kw):
        return call_from_request(func, *args, **kw)
    return wraped_for_parameters_from_request


class ObjFromDict:
    def __init__(self, d):
        self.d = d

    def __getitem__(self, key):
        return self.d[key]

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            try:
                return getattr(self.d, name)
            except AttributeError:
                raise AttributeError(name)

    def get(self, key, default=sys):
        try:
            return self[key]
        except KeyError:
            if default is sys:
                raise
            else:
                return default

class attr_dict(dict):
    """
    This will turn a dict into an object with equivalent attributes.
    Semantically this is not necesserily wise. Much like JavaScript,
    this blurs the difference between dict and object, but it
    frequently enables concise expressions.
    """
    def __getattr__(self, name):
        try:
            ret = self[name]
            if type(ret) is dict:
                return self.__class__(dict)
            else:
                return ret
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        self[name] = value


class FormParamHandler(object):
    def __init__(self, base_url=None, **kw):
        self.base_url = request.path
        self.kw = kw

    def href_to(self, **kw):
        if self.base_url:
            params = self.kw
            params.update(kw)
            return set_url_param(self.base_url, params)
        else:
            args = dict(request.args)
            args.update(kw)
            return request.path + "?" + urlencode(args)


class OrderByOption(object):
    def __init__(self, expression, label):
        """
        `expression` may be a string or an sql.orderby object.
        """
        self.expression = expression
        self.label = label
        self.id = title_to_id(label)

    def __eq__(self, other):
        if type(other) == str:
            return (self.id == other)
        else:
            return (self.id == other.id)

    def sql_clause(self):
        if type(self.expression) == str:
            return sql.orderby(self.expression)
        else:
            return self.expression

class OrderByHandler(FormParamHandler):
    def __init__(self, options, cookie_name, base_url=None, **kw):
        super().__init__(base_url=base_url, **kw)

        def make_option(o):
            if type(o) == tuple:
                option = OrderByOption(*o)
            else:
                option = o

            return (option.id, option,)

        self.options = collections.OrderedDict([make_option(o)
                                                for o in options])

        self.cookie_name = cookie_name
        self.kw = kw

        self.default = list(self.options)[0]

        new_active = rget("orderby")
        if new_active and new_active in self.options:
            session[self.cookie_name] = new_active

    @property
    def active(self):
        ret = rget("orderby") \
            or session.get(self.cookie_name, None) \
            or self.default

        # We need to check if the option exists, because the identifyer
        # may have been renamed, but somone might still have an old
        # cookie arround.
        if not ret in self.options:
            return self.options[self.default]
        else:
            return self.options[ret]

    def sql_clause(self):
        return self.active.sql_clause()

    def link_widget(self):
        buttons = xsc.Frag()

        active = self.active
        for option in self.options.values():
            if option == active:
                color = "btn-success"
            else:
                color = "btn-secondary"

            a = html.a(option.label,
                       href=self.href_to(orderby=option.id,
                                         page=0),
                       class_="btn " + color)
            a.attrs["data-id"] = option.id
            buttons.append(a)

        ret = html.div(buttons, class_="orderby-widget btn-group")
        return ret

    widget = link_widget

    def input_widget(self):
        buttons = xsc.Frag()

        active = self.active
        for option in self.options.values():
            if option == active:
                color = "btn-success"
            else:
                color = "btn-secondary"

            button = html.button(
                option.label,
                type="button",
                onclick=f"submit_orderby(this, '{option.id}')",
                class_="btn " + color)
            buttons.append(button)

        input = html.input(name="orderby",
                           type="text",
                           style="display: none; visibility: hidden")

        ret = html.div(buttons, input, class_="orderby-widget btn-group")
        return ret


    def display_class(self, id):
        if self.active == id:
            return "orderby-this"
        else:
            return ""

class empty_orderby_t:
    def display_class(self, t):
        return ""

empty_orderby = empty_orderby_t()

def pagination(overall_count, pagesize,
               baseurl=None, current_page=None, extra_class="", **kw):
    """
    extra_class => .pagination-large, .pagination-small,
                       or .pagination-mini
    """
    if overall_count is None: return xsc.Frag()
    if overall_count <= pagesize: return xsc.Frag()

    if baseurl is None:
        baseurl = "%s?%s" % ( request.path,
                              request.query_string.decode("utf-8"), )

    if kw: baseurl = set_url_param(baseurl, kw)

    if current_page is None:
        page = int(rget("page", "0"))
    else:
        page = current_page

    ret = html.nav()
    ul = html.ul(class_="pagination " + extra_class)
    ret.append(ul)

    pagecount = int(overall_count / pagesize)
    if overall_count % pagesize > 0:
        pagecount += 1

    def li(p, text=None):
        if text is None: text = str(p+1)
        if p >= 0 and p < pagecount:
            href = set_url_param(baseurl, {"page": p,
                                           "__ensure-reload": None})

            if p == page:
                cls = "active"
            else:
                cls = ""
        else:
            href = None
            cls = "disabled"

        ul.append(html.li(html.a(text, href=href, class_="page-link"),
                          class_="page-item " + cls))

    li(page-1, "«")
    for a in range(pagecount): li(a)
    li(page+1, "»")

    return ret


class PaginationHandler(FormParamHandler):
    def __init__(self, pagesize, count, base_url=None, **kw):
        super().__init__(base_url, **kw)

        self.pagesize = pagesize
        self.count = count

    @property
    def page(self):
        ret = int(rget("page", 0))
        if ret > int(self.count / self.pagesize):
            ret = 0
        return ret

    def sql_clauses(self):
        return ( sql.offset(self.page*self.pagesize),
                 sql.limit(self.pagesize), )

    def widget(self, extra_class="", **kw):
        return pagination(self.count, self.pagesize,
                          baseurl=self.base_url, current_page=self.page,
                          extra_class="", **kw)


class ViewsHandler(FormParamHandler):
    def __init__(self, possible_views, cookie_name,
                 pass_page=True,
                 base_url=None, **kw):
        super().__init__(base_url=base_url, **kw)

        self.possible_views = collections.OrderedDict(possible_views)
        self.cookie_name = cookie_name
        self.pass_page = pass_page

        new_active = rget("view")
        if new_active:
            assert new_active in self.possible_views, ValueError
            session[self.cookie_name] = new_active

    @property
    def active(self):
        return session.get(self.cookie_name, self.default)

    @property
    def default(self):
        return list(self.possible_views)[0]

    def widget(self):
        buttons = html.div(class_="view-widget btn-group")

        if self.pass_page:
            page = rget("page", None)
        else:
            page = 0

        active = self.active
        for id, label in self.possible_views.items():
            if id == active:
                color = "btn-primary"
            else:
                color = "btn-secondary"

            a = html.a(label,
                       href=self.href_to(view=id, page=page),
                       class_="btn " + color)
            buttons.append(a)

        return buttons


class FilterFormHandler(object):
    def __init__(self, session_identifyer, *parameters):
        self._session_identifyer = session_identifyer

        # This is where all the values will go:
        values = {}

        # Compile a list of the parameter names we are responsible for.
        self._parameter_names = set()
        for name, request_getter, default in parameters:
            self._parameter_names.add(name)

            # Initialize ourselves with the default values, just in case.
            values[name] = default

        # If a set of values is available, update ourseves accordingly. Check
        # if we are (still) responsable for each of the parameter names.
        # Otherwise values for renamed or removed parameters may stay in the
        # session object indefinetely.
        for name, value in session.get(self._session_identifyer, {}).items():
            if name in self._parameter_names:
                values[name] = value

        if request.method == "POST":
            for name, request_getter, default in parameters:
                value = request_getter(name, default)
                values[name] = value
            session[self._session_identifyer] = values

        self._values = values

    def __getattr__(self, name):
        return self._values[name]

    def __setattr__(self, name, value):
        # You can’t add a value, if it has not been initialized
        # by the constructor.
        if name[0] == "_":
            self.__dict__[name] = value
        else:
            assert name in self._values, NameError
            self._values[name] = value

class citextset(Hashable, MutableSet):
    """
    Implements a subset of the MutableSet interface ignoring
    string case on comparison.  The last occurance of a string will be
    saved as with-case version.
    """
    @staticmethod
    def _key(s):
        return s.lower()

    def __init__(self, initial=[]):
        # Maps lower case versions to actual strings.
        self.data = dict([(self._key(value), value)
                          for value in initial])

    def add(self, value):
        self.data[self._key(value)] = value

    def discard(self, value):
        try:
            del self.data[self._key(value)]
        except KeyError:
            pass

    def __contains__(self, value):
        return ( self._key(value) in self.data )

    def __iter__(self):
        return iter(self.data.values())

    def __len__(self):
        return len(self.data)

    def __repr__(self):
        if len(self) == 0:
            return self.__class__.__name__ + "()"
        else:
            return repr(set(self.data.values()))

    def __hash__(self):
        return hash(set(self.data.keys()))
