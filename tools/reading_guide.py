"""Validate and render offline, source-bound AI reading companions."""
import hashlib
import html
import json
import re
from pathlib import Path

IDENTIFIER = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
MARKUP = re.compile(r"<[^>]*>|`|\*\*|__|\[[^\]]+\]\(")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def read_json(path):
    try:
        return json.loads(Path(path).read_text(), object_pairs_hook=unique_object)
    except (ValueError, OSError) as error:
        raise ValueError(f"{path}: {error}") from error


def validate_guide(guide, row, source):
    prefix = f"Reading guide {row['slug']}"

    def require(condition, message):
        if not condition:
            raise ValueError(f"{prefix}: {message}")

    def shape(value, keys, where):
        require(isinstance(value, dict) and set(value) == set(keys.split()), f"{where}: invalid object keys")

    def text(value, limit, where):
        require(isinstance(value, str) and bool(value.strip()) and value == value.strip()
                and len(value) <= limit and "\n" not in value and not MARKUP.search(value),
                f"{where}: expected plain text, 1-{limit} characters")

    def identifier(value, where):
        require(isinstance(value, str) and IDENTIFIER.fullmatch(value), f"{where}: invalid kebab-case ID")

    shape(guide, "version slug sourceSha256 authorship sections notes", "guide")
    require(type(guide["version"]) is int and guide["version"] == 1, "unsupported version")
    require(guide["slug"] == row["slug"], "slug does not match its source/file")
    require(guide["authorship"] == "ai", "authorship must be ai")
    require(guide["sourceSha256"] == hashlib.sha256(source).hexdigest(), "stale or invalid sourceSha256")
    sections, notes = guide["sections"], guide["notes"]
    require(isinstance(sections, list) and 4 <= len(sections) <= 10, "expected 4-10 sections")
    require(isinstance(notes, list) and 3 <= len(notes) <= 5, "expected 3-5 notes")
    positions = {passage["id"]: index for index, passage in enumerate(row["passages"])}
    section_ids, starts = set(), []
    for section in sections:
        shape(section, "id label anchor bullets", "section")
        identifier(section["id"], "section")
        require(section["id"] not in section_ids, "duplicate section ID")
        section_ids.add(section["id"])
        text(section["label"], 58, "section label")
        anchor = section["anchor"]
        require(isinstance(anchor, str) and anchor in positions and anchor.startswith(("h-", "p-")),
                f"unknown/non-authored anchor {anchor!r}")
        starts.append(positions[anchor])
        require(isinstance(section["bullets"], list) and 1 <= len(section["bullets"]) <= 2, "expected 1-2 bullets")
    require(starts[0] == 0, "first section must begin at the first authored block")
    require(all(a < b for a, b in zip(starts, starts[1:])), "section anchors must be in strict source order")
    spans = {section["id"]: (start, end) for section, start, end in
             zip(sections, starts, starts[1:] + [len(positions)])}

    def citations(ids, section_id):
        require(isinstance(ids, list) and 1 <= len(ids) <= 3 and all(isinstance(item, str) for item in ids),
                "expected 1-3 source IDs")
        require(len(ids) == len(set(ids)), "duplicate source citation")
        begin, end = spans[section_id]
        require(all(item in positions and begin <= positions[item] < end for item in ids),
                f"unknown or out-of-section citation in {section_id}: {ids}")

    for section in sections:
        for bullet in section["bullets"]:
            shape(bullet, "text sourceIds", "bullet")
            text(bullet["text"], 160, "bullet")
            citations(bullet["sourceIds"], section["id"])
    note_ids, noted_sections = set(), set()
    for note in notes:
        shape(note, "id sectionId kind text sourceIds", "note")
        identifier(note["id"], "note")
        require(note["id"] not in note_ids, "duplicate note ID")
        note_ids.add(note["id"])
        require(isinstance(note["sectionId"], str) and note["sectionId"] in section_ids, "note refers to unknown section")
        require(note["sectionId"] not in noted_sections, "at most one note per section")
        noted_sections.add(note["sectionId"])
        require(note["kind"] in ("observation", "question"), "invalid note kind")
        text(note["text"], 320, "note")
        citations(note["sourceIds"], note["sectionId"])
    return guide


def load_guides(rows, root, directory=None, allow_partial=False):
    directory = Path(directory) if directory else root / "content/reading-guides"
    by_slug = {row["slug"]: row for row in rows}
    files = {path.stem: path for path in directory.glob("*.json")}
    unknown = sorted(set(files) - set(by_slug))
    missing = sorted(set(by_slug) - set(files))
    if unknown or (missing and not allow_partial):
        raise ValueError(f"Reading guide coverage: unknown={unknown}, missing={missing}")
    return {slug: validate_guide(read_json(path), by_slug[slug],
                                (root / "content/essays" / f"{slug}.html").read_bytes())
            for slug, path in sorted(files.items())}


def sources(ids, compact=False):
    opening = '<span class="guide-sources inline-sources"> ' if compact else '<span class="guide-sources">Source '
    return opening + " ".join(
        f'<a href="#{html.escape(identifier)}" aria-label="Read source passage {index}">{index}</a>'
        for index, identifier in enumerate(ids, 1)) + "</span>"


def render_guide(guide):
    items = []
    for index, section in enumerate(guide["sections"], 1):
        bullets = "".join(f'<li>{html.escape(bullet["text"])}{sources(bullet["sourceIds"], compact=True)}</li>'
                          for bullet in section["bullets"])
        items.append(f'''<li data-guide-section="{section["id"]}">
<a class="guide-link" href="#{section["anchor"]}" data-guide-anchor="{section["anchor"]}"><span>{index:02d}</span>{html.escape(section["label"])}</a>
<details class="guide-points"><summary>Key points</summary><ul>{bullets}</ul></details></li>''')
    return f'''<details class="reader-rail-disclosure" id="ai-reading-guide" data-guide-version="1" data-guide-authorship="ai" data-guide-source-sha256="{guide["sourceSha256"]}">
<summary>AI reading guide</summary><div class="reader-guide-content">
<p class="reader-rail-note">AI-generated, source-linked.</p>
<nav aria-label="AI reading guide"><ol>{"".join(items)}</ol></nav>
</div></details>'''


def render_notes(guide):
    labels = {section["id"]: section["label"] for section in guide["sections"]}
    notes = "".join(f'''<section class="reader-note" data-note-section="{note["sectionId"]}" id="ai-note-{note["id"]}">
<p class="reader-note-section">{html.escape(labels[note["sectionId"]])}</p><p class="reader-note-kind">{html.escape(note["kind"])}</p>
<p>{html.escape(note["text"])}</p>{sources(note["sourceIds"])}</section>''' for note in guide["notes"])
    return f'''<div class="reading-position enhanced" hidden>
<p>Reading progress <span data-reading-percent>0%</span></p>
<progress max="100" value="0" aria-label="Reading progress through the article body" title="Scroll position within the article text, not a measure of comprehension."></progress></div>
<details class="reader-rail-disclosure" id="ai-reading-notes"><summary>AI reading notes</summary>
<div class="reader-notes-content"><p class="reader-rail-note">Supplementary AI commentary.</p>
<p class="reader-current-section enhanced" data-current-section></p>
<p class="reader-note-empty enhanced" hidden>No AI note for this section.</p>
{notes}<button class="plain enhanced" type="button" data-all-notes aria-pressed="false">Show all AI notes</button>
</div></details>'''
