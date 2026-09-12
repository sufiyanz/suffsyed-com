"""Build suffsyed.com (the atlas) from the scraped Squarespace pages in scrape/raw/.

    python3 tools/build_site.py

Outputs static HTML into docs/. Images are fetched once into docs/assets/img (cached by URL hash).
"""
import html
import os
import re
import sys
import datetime
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(__file__))
from lib import soupify, clean_title, meta, convert_blog_body, download_image

ROOT = os.path.join(os.path.dirname(__file__), "..")
RAW = os.path.join(ROOT, "scrape", "raw")
OUT = os.path.join(ROOT, "docs")

SITE = "Suff Syed"
DOMAIN = "https://suffsyed.com"
SUBSTACK = "https://substack.com/@suffsyed"
SOCIAL = [("X", "https://x.com/suff_syed"), ("LinkedIn", "https://www.linkedin.com/in/suffsyed/"), ("Substack", SUBSTACK)]

THEMES = {
    "Design": ["how-future-designers-will-win-in-the-age-of-ai", "designers-have-to-move-from-the-surface-to-the-substrate",
               "designers-should-look-to-demis-hassabis-not-jony-ive", "the-design-leaders-are-lying-to-you", "why-im-leaving-design"],
    "Builders & craft": ["how-i-invented-claude-cowork-before-anthropic", "a-new-class-of-software-builders-is-emerging",
                         "stop-confusing-vibe-coding-and-context-engineering", "the-vibe-coders-are-lying-to-you",
                         "qubit-teams-the-future-built-by-two-people-using-ai"],
    "Work & careers": ["a-survival-playbook-for-an-ai-first-world", "ai-acceleration-org-chart-collapse",
                       "are-you-an-ai-illiterate", "ai-is-making-you-faster-and-dumber"],
    "Industry & markets": ["apple-buying-openai", "sour-fig-figma-s-future-is-uncertain-despite-ipo-hype",
                           "ai-has-a-that-s-a-feature-not-a-product-problem"],
    "Culture & hype": ["ai-doesnt-create-slop-humans-do", "what-most-people-are-oblivious-to", "why-people-are-buying-into-ai-doomerism"],
}
THEME_OF = {slug: t for t, slugs in THEMES.items() for slug in slugs}
START_HERE = "why-im-leaving-design"

# ---------------- helpers ----------------
def esc(s): return html.escape(s or "", quote=True)
def n(x): return f"{x:,}"
def mon(d): return d.strftime("%b %Y").upper()
def longdate(d): return d.strftime("%B %-d, %Y")

def write(path, content):
    full = os.path.join(OUT, path.lstrip("/"))
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)
    print("wrote", path)

# sitemap lastmod dates
_ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
LASTMOD = {}
for u in ET.parse(os.path.join(ROOT, "scrape", "sitemap.xml")).getroot().findall("s:url", _ns):
    lm = u.find("s:lastmod", _ns)
    if lm is not None:
        LASTMOD[u.find("s:loc", _ns).text.strip()] = datetime.date.fromisoformat(lm.text.strip())

# ---------------- shared chrome ----------------
def layout(title, description, body, path, og_image=None, current=None, extra_head=""):
    page_title = title if title == SITE else f"{title} — {SITE}"
    og = f'<meta property="og:image" content="{DOMAIN}{og_image}">' if og_image else ""
    cur = lambda k: ' aria-current="page"' if current == k else ""
    return f'''<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(page_title)}</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="{DOMAIN}{path}">
<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(description)}"><meta property="og:type" content="website">{og}
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="data:,"><link rel="stylesheet" href="/assets/atlas.css"><link rel="alternate" type="application/rss+xml" title="future(memo)" href="/futurememo/rss.xml">{extra_head}
</head><body id="top">
<header class="mast">
  <a class="mark" href="/" aria-label="{SITE}">S</a>
  <a class="name" href="/">{SITE}</a>
  <nav class="mono"><a href="/futurememo/"{cur('memo')}>future(memo)</a><a href="/about-me/"{cur('about')}>About</a><a href="/lightworks/"{cur('light')}>light(works)</a></nav>
  <a class="pill mono arrow" href="{SUBSTACK}" target="_blank" rel="noopener">Subscribe</a>
</header>
{body}
<footer class="foot mono">
  <span>{SITE} &middot; Bangalore, London, New York &amp; Seattle</span>
  <span class="social">{''.join(f'<a href="{u}" target="_blank" rel="noopener">{k}</a>' for k, u in SOCIAL)}</span>
  <a href="#top">Back to top ↑</a>
</footer>
</body></html>'''

