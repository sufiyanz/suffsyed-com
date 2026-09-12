import hashlib
import io
import os
import re
import urllib.parse
import urllib.request
from bs4 import BeautifulSoup
from PIL import Image

IMG_DIR = os.path.join(os.path.dirname(__file__), "..", "docs", "assets", "img")
os.makedirs(IMG_DIR, exist_ok=True)

MAX_WIDTH = 1600
WEBP_QUALITY = 82

_img_cache = {}

ALLOWED_TAGS = {
    "p", "h1", "h2", "h3", "h4", "ul", "ol", "li", "strong", "em", "b", "i",
    "a", "br", "blockquote", "code", "pre", "figure", "figcaption", "img",
    "hr", "span", "div"
}


def clean_url(u):
    """Strip Squarespace query-string image transforms, keep base asset URL."""
    parsed = urllib.parse.urlsplit(u)
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def download_image(url):
    """Download an image (if not already cached) and return its local /assets/img/<name> path."""
    if not url:
        return None
    if url.startswith("//"):
        url = "https:" + url
    base = clean_url(url)
    if base in _img_cache:
        return _img_cache[base]
    ext = os.path.splitext(base)[1].lower()
    h = hashlib.sha1(base.encode()).hexdigest()[:12]
    is_svg = ext == ".svg"
    fname = f"{h}{'.svg' if is_svg else '.webp'}"
    local_path = os.path.join(IMG_DIR, fname)
    web_path = f"/assets/img/{fname}"
    if not os.path.exists(local_path):
        try:
            req = urllib.request.Request(base, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = resp.read()
            if is_svg:
                with open(local_path, "wb") as f:
                    f.write(data)
            else:
                im = Image.open(io.BytesIO(data))
                im.load()
                im = im.convert("RGBA") if im.mode in ("RGBA", "P", "LA") else im.convert("RGB")
                if im.width > MAX_WIDTH:
                    ratio = MAX_WIDTH / im.width
                    im = im.resize((MAX_WIDTH, int(im.height * ratio)), Image.LANCZOS)
                im.save(local_path, "WEBP", quality=WEBP_QUALITY, method=6)
        except Exception as e:
            print(f"  [warn] failed to download {base}: {e}")
            return None
    _img_cache[base] = web_path
    return web_path


def soupify(path):
    with open(path, encoding="utf-8") as f:
        return BeautifulSoup(f, "lxml")


def meta(soup, name=None, prop=None):
    if name:
        tag = soup.find("meta", attrs={"name": name})
    else:
        tag = soup.find("meta", attrs={"property": prop})
    return tag["content"].strip() if tag and tag.get("content") else None


def clean_title(soup):
    t = soup.title.string if soup.title else ""
    t = re.sub(r"\s*[—|]\s*Suff Syed\s*$", "", t or "").strip()
    return t


def _strip_attrs(tag):
    keep = {"a": ["href"], "img": ["src", "alt"]}
    allowed = keep.get(tag.name, [])
    for attr in list(tag.attrs):
        if attr not in allowed:
            del tag[attr]


def convert_blog_body(soup, root_selector=".blog-item-content", skip_leading_image=None):
    """Walk Squarespace block markup and emit clean semantic HTML."""
    root = soup.select_one(root_selector)
    if not root:
        return ""
    out = []
    skipped_hero = False
    for block in root.select(".sqs-block"):
        classes = block.get("class", [])
        if "sqs-block-spacer" in classes or "newsletter-block" in classes:
            continue
        if "sqs-block-image" in classes:
            img = block.select_one("img")
            if img:
                src = img.get("data-image") or img.get("data-src") or img.get("src")
                if (not skipped_hero and skip_leading_image and src
                        and os.path.basename(clean_url(src)) == os.path.basename(clean_url(skip_leading_image))):
                    skipped_hero = True
                    continue
                local = download_image(src)
                if local:
                    caption = block.select_one("figcaption")
                    cap_text = caption.get_text(strip=True) if caption else ""
                    out.append(f'<figure><img src="{local}" alt="{img.get("alt", "")}" loading="lazy">')
                    if cap_text:
                        out.append(f"<figcaption>{cap_text}</figcaption>")
                    out.append("</figure>")
            continue
        if "html-block" in classes:
            content = block.select_one(".sqs-html-content")
            if not content:
                continue
            for img in content.select("img"):
                src = img.get("data-image") or img.get("data-src") or img.get("src")
                local = download_image(src)
                if local:
                    img["src"] = local
                for attr in list(img.attrs):
                    if attr not in ("src", "alt"):
                        del img[attr]
            for tag in content.find_all(True):
                if tag.name not in ALLOWED_TAGS:
                    tag.unwrap()
                else:
                    _strip_attrs(tag)
            inner = "".join(str(c) for c in content.contents)
            out.append(inner)
            continue
        # fallback: quote/embed/other block types -> take text content
        text = block.get_text(" ", strip=True)
        if text:
            out.append(f"<p>{text}</p>")
    html = "\n".join(out)
    html = re.sub(r"(<br\s*/?>\s*){2,}", "<br>", html)
    html = re.sub(r"<p>(\s|<br\s*/?>)*</p>", "", html)
    return html
