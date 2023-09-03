class SearchbarManager
{
    constructor()
    {
        document.addEventListener("DOMContentLoaded",
                                  this.on_dom_content_loaded.bind(this));
    }

    on_dom_content_loaded(event)
    {
        this.input = document.querySelector("form#searchbar input");
        this.input.addEventListener(
            "keypress", this.on_input_keypress.bind(this));

        document.addEventListener(
            "keypress", this.on_document_keypress.bind(this));

        if (!document.querySelector("main form"))
        {
            this.input.focus();
            this.input.select();
        }

        var numbered_links = {};
        document.querySelectorAll(
            "span.ctrl-no-jump-target").forEach(function(span) {
                const no = parseInt(span.textContent),
                      title = span.parentNode,
                      entry = title.parentNode,
                      link = entry.querySelector("a[href]");
                if (link)
                {
                    const href = link.getAttribute("href");
                    numbered_links[no] = href;
                }
            });

        this.numbered_links = numbered_links;
    }

    on_input_keypress(event)
    {
        if (event.key == "Enter")
        {
            event.preventDefault();

            var href = globalThis.site_url + "/" + this.input.value;

            if (event.getModifierState("Shift"))
            {
                href += "?search";
            }
            
            window.location.href = href;
        }
    }

    on_document_keypress(event)
    {
        if (event.key == "f" && event.getModifierState("Control"))
        {
            this.input.focus();
            this.input.select();
        }
        else if (event.getModifierState("Control"))
        {
            const no = parseInt(event.key);
            if (no)
            {
                window.location.href = this.numbered_links[no];
            }
        }
    }
}

export { SearchbarManager };


