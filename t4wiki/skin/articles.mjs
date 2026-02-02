import { title2path, normalize_whitespace } from "t4wiki";
import { html } from "xisty";

class Heading
{
    // Return the # from an h# tag as an integer;
    static h_element_level(h_element)
    {
        return parseInt(h_element.tagName.substr(1, 1));
    }

    constructor(parent, level, tag)
    {
        this.parent = parent;
        this.level = level;
        this.tag = tag;
        
        if (tag !== null)
        {
            this.caption = tag.innerHTML.replace(/<.*?>/g, "");
        }
        else
        {
            this.caption = "";
        }
        this.children = [];
    }

    // Append a heading for the h_element and return the newly inserted
    // child. If h_element is null, append and return an empty entry.
    // If the h_element’s level is more than one level apart from this
    // one’s, fill in empty entries.
    append(h_element)
    {
        if (h_element === null)
        {
            var kid = new Heading(this, this.level + 1, null);
            this.children.push(kid);
            return kid;
        }
        else
        {
            var level = Heading.h_element_level(h_element);
            var here = this;
            while(level > here.level + 1)
            {
                here = here.append(null);
            }

            var kid = new Heading(here, level, h_element);
            here.children.push(kid);
            return kid;
        }
    }

    li()
    {
        var li = document.createElement("li"),
            heading_index = 0;
        
        if (this.tag)
        {
            //heading_index++;
            //var name = "toc" + heading_index;
            //li.appendChild(document.createElement("a", {name: name}));

            if (this.tag)
            {
                var name = this.tag.getAttribute("id");
                var link = document.createElement("a");
                link.setAttribute("href", "#" + name);
                link.innerText = this.caption;
                li.appendChild(link);
            }
        }
            
        if (this.children.length > 0)
        {
            li.appendChild(this.ul());
        }
            
        return li;            
    }

    ul()
    {
        var ul = document.createElement("ul");
        this.children.forEach(function(kid) {
            ul.appendChild(kid.li());
        });
        return ul;
    }
}
    

class ArticleManager
{
    constructor(id_by_title, info_by_id, link_info)
    {
        this.id_by_title = id_by_title;
        this.info_by_id = info_by_id;

		// Make a copy because we will set the entries to null
		// after the include has been performed. 
		this._id_by_title = structuredClone(id_by_title);

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
		// Populate properties refering to DOM objectws.
        this.main_article = document.querySelector("article.main");
        this.main_article_id = parseInt(
            this.main_article.getAttribute("data-article-id"));
        this.article_section = this.main_article.parentNode.parentNode;

        this.start_full_text_search();
		this.handle_upload_links();
        this.deal_with_includes();
        this.collect_footnotes();
        this.make_headings_targets();
        this.process_links();
        this.construct_toc_maybe();
		this.set_filetype_icons_ext();

		this.prettify_classes();
    }

    start_full_text_search()
    {
		// First order of business: Start the full text query on the server.
		let ids = [];
		document.querySelectorAll("section.linking-here li").forEach(li => {
			ids.push(parseInt(li.getAttribute("data-article-id")));
		});		
		
		const section = document.querySelector(
			"aside.article-meta section.search-result");
		this.search_result_section = section;

		const article = document.querySelector("article.main"),
			  article_id = parseInt(article.getAttribute("data-article-id"));

		let params = new URLSearchParams();
		params.set("article_id", article_id);
		params.set("linking_here", ids.join(","));

		const url = globalThis.site_url
			  + "/article_fulltext_search?" + params.toString();
		
		fetch(url).then(this.on_search_result_loaded.bind(this));
    }

    on_search_result_loaded(response)
	{
		const self = this;
		response.text().then(function(text) {
			self.search_result_section.innerHTML = text;
		});
	}

	handle_upload_links()
	{
		const included = this.main_article.parentNode.querySelectorAll(
			"article.included");
		
		globalThis.file_manager.handle_uploads(this.main_article,
											   this.main_article_id);
		for ( const article of included )
		{
			const id = parseInt(article.getAttribute("data-article-id"));
			globalThis.file_manager.handle_uploads(article, id);
		}
	}

    deal_with_includes()
    {
        const self = this;
        
        var parent = this.main_article.parentNode,
            included = parent.querySelectorAll("article.included"),
            included_by_id = {};
        
        included.forEach(function(article) {
            const id = parseInt(article.getAttribute("data-article-id"));
            included_by_id[id] = article;
        });
        
        this.main_article.querySelectorAll(
            "div.t4wiki-include").forEach(function(div) {
				// In this method use this._id_by_title where we set the
				// entries to null after use. 
                var title = div.getAttribute("data-article-title"),
                    id = self._id_by_title[title],
                    article = included_by_id[id];
                
                if (article)
                {
                    for(const child of article.childNodes)
                    {                        
                        div.appendChild(child.cloneNode(true));
                    }
                    article.remove();
                    self._id_by_title[title] = null;
                }
            });
    }

