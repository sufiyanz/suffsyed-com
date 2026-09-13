"""Server-rendered opening composition for the scientific-journal home page."""

import json
import math
import re
from html import escape
from pathlib import PurePosixPath
from urllib.parse import quote, unquote, urlsplit


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
        <g filter="url(#{prefix}-shadow)"><rect x="150" y="126" width="320" height="320" fill="var(--cp-surface)"/></g>
        <rect x="150" y="126" width="320" height="320" fill="var(--cp-surface)" filter="url(#{prefix}-grain)"/>
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
            f'<figcaption>{_text(alt)}</figcaption></figure>'
        )
        if len(figures) == 3:
            break
    return "".join(figures)


def render_home(rows, themes, gallery):
    """Return body HTML only; the caller owns the shell, CSS/JS links and lightbox.

    ``rows`` is the metadata-only essay list, ``themes`` the ordered theme/color
    definitions, and ``gallery`` the original local photographs with dimensions.
    No input objects are mutated. The embedded home-data contains no essay bodies.
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
  <section class="opening" aria-labelledby="home-title">
    <header class="opening-copy"><h1 id="home-title">Reading a mind at work.</h1>
      <p class="subtitle">Essays on intelligence, creative work, and what remains human.</p></header>
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
      <div class="chapter-purpose"><p>Choose a theme to change the opening essay and drawing.</p>
        <p class="micro">Editorial paths, not machine-inferred connections.</p>
        <a class="secondary-link" href="/futurememo/">Explore the complete archive ↗</a></div>
    </header>
    <div class="collection-instrument">
      <details class="theme-selector" data-home-theme-selector open>
        <summary><span data-home-current-theme>{_text(theme["name"])}</span><span class="theme-toggle-label">Change theme</span></summary>
      <section class="themes" id="preoccupations" aria-labelledby="home-themes-title">
        <div><h3 id="home-themes-title">{theme_count} preoccupations.</h3>
          <p class="theme-help"><span data-home-theme-help>Follow a pattern into the essay archive.</span>
            <noscript>The diagram below depicts {_text(theme["name"])}. Each pattern links to its essays.</noscript></p></div>
        <div class="theme-options" data-home-theme-options aria-label="The preoccupations">{"".join(options)}</div>
      </section>
      </details>
      <div class="plate" id="reading" aria-label="An annotated portrait of the writing">
    <figure class="instrument">
      <div class="instrument-top"><span class="label muted" data-home-plate-label>Plate {active + 1:02d} / {_text(theme["name"])}</span>
        <button class="home-plain" data-home-motion type="button" aria-pressed="false" hidden>Pause the motion</button></div>
      <div data-home-drawing>{_plate(theme, len(items), essay["words"], "home-active")}</div>
      <figcaption class="instrument-caption">
        <span data-home-count>{total_words:,} words across this theme.</span>
        <span>Decorative motion, not live telemetry.</span>
      </figcaption>
      <details class="reading-key" id="reading-key">
        <summary>How to read this drawing</summary>
        <div class="margin-notes">
      <div class="annotation"><span class="number">01 / Theme</span><h4>A recurring preoccupation</h4>
        <p>The colored bands identify the selected theme.</p>
        <div class="swatches" data-home-swatches aria-hidden="true">{swatches}</div></div>
      <div class="annotation"><span class="number">02 / Length</span><h4>Time spent in a thought</h4>
        <p>One black bar per hundred words, rounded up. Length, not importance.</p></div>
      <div class="annotation"><span class="number">03 / Face</span><h4>A pattern, not a verdict</h4>
        <p>Each lobe stands for an essay. The fine lines are expressive, not measured evidence.</p></div>
        </div>
      </details>
    </figure>
    <div class="exploration-reading">
      <section class="selected-path" aria-labelledby="selected-path-title">
        <div class="selection-top"><p class="label" id="selected-path-title">Selected essay</p>
          <span class="label" data-home-position>{selected + 1} / {len(items)}</span></div>
        <h3><a data-home-selection-link data-home-selection-title href="{_text(essay["url"])}">{_text(essay["title"])}</a></h3>
        <span class="featured-length" data-home-length>{essay["words"]:,} words; {essay["minutes"]} minute read.</span>
        <div class="selection-actions"><div class="selection-links">
          <a class="primary-link" data-home-selection-link href="{_text(essay["url"])}">Read selected essay ↗</a>
          <a class="secondary-link" href="#home-essay-title">See cover above ↑</a></div>
          <span class="browse-controls" data-home-browse hidden>
            <button type="button" data-home-previous aria-label="Previous essay in this theme">←</button>
            <button type="button" data-home-next aria-label="Next essay in this theme">→</button>
          </span></div>
      </section>
      <section class="index-strip" aria-labelledby="home-index-title">
        <div><h3 id="home-index-title">Other ways into this question</h3>
          <p data-home-index-description>{len(items)} essays in {_text(theme["name"])}.</p></div>
        <ol class="essay-index" data-home-index aria-label="Essays in the selected theme">{_index(items, selected)}</ol>
        <a class="secondary-link" data-home-archive href="{theme["archive"]}">Browse this theme ↗</a>
      </section>
    </div>
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
