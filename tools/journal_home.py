"""Server-rendered opening composition for the scientific-journal home page."""

import json
import math
import re
from html import escape
from pathlib import PurePosixPath
from urllib.parse import quote, unquote, urlsplit

from corpus import TOKEN


def _text(value):
    return escape(str(value), quote=True)


def _integer(value, default=0):
    try:
        return max(0, int(value))
    except (TypeError, ValueError, OverflowError):
        return default


def _color(value, fallback):
    value = str(value)
    return value if re.fullmatch(r"var\(--[a-zA-Z0-9-]+\)", value) else fallback


def _asset(value):
    """Only local, original image URLs belong in this composition."""
    value = str(value or "")
    parsed = urlsplit(value)
    path = unquote(parsed.path)
    if (
        parsed.scheme
        or parsed.netloc
        or not path.startswith("/assets/")
        or any(part in (".", "..") for part in path.split("/"))
        or "\\" in path
    ):
        return ""
    return quote(path, safe="/-._~")


def _srcset(src):
    stem = PurePosixPath(unquote(src)).stem
    stem = quote(stem, safe="-._~")
    return (
        f"/assets/responsive/{stem}-640.webp 640w, "
        f"/assets/responsive/{stem}-960.webp 960w"
    )


def _essay_url(slug, canonical=None):
    canonical = str(canonical or "")
    if canonical.startswith("/futurememo/") and "\\" not in canonical:
        return canonical
    parts = str(slug).strip("/").split("/")
    return "/futurememo/" + "/".join(
        quote(part, safe="-_~") for part in parts if part not in ("", ".", "..")
    ) + "/"


def _polar(radius, angle):
    return 310 + radius * math.cos(angle), 282 + radius * math.sin(angle)


def _path(points, close=False):
    return " ".join(
        f"{'M' if index == 0 else 'L'}{x:.1f},{y:.1f}"
        for index, (x, y) in enumerate(points)
    ) + ("Z" if close else "")


def _engraving(theme, count, mini=False):
    """The lobe count is factual; every other contour is expressive."""
    face, band = theme["face"], theme["band"]
    layers = range(0, 38, 3) if mini else range(38)
    steps = 96 if mini else 180
    parts = [
        f'<circle cx="310" cy="282" r="138" fill="{face}" opacity=".72"/>',
        '<circle cx="310" cy="282" r="136" fill="none" '
        'stroke="var(--cp-engraving)" stroke-width="1"/>',
    ]
    for layer in layers:
        radius = 17 + layer * 2.82
        amplitude = 4 + layer * 0.42
        points = []
        for step in range(steps + 1):
            angle = step / steps * math.tau
            distance = radius + amplitude * math.cos(count * angle + layer * 0.045)
            points.append(_polar(distance, angle))
        strong = layer % 7 == 0
        parts.append(
            f'<path d="{_path(points, True)}" fill="none" '
            f'stroke="{band if strong else "var(--cp-engraving)"}" '
            f'stroke-width="{1.4 if strong else .58}" opacity="{.9 if strong else .7}"/>'
        )
    spokes = 36 if mini else 96
    spoke_paths = []
    for index in range(spokes):
        angle = index / spokes * math.tau
        spoke_paths.append(_path([_polar(33, angle), _polar(132, angle + 0.14)]))
    parts.append(
        f'<path d="{" ".join(spoke_paths)}" fill="none" '
        'stroke="var(--cp-engraving)" stroke-width=".45" opacity=".5"/>'
    )
    parts.append(
        f'<circle cx="310" cy="282" r="31" fill="{face}" '
        'stroke="var(--cp-engraving)" stroke-width=".7"/>'
    )
    for radius in range(5, 28, 3):
        parts.append(
            f'<circle cx="310" cy="282" r="{radius}" fill="none" '
            'stroke="var(--cp-engraving)" stroke-width=".45" opacity=".7"/>'
        )
    parts.append('<circle cx="310" cy="282" r="3" fill="var(--cp-bg-elevated)"/>')
    return "".join(parts)


