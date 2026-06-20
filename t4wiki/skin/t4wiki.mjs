export function title2path(title)
{
	return title.replace("?", "%3f");
}

const white_space_re = /\s+/;
export function normalize_whitespace(s)
{
	return s.trim().replace(white_space_re, " ");
}

document.addEventListener("DOMContentLoaded", function(event) {
	// Form tools
    function id_to_name(element)
    {
        if ( !element.hasAttribute("name") && element.hasAttribute("id") )
        {
            element.setAttribute(
                "name", element.getAttribute("id").replace(/-/g, "_"));
        }
    }
    document.querySelectorAll("form input").forEach(id_to_name);
    document.querySelectorAll("form textarea").forEach(id_to_name);
    document.querySelectorAll("form select").forEach(id_to_name);

	function submit_my_form(input_element)
    {
        input_element.form.submit();
    }
    
    function auto_submit_on_change(event)
    {
        submit_my_form(event.target);
    }
    
    document.querySelectorAll(
        "input[type=radio].auto-submit").forEach(
            input => {
                input.addEventListener("change", auto_submit_on_change);
            });
    document.querySelectorAll(
        "input[type=checkbox].auto-submit").forEach(
            input => {
                input.addEventListener("change", auto_submit_on_change);
            });

    document.querySelectorAll(
        "select.auto-submit").forEach(
            input => {
                input.addEventListener("change", auto_submit_on_change);
            });

    function auto_submit_search_on_clear(event)
    {
        if (event.target.value == "")
        {
            submit_my_form(event.target);
        }
    }

    class KeyPressAutosubmitter
    {
        constructor(input)
        {
            this.input = input;
            this.timer = null;
            input.addEventListener("keyup", this.on_keyup.bind(this));
        }

        on_keyup(event)
        {
            if (this.timer !== null)
            {
                clearTimeout(this.timer);
            }
            this.timer = setTimeout(this.on_timeout.bind(this), 250);
        }

        on_timeout(event)
        {
            this.timer = null;
            submit_my_form(this.input);
        }
    }

    document.querySelectorAll(
        "input[type=search].auto-submit").forEach(
            input => {
                input.addEventListener("search", auto_submit_search_on_clear);

                // Nervig:
                // new KeyPressAutosubmitter(input);
            });


	// OrderBy Widget
	document.querySelectorAll("button.orderby-button").forEach(button => {
		button.addEventListener("click", event => {
			let form = button.form,
				input = form.querySelector("input[name=orderby]");
			input.value = button.getAttribute("data-option-id");
			form.submit();			
		});
	});
	
	// Manage .stretch-to-bottom class
	function on_resize(event)
	{
		const div = document.querySelector(".stretch-to-bottom");
		if (div)
		{
			const r = div.getBoundingClientRect(),
				  mb = parseInt(div.getAttribute("data-margin-bottom")) || 120,
				  h = window.innerHeight - r.y - mb;
			if (h > 0)
			{
				div.style.height = h + "px";
			}
			
		}
	}

	on_resize();
	window.addEventListener("resize", on_resize);
});


