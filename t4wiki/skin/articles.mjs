import { title2path } from "t4wiki";

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

		// First order of business: Start the full text query on the server.
		let ids = [];
		document.querySelectorAll("section.linking-here li").forEach(li => {
			ids.push(parseInt(li.getAttribute("data-article-id")));
		});
		
		const section = document.querySelector(
			"aside.article-meta section.search-result");
		this.search_result_section = section;
		
		let params = new URLSearchParams();
		params.set("query", section.getAttribute("data-query"));
		params.set("lang", section.getAttribute("data-lang"));
		params.set("ids", ids.join(","));

		const url = globalThis.site_url
			  + "/article_fulltext_search?" + params.toString();
		
		fetch(url).then(this.on_search_result_loaded.bind(this));

        
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
                const href = decodeURI(a.getAttribute("href")),
					  key = href.toLowerCase(),
					  fulltitle = self.link_info[key];

                if (fulltitle)
                {
                    a.setAttribute("href", "/" + title2path(fulltitle));
                    a.classList.add("available");
                }
                else
                {
                    a.setAttribute("href", "/" + href);
                    a.classList.add("missing");
                }
            });
    }

	on_search_result_loaded(response)
	{
		const self = this;
		response.text().then(function(text) {
			self.search_result_section.innerHTML = text;
		});
	}
}


class FileManager
{
    constructor(file_info)
    {
        this.files_by_article_id = {};
        for (const article_id in file_info)
        {
            this.files_by_article_id[parseInt(article_id)] =
                file_info[article_id];
        }
        
        document.addEventListener("DOMContentLoaded",
                                  this.on_dom_content_loaded.bind(this));
    }

    on_dom_content_loaded(event)
    {
        for(const div of document.querySelectorAll("[data-article-id]"))
        {
            const article_id = parseInt(div.getAttribute("data-article-id"));

            for(const img of div.querySelectorAll("img.preview-image"))
            {
                const filename = decodeURI(img.getAttribute("src")),
                      files = this.files_by_article_id[article_id] || null,
                      fileinfo = files && files[filename];
				
                if (fileinfo)
                {
                    var size = 300;
                    if (img.classList.contains("preview-1800"))
                    {
                        size = 1800;
                    }
                    else if (img.classList.contains("preview-600"))
                    {
                        size = 600;
                    }

                    const id = fileinfo["id"], slug = fileinfo["slug"],
                          preview_ext = fileinfo["preview_ext"],
                          preview_dir = `${article_id}_${id}_${slug}`;
                    
                    img["src"] = `${globalThis.site_url}/previews/` +
                          `${preview_dir}/preview${size}${preview_ext}`;

                    const caption = img.parentNode.querySelector("figcaption");
                    if (caption && caption.textContent == "")
                    {
                        caption = fileinfo.title;
                    }
                }
				else
				{
					img.classList.add("missing");
				}
            }
        }
    }
}

export { ArticleManager, FileManager };
