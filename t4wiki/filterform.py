import sys, collections

from flask import request, session

from t4.title_to_id import title_to_id
from sqlclasses import sql

from ll.xist import xsc
from ll.xist.ns import html

from .db import query, rollup_sql
from .utils import rget

def pageget():
    page = rget("page", 0)
    if page == "":
        return 0
    else:
        return int(page)

class FormParamOption(object):
    sql_expression_class = sql.where

    def __init__(self, expression, label, group=None,
                 extra_button_class=None, id=None,):
        """
        `expression` may be a string or an self.sql_expression_class object.
        """
        if type(expression) is str:
            self.expression = self.sql_expression_class(expression)
        else:
            self.expression = expression

        self.label = label

        if id:
            self.id = id
        else:
            if group:
                self.id = title_to_id(f"{label} {group}")
            else:
                self.id = title_to_id(label)

        self.group = group
        self.extra_button_class = extra_button_class

    def __eq__(self, other):
        if type(other) == str:
            return (self.id == other)
        elif type(other) == type(self):
            return (self.id == other.id)
        else:
            return False

    def sql_clause(self):
        if type(self.expression) == str:
            return self.sql_expression_class(self.expression)
        else:
            return self.expression

class FormParamHandler(object):
    option_class = FormParamOption

    def __init__(self, options, param_name, auto_submit=False):
        self.options = collections.OrderedDict()

        for o in options:
            if type(o) == tuple:
                option = self.option_class(*o)
            else:
                option = o

            if option.id in self.options:
                raise KeyError(f"Duplicate param id: {repr(option.id)}")
            self.options[option.id] = option

        self.param_name = param_name
        self.auto_submit = auto_submit

        self.default = list(self.options)[0]


    @property
    def active(self):
        ret = rget(self.param_name) or self.default

        # We need to check if the option exists, because the identifyer
        # may have been renamed, but somone might still have an old
        # cookie arround.
        if not ret in self.options:
            return self.options[self.default]
        else:
            return self.options[ret]

    def sql_clause(self):
        return self.active.sql_clause()

    def button_for(self, option, color):
        cls = [ "btn", ]
        if color:
            cls.append(color)

        if option.extra_button_class:
            cls.append(option.extra_button_class)

        return html.button( option.label, type="button",
                            class_=" ".join(cls),
                            **{"data-id": option.id} )

    def widget(self):
        cls = ["formparam-widget", f"{self.param_name}-widget"]

        if self.auto_submit:
            cls.append("auto-submit");

        ret = html.div(class_="btn-toolbar", role="toolbar")
        buttons = None
        current_group = sys

        if request.method == "POST":
            active = self.active
        else:
            active = None

        for option in self.options.values():
            if option.group != current_group:
                buttons = html.div(class_="btn-group me-2")
                ret.append(buttons)
                current_group = option.group

            if option == active:
                color = "btn-primary"
            else:
                color = "btn-secondary"

            buttons.append(self.button_for(option, color))

        if len(ret) == 1:
            ret = ret[0]

        ret["class"] += " " + " ".join(cls)
        ret["data-for"] = self.param_name
        return xsc.Frag(ret, html.input(name=self.param_name, type="text",
                                        class_="formparam-input",
                                        **{"data-for": self.param_name}))

class empty_orderby_t:
    def display_class(self, t):
        return ""

class OrderByOption(FormParamOption):
    sql_expression_class = sql.orderby

class OrderByHandler(FormParamHandler):
    option_class = OrderByOption

# empty_orderby = empty_orderby_t()

class PaginationHandler(FormParamHandler):
    def __init__(self, pagesize, count):
        self.options = []

        self.param_name = "page"
        self.pagesize = pagesize
        self.count = count

    @property
    def needed(self):
        return self.count > self.pagesize

    @property
    def page(self):
        page = pageget()
        if page > int(self.count / self.pagesize):
            page = 0
        return page

    def sql_clauses(self):
        return ( sql.offset(self.page*self.pagesize),
                 sql.limit(self.pagesize), )

    def widget(self, extra_class="", **kw):
        """
        extra_class => .pagination-large, .pagination-small,
                           or .pagination-mini
        """
        if self.count is None: return xsc.Frag()
        if self.count <= self.pagesize: return xsc.Frag()

        page = pageget()

        ret = html.nav()
        ul = html.ul(class_="pagination " + extra_class, **kw)
        ret.append(ul)

        pagecount = int(self.count / self.pagesize)
        if self.count % self.pagesize > 0:
            pagecount += 1

        def li(p, text=None):
            if text is None: text = str(p+1)
            if p >= 0 and p < pagecount:
                href = str(p)
                if p == page:
                    cls = "active"
                else:
                    cls = ""
            else:
                href = None
                cls = "disabled"

            ul.append(html.li(html.a(text, href=href,
                                     class_="page-link"),
                              class_="page-item " + cls))

        li(page-1, "«")
        for a in range(pagecount): li(a)
        li(page+1, "»")

        ret.append(html.input(name=self.param_name, type="text",
                              class_="formparam-input",
                              **{"data-for": self.param_name}))

        return ret

class ViewOption(FormParamOption):
    def __init__(self, label, id=None, group=None, extra_button_class=None):
        super().__init__(None, label, group, extra_button_class, id)

    def sql_clause(self):
        raise NotImplementedError()

class ViewsHandler(FormParamHandler):
    option_class = ViewOption

