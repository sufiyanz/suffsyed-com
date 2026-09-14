"""The quiet homepage only; the journal's other renderers remain independent."""
from html import escape

from journal_questions import _role_mark


SELECTED_ESSAYS = (
    "qubit-teams-the-future-built-by-two-people-using-ai",
    "ai-doesnt-create-slop-humans-do",
    "a-new-class-of-software-builders-is-emerging",
)
SELECTED_PHOTOS = (0, 1)
IDENTITY = "Suff Syed is a Member of Technical Staff building across AI frontiers at Microsoft."
DESCRIPTION = "Essays on intelligence, creative work, and what remains human."


def render_foundation(rows, gallery, image):
    by_slug = {row["slug"]: row for row in rows}
    writing = []
    for slug in SELECTED_ESSAYS:
        row = by_slug[slug]
        first_sentence = row["description"].split(". ", 1)[0]
        excerpt = first_sentence if first_sentence.endswith(".") else first_sentence + "."
        writing.append(f'''<li>
<h3><a href="{escape(row["url"])}">{escape(row["title"])}</a></h3>
<p>{escape(excerpt)}</p>
</li>''')
    photographs = []
    for position, index in enumerate(SELECTED_PHOTOS):
        photo = gallery[index]
        sizes = ("(max-width: 700px) calc(100vw - 72px), "
                 "(max-width: 1599px) 51vw, 768px") if position == 0 else (
                     "(max-width: 700px) 72vw, (max-width: 1599px) 29vw, 432px")
        photographs.append(f'''<figure class="photo-{"print" if position == 0 else "study"}">
<a href="/lightworks/#plate-{index + 1:02d}">{image(photo["src"], photo["alt"], sizes=sizes)}</a>
<figcaption>{escape(photo["alt"])}</figcaption>
</figure>''')
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
<meta property="og:image" content="https://suffsyed.com{gallery[0]["src"]}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="alternate" type="application/rss+xml" title="future(memo)" href="/futurememo/rss.xml">
<link rel="stylesheet" href="/assets/foundation.css">
</head>
<body id="top" class="foundation">
<a class="skip" href="#main">Skip to content</a>
<header class="site-header frame">
<a class="site-name" href="/" aria-label="Suff Syed, home">Suff Syed</a>
<nav aria-label="Main navigation">
<a href="#writing">Writing</a><a href="#photography">Photography</a><a href="/about-me/">About</a>
</nav>
</header>
<main id="main" tabindex="-1">
<section class="cover frame" aria-labelledby="cover-title">
<h1 id="cover-title"><span class="sr-only">Suff Syed</span><span class="signature-ink">
<img class="cover-signature" src="/assets/suff-syed-signature.svg" width="350" height="148" alt="" fetchpriority="high">
</span></h1>
<div class="cover-copy"><p class="cover-role">{IDENTITY}</p>
<p class="cover-description">{DESCRIPTION}</p></div>
</section>
<section class="writing frame" id="writing" aria-labelledby="writing-title">
<div class="section-heading"><h2 id="writing-title">Selected <br>writing.</h2>
<a class="text-link" href="/futurememo/">All essays <span aria-hidden="true">↗</span></a></div>
<ol class="writing-list">{"".join(writing)}</ol>
</section>
<section class="photography frame" id="photography" aria-labelledby="photography-title">
<header class="photo-heading"><h2 id="photography-title">Light(works).</h2>
<div><p>A deliberate step away from screens and into the world.</p>
<a class="text-link" href="/lightworks/">All photographs <span aria-hidden="true">↗</span></a></div></header>
<div class="photo-pair">{"".join(photographs)}</div>
</section>
</main>
<footer class="site-footer frame">
<div class="footer-opening"><p class="footer-thought">A mind at work.<br>A work in progress.</p>
{_role_mark("synthesist")}</div>
<div class="footer-bottom"><p>Thanks for spending a little time here.</p>
<nav aria-label="Further reading"><a href="/about-me/">About me</a>
<a href="/futurememo/">Writing</a><a href="/futurememo/rss.xml">RSS</a>
<a href="#top">Back to top <span aria-hidden="true">↑</span></a></nav></div>
</footer>
</body>
</html>
'''
