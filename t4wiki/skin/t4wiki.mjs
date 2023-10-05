export function title2path(title)
{
	return title.replace("?", "%3f");
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

