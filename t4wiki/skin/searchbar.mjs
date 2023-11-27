import { title2path } from "t4wiki";

class SearchbarManager
{       
    constructor()
    {
        document.addEventListener("DOMContentLoaded",
                                  this.on_dom_content_loaded.bind(this));
        this.f_key_re = /F\(?(\d)\)?/;
    }    

    on_dom_content_loaded(event)
    {
        this.input = document.querySelector("form#searchbar input");

        if (!this.input)
        {
            // Search bar HTML is not part of the current document. 
            return
        }
        
        this.input.addEventListener(
            "keydown", this.on_input_keydown.bind(this));

        document.addEventListener(
            "keydown", this.on_document_keydown.bind(this));

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

    on_input_keydown(event)
    {
        if (event.key == "Enter")
        {
            event.preventDefault();

            var href = globalThis.site_url + "/" + title2path(this.input.value);

            if (event.getModifierState("Shift"))
            {
                href += "?search";
            }
            
            window.location.href = href;
        }
    }

    on_document_keydown(event)
    {
        const meta = (event.getModifierState("Meta") ||
                      event.getModifierState("OS")),
              control = event.getModifierState("Control");

        if (meta)
        {
            if (event.key == "s")
            {
                this.input.focus();
                this.input.select();

                event.preventDefault();
            }
            else if (event.key == "k")
            {
                window.location.href = globalThis.site_url;
                event.preventDefault();
            }
        }
        
        if (control)
        {
            const no = parseInt(event.key);
            if (no)
            {
                window.location.href = this.numbered_links[no];
                event.preventDefault();
            }
        }

        const match = this.f_key_re.exec(event.key);
        if (match)
        {
            const no = parseInt(match[1]);
            for(const a of document.querySelectorAll("a[href].f-key"))
            {
                const small = a.querySelector("small");
                if (small)
                {
                    const match = this.f_key_re.exec(small.textContent);
                    if (match)
                    {
                        const found_no = parseInt(match[1]);
                        
                        if (found_no && found_no == no)
                        {
                            window.location.href = a.getAttribute("href");
                            break;
                        }
                    }
                }
            }
        }

        // The Escape key opens the menu.
        // Does this need a condition?
        // document.querySelector("article.main") !== null && 
        if (event.key == "Escape")
        {
            document.querySelector("button.dropdown-toggle").click()
        }
    }
}

export { SearchbarManager };