def sheet(r):
    return f'''<a class="sheet" href="/futurememo/{r['slug']}/" title="{esc(r['title'])}"><div class="pg">
  <div class="st"><span>future(memo)</span><span>No. {r['no']:02d}</span></div>
  <h4>{esc(r['title'])}</h4>
  <div class="fig"><img src="{r['img']}" alt="" loading="lazy"></div>
  <p class="body">{esc(r['first'])}</p>
</div></a>'''

def index_list(rows):
    return '<ul class="idx">' + "".join(
        f'<li><a href="/futurememo/{r["slug"]}/"><span class="i">{r["no"]:02d}</span><span class="t">{esc(r["title"])}</span>'
        f'<span class="d">{mon(r["date"])}</span><span class="w">{n(r["words"])} w</span></a></li>' for r in rows) + '</ul>'

# ---------------- essays ----------------
def load_essays():
    rows = []
    for t_slugs in THEMES.values():
        for slug in t_slugs:
            soup = soupify(os.path.join(RAW, f"futurememo__{slug}.html"))
            og_img = meta(soup, prop="og:image")
            hero = download_image(og_img) if og_img else None
            body_html = convert_blog_body(soup, skip_leading_image=og_img)
            text = re.sub(r"<[^>]+>", " ", body_html)
            paras = [re.sub(r"^[^A-Za-z0-9“\"‘']+", "", html.unescape(re.sub(r"<[^>]+>", "", p)).strip())
                     for p in re.findall(r"<p>(.*?)</p>", body_html, re.S)]
            buf = []
            for p in paras:
                if len(p) < 60: continue
                buf.append(p)
                if sum(map(len, buf)) >= 700: break
            words = len(re.findall(r"[A-Za-z0-9’'\-]+", html.unescape(text)))
            date = LASTMOD.get(f"https://www.suffsyed.com/futurememo/{slug}", datetime.date(2025, 11, 1))
            rows.append(dict(slug=slug, title=clean_title(soup), excerpt=meta(soup, name="description") or "",
                             img=hero or "", body=body_html, words=words, minutes=max(1, round(words / 230)),
                             date=date, first=" ".join(buf)[:1100], theme=THEME_OF[slug]))
    rows.sort(key=lambda r: (-r["date"].toordinal(), r["title"]))
    for i, r in enumerate(rows, 1):
        r["no"] = i
    return rows

