"""The sage observatory and an exhibition of original essay illustrations."""
from html import escape

from foundation_art import orbit, ribbon
from writing_frame import footer, header


SELECTED_ESSAYS = (
    "qubit-teams-the-future-built-by-two-people-using-ai",
    "how-future-designers-will-win-in-the-age-of-ai",
    "a-new-class-of-software-builders-is-emerging",
)
IDENTITY = "Suff Syed is a Member of Technical Staff building across AI frontiers at Microsoft."
DESCRIPTION = "Essays on intelligence, creative work, and what remains human."


def render_foundation(rows, image):
    by_slug = {row["slug"]: row for row in rows}
    writing = []
    for index, slug in enumerate(SELECTED_ESSAYS):
        row = by_slug[slug]
        first_sentence = row["description"].split(". ", 1)[0]
        excerpt = first_sentence if first_sentence.endswith(".") else first_sentence + "."
        sizes = ("(max-width: 700px) calc(100vw - 32px), "
                 "(max-width: 1599px) 56vw, 864px") if index != 1 else (
                     "(max-width: 700px) calc(100vw - 32px), (max-width: 1050px) 40vw, "
                     "(max-width: 1599px) 34vw, 520px")
        writing.append(f'''<li class="writing-plane writing-plane--{index + 1}">
<a class="exhibition-art" href="{escape(row["url"])}" aria-label="Read {escape(row["title"])}">{image(row["cover"], row["coverAlt"], sizes=sizes)}</a>
<div class="essay-copy">
<span class="exhibition-label">{index + 1:02d} / {escape(row["theme"])}</span>
<h3><a href="{escape(row["url"])}">{escape(row["title"])}</a></h3>
<p>{escape(excerpt)}</p>
<a class="text-link" href="{escape(row["url"])}" aria-label="Read {escape(row["title"])}">Read essay <span aria-hidden="true">↗</span></a>
</div>
</li>''')
    return f'''<!doctype html>
<html lang="en">
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
<meta property="og:image" content="https://suffsyed.com{by_slug[SELECTED_ESSAYS[0]]["cover"]}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="alternate" type="application/rss+xml" title="future(memo)" href="/futurememo/rss.xml">
<link rel="preload" href="/assets/foundation/instrument-sans-regular.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/assets/fonts/dm-mono-regular.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/assets/foundation.css">
<link rel="stylesheet" href="/assets/frame.css">
<script type="module" src="/assets/motion.js"></script>
</head>
<body id="top" class="foundation">
<a class="skip" href="#main">Skip to content</a>
{header(home=True, motion=True)}
<main id="main" tabindex="-1">
<section class="cover technical-surface" aria-labelledby="cover-title">
<div class="hero-field motion-field" data-motion-scene>{ribbon("home-ribbon")}</div>
<p class="cover-role">{IDENTITY}</p>
<div class="editorial-plane">
<h1 id="cover-title"><span class="sr-only">Suff Syed</span><span class="signature-ink">
<img class="cover-signature" src="/assets/suff-syed-signature.svg" width="350" height="148" alt="" fetchpriority="high">
</span></h1>
<p class="cover-description">{DESCRIPTION}</p>
<a class="text-link" href="#writing">Explore the writing <span aria-hidden="true">↗</span></a>
</div>
</section>
<section class="writing technical-surface" id="writing" aria-labelledby="writing-title">
<header class="chapter-heading"><h2 id="writing-title">[ Selected writing ]</h2>
<a class="text-link" href="/futurememo/">All essays <span aria-hidden="true">↗</span></a>
</header>
<ol class="writing-list">{"".join(writing)}</ol>
</section>
<section class="ideas technical-surface" aria-labelledby="ideas-title">
<div class="idea-field motion-field" data-motion-scene>{orbit("home-ideas")}</div>
<div class="idea-copy"><p class="exhibition-label">[ A thought in company ]</p>
<h2 id="ideas-title">One question.<br>Many ways in.</h2>
<p>Follow a preoccupation through the writing. Every connection leads back to an original passage.</p>
<a class="text-link" href="/futurememo/#by-preoccupation">Enter the question atlas <span aria-hidden="true">↗</span></a></div>
</section>
</main>
{footer()}
</body>
</html>
'''
