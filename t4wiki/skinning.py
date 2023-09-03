

# Example usage:
#
# def create_app():
#     from t4wiki import skinning
#     skin = skinning.Skin(app.config["SKIN_LOCATIONS"])
#     skin.register_with_app(app)
#     app.register_blueprint(skinning.bp)

import sys, os, os.path as op, time, datetime, re, dataclasses
import functools, threading, runpy, inspect
from pathlib import Path
from wsgiref.handlers import format_date_time
import chameleon, chameleon.tales

from flask import ( g, current_app as app, session, request,
                    Blueprint, abort, Response, )

from . import debug
from .utils import get_site_url, rget

startup_time = time.time()

module_load_lock = threading.Lock()
module_cache = {}

def cached_property_maybe(f):
    """
    If debugging is on, do not cache these properties.
    """
    if debug:
        return f
    else:
        return functools.cached_property(f)

class TemplateWithCustomRenderMethod(chameleon.PageTemplateFile):
    auto_reload = debug

    def render(self, **kw):
        from . import authentication

        extras = {"session": session,
                  "request": request,
                  "rget": rget,
                  "user": authentication.get_user(), }

        if hasattr(self, "filename") and self.filename != "<string>":
            extras["template_mtime"] = datetime.datetime.fromtimestamp(
                op.getmtime(self.filename))

        for key, value in extras.items():
            if key not in kw:
                kw[key] = value

        return super().render(**kw)

class FormatExpression(chameleon.tales.PythonExpr):
    def translate(self, expression, target):
        expression = expression.replace('"', r'\"')
        return chameleon.tales.PythonExpr.translate(
            self, 'f"' + expression + '"', target)

class CustomPageTemplateFile(TemplateWithCustomRenderMethod):
    expression_types = {**chameleon.PageTemplateFile.expression_types,
                        **{"f": FormatExpression}}

class CustomPageTemplate(TemplateWithCustomRenderMethod):
    expression_types = {**chameleon.PageTemplate.expression_types,
                        **{"f": FormatExpression}}

class CustomPageTemplateLoader(chameleon.PageTemplateLoader):
    formats = { "xml": CustomPageTemplateFile,
                "text": chameleon.PageTextTemplateFile, }

    def load(self, filename, format=None):
        if isinstance(filename, Path):
            filename = str(filename.absolute())
        else:
            filename = str(filename)

        return super().load(filename, format)

class MacrosPageTemplateWrapper(CustomPageTemplate):
    def __init__(self, macros_template, macro_name):
        self.macros_template = macros_template

        tmpl = '<metal:block metal:use-macro="macros_template[\'%s\']" />'
        super().__init__(tmpl % macro_name)

    def _builtins(self):
        builtins = chameleon.PageTemplate._builtins(self)
        builtins["macros_template"] = self.macros_template
        return builtins

class MacrosFrom:
    """
    This is a wrapper arround a Page Template containing only macro
    definitions. These are available as methods of this object.

    Macro example:

    ...
    <metal:block metal:define-macro="user-list">
       <div tal:repeat="user users">
         ... “my smart html” ...
       </div>
    </metal:block>

    mf = MacrosFrom(<page template>)
    mf.user_list(users) → “my smart html” with the users filled in

    """
    def __init__(self, template):
        self.template = template
        self._template_wrappers = {}

    def __getattr__(self, name):
        if debug:
            self._template_wrappers = {}
            self.template.cook_check()

        if not name in self._template_wrappers:
            macro = None
            for n in ( name.replace("_", "-"),
                       name, ):
                try:
                    macro = self.template.macros[n]
                except KeyError:
                    pass
                else:
                    break
            else:
                raise NameError("No macro named %s." % name)

            self._template_wrappers[name] = MacrosPageTemplateWrapper(
                self.template, n)

        return self._template_wrappers[name]

@dataclasses.dataclass
class SkinPath:
    fs_path: Path
    href: str

    def resource_exists(self, path):
        return self.resource_path(path).exists()

    def resource_path(self, path):
        return Path(self.fs_path, path)

    def url(self, path):
        return self.href + "/" + str(path)


