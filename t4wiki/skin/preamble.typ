// -*- typst-script: t -*-

#let contains-block(it) = {
    if it.has("children") {
        it.children.map(contains-block).contains(true)
    } else if it.has("text") {
        false
    } else {
        // This is bad programming, because it relies on repr()ʼs user 
        // representation to make a decision.
        // 
        // I assume typst's HTML output will improve and put lang=
        // attributes into the HTML where appropriate. At this time
        // lang= is only used at document level.
        
        let r = repr(it)                
        let match = r.match(regex("\[?([a-z]+)\("))
        let t = none
        if (match != none) {
            t = match.captures.at(0)
        }
        let spans = ("emph", "strong", "cite", "link", "ref")
        if (spans.contains(t)) {
            false
        } else if (t == "quote") {
            it.fields().at("block", default:false)
        } else {
            true
        }
    } 
}


#let wikilang(lang, body) = context {
    let style = "normal"
    if (context text.lang) != lang {
        style = "italic"
    } 
    
    if target() == "html" {
        if (contains-block(body)) {
            html.elem("div", attrs: (lang: lang), text(body))
        } else {
            html.elem("span", attrs: (lang: lang), body)
        }        
    } else {
        text(lang: lang, style: style, body)
    }
}

// #let de(body) = wikilang("de", body)
// #let en(body) = wikilang("en", body)
// #let la(body) = wikilang("la", body)
// #let fr(body) = wikilang("fr", body)
// #let gr(body) = wikilang("gr", body)

#set text(lang: "en")

// Show-set rule	show heading: set block(..)	Styling
// Show rule with function	show raw: it => {..}	Styling
// Show-everything rule	show: template	Styling
#set cite(form: "prose")
#show cite: it => {
    if target() == "html" {
        html.elem("a", attrs: (data-citekey: str(it.key),
            class: "cite"))[#text(it.supplement)]
    } else {
        [#text(it)]
    }
}

// #let blockquote(attribution: none, content) = context {
//     if target() == "html" {
//         html.elem("blockquote", attrs: (class: "blockquote"))[
//             #text(content)
// 
//             #if attribution != none [
//                 #html.elem("p", attrs: (class: "attribution"))[
//                     #text(attribution)]
//             ]
//         ]
//     } else {
//         [#quote(attribution: attribution, block: true)[#text(content)]]
//     }
// }

#let blockquote(attribution: none, content) = {
    quote(block: true, attribution: attribution)[#text(content)]
}

#let bq = blockquote

#let bqa(attribution, content) = context {
    blockquote(attribution: attribution, content)
}

#show quote: it => {
    if target() == "html" and it.block {
        html.elem("figure")[
            #html.elem("blockquote", attrs: (class: "blockquote"))[
                #text(it.body)
            ]
            #if it.attribution != none [
                #html.elem("figcaption", attrs: (class: "blockquote-footer"))[
                    #text(it.attribution)]
            ]            
        ]
    } else {    
        [#text(it)]
    }
}

#show footnote: it => {
    if target() == "html" {
        html.elem("span", attrs: (class: "footnote"))[#text(it.body)]
    } else {
        [#text(it)]
    }
}

#show link: it => {
    if target() == "html" {
        if str(type(it.dest)) == "location" {            
            // The loc-# attribute us not user-accessible (at this point in
            // time?) But just going the regular way will insert a regular
            // link which will work fine for our purposes. 
            text(it)
        }
        else {
            html.elem("a", attrs: (class: "t4wiki-link",
                href: repr(it.dest).slice(1, -1)))[#text(it.body)]
        }
    } else {
        text(it)
    }
}

// https://github.com/typst/typst/issues/2196
// Cool!
#let to-string(it) = {
  if type(it) == str {
    it
  } else if type(it) != content {
    str(it)
  } else if it.has("text") {
    it.text
  } else if it.has("children") {
    it.children.map(to-string).join()
  } else if it.has("body") {
    to-string(it.body)
  } else if it == [ ] {
    " "
  }
}

// This is that the [[body]] or [[body|target]] syntax is turned into.
// This definition exists in case I want to or have to separate #link and
// #wikilink in the future. 
#let wikilink(body, target:none) = {
    if (target == none) {        
        link(to-string(body))
    } else {
        link(target, body)
    }
}


#let bild(name, caption) = context {
    if target() == "html" {
        let capelem = none        
        if caption != none {
            capelem = html.elem("figcaption", attrs: (class: "figure-caption"))[
                #caption]
        }
        
        html.elem("figure",
                  attrs: (class: "figure t4wiki-figure"))[
          #html.elem("img",
                     attrs: (data-filename: name,
                             class: "rounded preview-image preview-1800"))
          #capelem
        ]
    } else {
        figure(image(name), caption: caption)
    }
}

#let bildrechts(name, caption) = context {
    if target() == "html" {
        let capelem = none        
        if caption != none {
            capelem = html.elem("figcaption", attrs: (class: "figure-caption"))[
                #caption]
        }
        
        html.elem("figure",
                  attrs: (class: "figure t4wiki-figure float-end small"))[
          #html.elem("img",
                     attrs: (data-filename: name,
                             class: "rounded preview-image preview-300"))
          #capelem
        ]
    } else {
        figure(image(name), caption: caption)
    }
}

#set outline(title:none)