def gen_essay(r, rows):
    i = r["no"] - 1
    prev_ = rows[i + 1] if i + 1 < len(rows) else None   # older
    next_ = rows[i - 1] if i > 0 else None               # newer
    same = [x for x in rows if x["theme"] == r["theme"] and x["slug"] != r["slug"]][:4]
    hero = f'<figure class="hero-fig"><img src="{r["img"]}" alt=""><figcaption></figcaption></figure>' if r["img"] else ""
    sep = '<span class="sep">·</span>'
    nav_cells = ""
    if prev_:
        nav_cells += f'<div class="cell"><a href="/futurememo/{prev_["slug"]}/"><span class="lbl mono back">Previous essay</span><span class="t">{esc(prev_["title"])}</span></a></div>'
    if next_:
        nav_cells += f'<div class="cell next"><a href="/futurememo/{next_["slug"]}/"><span class="lbl mono arrow">Next essay</span><span class="t">{esc(next_["title"])}</span></a></div>'
    more = "".join(f'<li><a href="/futurememo/{x["slug"]}/"><span class="i">{x["no"]:02d}</span><span><span class="t">{esc(x["title"])}</span><span class="d">{mon(x["date"])}</span></span><span class="c">{n(x["words"])}</span></a></li>' for x in same)
    body = f'''
<section class="essay-head">
  <div class="strip mono">
    <span>{sep.join(f'<span style="white-space:nowrap">{x}</span>' for x in [f'<span class="n num">No. {r["no"]:02d}</span>', esc(r["theme"]), mon(r["date"]), f'<span class="num">{n(r["words"])}</span>&nbsp;words', f'<span class="num">{r["minutes"]}</span>&nbsp;min'])}</span>
    <a class="arrow" href="/futurememo/">future(memo)</a>
  </div>
  <h1>{esc(r['title'])}</h1>
  <p class="dek">{esc(r['excerpt'])}</p>
</section>
<article class="essay">
  {hero}
  <div class="body">
{r['body']}
  </div>
  <div class="end mono"><span>End of essay No. {r['no']:02d}</span><span>{esc(r['theme'])} &middot; {longdate(r['date'])}</span></div>
</article>
<div class="band nav two">{nav_cells}</div>
<div class="band soft two">
  <div class="cell"><div class="cell-head mono"><span>More in {esc(r['theme'])}</span><a class="more arrow" href="/futurememo/">All essays</a></div><ul class="list ranked">{more}</ul></div>
  <div class="cell"><div class="cell-head mono"><span>Subscribe</span></div><p class="prose">Get a quarterly email from me about a curated set of topics. Your privacy and time will be respected.</p><p class="prose" style="margin-top:14px"><a class="mono arrow go" href="{SUBSTACK}" target="_blank" rel="noopener">future(memo) on Substack</a></p></div>
</div>
<script>
const bar=document.createElement('div');bar.className='progress';document.body.prepend(bar);
addEventListener('scroll',()=>{{const h=document.documentElement;bar.style.width=(h.scrollTop/(h.scrollHeight-h.clientHeight)*100)+'%';}},{{passive:true}});
</script>'''
    write(f"/futurememo/{r['slug']}/index.html", layout(r["title"], r["excerpt"], body, f"/futurememo/{r['slug']}/", r["img"], "memo"))

# ---------------- home & archive ----------------
def hero_band(rows):
    latest, longest = rows[0], sorted(rows, key=lambda r: -r["words"])[:4]
    themes = "".join(f'<li><a href="/futurememo/#theme-{i}"><span class="i">{i:02d}</span><span class="t">{esc(t)}</span><span class="c num">{len(sl)}</span></a></li>'
                     for i, (t, sl) in enumerate(THEMES.items(), 1))
    ranked = "".join(f'<li><a href="/futurememo/{r["slug"]}/"><span class="i">{i:02d}</span><span><span class="t">{esc(r["title"])}</span><span class="d">{mon(r["date"])}</span></span><span class="c">{n(r["words"])}</span></a></li>'
                     for i, r in enumerate(longest, 1))
    return f'''
<div class="band hero">
  <div class="cell"><div class="cell-head mono"><span>Browse by theme</span><a class="more arrow" href="/futurememo/">All essays</a></div><ul class="list">{themes}</ul></div>
  <div class="cell"><div class="feat"><div>
    <div class="k mono"><span class="red num">01</span><span>Latest essay</span></div>
    <h2>{esc(latest['title'])}</h2><p class="dek">{esc(latest['excerpt'])}</p>
    <a class="go mono arrow" href="/futurememo/{latest['slug']}/">Read the essay</a>
  </div><div class="sheets-3">{''.join(sheet(r) for r in rows[:3])}</div></div></div>
  <div class="cell"><div class="cell-head mono"><span>Longest reads</span><span class="more">Words</span></div><ul class="list ranked">{ranked}</ul></div>
</div>'''