def _bars(words):
    count = (words + 99) // 100
    spacing = min(11, 190 / max(1, count - 1))
    return "".join(
        f'<path class="word-bar" d="M{190 + index * spacing:.2f} 47V107" '
        f'stroke="var(--cp-text)" stroke-width="{2.2 if index % 5 == 4 else .8}"/>'
        for index in range(count)
    )


def _plate(theme, count, words, prefix):
    bars = (words + 99) // 100
    border = []
    for index in range(40):
        x, y = _polar(150, index / 40 * math.tau)
        major = index % 5 == 0
        border.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{5 if major else 2.4}" '
            f'fill="{theme["band"] if major else "var(--cp-engraving)"}" '
            f'opacity="{.85 if major else .6}"/>'
        )
    name, question = _text(theme["name"]), _text(theme["question"])
    return f"""
      <svg class="engraving" viewBox="0 0 620 570" role="img"
           aria-labelledby="{prefix}-title {prefix}-description" data-lobes="{count}">
        <title id="{prefix}-title">An engraved portrait of {name}</title>
        <desc id="{prefix}-description" data-drawing-description="">{count} essays form this theme.
          The selected essay contains {words:,} words, represented by {bars} bars, rounded up
          to hundreds. The {count}-lobed face follows the essay count.
          Fine lines and the gently moving rings are expressive, not measured evidence.</desc>
        <defs>
          <filter id="{prefix}-grain" x="0%" y="0%" width="100%" height="100%">
            <feTurbulence type="fractalNoise" baseFrequency=".65" numOctaves="3" seed="12" result="noise"/>
            <feColorMatrix in="noise" type="saturate" values="0"/>
            <feComponentTransfer><feFuncA type="linear" slope=".14"/></feComponentTransfer>
            <feBlend in="SourceGraphic" mode="multiply"/>
          </filter>
          <filter id="{prefix}-shadow" x="-20%" y="-20%" width="150%" height="150%">
            <feDropShadow dx="3" dy="7" stdDeviation="7" flood-color="var(--cp-engraving)" flood-opacity=".17"/>
          </filter>
        </defs>
        <rect x="78" y="86" width="324" height="148" fill="{theme["band"]}"/>
        <rect x="109" y="116" width="326" height="152" fill="{theme["second"]}"/>
        <g data-word-bars="">{_bars(words)}</g>
        <text x="190" y="32" font-size="17" data-word-label="">{words:,} words</text>
        <path class="leader" d="M171 67H44V205H17"/>
        <text x="16" y="220" class="technical">02 / LENGTH</text>
        <path d="M470 126L481 135V447L470 438Z" fill="{theme["edge"]}"/>
        <g filter="url(#{prefix}-shadow)"><rect x="150" y="126" width="320" height="320" fill="var(--cp-figure)"/></g>
        <rect x="150" y="126" width="320" height="320" fill="var(--cp-figure)" filter="url(#{prefix}-grain)"/>
        {_engraving(theme, count)}
        <g class="running-ring">{"".join(border)}</g>
        <g class="running-light"><path d="M310 136A146 146 0 0 1 448 234"
           stroke="var(--cp-bg-elevated)" stroke-width="1" fill="none" opacity=".8"/></g>
        <path class="leader" d="M112 156H52V357H22"/>
        <text x="16" y="374" class="technical">01 / THEME</text>
        <path class="leader" d="M436 283H571V314"/>
        <text x="533" y="337" class="technical">03 / FACE</text>
        <text transform="translate(501 443) rotate(-90)" font-size="22">{name}</text>
        <text x="150" y="485" font-size="25">{count} {"essay" if count == 1 else "essays"}. One preoccupation.</text>
        <text x="150" y="510" font-size="16" font-style="italic">{question}</text>
        <path d="M150 534H470M150 530V538M470 530V538" stroke="var(--cp-border-strong)" stroke-width=".6"/>
        <text x="310" y="552" text-anchor="middle" class="technical">A DRAWING OF THE COLLECTION, NOT A MEASURE OF CERTAINTY</text>
      </svg>"""