document.addEventListener("DOMContentLoaded", function(event) {
    ////////////////////////////////////////////////////////////
    const local_storage_prefix = "filter-param";

    class FormButtonHandler
    {
        constructor(param_handler, button)
        {
            let self = this;

            this.param_handler = param_handler;
            this.button = button;
            this.button.addEventListener( "click", self.on_click.bind(self));
        }

        get id() {
            return this.button.getAttribute("data-id");
        }

        set active(a) {
            if (a)
            {
                this.button.classList.replace("btn-secondary", "btn-primary");
            }
            else
            {
                this.button.classList.replace("btn-primary", "btn-secondary");
            }
        }

        get active()
        {
            return this.button.classList.contains("btn-primary");
        }

        on_click(event)
        {
            this.param_handler.set_id(this.id, true);

            if (this.param_handler.auto_submit)
            {
                this.param_handler.form.store_params();
                this.param_handler.form.submit();
            }
        }
    }

    class FormParamHandler
    {
        constructor(form, widget)
        {
            let self = this;

            this.form = form;
            this.widget = widget;

            this.buttons = Array.from(widget.querySelectorAll(".btn")).map(
                button => new FormButtonHandler(self, button));
            var p = `input[data-for=${this.param_name}]`;
            this.input = document.querySelector(p);

            let stored_param = this.form.get_param(this.param_name);
            if ( this.active )
            {
                this.set_id(this.active.id);
            }
            else if (stored_param)
            {
                this.set_id(stored_param, true);
            }
            else
            {
                this.set_id(this.default.id, true);
            }
        }

        set_id(id, activate_button)
        {
            this.input.value = id;

            if (activate_button)
            {

                let active_button = this.by_id(id);

                this.buttons.forEach(button => {
                    if (button == active_button)
                    {
                        button.active = true;
                    }
                    else
                    {
                        button.active = false;
                    }
                });
            }
        }

        get param_name()
        {
            return this.widget.getAttribute("data-for");
        }

        get default()
        {
            return this.buttons[0];
        }

        get active()
        {
            return this.buttons.find(button => button.active);
        }

        set active(new_active)
        {
            this.set_id(new_active.id);
            new_active.active = true;
        }

        get auto_submit()
        {
            return this.widget.classList.contains("auto-submit");
        }

        by_id(id)
        {
            return this.buttons.find(button => button.id == id);
        }
    }

    class PaginationHandler
    {
        constructor(form_handler)
        {
            let self = this;

            this.form_handler = form_handler;

            let links = this.form.querySelectorAll(".pagination a.to-page");

            links.forEach( a => {
                let page = parseInt(a.getAttribute("href"));
                a.setAttribute("href", "javascript:{}");
                a.addEventListener("click", event => {
                    self.form.goto_page(page);
                });
            });

			let ells = this.form.querySelectorAll(".pagination a.ellipsis");
			ells.forEach( a => {
				a.setAttribute("href", "javascript:{}");
			});

            this.form.reset_page();
        }

        get form()
        {
            return this.form_handler.form;
        }
    }

    class FormFilterHandler
    {
        constructor(form)
        {
            this.form = form;

            this.form.store_params = this.store_params.bind(this);
            this.form.get_param = this.get_param.bind(this);
            this.form.reset_filter = this.reset_filter.bind(this);
            this.form.goto_page = this.goto_page.bind(this);
            this.form.reset_page = this.reset_page.bind(this);

            this.param_handlers = Array.from(
                form.querySelectorAll(".formparam-widget")).map(
                    widget => new FormParamHandler(form, widget));

            this.form.addEventListener(
                "submit", this.store_params.bind(this), false);

            let reset_button = this.form.querySelector(".filter-reset-button");
            if (reset_button)
            {
                reset_button.addEventListener(
                    "click", this.reset_filter.bind(this));
            }

            this.pagination = new PaginationHandler(this);
        }


        get form_id()
        {
            let id = this.form.getAttribute("id");
            if ( ! id)
            {
                id = window.location.pathname;
            }

            return id;
        }

        store_params()
        {
            this.param_handlers.forEach(ph => {
                let key =
                    `${local_storage_prefix}-${this.form_id}-${ph.param_name}`;
                window.localStorage.setItem(key, ph.active.id);
            });
        }

        get_param(name)
        {
            let key = `${local_storage_prefix}-${this.form_id}-${name}`;
            return window.localStorage.getItem(key);
        }

        reset_filter()
        {
            this.param_handlers.forEach(ph => {
                ph.active = ph.default;
            });
        }

        reset_page()
        {
            this.set_page_widget(0);
        }

        set_page_widget(page)
        {
            let widget = this.form.querySelector("input[name=page]");
            if (widget)
            {
                widget.value = page;
            }
        }

        goto_page(page)
        {
            this.set_page_widget(page);
            this.form.submit();
        }
    }

    let forms = document.querySelectorAll("form.filtered");
    if (forms)
    {
        forms.forEach(form => {
            form.filter = new FormFilterHandler(form);
        });
    }


    function add_search_params_to(form_id, form, overwrite)
    {
        // Boolean return value indicates, whether form settings were found
        // in local storage.         
        var ret = false;
        
        if ( ! overwrite )
        {
            overwrite = {};
        }

        for(var a = 0; a < window.localStorage.length; a++)
        {
            let prefix = `${local_storage_prefix}-${form_id}-`,
                key = window.localStorage.key(a);

            if ( key.startsWith(prefix) )
            {
                var value = window.localStorage.getItem(key),
                    name = key.substring(prefix.length),
                    input = document.createElement("INPUT");

                if ( overwrite[name] )
                {
                    value = overwrite[name];
                }

                input.setAttribute("name", name);
                input.setAttribute("value", value);
                input.setAttribute("style", "display:none;visibility:hidden");

                form.appendChild(input);

                ret = true;
            }
        }

        return ret;
    }

    let search_form = document.querySelector("#nav-search-form");
    if (search_form)
    {
        let added_inputs = add_search_params_to(
            "episodes", search_form, { orderby: "suche"} );

        if (added_inputs)
        {
            const link = document.querySelector("#to-eposodes-filter");

            if (link)
            {
                link.setAttribute("href", "javascript:{}");
                
                link.addEventListener("click", event => {
                    search_form.submit();
                });
            }
        }
    }
});