# AndreasPager, named after my good friend Andreas Junge, who came up with
# this design as a programming challange, display from–to values for each
# the the pagerʼs pages. The PagerOptions must be identical to the
# OrderByOptions used to formulate the query and go into the OrderByHandler
# as well as the AndreasPager below.
class AndreasPagerOption(OrderByOption):
    def __init__(self, expression, label, group=None,
                 extra_button_class=None, id=None,
                 pager_button_label_f=lambda s: str(s),
                 select_expressions=None,
                 midlinknum=5):
        """
        • “pager_button_label_f”: The AndreasPager knows the dbobject class
          for the result to be displayed. Objects of that class will be
          instantiated for each row and passed to the pager_button_label_f.
          The function will be called as: pager_button_label_f(dbobject). 
          If None, a page number will be displayed, no a–b pattern. 
        • “select_expressions” is a tuple of column names used in the SELECT.
          If None, “*” will be used fetching all expressions.
        """
        super().__init__(expression, label, group, extra_button_class, id)
        self.pager_button_label_f = pager_button_label_f
        self.select_expressions = select_expressions
        self.midlinknum = midlinknum
        
class AndreasPager(PaginationHandler):
    def __init__(self, pagesize, count, orderby_handler,
                 dbclass, where, orderby, *sqlclauses):
        """
        The orderby_handler here must be initialized with
        AndreasPagerOptions.
        """
        super().__init__(pagesize, count)
        self.orderby_handler = orderby_handler
        self.dbclass = dbclass
        self.where = where
        self.orderby = orderby
        self.sqlclauses = sqlclauses

    def run_query(self):
        expressions = self.orderby_handler.active.select_expressions
        if expressions is None:
            expressions = "*"

        select = sql.select(expressions, (self.dbclass.__view__,),
                            self.where, self.orderby, *self.sqlclauses)

        with_ = sql.with_(
            ("res", select,),
            ("e", sql.select(
                ("ROW_NUMBER() OVER () AS __row_id", "*"), ("res",)),),
            ("tail", sql.select( ("MAX(__row_id) AS tail",
                                  "%i AS __pagesize" % self.pagesize),
                                 ("e",))),
            sql.select( expressions,
                        ("e", "tail"),
                        sql.where("__row_id %% __pagesize = 0",
                                  " OR ",
                                  "(__row_id - 1) %% __pagesize = 0",
                                  " OR ",
                                  "__row_id = tail.tail")))

        return query(with_, dbobject_class=self.dbclass)

    def widget(self, extra_class="", **kw):
        """
        midlinknum => Number of links “in the middle” between to optional
           “…” items. 
        extra_class => .pagination-large, .pagination-small,
                           or .pagination-mini
        """
        if self.count is None: return xsc.Frag()
        if self.count <= self.pagesize: return xsc.Frag()

        midlinknum = self.orderby_handler.active.midlinknum
        label_f = self.orderby_handler.active.pager_button_label_f

        pagecount = int(self.count / self.pagesize)
        if self.count % self.pagesize > 0:
            pagecount += 1

        if label_f is None:
            pages = [ (a, str(a+1)) for a in range(pagecount)]
        else:
            rows = self.run_query()
            def pages():
                i = iter(rows)
                p = 0
                while True:
                    try:
                        yield (p, label_f(next(i)) + "–" + label_f(next(i)),)
                        p += 1
                    except StopIteration:
                        break
            pages = list(pages())
                
        current = pageget()

        nav = html.nav()
        ret = xsc.Frag(nav)
        mainul = html.ul(class_="pagination" + extra_class, **kw)
        nav.append(mainul)

        def addli(ul, page):
            p, label = page
            
            if p >= 0 and p < pagecount:
                href = str(p)
                if p == current:
                    cls = "active"
                else:
                    cls = ""
            else:
                href = None
                cls = "disabled"

            if ul == mainul:
                li = html.li(html.a(label, href=href,
                                    class_="page-link to-page"),
                             class_="page-item " + cls)
            else:
                li = html.li(html.a(label, href=href,
                                    class_="dropdown-item to-page"))

            ul.append(li)
            
        def addlis(ul, pages):
            for page in pages:
                addli(ul, page)

        def make_dropdown():
            li = html.li(class_="page-item")
            button = html.a("…", class_="page-link ellipsis",
                            **{"data-bs-toggle": "dropdown"})
            li.append(button)
            
            ul = html.ul(class_="dropdown-menu")
            li.append(ul)

            mainul.append(li)
            
            return ul

        addli(mainul, (current-1, "«"))

        if pagecount <= midlinknum+1:
            addlis(mainul, pages)
        else:
            if current < midlinknum - 1:
                # only a right …
                addlis(mainul, pages[:midlinknum])
            
                dropdown = make_dropdown()
                addlis(dropdown, pages[midlinknum:-1])

                addli(mainul, pages[-1])
            elif current > pagecount - midlinknum - 1:
                # only a left …
                addli(mainul, pages[0])
                
                r = pagecount - midlinknum                
                dropdown = make_dropdown()
                addlis(dropdown, pages[1:r])

                addlis(mainul, pages[r:])                
            else:
                # both (current // midlinknum) * midlinknum  #                 
                l = current - midlinknum//2
                r = l + midlinknum

                addli(mainul, pages[0])
                
                ldropdown = make_dropdown()
                addlis(ldropdown, pages[1:l])

                addlis(mainul, pages[l:r])
                       
                rdropdown = make_dropdown()
                addlis(rdropdown, pages[r:-1])

                addli(mainul, pages[-1])
            
        addli(mainul, (current+1, "»"))

        ret.append(html.input(name=self.param_name, type="text",
                              class_="formparam-input",
                              **{"data-for": self.param_name}))

        return ret

    
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