def _index(items, selected):
    return "".join(
        f'<li data-essay-index="{index}"><a href="{_text(item["url"])}">'
        f'<span class="index-number">{_text(item["no"])}</span>'
        f'<span>{_text(item["title"])}</span></a>'
        f'<button type="button" class="home-preview" data-preview="{index}" '
        f'aria-label="Preview {_text(item["title"])} in the plate" '
        f'aria-pressed="{str(index == selected).lower()}" hidden>Preview</button></li>'
        for index, item in enumerate(items)
    )


def _marked_text(text, term):
    parts, cursor = [], 0
    for match in TOKEN.finditer(text):
        if match.group().lower().replace("’", "'") != term:
            continue
        parts.extend([_text(text[cursor:match.start()]), f"<mark>{_text(match.group())}</mark>"])
        cursor = match.end()
    return "".join(parts) + _text(text[cursor:])


def _trace_rows(word):
    maximum = word["sections"][0]["count"]
    return "".join(
        f'<li><a href="{_text(section["url"])}" data-trace-section="{_text(section["id"])}">'
        f'<span>{_text(section["title"])}</span><span class="trace-count">{section["count"]}</span>'
        f'<span class="trace-rule" style="--portion:{section["count"] / maximum * 100:.6f}%" aria-hidden="true"></span></a></li>'
        for section in word["sections"][:3]
    )


def _plate_terms(plate):
    return "".join(
        f'<a class="plate-term" data-plate-term="{_text(word["term"])}" href="{_text(word["url"])}"'
        f'{" data-selected=true" if index == 0 else ""}>'
        f'{_text(word["term"])} <small>{word["count"]}</small></a>'
        for index, word in enumerate(plate["terms"])
    )


def _neighbor(plate):
    if not plate["related"]:
        return '<p>No qualifying prose neighbor for this passage.</p>'
    match = plate["related"][0]
    return (f'<a href="{_text(match["url"])}">{_text(match["title"])}</a>'
            f'<p>Shared words: {_text(" · ".join(match["shared"]))}.</p>'
            '<p>Shared vocabulary, not agreement or evidence.</p>')


def _photographs(gallery):
    figures = []
    for image in gallery:
        src = _asset(image.get("src"))
        if not src:
            continue
        alt = str(image.get("alt") or "A photograph from light(works)")
        width, height = _integer(image.get("width")), _integer(image.get("height"))
        dimensions = f' width="{width}" height="{height}"' if width and height else ""
        sizes = ("(max-width: 760px) calc(100vw - 40px), (max-width: 900px) 50vw, 58vw"
                 if not figures else
                 "(max-width: 760px) calc((100vw - 56px) / 2), (max-width: 900px) 24vw, 21vw")
        figures.append(
            '<figure><a class="artwork-link" '
            f'href="{_text(src)}" data-artwork="{_text(src)}" data-caption="{_text(alt)}" '
            f'aria-label="Inspect photograph: {_text(alt)}">'
            f'<img src="{_text(src)}" srcset="{_text(_srcset(src))}" '
            f'sizes="{sizes}" '
            f'alt="{_text(alt)}"{dimensions} loading="lazy" decoding="async">'
            f'<span class="home-inspect" aria-hidden="true">↗</span></a>'
            f'<figcaption><span class="photo-plate-number">Plate {len(figures) + 1:02d}</span>{_text(alt)}</figcaption></figure>'
        )
        if len(figures) == 3:
            break
    return "".join(figures)


def render_cover():
    return '''
<section class="home-cover" id="home-title" aria-labelledby="cover-title">
  <p class="label cover-kicker">An open field guide</p>
  <div class="cover-identity">
    <h1 id="cover-title">Suff Syed</h1>
    <p class="cover-role">Suff Syed is a Member of Technical Staff building across AI frontiers at Microsoft.</p>
  </div>
  <div class="cover-invitation">
    <p class="cover-description">Essays on intelligence, creative work, and what remains human.</p>
    <p class="cover-path">Start with <a href="#featured-story">an essay<sup aria-hidden="true">01</sup></a>.
      Trace <a href="#connections">a thought through its words<sup aria-hidden="true">02</sup></a>.
      Step into <a href="#lightworks">the light<sup aria-hidden="true">03</sup></a>.
      Leave room for <a href="#unfinished">the unfinished<sup aria-hidden="true">04</sup></a>.</p>
  </div>
  <div class="cover-signoff">
    <a class="cover-continue" href="#featured-story"><span>Open the field guide</span><span aria-hidden="true">↓</span></a>
    <img class="cover-signature" src="/assets/suff-syed-signature-reversed.svg" width="350" height="148" alt="" decoding="async">
  </div>
</section>'''


