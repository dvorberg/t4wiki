class ArticleManager
{
    constructor(id_by_title, info_by_id, link_info)
    {
        this.id_by_title = id_by_title;
        this.info_by_id = info_by_id;

        // Make a lower case copy of each of the link targets.
        this.link_info = link_info;
        for (var key in this.link_info)
        {
            var value = this.link_info[key];
            this.link_info[key.toLowerCase()] = value;
        }

        document.addEventListener("DOMContentLoaded",
                                  this.on_dom_content_loaded.bind(this));
    }

    on_dom_content_loaded(event)
    {
        var self = this;
        
        // Deal with includes.
        this.main_article = document.querySelector("article.main");
        this.main_article_id = parseInt(
            this.main_article.getAttribute("data-article-id"));
        this.article_section = this.main_article.parentNode.parentNode;

        var parent = this.main_article.parentNode,
            included = parent.querySelectorAll("article.included"),
            included_by_id = {};
        
        included.forEach(function(article) {
            var id = parseInt(article.getAttribute("data-article-id"));
            included_by_id[id] = article;
        });
        
        this.main_article.querySelectorAll(
            "div.t4wiki-include").forEach(function(div) {
                var title = div.getAttribute("data-article-title"),
                    id = self.id_by_title[title],
                    article = included_by_id[id];
                
                if (article)
                {
                    for(const child of article.childNodes)
                    {                        
                        div.appendChild(child.cloneNode(true));
                    }
                    article.remove();
                    self.id_by_title[title] = null;
                }
            });

        // Collect footnotes and move them to the end of the document.
        const footnotes = this.main_article.querySelectorAll(".footnote"),
              aside = this.article_section.querySelector("aside"),
              footnote_div = aside.querySelector(".footnotes"),
              footnote_list = footnote_div.querySelector("ol");
        if (footnotes.length == 0)
        {
            footnote_div.remove();
        }
        else
        {
            var counter = 1;
            for(const footnote of footnotes)
            {
                const id = "footnote-" + counter;
                
                const li = document.createElement("LI");
                li.setAttribute("id", id);
                for (const child of footnote.childNodes)
                {
                    li.appendChild(child.cloneNode(true));
                }                
                footnote_list.appendChild(li);

                const mark = document.createElement("A");
                mark.classList.add("footnote-mark");
                mark.setAttribute("href", "#" + id);
                mark.appendChild(document.createTextNode(counter));
                footnote.replaceWith(mark);
            }
        }

        
        // Go through the links and set their targets correctly.
        // Also set link classes.
        this.article_section.querySelectorAll("a.t4wiki-link").forEach(
            function(a) {
                var href = decodeURI(a.getAttribute("href")),
                    fulltitle = self.link_info[href.toLowerCase()];

                if (fulltitle)
                {
                    a.setAttribute("href", "/" + fulltitle);
                    a.classList.add("available");
                }
                else
                {
                    a.setAttribute("href", "/" + href);
                    a.classList.add("missing");
                }
            });
    }
}



export { ArticleManager };

