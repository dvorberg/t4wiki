from ll.xist import xsc
from ll.xist.ns import html

def block_level_figure(image_filename, description):
    return html.figure(
        html.img(class_="rounded preview-image preview-1800",
                 **{"data-filename": image_filename}),
        html.figcaption(description, class_="figure-caption"),
        class_="figure t4wiki-figure")

def float_right_image(image_filename, description):
    return html.figure(
        html.img(class_="rounded preview-image preview-300",
                 **{"data-filename": image_filename}),
        html.figcaption(description, class_="figure-caption"),
        class_="figure t4wiki-figure float-end small")