    collect_footnotes()
    {
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

				counter++;
            }
        }
    }

    make_headings_targets()
    {
		// Go through the headlines and set the name= attribute to their
		// text contents. 
		let heading_ids = Array();
		this.article_section.querySelectorAll("h1, h2, h3, h4, h5, h6").forEach(
			function(h) {
				if ( ! h.hasAttribute("id"))
				{
					const id = normalize_whitespace(h.textContent);
					
					if (heading_ids.indexOf(id) == -1)
					{
						h.setAttribute("id", id);
						heading_ids.push(id);
					}
				}
			});
    }

    process_links()
    {
        const link_info = this.link_info;
        
        // Go through the links and set their targets correctly.
        // Also set link classes.
        this.article_section.querySelectorAll("a.t4wiki-link").forEach(
            function(a) {
                const href = decodeURI(a.getAttribute("href")),
					  parts = href.split("#"),
					  key = parts[0].toLowerCase(), 
					  fulltitle = link_info[key];

				var anchor;
				if (parts.length == 2)
				{
					anchor = "#" + parts[1];
				}
				else
				{
					anchor = "";
				}

                if (fulltitle)
                {
                    a.setAttribute(
						"href", "/" + title2path(fulltitle) + anchor);
                    a.classList.add("available");
                }
                else
                {
                    a.setAttribute("href", "/" + href);
                    a.classList.add("missing");
                }

				// Links that point to an anchor and have a href
				// identical with their text content get the # removed
				// and a pair of () added.
				if (a.textContent == href && anchor != "")
				{
					a.textContent = `${parts[0]} (${parts[1]})`;
				}
            });
    }

    construct_toc_maybe()
    {
        document.querySelectorAll("div.t4wiki-toc").forEach(
            this.construct_toc.bind(this));
    }

    construct_toc(div)
    {
        // Walk the DOM tree upwards to find the <article> element. 
        let here = div;
        while (here.tagName != "ARTICLE")
        {
            here = here.parentNode;

            // Better safe than sorry. 
            if (here.tagName == "BODY")
            {
                throw "HTML nesting error.";
            }
        }
        const article = here;

        var h_elements = article.querySelectorAll("h1,h2,h3,h4,h5,h6");
        var min_level = 7;
        h_elements.forEach( element => {
            const level = Heading.h_element_level(element);
            if (level < min_level)
            {
                min_level = level;
            }
        });
        var toc = new Heading(null, min_level-1, null);
        var current = toc;
        for(var a = 0; a < h_elements.length; a++)
        {
            var h_element = h_elements[a];

			if ( ! h_element.classList.contains("downloads"))
			{
				var level = Heading.h_element_level(h_element);
				if ( level <= current.level )
				{
					while (level < current.level)
					{
						current = current.parent;
					}
					current = current.parent.append(h_element)
				}
				else if (level > current.level)
				{
					current = current.append(h_element);
				}
			}
        };

        // Remove redundant first entries.
        while (toc.children.length == 1 && toc.caption == "")
        {
            toc = toc.children[0];
        }
        
        div.appendChild(toc.ul());
    }

	set_filetype_icons_ext()
	{
		const icons = this.main_article.querySelectorAll(
			"embed.file-type-icon");
		
		for ( const icon of icons )
		{
			const ext = icon.getAttribute("data-ext");
			
			icon.addEventListener("load", event => {
				const icon_dom = event.target.getSVGDocument();
				set_fileicon_class(icon_dom, ext);
			});
		}	
	}

	prettify_classes()
	{
		// Go to the DOM tree and add some bootstrap classes that
		// make things look prettier.
		document.querySelectorAll(".box").forEach(box => {
			box.classList.add("alert");

			if (box.classList.contains("box-question"))
			{
				box.classList.add("alert-warning");
			}
			else
			{
				box.classList.add("alert-primary");
			}
		});
		
		document.querySelectorAll(".sidebox").forEach(box => {
			box.classList.add("alert");

			if (box.classList.contains("sidebox-question"))
			{
				box.classList.add("alert-warning");
			}
			else
			{
				box.classList.add("alert-primary");
			}
		});
	}
}

function set_fileicon_class(icon_dom, ext)
{
	ext = ext.toLowerCase();
	const all = icon_dom.querySelector("#all"),
		  extension_text = icon_dom.querySelector(".extension-text");

	for ( const cls in class_to_exts )
	{
		if (class_to_exts[cls].includes(ext))
		{
			all.classList.add(cls);
			break;
		}
	}
	extension_text.textContent = ext.toUpperCase();
}