def corpus_band(rows):
    total, maxw = sum(r["words"] for r in rows), max(r["words"] for r in rows)
    span = f"{mon(rows[-1]['date'])} — {mon(rows[0]['date'])}"
    spark = "".join(f'<a href="/futurememo/{r["slug"]}/" style="height:{max(2, round(44 * r["words"] / maxw))}px" data-t="No. {r["no"]:02d} · {esc(r["title"])} · {n(r["words"])} words"></a>' for r in reversed(rows))
    return f'''
<div class="band corpus">
  <div class="cell"><div class="cell-head mono"><span>The corpus, in order of publication</span><span class="more">Bar height = length</span></div>
    <div class="spark" id="spark">{spark}</div><div class="spark-label mono" id="sparkLabel">Hover a bar</div></div>
  <div class="cell stat"><span class="big">{n(total)}</span><span class="cap">words across {len(rows)} essays, {span.lower()}</span></div>
</div>
<script>const L=document.getElementById('sparkLabel');document.querySelectorAll('#spark a').forEach(a=>a.addEventListener('mouseenter',()=>L.textContent=a.dataset.t));document.getElementById('spark').addEventListener('mouseleave',()=>L.textContent='Hover a bar');</script>'''

def start_card(rows):
    s = next(r for r in rows if r["slug"] == START_HERE)
    return f'''
<div class="start">
  <div><div class="star">✦</div><div class="mono muted">If you read one,<br>start here</div></div>
  <div><div class="mono muted" style="margin-bottom:8px">Essay No. {s['no']:02d} · {mon(s['date'])} · {n(s['words'])} words</div><h3>{esc(s['title'])}</h3><p class="dek">{esc(s['excerpt'])}</p></div>
  <div><a class="go mono arrow" href="/futurememo/{s['slug']}/">Read</a></div>
</div>'''

def gen_home(rows, about, light_imgs):
    body = f'''
<section class="title">
  <h1 class="hang"><span class="p">(</span>Future memo<span class="p">)</span></h1>
  <p class="dek">{len(rows)} long-form essays on artificial intelligence, design, and the small number of people quietly building what comes next. By Suff Syed, written from the frontier at Microsoft Research.</p>
</section>
{hero_band(rows)}
{corpus_band(rows)}
{start_card(rows)}
<section class="sec">
  <div class="sec-head mono"><span class="n num">02</span><span>The index</span></div>
  <div class="sec-lead"><h2>Every essay, in order of publication.</h2><p>Each piece is written to outlast the news cycle that provoked it. Word counts are exact.</p></div>
  {index_list(rows)}
</section>
<section class="sec">
  <div class="sec-head mono"><span class="n num">03</span><span>The author</span></div>
</section>
<div class="band soft three" style="border-top:0">
  <div class="cell"><div class="cell-head mono"><span>About</span><a class="more arrow" href="/about-me/">More</a></div><p class="prose">{esc(about['bio'])}</p></div>
  <div class="cell"><div class="cell-head mono"><span>light(works)</span><a class="more arrow" href="/lightworks/">All plates</a></div>
    <div class="sheets-3" style="grid-template-columns:repeat(4,1fr);gap:8px">{''.join(f'<a href="/lightworks/"><img src="{i}" alt="" loading="lazy" style="aspect-ratio:1;object-fit:cover;border:1px solid var(--rule-2)"></a>' for i in light_imgs[:4])}</div></div>
  <div class="cell"><div class="cell-head mono"><span>Elsewhere</span></div><ul class="list plain">{''.join(f'<li><a href="{u}" target="_blank" rel="noopener"><span class="t">{k}</span><span class="c mono">↗</span></a></li>' for k, u in SOCIAL)}<li><a href="{about['interview_url']}" target="_blank" rel="noopener"><span class="t">Interview · The Creative Factor</span><span class="c mono">↗</span></a></li></ul></div>
</div>'''
    write("/index.html", layout(SITE, "Essays on AI, design, and the builders shaping what comes next, by Suff Syed.", body, "/", rows[0]["img"]))

