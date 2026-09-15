"""Source-bound authored series, separate from themes and recommendations."""
import hashlib
import re
from html import escape

from bs4 import BeautifulSoup

from reading_guide import read_json

ROMAN = ("I", "II", "III", "IV")


def load_series(rows, root):
    data = read_json(root / "content/series.json")
    if (not isinstance(data, dict) or set(data) != {"version", "id", "title", "description", "parts"}
            or type(data["version"]) is not int or data["version"] != 1):
        raise ValueError("Series definition requires the exact version-1 schema")
    if not isinstance(data["id"], str) or not re.fullmatch(r"[a-z]+(?:-[a-z]+)*", data["id"]):
        raise ValueError("Series id must be a stable slug")
    for key, limit in (("title", 100), ("description", 180)):
        value = data[key]
        if not isinstance(value, str) or not value.strip() or len(value) > limit or re.search(r"[<>]", value):
            raise ValueError(f"Series {key} must be bounded plain text")
    if not isinstance(data["parts"], list) or len(data["parts"]) != 4:
        raise ValueError("The verified series requires four ordered parts")
    by_slug = {row["slug"]: row for row in rows}
    seen, parts = set(), []
    for index, part in enumerate(data["parts"]):
        if not isinstance(part, dict) or set(part) != {"number", "slug", "sourceSha256", "sourceIds"}:
            raise ValueError("Each series part requires its authored number, slug, source hash and source IDs")
        if type(part["number"]) is not int or part["number"] != index + 1:
            raise ValueError("Series parts must retain their authored order")
        slug = part["slug"]
        if not isinstance(slug, str) or slug not in by_slug or slug in seen:
            raise ValueError(f"Unknown or duplicate series member: {slug!r}")
        seen.add(slug)
        source = (root / "content/essays" / f"{slug}.html").read_bytes()
        if hashlib.sha256(source).hexdigest() != part["sourceSha256"]:
            raise ValueError(f"Stale series evidence: {slug}")
        ids = part["sourceIds"]
        if (not isinstance(ids, list) or not 1 <= len(ids) <= 3
                or not all(isinstance(identifier, str) for identifier in ids) or len(set(ids)) != len(ids)):
            raise ValueError(f"Invalid series source IDs: {slug}")
        body = BeautifulSoup(source, "html.parser")
        positions = {node["id"]: index for index, node in enumerate(body.select("[id]"))}
        if any(identifier not in positions for identifier in ids):
            raise ValueError(f"Missing authored series evidence: {slug}")
        if [positions[identifier] for identifier in ids] != sorted(positions[identifier] for identifier in ids):
            raise ValueError(f"Series evidence must follow source order: {slug}")
        parts.append({**part, "number": index + 1, "label": ROMAN[index], "row": by_slug[slug]})
    return {**data, "parts": parts}


def member(series, slug):
    return next((part for part in series["parts"] if part["slug"] == slug), None)


def render_context(series, slug):
    part = member(series, slug)
    if part is None:
        return ""
    return f'''<nav class="series-context" aria-label="Authored series" data-series="{escape(series["id"])}" data-series-part="{part["number"]}">
<a href="/#writing">{escape(series["title"])}</a><span>Part {part["label"]} of IV</span>
<a class="series-evidence" href="#{escape(part["sourceIds"][0])}">Author's series note</a></nav>'''


def render_part_navigation(series, slug):
    part = member(series, slug)
    if part is None:
        return ""
    links = []
    index = part["number"] - 1
    for offset, label, rel in ((-1, "Previous", "prev"), (1, "Next", "next")):
        target = index + offset
        if 0 <= target < len(series["parts"]):
            other = series["parts"][target]
            links.append(f'''<a class="series-step" rel="{rel}" href="{escape(other["row"]["url"])}">
<span class="series-step-label">{label} / Part {other["label"]}</span>
<span class="series-step-title">{escape(other["row"]["title"])}</span></a>''')
    return f'''<nav class="series-pagination" aria-label="{escape(series["title"])} part navigation">
<h2>Continue the series</h2>{"".join(links)}</nav>'''
