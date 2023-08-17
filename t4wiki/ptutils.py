#!/usr/bin/env python
# -*- mode: python; coding: utf-8 -*-

##  Copyright 2003–2023 by Diedrich Vorberg <diedrich@tux4web.de>
import sys, types, re, decimal
from gettext import gettext as _
from html import escape

from flask import request

from .utils import *

from t4.web import add_url_param, set_url_param, js_string_literal
from t4.typography import (pretty_duration, pretty_bytes, pretty_german_date,
                           add_web_paragraphs)

pretty_date = pretty_german_date


def checked(b):
    if b: return "checked"

def selected(b):
    if b: return "selected"

def active(b):
    if b: return "active"

def disabled(b):
    if b: return "disabled"

extension_from_url_re = re.compile(r".*\.([^\.]+)$")
def extension_from_url(url):
    match = extension_from_url_re(url)
    if match is None:
        return None
    else:
        extension, = match.groups()
        return extension

def test(condition, a, b=None):
    if condition:
        return a
    else:
        return b

def exclass(class_, *other_classes):
    names = [ class_, ] + list(other_classes)
    names = filter(lambda s: bool(s), names)
    names = [ s.strip() for s in names ]
    return " ".join(names)

def html_with_paras(s):
    s = s.replace("\r\n", "\n")
    paras = s.split("\n\n")
    paras = [ '<p>'+escape(p.strip()).replace("\n", "<br/>")+'</p>'
              for p in paras ]
    return "\n".join(paras)

def delete_onclick(title, tmpl="Would you really like to delete “{}”?"):
    question = _(tmpl).format(title)
    return f"return confirm({js_string_literal(question)})"