def gen_archive(rows, memo):
    by_theme = ""
    for i, (t, slugs) in enumerate(THEMES.items(), 1):
        rs = [r for r in rows if r["slug"] in slugs]
        by_theme += f'<section class="sec" id="theme-{i}"><div class="sec-head mono"><span class="n num">{i + 1:02d}</span><span>{esc(t)}</span><span class="muted" style="margin-left:auto">{len(rs)} essays</span></div>{index_list(rs)}</section>'
    body = f'''
<section class="title">
  <h1 class="hang"><span class="p">(</span>Future memo<span class="p">)</span></h1>
  <p class="dek big">{esc(memo['lede'])}</p>
  <p class="dek">{esc(memo['p2'])} <a href="/about-the-memo/" class="mono arrow">About the memo</a></p>
</section>
<section class="sec" style="padding-top:36px">
  <div class="sec-head mono"><span class="n num">01</span><span>The sheets</span><span class="muted" style="margin-left:auto">{len(rows)} essays · {n(sum(r['words'] for r in rows))} words</span></div>
  <div class="sheet-grid">{''.join(f'<div>{sheet(r)}<div class="fig-cap"><span class="n mono">No. {r["no"]:02d} · {mon(r["date"])}</span><span class="t">{esc(r["title"])}</span></div></div>' for r in rows)}</div>
</section>
{by_theme}'''
    write("/futurememo/index.html", layout("future(memo)", memo["lede"], body, "/futurememo/", rows[0]["img"], "memo"))

# ---------------- other pages ----------------
def load_about():
    s = soupify(os.path.join(RAW, "about-me.html")); m = s.select_one("main")
    a = next(x for x in m.select("a[href]") if "thecreativefactor" in x.get("href", ""))
    return dict(bio=m.select_one("h2").get_text(" ", strip=True), interview_title=m.select_one("h1").get_text(" ", strip=True),
                interview_kicker=m.select_one("h3").get_text(" ", strip=True), interview_url=a["href"],
                desc=meta(s, name="description") or "")

def gen_about(about, rows):
    body = f'''
<section class="title"><h1>About</h1><p class="dek big">{esc(about['bio'])}</p></section>
<div class="band three">
  <div class="cell"><div class="cell-head mono"><span>{esc(about['interview_kicker'])}</span></div><h3 style="font-size:24px;line-height:27px;letter-spacing:-.025em;max-width:16ch">{esc(about['interview_title'])}</h3><p class="prose" style="margin-top:14px"><a class="mono arrow go" href="{about['interview_url']}" target="_blank" rel="noopener">Full interview</a></p></div>
  <div class="cell"><div class="cell-head mono"><span>Writes</span><a class="more arrow" href="/futurememo/">future(memo)</a></div><div class="stat"><span class="big num">{len(rows)}</span><span class="cap">essays · {n(sum(r['words'] for r in rows))} words · since {rows[-1]['date'].year}</span></div><p class="prose" style="margin-top:14px">Long-form memos on AI, design, and the people building what comes next.</p></div>
  <div class="cell"><div class="cell-head mono"><span>Elsewhere</span></div><ul class="list plain">{''.join(f'<li><a href="{u}" target="_blank" rel="noopener"><span class="t">{k}</span><span class="c mono">↗</span></a></li>' for k, u in SOCIAL)}</ul></div>
</div>
<div class="band soft two">
  <div class="cell"><div class="cell-head mono"><span>Photographs</span><a class="more arrow" href="/lightworks/">light(works)</a></div><p class="prose">Light(Works) is my escape from AI. A deliberate step away from screens and into the world. Out here in the Pacific Northwest, with a camera in hand, I'm just looking.</p></div>
  <div class="cell"><div class="cell-head mono"><span>Questions</span><a class="more arrow" href="/faqs/">FAQs</a></div><p class="prose">Why I don’t respond to comments, and whether I use AI in my writing.</p></div>
</div>'''
    write("/about-me/index.html", layout("About", about["desc"] or about["bio"], body, "/about-me/", None, "about"))

