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
SITEMAP = os.path.join(ROOT, "scrape", "sitemap.xml")

SITE_NAME = "Suff Syed"
SOCIAL = {
    "X": "https://x.com/suff_syed",
    "LinkedIn": "https://www.linkedin.com/in/suffsyed/",
    "Substack": "https://substack.com/@suffsyed",
}

# ---- lastmod dates from sitemap ----
ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
tree = ET.parse(SITEMAP)
LASTMOD = {}
for url_el in tree.getroot().findall("s:url", ns):
    loc = url_el.find("s:loc", ns).text.strip()
    lastmod_el = url_el.find("s:lastmod", ns)
    if lastmod_el is not None:
        LASTMOD[loc] = lastmod_el.text.strip()


def fmt_date(iso):
    if not iso:
        return ""
    d = datetime.date.fromisoformat(iso)
    return d.strftime("%B %-d, %Y")


POSTS = [
    "a-new-class-of-software-builders-is-emerging",
    "a-survival-playbook-for-an-ai-first-world",
    "ai-acceleration-org-chart-collapse",
    "ai-doesnt-create-slop-humans-do",
    "ai-has-a-that-s-a-feature-not-a-product-problem",
    "ai-is-making-you-faster-and-dumber",
    "apple-buying-openai",
    "are-you-an-ai-illiterate",
    "designers-have-to-move-from-the-surface-to-the-substrate",
    "designers-should-look-to-demis-hassabis-not-jony-ive",
    "how-future-designers-will-win-in-the-age-of-ai",
    "how-i-invented-claude-cowork-before-anthropic",
    "qubit-teams-the-future-built-by-two-people-using-ai",
    "sour-fig-figma-s-future-is-uncertain-despite-ipo-hype",
    "stop-confusing-vibe-coding-and-context-engineering",
    "the-design-leaders-are-lying-to-you",
    "the-vibe-coders-are-lying-to-you",
    "what-most-people-are-oblivious-to",
    "why-im-leaving-design",
    "why-people-are-buying-into-ai-doomerism",
]


def base_layout(title, description, content, canonical_path, hero_image=None):
    og_image_tag = f'<meta property="og:image" content="https://suffsyed.com{hero_image}">' if hero_image else ""
    page_title = title if title == SITE_NAME else f"{title} — {SITE_NAME}"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{page_title}</title>
<meta name="description" content="{description}">
<link rel="canonical" href="https://suffsyed.com{canonical_path}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:type" content="website">
{og_image_tag}
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="data:,">
<link rel="stylesheet" href="/assets/style.css">
</head>
<body>
<header class="site-header">
  <a class="brand" href="/">Suff Syed</a>
  <nav>
    <a href="/futurememo/">future(memo)</a>
    <a href="/about-me/">About(Me)</a>
    <a href="/lightworks/">light(works)</a>
  </nav>
  <a class="subscribe" href="{SOCIAL['Substack']}" target="_blank" rel="noopener">Subscribe &rarr;</a>
</header>
<main>
{content}
</main>
<footer class="site-footer">
  <p class="quote">&ldquo;Every original idea must withstand the fury of conventional wisdom.&rdquo;</p>
  <p class="social">
    <a href="{SOCIAL['X']}" target="_blank" rel="noopener">X</a>
    <a href="{SOCIAL['LinkedIn']}" target="_blank" rel="noopener">LinkedIn</a>
    <a href="{SOCIAL['Substack']}" target="_blank" rel="noopener">Substack</a>
  </p>
  <p class="location">Bangalore, London, New York, &amp; Seattle.</p>
  <p class="copyright">&copy; {datetime.date.today().year}. All rights reserved.</p>
</footer>
</body>
</html>"""


def write(path, html):
    full = os.path.join(OUT, path.lstrip("/"))
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(html)
    print("wrote", path)


def gen_post(slug):
    src = os.path.join(RAW, f"futurememo__{slug}.html")
    soup = soupify(src)
    title = clean_title(soup)
    desc = meta(soup, name="description") or ""
    og_img_url = meta(soup, prop="og:image")
    hero_local = download_image(og_img_url) if og_img_url else None
    body = convert_blog_body(soup, skip_leading_image=hero_local)
    url = f"https://www.suffsyed.com/futurememo/{slug}"
    date_iso = LASTMOD.get(url)
    date_str = fmt_date(date_iso)

    hero_html = f'<img class="hero" src="{hero_local}" alt="">' if hero_local else ""
    content = f"""
<article class="post">
  <p class="post-meta"><a href="/futurememo/">future(memo)</a> &middot; {date_str}</p>
  <h1>{title}</h1>
  {hero_html}
  <div class="post-body">
  {body}
  </div>
  <p class="back"><a href="/futurememo/">&larr; Back to future(memo)</a></p>