class PathList(list):
    def __init__(self, paths):
        for fs, href in paths:
            self.append(SkinPath(fs, href))

    def first_that_has(self, path):
        path = Path(path)
        for skinpath in self:
            if skinpath.resource_exists(path):
                return skinpath

        return None

class Skin(object):
    def __init__(self, paths):
        self._paths = PathList(paths)
        self._pt_loader = CustomPageTemplateLoader(
            "/tmp",
            default_extension=".html",
            debug=debug,
            extra_builtins = self.extra_builtins)

    def register_with_app(self, app):
        if hasattr(app, "skin"):
            raise AttributeError("A skin has already been registered "
                                 "with this app.")
        app.skin = self

    @property
    def extra_builtins(self):
        """
        These elements are available globally in every template.
        """
        from . import ptutils

        return { "skin": self,
                 "test": ptutils.test,
                 "ptutils": ptutils, }

    @cached_property_maybe
    def resource_exists(self, path) -> bool:
        return self._paths.first_that_has(path) is not None

    @cached_property_maybe
    def resource_path(self, path)-> Path:
        skinpath = self._paths.first_that_has(path)
        if skinpath is None:
            raise IOError(f"No skin file found for {path}")
        return skinpath.resource_path(path)

    def href(self, path):
        if debug and not (".min." in path or path.endswith(".scss")):
            t = ""
        else:
            t = "?t=%f" % time.time()

        skinpath = self._paths.first_that_has(path)
        if skinpath is None:
            raise IOError(f"File not found: {path}")
        return skinpath.url(path) + t

    def read(self, path, mode="r"):
        return self.resource_path(path).open().read(mode)

    def script_tag(self, path):
        js = self.read(path)
        return "<script><!--\n%s\n// -->\n</script>" % js

    @property
    def site_url(self):
        return get_site_url()

    def load_template(self, path):
        path = self.resource_path(path)
        template = self._pt_loader.load(path.absolute())
        if debug:
            template.cook_check()
        return template

    @property
    def main_template(self):
        return self.load_template("main_template.pt")

    def macros_from(self, template_path):
        return MacrosFrom(self.load_template(template_path))


bp = Blueprint("templated_www", __name__, url_prefix="/templated_www")

template_path_re = re.compile("([a-z0-9][/a-z0-9_]*)\.([a-z]{2,3})")
@bp.route("/<path:template_path>", methods=['GET', 'POST'])
def html_files(template_path):
    if ".." in template_path:
        raise ValueError(template_path)

    path = Path(app.config["WWW_PATH"], template_path)

    if path.suffix == ".html":
        # HTML files are static.
        try:
            template = app.skin.load_template(path)
        except ValueError:
            err = f"{template_path} not found by loader."
            abort( 404, description=err)

        response = Response(template())
        if not debug:
            response.headers["Cache-Control"] = "max-age=604800"
            response.headers["Last-Modified"] = format_date_time(
                startup_time)
        return response

    elif template_path.suffix == ".py":
        match = template_path_re.match(path.name)
        if match is None:
            raise ValueError(f"Illegal template name {template_path}.")
        else:
            # Is there a default template?
            # A .pt file with the same name at the same
            # location?
            pt_path = Path(path.parent, path.suffix + ".pt")
            if pt_path.exists():
                template = app.skin.load_template(pt_path)
            else:
                template = None

            module_name, suffix = match.groups()

            with module_load_lock:
                if py_path in module_cache:
                    module = module_cache[py_path]
                else:
                    module = runpy.run_path(
                        py_path, run_name=module_name)
                    if not debug:
                        module_cache[py_path] = module

            function_name = module_name.rsplit("/", 1)[-1]
            if function_name in module:
                function = module[function_name]
            elif "main" in module:
                function = module["main"]
            else:
                raise ValueError(f"No function in {module_name}")

            if inspect.isclass(function):
                function = function()

            if template is None:
                return call_from_request(function)
            else:
                return call_from_request(function, template)
    else:
        raise ValueError(template_path)