def load_memo():
    s = soupify(os.path.join(RAW, "about-the-memo.html")); m = s.select_one("main")
    ps = [p.get_text(" ", strip=True) for p in m.select("p") if p.get_text(strip=True)]
    h3s = [h.get_text(" ", strip=True) for h in m.select("h3")]
    # first six paragraphs are the intro; the next six are the values (one precedes its heading in source order)
    intro, values = ps[:6], list(zip(h3s[:6], ps[6:12]))
    return dict(lede=intro[0], p2=" ".join(intro[1:4]), intro=intro, values=values, title=m.select_one("h1").get_text(" ", strip=True), desc=meta(s, name="description") or "")

def gen_memo(memo):
    vals = "".join(f'<li><span class="i">{i:02d}</span><div><h3>{esc(h)}</h3><p>{esc(p)}</p></div></li>' for i, (h, p) in enumerate(memo["values"], 1))
    body = f'''
<section class="title"><h1>{esc(memo['title'])}</h1><p class="dek big">{esc(memo['intro'][0])}</p>{''.join(f'<p class="dek">{esc(p)}</p>' for p in memo['intro'][1:])}</section>
<section class="sec" style="padding-top:8px">
  <div class="sec-head mono"><span class="n num">01</span><span>Values that guide the writing</span></div>
  <ul class="entries">{vals}</ul>
</section>
<div class="band soft two" style="margin-top:48px">
  <div class="cell"><div class="cell-head mono"><span>Subscribe to the future(memo)</span></div><p class="prose">Get a quarterly email from me about a curated set of topics. Your privacy and time will be respected.</p><p class="prose" style="margin-top:14px"><a class="mono arrow go" href="{SUBSTACK}" target="_blank" rel="noopener">Subscribe on Substack</a></p></div>
  <div class="cell"><div class="cell-head mono"><span>Read</span></div><p class="prose"><a class="mono arrow go" href="/futurememo/">All essays</a></p></div>
</div>'''
    write("/about-the-memo/index.html", layout("About the future(memo)", memo["desc"] or memo["lede"], body, "/about-the-memo/", None, "memo"))

def gen_faqs():
    s = soupify(os.path.join(RAW, "faqs.html")); m = s.select_one("main")
    items, cur = [], None
    for el in m.select("h4, p"):
        t = el.get_text(" ", strip=True)
        if not t: continue
        if el.name == "h4":
            cur = [t, []]; items.append(cur)
        elif cur:
            cur[1].append(t)
    lis = "".join(f'<li><span class="i">{i:02d}</span><div><h3>{esc(q)}</h3>{"".join(f"<p>{esc(p)}</p>" for p in ps)}</div></li>' for i, (q, ps) in enumerate(items, 1))
    body = f'''
<section class="title"><h1>FAQs</h1><p class="dek">Frequently asked questions.</p></section>
<section class="sec" style="padding-top:8px"><ul class="entries">{lis}</ul></section>'''
    write("/faqs/index.html", layout("FAQs", meta(s, name="description") or "Frequently asked questions.", body, "/faqs/", None, "about"))

def gen_report():
    s = soupify(os.path.join(RAW, "the-end-of-design-report.html")); m = s.select_one("main")
    ps = [p.get_text(" ", strip=True) for p in m.select("p") if len(p.get_text(strip=True)) > 40]
    body = f'''
<section class="title"><h1>The End of Design Report</h1>{''.join(f'<p class="dek big">{esc(p)}</p>' for p in ps[:1])}{''.join(f'<p class="dek">{esc(p)}</p>' for p in ps[1:])}</section>
<div class="band two">
  <div class="cell"><div class="cell-head mono"><span>Read the series</span></div><p class="prose"><a class="mono arrow go" href="/futurememo/#theme-1">Design essays in future(memo)</a></p></div>
  <div class="cell"><div class="cell-head mono"><span>Get the memo</span></div><p class="prose"><a class="mono arrow go" href="{SUBSTACK}" target="_blank" rel="noopener">Subscribe on Substack</a></p></div>
</div>'''
    write("/the-end-of-design-report/index.html", layout("The End of Design Report", meta(s, name="description") or ps[0], body, "/the-end-of-design-report/", None, "memo"))