</article>
"""
    html = base_layout(title, desc, content, f"/futurememo/{slug}/", hero_local)
    write(f"/futurememo/{slug}/index.html", html)
    return {
        "slug": slug, "title": title, "desc": desc,
        "date_iso": date_iso, "date_str": date_str, "hero": hero_local,
    }


def gen_futurememo_index(posts):
    posts_sorted = sorted(posts, key=lambda p: p["date_iso"] or "", reverse=True)
    cards = []
    for p in posts_sorted:
        thumb = f'<img src="{p["hero"]}" alt="" loading="lazy">' if p["hero"] else ""
        cards.append(f"""
<a class="post-card" href="/futurememo/{p['slug']}/">
  {thumb}
  <div class="post-card-body">
    <p class="post-meta">{p['date_str']}</p>
    <h3>{p['title']}</h3>
    <p class="excerpt">{p['desc'][:180]}{'…' if len(p['desc']) > 180 else ''}</p>
  </div>
</a>""")
    content = f"""
<div class="page-header">
  <h1>future(memo)</h1>
  <p class="lede">Essays on AI, design, and the builders shaping what comes next.</p>
</div>
<div class="post-grid">
{''.join(cards)}
</div>
"""
    html = base_layout("future(memo)", "Essays on AI, design, and the builders shaping what comes next.", content, "/futurememo/")
    write("/futurememo/index.html", html)


def gen_simple_page(raw_name, out_path, nav_title=None):
    soup = soupify(os.path.join(RAW, f"{raw_name}.html"))
    seo_title = clean_title(soup)
    main = soup.select_one("main")
    h1 = main.select_one("h1") if main else None
    title = nav_title or (h1.get_text(strip=True) if h1 else seo_title)
    desc = meta(soup, name="description") or ""
    body = convert_blog_body(soup, root_selector=".page-section, main .sqs-layout, .content")
    if not body:
        # fallback: grab all sqs-html-content in main
        main = soup.select_one("main") or soup
        parts = []
        for block in main.select(".sqs-block-html .sqs-html-content"):
            parts.append(str(block))
        body = "\n".join(parts)
    content = f"""
<article class="simple-page">
  <h1>{title}</h1>
  <div class="post-body">
  {body}
  </div>
</article>
"""
    html = base_layout(title, desc, content, out_path)
    write(f"{out_path}index.html", html)


def gen_lightworks():
    soup = soupify(os.path.join(RAW, "lightworks.html"))
    imgs = []
    for img in soup.select("img"):
        src = img.get("data-image") or img.get("data-src") or img.get("src")
        if not src or "squarespace-cdn.com" not in src:
            continue
        local = download_image(src)
        if local and local not in imgs:
            imgs.append(local)
    gallery = "\n".join(f'<img src="{i}" alt="" loading="lazy">' for i in imgs)
    content = f"""
<div class="page-header">
  <h1>light(works)</h1>
  <p class="lede">Light(Works) is my escape from AI. A deliberate step away from screens and into the world. Out here in the Pacific Northwest, with a camera in hand, I'm just looking. Noticing light. Finding beauty in the ordinary.</p>
</div>
<div class="gallery">
{gallery}
</div>
"""
    html = base_layout("light(works)", "A photo gallery — light, noticed.", content, "/lightworks/")
    write("/lightworks/index.html", html)


def gen_home():
    soup = soupify(os.path.join(RAW, "home.html"))
    desc = meta(soup, name="description") or "Building AI things."
    content = """
<div class="hero-home">
  <h1>Suff Syed</h1>
  <p class="lede">Building AI things at Microsoft Research. Writing future(memo) — essays on AI, design, and the builders shaping what comes next.</p>
  <p class="home-links">
    <a href="/futurememo/">Read future(memo) &rarr;</a>
    <a href="/about-me/">About me &rarr;</a>
    <a href="/lightworks/">light(works) &rarr;</a>
  </p>
</div>
"""
    html = base_layout("Suff Syed", desc, content, "/")
    write("/index.html", html)


def copy_cname():
    with open(os.path.join(OUT, "CNAME"), "w") as f:
        f.write("suffsyed.com\n")


if __name__ == "__main__":
    gen_home()
    posts = [gen_post(s) for s in POSTS]
    gen_futurememo_index(posts)
    gen_simple_page("about-me", "/about-me/")
    gen_simple_page("about-the-memo", "/about-the-memo/")
    gen_simple_page("faqs", "/faqs/")
    gen_simple_page("the-end-of-design-report", "/the-end-of-design-report/")
    gen_lightworks()
    copy_cname()
    print(f"\nDone. {len(posts)} posts generated.")