const illegal_filename_char_re = /\s+|\./i;
class FileInfoByFilename
{
	constructor(info)
	{
		this.length = 0;
		this.download_count = 0;
		for (const filename in info)
		{
			this[filename] = info[filename];
			this.length++;

			if (info[filename].dl)
			{
				this.download_count++;
			}
		}
	}

	search_by_filename(filename)
	{
		return this[filename] ||
			this[this.normalize_filename(filename)] ||
			this[this.normalize_filename(filename.toLowerCase())] ||
			null;
	}

	normalize_filename(filename)
	{
		// For String.prototype.normalize() cf. 
		// https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/String/normalize
		return filename.replace(illegal_filename_char_re, "_").normalize("NFC");
	}
}

const class_to_exts = {
	"text": [ "txt", "doc", "docx", "otd", ],
	"rasterimage": [ "jpg", "jpeg", "png", "gif", "png", ],
	"pdf": [ "pdf" ],
	"zip": [ "zip", "tgz", ]
}

class FileManager
{	
    constructor(file_info)
    {
		/* The ‘file_info’ JSON is queries using json_object_agg() from the
		   uploads.upload_info_for_view SQL view. 
		 */
        this.fileinfos_by_article_id = {};
        for (const article_id in file_info)
        {
            this.fileinfos_by_article_id[parseInt(article_id)] =
                new FileInfoByFilename(file_info[article_id]);
        }        
    }

	fileinfo_for_article(id)
	{
		return this.fileinfos_by_article_id[id] ||
			new FileInfoByFilename({});
	}

    handle_uploads(container, article_id)
    {
		const fileinfos = this.fileinfo_for_article(article_id);

		this.handle_images(container, article_id, fileinfos);
		this.handle_downloads(container, article_id, fileinfos);
    }

	handle_images(article_div, article_id, fileinfos)
	{
        for(const img of article_div.querySelectorAll("img.preview-image"))
        {
            const src = img.getAttribute(
				"data-filename") || img.getAttribute("src"),
				  filename = decodeURI(src),
                  fileinfo = fileinfos.search_by_filename(filename);
			
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
                      preview_ext = fileinfo["pext"],
                      preview_dir = `${article_id}_${id}_${slug}`;
                
                img["src"] = `${globalThis.site_url}/previews/` +
                    `${preview_dir}/preview${size}${preview_ext}`;

				if (img.parentNode.tagName == "FIGURE")
				{
					const caption = img.parentNode.querySelector(
						"figcaption");
					if (caption && caption.textContent == "")
					{
						caption.textContent = fileinfo.title;
					}
				}
            }
			else
			{
				img.classList.add("missing");
			}
        }
    }

	handle_downloads(article_div, article_id, fileinfos)
	{
		if (fileinfos.download_count > 0)
		{
			let div = article_div.querySelector("div.t4wiki-downloads");
		
			if (div)
			{
				div = html.Wrapper(div);
			}
			else
			{
				div = html.div({class: "t4wiki-downloads"});
				div.append_to(article_div);
			}

			this.populate_downloads_div(div, fileinfos);
		}
	}

	populate_downloads_div(div, fileinfos)
	{
		if (fileinfos.length > 0)
		{
			const cardgroup = html.div(
				{class: "row row-cols-2 row-cols-xl-3 g-2 mb-4"});
			
			div.append(html.h4("Downloads", {class: "downloads"}),
					   cardgroup);
			
			for (const filename in fileinfos)
			{
				const fileinfo = fileinfos[filename];

				if (fileinfo.dl)
				{
					const href = globalThis.site_url + 
						  `/articles/download_upload.cgi?id=${fileinfo.id}`;

					let filename = null;
					if (fileinfo.t)
					{
						filename = html.span(" ", "(" + fileinfo.n + ")",
											 {class: "text-muted text-small"});
					}
					const ext = fileinfo.n.toLowerCase(
					                            ).split(".").slice(-1)[0],
						  title = fileinfo.t || fileinfo.n,
						  body = html.div(
							  html.h5(title, filename,
									  {class: "downloads"}),
							  html.p(html.span(fileinfo.d,
											   {class: "text-muted"}),
									 " ",
									 html.a("download",
											{href: href,
											 class: "stretched-link"}))), 
						  icon = html.embed({
							  class: "file-type-icon",
							  "data-ext": ext,
							  type: "image/svg+xml",
							  src: "/t4wiki_skin/filetype_icon.svg"});
					
					const inner = html.div({class: "row g-0"},
										   html.div({class: "col-2"}, icon),
										   html.div({class: "col-10"}, body));

					cardgroup.append(
						html.div({class: "col"},
								 html.div({ class: "download h-100 " +
											       "position-relative"},
										  inner)));
				}
			}
		}
	}
}

export { ArticleManager, FileManager };

