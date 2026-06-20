import sys, os, os.path as op, fnmatch, shutil, types, functools, inspect, re
import subprocess, threading, collections
from collections.abc import MutableSet, Hashable
from urllib.parse import urlencode, quote_plus

from flask import (g, current_app as app, request, session,
                   redirect as flask_redirect)

from t4 import sql
from t4.web import set_url_param
from t4.title_to_id import title_to_id
from t4.typography import improve_typography

from ll.xist import xsc
from ll.xist.ns import html

def get_languages():
    return app.config["LANGUAGES"]

def get_article_root_languages():
    isos = app.config.get("ARTICLE_ROOT_LANGUAGE_ISOS",
                          tuple(get_languages().keys()))
    languages = get_languages()
    return [ languages.by_iso(iso) for iso in isos ]


def title2path(title):
    return title.replace("?", "%3f")

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

    return app.config["APPLICATION_ROOT"] + params

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
