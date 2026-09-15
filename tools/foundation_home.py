"""An art-led gallery entrance following the archive's ordered essay sequence."""
from html import escape

from writing_frame import footer, header


IDENTITY = "Suff Syed is a Member of Technical Staff building across AI frontiers at Microsoft."
DESCRIPTION = "Essays on intelligence, creative work, and what remains human."


def render_foundation(rows, image, series):
    if not rows:
        raise ValueError("The gallery entrance requires an archive lead.")
    lead = rows[0]
    writing = []
    for index, part in enumerate(series["parts"]):
        row = part["row"]
        first_sentence = row["description"].split(". ", 1)[0]
        excerpt = first_sentence if first_sentence.endswith(".") else first_sentence + "."
        sizes = ("(max-width: 700px) calc(100vw - 32px), "
                 "(max-width: 1599px) 56vw, 864px") if index % 2 == 0 else (
                     "(max-width: 700px) calc(100vw - 32px), (max-width: 1050px) 40vw, "
                     "(max-width: 1599px) 34vw, 520px")
        writing.append(f'''<li class="writing-plane writing-plane--{index + 1}" data-series-part="{part["number"]}" data-series-slug="{escape(row["slug"])}">
<a class="exhibition-art" href="{escape(row["url"])}" aria-label="Read {escape(row["title"])}">{image(row["cover"], row["coverAlt"], sizes=sizes)}</a>
<div class="essay-copy">
<span class="exhibition-label">Part {part["label"]}</span>
<h3><a href="{escape(row["url"])}">{escape(row["title"])}</a></h3>
<p>{escape(excerpt)}</p>
<a class="text-link reading-action" href="{escape(row["url"])}" aria-label="Read {escape(row["title"])}">Read Part {part["label"]} <span aria-hidden="true">↗</span></a>
</div>
</li>''')
    return f'''<!doctype html>
<html lang="en" class="gallery-home">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Suff Syed</title>
<meta name="description" content="{IDENTITY} {DESCRIPTION}">
<link rel="canonical" href="https://suffsyed.com/">
<meta property="og:title" content="Suff Syed">
<meta property="og:description" content="{DESCRIPTION}">
<meta property="og:type" content="website">
<meta property="og:url" content="https://suffsyed.com/">
<meta property="og:image" content="https://suffsyed.com{escape(lead["cover"])}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="alternate" type="application/rss+xml" title="future(memo)" href="/futurememo/rss.xml">
<link rel="preload" href="/assets/foundation/instrument-sans-regular.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/assets/fonts/dm-mono-regular.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/assets/foundation.css">
<link rel="stylesheet" href="/assets/frame.css">
<link rel="stylesheet" href="/assets/gallery-home.css">
</head>
<body id="top" class="foundation">
<a class="skip" href="#main">Skip to content</a>
{header(home=True)}
<main id="main" tabindex="-1">
<section class="cover gallery-cover technical-surface" aria-labelledby="cover-title">
<div class="cover-introduction">
<h1 class="cover-description" id="cover-title">{DESCRIPTION}</h1>
<p class="cover-role">{IDENTITY}</p>
</div>
<figure class="featured-essay" data-featured-slug="{escape(lead["slug"])}">
<a class="featured-art" href="{escape(lead["url"])}" aria-label="Read {escape(lead["title"])}">{image(lead["cover"], lead["coverAlt"], lazy=False, sizes="(max-width: 700px) calc(100vw - 48px), (max-width: 1100px) calc(55vw - 30px), (max-width: 1344px) calc(53.75vw - 50px), 672px")}</a>
<figcaption><p class="exhibition-label">Featured essay</p>
<h2><a href="{escape(lead["url"])}">{escape(lead["title"])}</a></h2>
<a class="text-link reading-action" href="{escape(lead["url"])}">Read this essay <span aria-hidden="true">↗</span></a>
</figcaption>
</figure>
</section>
<section class="writing technical-surface" id="writing" aria-labelledby="writing-title">
<header class="chapter-heading"><div><p class="section-context">A four-part series</p>
<h2 id="writing-title">{escape(series["title"])}</h2><p class="section-deck">{escape(series["description"])}</p></div>
<div class="section-actions"><a class="text-link reading-action" href="{escape(series["parts"][0]["row"]["url"])}">Start with Part I <span aria-hidden="true">↗</span></a>
<a class="text-link" href="/futurememo/">All essays <span aria-hidden="true">↗</span></a></div>
</header>
<ol class="writing-list">{"".join(writing)}</ol>
</section>
</main>
{footer()}
</body>
</html>
'''
