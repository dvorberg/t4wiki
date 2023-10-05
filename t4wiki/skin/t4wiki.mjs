export function title2path(title)
{
	return title.replace("?", "%3f");
}

document.addEventListener("DOMContentLoaded", function(event) {
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