def render_home(rows, themes, gallery):
    """Return body HTML only; the caller owns the shell, CSS/JS links and lightbox.

    ``rows`` supplies essay metadata and derived reading plates, ``themes`` the ordered theme/color
    definitions, and ``gallery`` the original local photographs with dimensions.
    No input objects are mutated. The embedded home-data contains selected whole
    prose passages, not duplicate full essay bodies.
    """
    palette = []
    for index, theme in enumerate(themes):
        palette.append({
            "name": str(theme["name"]),
            "id": str(theme["id"]),
            "question": str(theme["question"]),
            "face": _color(theme["face"], "var(--cp-pigment-mint)"),
            "band": _color(theme["band"], "var(--cp-pigment-teal)"),
            "second": _color(theme["second"], "var(--cp-pigment-lilac)"),
            "edge": _color(theme["edge"], "var(--cp-pigment-coral)"),
            "archive": f"/futurememo/#theme-{index + 1}",
        })
    if not palette:
        raise ValueError("render_home requires at least one theme")
    essays = []
    for index, row in enumerate(rows):
        cover = _asset(row.get("cover"))
        words = _integer(row.get("words"))
        essays.append({
            "slug": str(row["slug"]),
            "url": _essay_url(row["slug"], row.get("url")),
            "title": str(row["title"]),
            "description": str(row.get("description") or ""),
            "excerpt": re.split(r"(?<=[.!?])\s+", str(row.get("description") or ""), maxsplit=1)[0],
            "cover": cover,
            "coverAlt": str(row.get("coverAlt") or f'Original cover illustration for {row["title"]}'),
            "srcset": _srcset(cover) if cover else "",
            "words": words,
            "minutes": _integer(row.get("minutes"), max(1, math.ceil(words / 220))),
            "theme": str(row["theme"]),
            "no": str(row.get("no", index + 1)).zfill(2),
            "readingPlate": row["readingPlate"],
        })
    groups = [[row for row in essays if row["theme"] == theme["name"]] for theme in palette]
    active = next(
        (index for index, group in enumerate(groups) if any("qubit-teams" in row["slug"].lower() for row in group)),
        next((index for index, group in enumerate(groups) if group), 0),
    )
    items = groups[active]
    if not items:
        raise ValueError("render_home requires an essay in one of its themes")
    selected = next((index for index, row in enumerate(items) if "qubit-teams" in row["slug"].lower()), 0)
    essay, theme = items[selected], palette[active]
    plate = essay["readingPlate"]
    passage, word = plate["passage"], plate["terms"][0]
    total_words = sum(row["words"] for row in items)
    swatches = "".join(
        f'<span style="--swatch:{theme[key]}"></span>' for key in ("band", "second", "edge")
    )
    options, templates = [], []
    for index, entry in enumerate(palette):
        count = len(groups[index])
        options.append(
            f'<a class="theme-option" href="{entry["archive"]}" data-home-theme="{index}" '
            f'style="--tone:{entry["band"]}"'
            f'{" data-selected=true" if index == active else ""}>'
            f'<svg viewBox="164 136 292 292" aria-hidden="true" focusable="false" data-lobes="{count}">'
            f'{_engraving(entry, count, mini=True)}</svg>'
            f'<span><span class="theme-name">{_text(entry["name"])}</span>'
            f'<small>{count} {"essay" if count == 1 else "essays"}</small></span></a>'
        )
        initial_words = essay["words"] if index == active else (groups[index][0]["words"] if count else 0)
        templates.append(
            f'<template id="home-plate-{index}">'
            f'{_plate(entry, count, initial_words, f"home-pattern-{index}")}</template>'
        )
    data = json.dumps(
        {"themes": palette, "essays": essays, "initial": {"theme": active, "essay": selected}},
        ensure_ascii=True, separators=(",", ":"),
    ).replace("<", "\\u003c")
    photos = _photographs(gallery)
    collection_count = "Twenty" if len(essays) == 20 else str(len(essays))
    theme_count = "Five" if len(palette) == 5 else str(len(palette))
    cover_hidden = "" if essay["cover"] else " hidden"
    cover_source = (
        f'src="{_text(essay["cover"])}" srcset="{_text(essay["srcset"])}"'
        if essay["cover"] else ""
    )
    return f"""
<div class="journal-opening" data-home-root data-motion="paused">
  <section class="opening" id="featured-story" aria-labelledby="home-essay-title">
    <article class="featured" aria-labelledby="home-essay-title">
      <div class="featured-copy">
        <p class="label">One thought to start with</p>
        <h2 id="home-essay-title"><a data-home-title href="{_text(essay["url"])}">{_text(essay["title"])}</a></h2>
        <p data-home-excerpt>{_text(essay["excerpt"])}</p>
        <div class="featured-meta">
          <a class="primary-link" data-home-essay-link href="{_text(essay["url"])}">Read this essay ↗</a>
          <a class="secondary-link" href="#connections">Explore the connections ↓</a>
        </div>
      </div>
      <a class="cover-button artwork-link" data-home-artwork href="{_text(essay["cover"])}"
         data-artwork="{_text(essay["cover"])}" data-caption="Original cover illustration for {_text(essay["title"])}"
         aria-label="Inspect original cover illustration for {_text(essay["title"])}"{cover_hidden}>
        <img data-home-cover {cover_source} sizes="(max-width: 760px) calc(100vw - 40px), 52vw"
             alt="{_text(essay["coverAlt"])}" fetchpriority="high" decoding="async">
        <span class="enlarge" aria-hidden="true">↗</span>
      </a>
    </article>
  </section>
  <section class="exploration chapter" id="connections" aria-labelledby="connections-title">
    <header class="chapter-heading">
      <div><p class="label chapter-number">The collection / {collection_count} essays</p>
        <h2 id="connections-title">Follow a thought further.</h2></div>
      <div class="chapter-purpose"><p>Read a whole passage. Follow a word through the essay around it.</p>
        <a class="secondary-link" href="/methods/#reading-plates">How to read this plate ↗</a></div>
    </header>
    <div class="collection-instrument">
      <details class="theme-selector" data-home-theme-selector open>
        <summary><span data-home-current-theme>{_text(theme["name"])}</span><span class="theme-toggle-label">Change theme</span></summary>
      <section class="themes" id="preoccupations" aria-labelledby="home-themes-title">
        <div><h3 id="home-themes-title">{theme_count} preoccupations</h3>
          <p class="theme-help"><span data-home-theme-help>Follow a pattern into the essay archive.</span>
            <noscript>The diagram below depicts {_text(theme["name"])}. Each pattern links to its essays.</noscript></p></div>
        <div class="theme-options" data-home-theme-options aria-label="The preoccupations">{"".join(options)}</div>
      </section>
      </details>
      <div class="plate" id="reading" aria-label="Original prose beside its measured reading plate">
    <div class="exploration-reading">
      <section class="selected-path" aria-labelledby="selected-path-title">
        <div class="selection-top"><p class="label" id="selected-path-title">Fig. 01 / A passage to follow</p>
          <span class="label" data-home-position>{selected + 1} / {len(items)}</span></div>
        <h3><a data-home-selection-link data-home-selection-title href="{_text(essay["url"])}">{_text(essay["title"])}</a></h3>
        <p class="plate-source" data-home-source>Passage {passage["no"]} / {_text(plate["sectionTitle"])} · {passage["words"]} words, unabridged.</p>
        <blockquote class="plate-quote" data-home-passage-text cite="{_text(plate["url"])}">{_marked_text(passage["text"], word["term"])}</blockquote>
        <div class="selection-actions"><div class="selection-links">
          <a class="primary-link" data-home-selection-link data-home-context href="{_text(plate["url"])}">Read in context ↗</a>
          <a class="secondary-link" href="#home-essay-title">See cover above ↑</a></div>
          <span class="browse-controls" data-home-browse hidden>
            <button type="button" data-home-previous aria-label="Previous essay in this theme">←</button>
            <button type="button" data-home-next aria-label="Next essay in this theme">→</button>
          </span></div>
        <div class="plate-vocabulary">
          <p class="label" id="plate-word-label">A word from this passage</p>
          <div class="plate-terms" data-home-terms aria-labelledby="plate-word-label">{_plate_terms(plate)}</div>
          <p class="micro" data-home-word-status role="status">“{_text(word["term"])}”: {word["here"]} here · {word["count"]} across the full essay.</p>
          <noscript><p class="micro">The word links open the original passage. With JavaScript, they also open the essay’s filtered reading lens.</p></noscript>
        </div>
        <details class="passage-neighbor"><summary>A shared-word detour</summary><div data-home-neighbor>{_neighbor(plate)}</div></details>
      </section>
      <details class="index-strip">
        <summary id="home-index-title">Other essays in this preoccupation</summary>
          <p data-home-index-description>{len(items)} essays in {_text(theme["name"])}.</p>
        <ol class="essay-index" data-home-index aria-label="Essays in the selected theme">{_index(items, selected)}</ol>
        <a class="secondary-link" data-home-archive href="{theme["archive"]}">Browse this theme ↗</a>
      </details>
    </div>
    <figure class="instrument">
      <div class="instrument-top"><span class="label muted" data-home-plate-label>Fig. 02 / {_text(theme["name"])}</span>
        <button class="home-plain" data-home-motion type="button" aria-pressed="false" hidden>Pause the motion</button></div>
      <div data-home-drawing>{_plate(theme, len(items), essay["words"], "home-active")}</div>
      <figcaption class="instrument-caption">
        <span data-home-length>The quoted passage belongs to a {essay["words"]:,}-word essay; about {essay["minutes"]} minutes to read.</span>
        <span data-home-count>{total_words:,} words across this theme.</span>
      </figcaption>
      <details class="reading-key" id="reading-key">
        <summary>How to read this drawing</summary>
        <div class="margin-notes">
      <div class="annotation"><span class="number">01 / Theme</span><h4>A recurring preoccupation</h4>
        <p>The colored bands identify the selected editorial theme.</p>
        <div class="swatches" data-home-swatches aria-hidden="true">{swatches}</div></div>
      <div class="annotation"><span class="number">02 / Length</span><h4>Time spent in a thought</h4>
        <p>One black bar per hundred essay words, rounded up. Length, not importance.</p></div>
      <div class="annotation"><span class="number">03 / Face</span><h4>A pattern, not a verdict</h4>
        <p>Each lobe stands for an essay. Fine lines and motion are expressive, not measured evidence or live telemetry.</p></div>
        </div>
      </details>
      <div class="word-trace" aria-labelledby="word-trace-title">
        <p class="label" id="word-trace-title">Fig. 03 / Where the word returns</p>
        <p class="trace-title" data-home-trace-title>“{_text(word["term"])}” through the essay</p>
        <ol class="trace-sections" data-home-trace-sections>{_trace_rows(word)}</ol>
        <p class="micro" data-home-trace-note>Occurrences by section, including headings and captions. Showing {min(3, len(word["sections"]))} of {len(word["sections"])} matching sections, most frequent first.</p>
        <a class="secondary-link" data-home-word-link href="{_text(word["url"])}">Find all {word["count"]} occurrences in context ↗</a>
      </div>
    </figure>
    </div>
    </div>
  </section>
  <section class="home-photography chapter" id="lightworks" aria-labelledby="home-photography-title">
    <header class="chapter-heading">
      <div><p class="label chapter-number">Light(works) / A photographic notebook</p>
        <h2 id="home-photography-title">Step outside.</h2></div>
      <div class="chapter-purpose"><p>For a moment, just looking.</p>
        <a class="primary-link" href="/lightworks/">Enter the gallery ↗</a></div>
    </header>
    <div class="home-photo-grid">{photos or '<p class="home-photo-empty">The photographic notebook continues in light(works).</p>'}</div>
  </section>
  <div class="home-sr-only" role="status" aria-live="polite" aria-atomic="true" data-home-status></div>
  {"".join(templates)}
  <script id="home-data" type="application/json">{data}</script>
</div>"""