def load_light():
    s = soupify(os.path.join(RAW, "lightworks.html"))
    imgs = []
    for img in s.select("img"):
        src = img.get("data-image") or img.get("data-src") or img.get("src")
        if src and "squarespace-cdn.com" in src:
            local = download_image(src)
            if local and local not in imgs:
                imgs.append(local)
    dek = s.select_one("main h3").get_text(" ", strip=True)
    return dict(imgs=imgs, dek=dek)

def gen_light(light):
    plates = "".join(f'<figure class="plate"><a href="{i}" target="_blank" rel="noopener"><img src="{i}" alt="" loading="lazy"></a><div class="fig-cap"><span class="n mono">Plate {k:02d}</span></div></figure>' for k, i in enumerate(light["imgs"], 1))
    body = f'''
<section class="title"><h1>Light<span class="p" style="color:var(--red)">(</span>works<span class="p" style="color:var(--red)">)</span></h1><p class="dek big">{esc(light['dek'])}</p></section>
<section class="sec" style="padding-top:8px"><div class="sec-head mono"><span class="n num">01</span><span>Plates</span><span class="muted" style="margin-left:auto">{len(light['imgs'])} photographs</span></div><div class="plates">{plates}</div></section>'''
    write("/lightworks/index.html", layout("light(works)", light["dek"], body, "/lightworks/", light["imgs"][0] if light["imgs"] else None, "light"))


# ---------------- no-404 hardening ----------------
def redirect_stub(from_path, to_path):
    """Client-side redirect for URLs that existed on the Squarespace site (GitHub Pages has no server redirects)."""
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Redirecting…</title>
<link rel="canonical" href="{DOMAIN}{to_path}"><meta name="robots" content="noindex"><meta http-equiv="refresh" content="0; url={to_path}">
<script>location.replace({to_path!r})</script></head>
<body style="font-family:Georgia,serif;padding:2rem"><p>This page has moved to <a href="{to_path}">suffsyed.com{to_path}</a>.</p></body></html>"""
    write(from_path.rstrip("/") + "/index.html", page)

def gen_redirects():
    for src, dst in [("/home", "/"), ("/member-site-homepage-1", "/"), ("/futurememo/tag", "/futurememo/"),
                     ("/futurememo/tag/June+2024+Edition", "/futurememo/"),
                     ("/store/p/buy-me-a-coffee", "/store/"), ("/store/p/chemex", "/store/"),
                     ("/store/p/iced-coffee", "/store/"), ("/store/p/pour-over", "/store/")]:
        redirect_stub(src, dst)

def gen_store():
    body = f"""
<section class="title"><h1>Store</h1><p class="dek big">The shop is closed while the site moves house.</p><p class="dek">If you came here to buy me a coffee — thank you. The best way to support the writing right now is to subscribe.</p></section>
<div class="band two">
  <div class="cell"><div class="cell-head mono"><span>Subscribe</span></div><p class="prose"><a class="mono arrow go" href="{SUBSTACK}" target="_blank" rel="noopener">future(memo) on Substack</a></p></div>
  <div class="cell"><div class="cell-head mono"><span>Read</span></div><p class="prose"><a class="mono arrow go" href="/futurememo/">All essays</a></p></div>
</div>"""
    write("/store/index.html", layout("Store", "The shop is closed while the site moves house.", body, "/store/"))

def gen_404(rows):
    recent = "".join(f'<li><a href="/futurememo/{r["slug"]}/"><span class="i">{r["no"]:02d}</span><span class="t">{esc(r["title"])}</span><span class="c mono">{mon(r["date"])}</span></a></li>' for r in rows[:6])
    slugs = [r["slug"] for r in rows]
    body = f"""
