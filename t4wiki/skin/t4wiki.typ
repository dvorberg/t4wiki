#let wikilang(lang, body) = context {
    let style = "normal"
    if (context text.lang) != lang {
        style = "italic"
    } 
    
    if target() == "html" {
        html.elem("span", attrs: (lang: lang), body)
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
        html.elem("a", attrs: (data-citekey: str(it.key)))
    }
    [#text(it)]
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

