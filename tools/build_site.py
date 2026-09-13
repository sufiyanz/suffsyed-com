"""Build the complete, offline scientific journal from committed content."""
import html
import json
import shutil
from pathlib import Path
from urllib.parse import quote

from bs4 import BeautifulSoup
from PIL import Image

from corpus import connect, measure
from journal_home import render_home
from journal_questions import render_margin, render_research, render_research_teaser

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs"
DOMAIN = "https://suffsyed.com"


def esc(value):
    return html.escape(str(value), quote=True)


def safe_json(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c").replace("&", "\\u0026")


def write(path, content):
    target = OUT / path.lstrip("/")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def image(src, alt, lazy=True, sizes="(max-width: 700px) 90vw, 70vw"):
    with Image.open(OUT / src.lstrip("/")) as im:
        width, height = im.size
    stem = Path(src).stem
    sources = [f"/assets/responsive/{stem}-{size}.webp {size}w" for size in (640, 960) if width > size]
    sources.append(f"{src} {width}w")
    return f'<img src="{src}" srcset="{", ".join(sources)}" sizes="{sizes}" width="{width}" height="{height}" alt="{esc(alt)}" {"loading=" + chr(34) + "lazy" + chr(34) if lazy else "fetchpriority=" + chr(34) + "high" + chr(34)} decoding="async">'


def layout(title, description, body, path, current="", cover=None, kind="page"):
    nav = [("Writing", "/futurememo/", "writing"), ("Light(works)", "/lightworks/", "light"), ("The unfinished", "/research/", "research"), ("About", "/about-me/", "about")]
    links = "".join(f'<a href="{url}"{" aria-current=" + chr(34) + "page" + chr(34) if key == current else ""}>{label}</a>' for label, url, key in nav)
    og = f'<meta property="og:image" content="{DOMAIN}{cover}">' if cover else ""
    return f'''<!doctype html>
<html lang="en" data-theme="light">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} — Suff Syed</title><meta name="description" content="{esc(description)}">
<link rel="canonical" href="{DOMAIN}{path}">
<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(description)}">
<meta property="og:type" content="{"article" if kind == "essay" else "website"}">{og}
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="preload" href="/assets/fonts/newsreader-roman.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/assets/fonts/dm-mono-regular.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/assets/journal.css"><link rel="stylesheet" href="/assets/home.css"><link rel="stylesheet" href="/assets/questions.css">
<link rel="alternate" type="application/rss+xml" title="future(memo)" href="/futurememo/rss.xml">
<script type="module" src="/assets/app.js"></script>
</head><body id="top" class="{kind}">
<a class="skip" href="#main">Skip to content</a>
<div class="sheet"><header class="mast"><a class="signature" href="/" aria-label="Suff Syed, home">Suff Syed</a><nav aria-label="Main navigation">{links}</nav></header>
<main id="main">{body}</main>
<footer class="foot"><div><a class="signature" href="/">Suff Syed</a><p>A mind at work. A work in progress.</p><p><a href="/about-me/">About the person behind these questions ↗</a></p></div>
<nav aria-label="Further reading"><a href="/about-the-memo/">About the memo</a><a href="/faqs/">FAQs</a><a href="/the-end-of-design-report/">The End of Design</a><a href="/store/">A coffee, perhaps</a><a href="/methods/">How to read the data</a><a href="/futurememo/rss.xml">RSS</a></nav>
<nav aria-label="Elsewhere"><a href="https://substack.com/@suffsyed">Substack ↗</a><a href="https://x.com/suff_syed">X ↗</a><a href="https://www.linkedin.com/in/suffsyed/">LinkedIn ↗</a><a href="#top">Back to top ↑</a></nav></footer></div>
<div class="outside-caption"><span>SUFF SYED / NOTES FROM THE FRONTIER</span><span>Independent writing · No tracking</span></div>
<dialog id="artwork-dialog" aria-labelledby="artwork-title"><div class="dialog-head"><h2 id="artwork-title">A closer look.</h2><button class="close" data-close-dialog aria-label="Close artwork">×</button></div>
<figure><img id="artwork-image" alt=""><figcaption id="artwork-caption"></figcaption></figure>
<div class="artwork-actions"><button id="artwork-prev" class="plain" aria-label="Previous photograph">← Previous</button><a id="artwork-original">Open image file ↗</a><button id="artwork-next" class="plain" aria-label="Next photograph">Next →</button></div></dialog>
</body></html>'''


def essay_page(row, rows):
    body = BeautifulSoup(row["body"], "html.parser")
    for passage_number, el in enumerate(body.select("[data-passage]"), 1):
        tools = body.new_tag("span", attrs={"class": "passage-tools"})
        if "table-passage" in el.get("class", []):
            hint = body.new_tag("span", attrs={"id": f"hint-{el['id']}", "class": "table-help"})
            hint.string = "Table / Scroll horizontally to see every column."
            tools.append(hint)
            el.select_one(".passage-text")["aria-describedby"] = hint["id"]
        link = body.new_tag("a", href=f"#{el['id']}", attrs={"class": "paragraph-anchor", "aria-label": f"Link to passage {passage_number}"})
        link.string = "¶"
        tools.append(link)
        button = body.new_tag("button", attrs={"type": "button", "data-inspect": el["id"], "class": "inspect-passage enhanced", "aria-label": "Explore this passage and its connections"})
        button.string = "↗"
        tools.append(button)
        el.append(tools)
    for img in body.select("img"):
        img["loading"] = "lazy"
        if img["src"].startswith("/assets/"):
            with Image.open(OUT / img["src"].lstrip("/")) as im:
                img["width"], img["height"] = im.size
    toc = "".join(f'<li><a href="#{s["id"]}"><span>{esc(s["title"])}</span><small>{s["words"]:,} w</small><span class="section-measure" style="--portion:{s["words"] / row["words"] * 100:.6f}%"></span></a></li>' for s in row["sections"])
    ribbon = "".join(f'<a href="#{s["id"]}" style="flex-grow:{s["words"]}" aria-label="{esc(s["title"])}: {s["words"]:,} words" title="{esc(s["title"])} · {s["words"]:,} words"></a>' for s in row["sections"])
    options = "".join(f'<option value="{s["id"]}">{esc(s["title"])}</option>' for s in row["sections"])
    terms = "".join(f'<button type="button" data-term="{esc(t["term"])}">{esc(t["term"])} <small>{t["count"]}</small></button>' for t in row["terms"][:10])
    next_rows = [item for item in rows if item["theme"] == row["theme"] and item["slug"] != row["slug"]][:2]
    related = "".join(f'<a href="{item["url"]}"><span class="label">{esc(item["theme"])}</span><h3>{esc(item["title"])}</h3><span class="plain">Read the essay ↗</span></a>' for item in next_rows)
    content = f'''
<header class="essay-head">
<div class="essay-kicker label"><a href="/futurememo/">future(memo)</a><span>Essay {row["no"]:02d} / {esc(row["theme"])}</span><span>{row["words"]:,} words · About {row["minutes"]} min</span></div>
<h1>{esc(row["title"])}</h1><p class="dek">{esc(row["description"])}</p>
<div class="head-foot"><span>By Suff Syed</span><a href="#reading">Begin reading ↓</a><a href="#reading-lens" class="enhanced">Read through a different lens ↗</a></div>
</header>
<figure class="essay-artwork"><a href="{row["cover"]}" class="artwork-link" data-artwork data-caption="Original cover illustration for {esc(row["title"])}. {esc(row["coverAlt"])} Shown without cropping.">{image(row["cover"], row["coverAlt"], False)}</a><figcaption><span>Frontispiece / Original essay artwork</span><a href="{row["cover"]}" data-artwork data-caption="Original cover illustration for {esc(row["title"])}. {esc(row["coverAlt"])}">Enlarge the whole image ↗</a></figcaption></figure>
<div class="reading-intro" id="reading"><div><span class="label">A path through this essay</span><p>Read in sequence, or enter through a question.</p></div><div><div class="section-ribbon" aria-label="Sections, widths proportional to word counts">{ribbon}</div><p class="micro">Band widths follow section length, not importance. <a href="/methods/#counting">How this is counted</a></p></div></div>
<div class="reading-layout"><aside class="reading-aside"><details class="contents" open><summary>In this essay <span class="label">{len(row["sections"])} parts</span></summary><ol>{toc}</ol></details><p class="aside-note">Every paragraph has an address. The ¶ keeps your place; the ↗ follows shared vocabulary into another essay.</p>
<button class="plain enhanced open-lens" type="button">Open the reading lens ↗</button></aside>
<article class="essay-body" id="essay-body" aria-label="Complete essay"><span id="introduction" tabindex="-1"></span>{body}</article>
<aside class="reading-lens enhanced" id="reading-lens" aria-labelledby="lens-title" hidden>
<div class="lens-heading"><span class="label">Optional / Text as data</span><button class="plain" id="close-lens" type="button">Close lens ×</button></div>
<h2 id="lens-title">Follow a word.<br>Find another thought.</h2><p class="lens-intro">Exact words, original passages. Nothing is rewritten.</p>
<form id="term-form"><label for="term-query">A full word or hyphenated term</label><div class="search-line"><input id="term-query" name="term" type="search" maxlength="80" autocomplete="off" placeholder="Try judgment"><button type="submit">Find</button></div><label for="term-scope">Look within</label><select id="term-scope"><option value="">The whole essay</option>{options}</select></form>
<div class="term-chips" aria-label="Recurring words in this essay">{terms}</div><p class="micro">Numbers are exact occurrences in the full body, including headings and captions.</p>
<div class="lens-actions"><button type="button" id="clear-term" class="plain">Clear highlights</button><a href="/methods/#connections">About these connections ↗</a></div>
<p id="term-status" class="lens-status" role="status"></p><ol id="term-results" class="passage-results"></ol>
<section id="passage-inspector" hidden aria-labelledby="inspector-title"><span class="label">One passage / Other possibilities</span><h3 id="inspector-title">A thought in company.</h3><blockquote id="inspected-text"></blockquote><a id="inspected-link">Return to the passage ↗</a><p class="micro">Lexical neighbors, not agreement or evidence. Ranked by shared, less-common words. Short passages may have no match.</p><ol id="related-passages" class="passage-results"></ol></section>
</aside></div>
<div class="essay-end"><span class="label">End of essay {row["no"]:02d}</span><p>Keep the question open.</p><a href="/futurememo/">Return to the whole collection ↗</a></div>
<section class="next-reading"><div><span class="label">Still in this preoccupation</span><h2>One thought leads<br>to another.</h2></div>{related}</section>
<details class="provenance"><summary>A note on the archive</summary><p>The complete migrated text is preserved. The migration assigned the date label “{esc(row["migrationLastmodLabel"])}” using sitemap last-modified values or a fallback; it is not a confirmed publication date. <a href="/methods/">Text and measurement notes.</a></p></details>
<script id="essay-data" type="application/json">{safe_json({k: v for k, v in row.items() if k != "body"})}</script>'''
    write(f"{row['url']}index.html", layout(row["title"], row["description"], content, row["url"], "writing", row["cover"], "essay"))


def archive_page(rows, data):
    theme_links = "".join(f'<a href="#theme-{i}" data-filter-theme="{esc(t["name"])}">{esc(t["name"])}</a>' for i, t in enumerate(data["themes"], 1))
    entries = ""
    for row in rows:
        entries += f'''<li class="archive-entry" data-slug="{row["slug"]}" data-theme="{esc(row["theme"])}"><span class="entry-number label">{row["no"]:02d}</span>
<a class="archive-art artwork-link" href="{row["cover"]}" data-artwork data-caption="Original cover illustration for {esc(row["title"])}. {esc(row["coverAlt"])}">{image(row["cover"], row["coverAlt"], sizes="(max-width: 700px) 36vw, 220px")}</a>
<div class="entry-copy"><div class="label">{esc(row["theme"])} <span>· {row["words"]:,} words</span></div><h2><a href="{row["url"]}">{esc(row["title"])}</a></h2><p>{esc(row["description"])}</p><div class="entry-thread"><span class="label">A word to follow</span><a href="{row["url"]}?term={quote(row["terms"][0]["term"])}#reading-lens">{esc(row["terms"][0]["term"])} <small>{row["terms"][0]["count"]} occurrences ↗</small></a></div><div class="archive-matches"></div></div>
<a class="entry-read" href="{row["url"]}" aria-label="Read {esc(row["title"])}">↗</a></li>'''
    groups = ""
    for i, theme in enumerate(data["themes"], 1):
        rs = [row for row in rows if row["theme"] == theme["name"]]
        links = "".join(f'<li><a href="{r["url"]}">{esc(r["title"])}</a><small>{r["words"]:,} w</small></li>' for r in rs)
        groups += f'<section class="theme-list" id="theme-{i}"><div><span class="label">Preoccupation {i:02d}</span><h2>{esc(theme["name"])}</h2><p>{esc(theme["question"])}</p></div><ol>{links}</ol></section>'
    body = f'''<header class="page-opening"><span class="label">The complete collection / future(memo)</span><h1>Following the<br>same restlessness.</h1><div class="page-dek"><p>Twenty essays about intelligence, creative work, and what remains ours to do.</p><p>Read the covers. Follow a word. Enter anywhere.<br><a href="/about-the-memo/">A note on the memo ↗</a></p></div></header>
<section class="archive-tools enhanced" aria-label="Explore the writing"><form id="archive-search"><label for="archive-query">Search every written passage</label><div class="search-line"><input id="archive-query" type="search" placeholder="A word, a phrase, a question…" maxlength="180"><button type="submit">Search</button></div><p class="micro">Case-insensitive phrase search across the full text. No network search, no generated summaries.</p></form><div><label for="archive-theme">A preoccupation</label><select id="archive-theme"><option value="">All five themes</option>{"".join(f'<option>{esc(t["name"])}</option>' for t in data["themes"])}</select><div class="archive-view"><button id="archive-list-toggle" type="button" aria-pressed="false" class="plain">Compact reading list</button><button id="archive-reset" type="button" class="plain">Reset</button></div></div></section>
<div class="archive-meta"><p id="archive-status" role="status">{len(rows)} essays · {sum(r["words"] for r in rows):,} words</p><a href="#by-preoccupation">Browse by preoccupation ↓</a></div><ol id="archive-entries" class="archive-entries">{entries}</ol>
<section id="by-preoccupation"><header class="section-heading"><span class="label">An alternative index</span><h2>Five preoccupations.</h2><p>Editorial groupings, not machine-inferred categories.</p></header><nav class="theme-jumps" aria-label="Theme index">{theme_links}</nav>{groups}</section>'''
    write("/futurememo/index.html", layout("future(memo)", "The complete collection of essays by Suff Syed.", body, "/futurememo/", "writing"))


def gallery_page(data):
    plates = ""
    for i, photo in enumerate(data["gallery"], 1):
        plates += f'<figure class="photograph" id="plate-{i:02d}"><a class="artwork-link" data-artwork data-gallery data-caption="Plate {i:02d} / {esc(photo["alt"])}" href="{photo["src"]}">{image(photo["src"], photo["alt"], i != 1, "(max-width: 700px) 86vw, 46vw")}</a><figcaption><a href="#plate-{i:02d}" class="label">Plate {i:02d}</a><a href="{photo["src"]}" data-artwork data-caption="{esc(photo["alt"])}">Look closer ↗</a></figcaption></figure>'
    body = f'<header class="page-opening photo-opening"><span class="label">A deliberate step away</span><h1>Light(works).</h1><div class="page-dek"><p>{esc(data["galleryIntroduction"])}</p><p>22 photographs. No inferred locations or dates.<br>Take your time. Nothing here needs optimizing.</p></div></header><div class="photographs">{plates}</div><div class="photo-end"><p>Just looking.</p><a href="/futurememo/">When you’re ready, back to the words ↗</a></div>'
    write("/lightworks/index.html", layout("light(works)", data["galleryIntroduction"], body, "/lightworks/", "light", data["gallery"][0]["src"], "photography"))


def methods_page(rows):
    total = sum(row["words"] for row in rows)
    passages = sum(len(row["passages"]) for row in rows)
    body = f'''<header class="page-opening"><span class="label">Colophon / Measurement notes</span><h1>A drawing, not<br>a verdict.</h1><div class="page-dek"><p>The data is here to make the writing more navigable, not to tell you what to think.</p></div></header><article class="document-prose">
<h2 id="counting">What gets counted</h2><p>The current collection contains {len(rows)} complete essays, {total:,} words and {passages:,} addressable text passages. Headings, paragraphs, list items, captions and nonempty quotations are counted once. A word is a run of English letters or digits, with an internal apostrophe or hyphen allowed. Curly and straight apostrophes are equivalent for search; plurals are not stemmed. Punctuation alone is not a word.</p><p>The previous migration’s counter reported 45,308 words using a looser HTML-based rule. Differences from that number reflect tokenization, not abridgement. The original text is preserved and checked against its migration fingerprint. Reading time is an estimate at 230 words per minute, rounded up.</p>
<h2 id="sections">An essay has a shape</h2><p>Each heading begins a section. The opening before the first heading is “Opening.” Section lengths include their heading and all following passages up to the next heading. The reading band’s widths are proportional to those counts. The adjacent text index is the keyboard and touch alternative. Paragraph addresses are stored in the source, so an unrelated edit does not move every anchor.</p>
<h2 id="connections">Shared words, not shared beliefs</h2><p>Connections compare prose paragraphs, list items and quotations of at least 20 words from different essays. Tables, headings, captions and code remain counted and searchable, but are not suggested as prose neighbors. Four tables flattened by the previous migration have their original rows and columns restored without changing their text or passage IDs.</p><p>Common function words and “AI” are excluded. A candidate must share at least two eligible words. Shared words that occur in fewer passages receive more weight: squared log(1 + eligible passage count / passages containing the word), summed and divided by the geometric mean of the two vocabulary sizes. Ties use the essay slug and passage ID. At most three different essays are suggested.</p><p>The displayed words are the reasons for a connection. These are lexical neighbors, not semantic similarity scores, fact checks, influence claims, endorsements, or evidence of agreement. A match may be illuminating precisely because the arguments differ. Short passages and passages with no qualifying neighbors say so.</p>
<h2>The illustrated collection</h2><p>The five preoccupations are editorial categories inherited from the original collection. Colored bands identify them. The engraving’s lobes follow the number of essays in a theme; its fine lines and decorative motion are expressive, not measurements. Each tally above the plate represents one hundred words, rounded up. Covers and photographs come from the existing site and can be opened without cropping.</p>
<h2>Privacy, dates and unfinished work</h2><p>Reading and searching happen locally. Only optional reader marks are stored in this browser, with a visible reset. There is no analytics endpoint, live poll or tracking pixel. The research cycle is an authored demonstration, not a running agent system, and gathers no external evidence. The archive’s historical dates came from a sitemap’s last-modified field; unverified publication dates are not presented as publication dates or put into RSS pubDate fields.</p><p>The complete site is static HTML. Reading, section navigation, images and the alternative theme index work without JavaScript. Search and the optional reading lens require JavaScript; no API key or backend is required.</p></article>'''
    write("/methods/index.html", layout("How to read the data", "Transparent notes on this collection's measurements, links and local interactions.", body, "/methods/"))


def feeds(rows, pages):
    items = "".join(f'<item><title>{esc(row["title"])}</title><link>{DOMAIN}{row["url"]}</link><guid isPermaLink="true">{DOMAIN}{row["url"]}</guid><description>{esc(row["description"])}</description></item>' for row in rows)
    rss = f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel><title>future(memo)</title><link>{DOMAIN}/futurememo/</link><description>Essays by Suff Syed. Publication dates are unverified in the migrated archive.</description><atom:link href="{DOMAIN}/futurememo/rss.xml" rel="self" type="application/rss+xml"/>{items}</channel></rss>'
    write("/rss.xml", rss)
    write("/futurememo/rss.xml", rss)
    paths = ["/", "/futurememo/", "/lightworks/", "/research/", "/methods/"] + [row["url"] for row in rows] + [f'/{page["slug"]}/' for page in pages]
    write("/sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + "".join(f"<url><loc>{DOMAIN}{path}</loc></url>" for path in paths) + "</urlset>")
    write("/robots.txt", f"User-agent: *\nAllow: /\nSitemap: {DOMAIN}/sitemap.xml\n")
    write("/.nojekyll", "")


def main():
    data = json.loads((ROOT / "content/corpus.json").read_text())
    cover_descriptions = json.loads((ROOT / "content/cover-descriptions.json").read_text())
    descriptions = json.loads((ROOT / "content/photograph-descriptions.json").read_text())
    if len(descriptions) != len(data["gallery"]):
        raise ValueError("Every photograph requires a description")
    for photo, description in zip(data["gallery"], descriptions):
        photo["alt"] = description
        with Image.open(OUT / photo["src"].lstrip("/")) as im:
            photo["width"], photo["height"] = im.size
    rows = [measure(row, ROOT) for row in data["essays"]]
    for row in rows:
        row["coverAlt"] = cover_descriptions[row["slug"]]
    connect(rows)
    # Asset originals are committed migration inputs; the build never fetches.
    (OUT / "assets/responsive").mkdir(parents=True, exist_ok=True)
    sources = {row["cover"] for row in rows} | {photo["src"] for photo in data["gallery"]}
    for src in sorted(sources):
        with Image.open(OUT / src.lstrip("/")) as im:
            for width in [640, 960]:
                if im.width > width:
                    target = OUT / "assets/responsive" / f"{Path(src).stem}-{width}.webp"
                    resized = im.resize((width, round(im.height * width / im.width)), Image.Resampling.LANCZOS)
                    resized.save(target, "WEBP", quality=82, method=6)
    for source in sorted((ROOT / "site").rglob("*")):
        if source.is_file():
            target = OUT / "assets" / source.relative_to(ROOT / "site")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    for row in rows:
        essay_page(row, rows)
    public_rows = [{key: value for key, value in row.items() if key not in {"body", "passages"}} for row in rows]
    perspective = '<details class="perspective-disclosure"><summary><span>Leave your perspective</span><small>Optional / This browser only</small></summary>' + render_margin() + '</details>'
    home = render_home(public_rows, data["themes"], data["gallery"]) + render_research_teaser() + perspective
    write("/index.html", layout("Reading a mind at work", "An incomplete field guide to intelligence, creative work, and the things that make us human.", home, "/", cover=rows[11]["cover"], kind="home"))
    archive_page(rows, data)
    gallery_page(data)
    for page in data["pages"]:
        content = (ROOT / "content/pages" / f'{page["slug"]}.html').read_text()
        if page["slug"] == "about-me":
            content = content.replace("45,308 words", f'{sum(row["words"] for row in rows):,} words')
        write(f'/{page["slug"]}/index.html', layout(page["title"], page["description"], f'<div class="legacy-document">{content}</div>', f'/{page["slug"]}/', "about" if page["slug"] in {"about-me", "faqs"} else "writing"))
    write("/research/index.html", layout("The unfinished", "An open notebook and an authored example of a research practice. No live agents.", render_research(public_rows), "/research/", "research"))
    methods_page(rows)
    index = [{"slug": row["slug"], "title": row["title"], "theme": row["theme"], "url": row["url"], "passages": [{"id": p["id"], "text": p["text"], "kind": p["kind"], "label": p["label"]} for p in row["passages"]]} for row in rows]
    write("/assets/search-index.json", safe_json(index))
    not_found = '<header class="page-opening"><span class="label">404 / An unexpected turning</span><h1>A loose thread.</h1><div class="page-dek"><p>This address doesn’t lead to a page.<br>The collection is still here.</p><p><a href="/futurememo/">Find an essay in the complete index ↗</a><br><a href="/">Return to the opening collection ↗</a></p></div></header><section class="lost-links"><h2>Another way in.</h2>' + "".join(f'<p><a href="{row["url"]}">{esc(row["title"])}</a></p>' for row in rows[:5]) + '</section>'
    write("/404.html", layout("Not found", "Find a path back into the writing.", not_found, "/404.html"))
    for src, dest in [("/home", "/"), ("/member-site-homepage-1", "/"), ("/futurememo/tag", "/futurememo/"), ("/futurememo/tag/June+2024+Edition", "/futurememo/"), *[(f"/store/p/{slug}", "/store/") for slug in ["buy-me-a-coffee", "chemex", "iced-coffee", "pour-over"]]]:
        body = f'<section class="page-opening"><span class="label">A change of address</span><h1>This way.</h1><p>This page has moved. <a href="{dest}">Continue to its new home ↗</a></p></section>'
        page = layout("This page has moved", "A preserved route from the original site.", body, dest)
        page = page.replace("</head>", f'<meta name="robots" content="noindex"><meta http-equiv="refresh" content="0;url={dest}"></head>')
        write(src + "/index.html", page)
    feeds(rows, data["pages"])
    print(f"Built {len(rows)} complete essays / {sum(row['words'] for row in rows):,} measured words / {len(data['gallery'])} photographs. CNAME unchanged.")


if __name__ == "__main__":
    main()
