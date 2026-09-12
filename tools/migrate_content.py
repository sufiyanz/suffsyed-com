"""One-time, offline migration of the committed Atlas pages into editable sources.

Run only against the original migration revision. The normal build never needs git
history, Squarespace, or scrape/raw. Existing stable IDs survive subsequent edits.
"""
import hashlib
import json
import re
import subprocess
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
REVISION = "a0fca809ff8b76dfb5d89aed56fb4e2e7300e2c3"
THEMES = [
    ("design", "Design", "Where does creative agency go next?", "mint", "teal", "rose", "coral"),
    ("builders-craft", "Builders & craft", "What can one person become?", "slate", "teal", "lilac", "mint"),
    ("work-careers", "Work & careers", "What do we gain—and what do we lose?", "lemon", "coral", "rose", "orange"),
    ("industry-markets", "Industry & markets", "Who gets to shape what comes next?", "mint", "blue", "lemon", "lilac"),
    ("culture-hype", "Culture & hype", "What is worth believing?", "rose", "green", "orange", "teal"),
]


def original(path):
    return subprocess.check_output(["git", "show", f"{REVISION}:{path}"], cwd=ROOT).decode()


def normalized(fragment):
    soup = BeautifulSoup(fragment, "html.parser")
    return " ".join(soup.get_text(" ", strip=True).split())


def stable_ids(soup):
    seen = set()
    for el in soup.find_all(["h1", "h2", "h3", "h4", "p", "li", "figcaption", "pre", "blockquote"]):
        if not el.get_text(strip=True):
            continue
        prefix = "h" if el.name.startswith("h") else "p"
        digest = hashlib.sha256(normalized(str(el)).encode()).hexdigest()[:10]
        base = el.get("id") or f"{prefix}-{digest}"
        identifier, count = base, 2
        while identifier in seen:
            identifier = f"{base}-{count}"
            count += 1
        el["id"] = identifier
        seen.add(identifier)


def main():
    content = ROOT / "content"
    if (content / "corpus.json").exists():
        raise SystemExit("Content already exists; migration is deliberately one-time.")
    (content / "essays").mkdir(parents=True, exist_ok=True)
    (content / "pages").mkdir(exist_ok=True)
    paths = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", REVISION, "docs"], cwd=ROOT).decode().splitlines()
    essays = []
    for path in paths:
        if not re.fullmatch(r"docs/futurememo/[^/]+/index.html", path) or "/tag/" in path:
            continue
        soup = BeautifulSoup(original(path), "html.parser")
        body = soup.select_one("article.essay > .body")
        if body is None:
            continue
        slug = path.split("/")[2]
        body_html = body.decode_contents().strip()
        theme = next(name for _, name, *_ in THEMES if name in soup.select_one(".strip").get_text())
        words = int(re.search(r'([\d,]+)</span>&nbsp;words', original(path)).group(1).replace(",", ""))
        clean = BeautifulSoup(body_html, "html.parser")
        stable_ids(clean)
        (content / "essays" / f"{slug}.html").write_text(str(clean) + "\n")
        date = soup.select_one(".essay .end").get_text(" ", strip=True).split("·")[-1].strip()
        essays.append({
            "slug": slug,
            "title": soup.select_one(".essay-head h1").get_text(),
            "description": soup.select_one('meta[name="description"]')["content"],
            "cover": soup.select_one(".hero-fig img")["src"],
            "theme": theme,
            "no": int(soup.select_one(".strip .n").get_text().split()[-1]),
            "migrationLastmodLabel": date,
            "publicationDate": None,
            "legacyWords": words,
            "originalTextSha256": hashlib.sha256(normalized(body_html).encode()).hexdigest(),
        })
    essays.sort(key=lambda row: row["no"])
    pages = []
    for slug in ["about-me", "about-the-memo", "faqs", "the-end-of-design-report", "store"]:
        soup = BeautifulSoup(original(f"docs/{slug}/index.html"), "html.parser")
        title = soup.select_one("h1").get_text()
        for el in soup.select("header.mast, footer.foot, script"):
            el.decompose()
        body = soup.body
        for el in body.select("[style]"):
            del el["style"]
        # The old "since" label incorrectly treated migration dates as publication.
        for el in body.select(".cap"):
            if "since 2025" in el.get_text():
                el.string = el.get_text().replace(" · since 2025", "")
        (content / "pages" / f"{slug}.html").write_text(body.decode_contents().strip() + "\n")
        pages.append({"slug": slug, "title": title, "description": soup.select_one('meta[name="description"]')["content"]})
    light = BeautifulSoup(original("docs/lightworks/index.html"), "html.parser")
    gallery = [{"src": img["src"], "alt": f"Photograph {i:02d} from light(works), by Suff Syed."}
               for i, img in enumerate(light.select(".plates img"), 1)]
    data = {
        "version": 1,
        "migrationRevision": REVISION,
        "provenance": "Full text and local assets migrated from the previously committed static Squarespace rebuild. Dates were sitemap lastmod values or a migration fallback, not confirmed publication dates.",
        "themes": [
            dict(id=key, name=name, question=question, **{k: f"var(--cp-pigment-{v})" for k, v in zip(["face", "band", "second", "edge"], colors)})
            for key, name, question, *colors in THEMES
        ],
        "essays": essays, "pages": pages, "gallery": gallery,
        "galleryIntroduction": light.select_one(".dek").get_text(),
    }
    (content / "corpus.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    print(f"Migrated {len(essays)} complete essays, {sum(row['legacyWords'] for row in essays):,} legacy-count words, {len(gallery)} photographs.")


if __name__ == "__main__":
    main()