<section class="title"><h1>Not found</h1><p class="dek big" id="nf-msg">There's nothing at this address.</p><p class="dek">The site recently moved off Squarespace; a few old links didn't survive the trip. Everything that was published is still here.</p></section>
<div class="band two">
  <div class="cell"><div class="cell-head mono"><span>Recent essays</span><a class="more arrow" href="/futurememo/">All {len(rows)}</a></div><ul class="list">{recent}</ul></div>
  <div class="cell"><div class="cell-head mono"><span>Elsewhere on the site</span></div><ul class="list plain">
    <li><a href="/"><span class="t">Home</span><span class="c mono">→</span></a></li>
    <li><a href="/futurememo/"><span class="t">future(memo) — every essay</span><span class="c mono">→</span></a></li>
    <li><a href="/about-me/"><span class="t">About</span><span class="c mono">→</span></a></li>
    <li><a href="/lightworks/"><span class="t">light(works)</span><span class="c mono">→</span></a></li></ul></div>
</div>
<script>
// If the requested path looks like an old essay URL, guess the closest current one.
const slugs={slugs!r};const p=location.pathname.replace(/\\/+$/,'').split('/').pop().toLowerCase();
if(p){{const score=s=>{{const a=new Set(p.split('-')),b=new Set(s.split('-'));let n=0;a.forEach(x=>b.has(x)&&n++);return n/Math.max(a.size,b.size);}};
const best=slugs.map(s=>[score(s),s]).sort((x,y)=>y[0]-x[0])[0];
if(best&&best[0]>=0.5){{document.getElementById('nf-msg').innerHTML='Did you mean <a href="/futurememo/'+best[1]+'/" style="text-decoration:underline;text-underline-offset:3px">this essay</a>?';}}}}
</script>"""
    write("/404.html", layout("Not found", "There's nothing at this address.", body, "/404.html"))

def gen_feeds(rows):
    import email.utils, time
    def rfc(d): return email.utils.format_datetime(datetime.datetime(d.year, d.month, d.day, 12, tzinfo=datetime.timezone.utc))
    items = "".join(f"""<item><title>{esc(r['title'])}</title><link>{DOMAIN}/futurememo/{r['slug']}/</link><guid isPermaLink="true">{DOMAIN}/futurememo/{r['slug']}/</guid>
<pubDate>{rfc(r['date'])}</pubDate><description>{esc(r['excerpt'])}</description></item>\n""" for r in rows)
    rss = f"""<?xml version="1.0" encoding="UTF-8"?><rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel>
<title>future(memo)</title><link>{DOMAIN}/futurememo/</link><description>Essays on AI, design, and the builders shaping what comes next, by Suff Syed.</description>
<atom:link href="{DOMAIN}/futurememo/rss.xml" rel="self" type="application/rss+xml"/>
{items}</channel></rss>"""
    write("/futurememo/rss.xml", rss); write("/rss.xml", rss)
    urls = ["/", "/futurememo/", "/about-me/", "/about-the-memo/", "/faqs/", "/the-end-of-design-report/", "/lightworks/", "/store/"] + [f"/futurememo/{r['slug']}/" for r in rows]
    today = datetime.date.today().isoformat()
    sm = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + "".join(f"<url><loc>{DOMAIN}{u}</loc><lastmod>{today}</lastmod></url>" for u in urls) + "</urlset>"
    write("/sitemap.xml", sm)
    write("/robots.txt", f"User-agent: *\nAllow: /\nSitemap: {DOMAIN}/sitemap.xml\n")
    open(os.path.join(OUT, ".nojekyll"), "w").close()

# ---------------- main ----------------
if __name__ == "__main__":
    rows = load_essays()
    about, memo, light = load_about(), load_memo(), load_light()
    for r in rows:
        gen_essay(r, rows)
    gen_home(rows, about, light["imgs"])
    gen_archive(rows, memo)
    gen_about(about, rows)
    gen_memo(memo)
    gen_faqs()
    gen_report()
    gen_light(light)
    gen_redirects(); gen_store(); gen_404(rows); gen_feeds(rows)
    with open(os.path.join(OUT, "CNAME"), "w") as f:
        f.write("suffsyed.com\n")
    print(f"\nDone: {len(rows)} essays, {sum(r['words'] for r in rows):,} words, {len(light['imgs'])} plates.")
