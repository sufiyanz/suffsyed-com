"""A curated, source-addressed index; never a semantic inference or research feed."""
from collections import Counter
from html import escape
import re


def build_atlas(rows, themes, config):
    if config.get("version") != 1 or config.get("kind") != "editorial-reading-index":
        raise ValueError("Question atlas: unsupported editorial index schema")
    essays = {row["slug"]: row for row in rows}
    entries = config.get("entries")
    if not isinstance(entries, dict) or set(entries) != set(essays):
        raise ValueError("Question atlas: exactly one passage reference per essay is required")
    if len(themes) != 5:
        raise ValueError("Question atlas: review the five-question layout before adding themes")
    by_name = {theme["name"]: theme for theme in themes}
    by_id = {theme["id"]: theme for theme in themes}
    if len(by_name) != len(themes) or len(by_id) != len(themes):
        raise ValueError("Question atlas: duplicate theme")
    for theme in themes:
        if not re.fullmatch(r"[a-z][a-z0-9-]*", theme["id"]) or not theme["question"].strip():
            raise ValueError("Question atlas: invalid question identity")

    def source(slug, identifier):
        if slug not in essays:
            raise ValueError(f"Question atlas: unknown essay {slug!r}")
        essay = essays[slug]
        passage = next((p for p in essay["passages"] if p["id"] == identifier), None)
        if passage is None or passage["kind"] not in {"p", "li", "blockquote"}:
            raise ValueError(f"Question atlas: missing prose passage {slug}#{identifier}")
        if not 15 <= passage["words"] <= 120:
            raise ValueError(f"Question atlas: review passage length for {slug}#{identifier}")
        return {
            "slug": slug, "title": essay["title"], "no": essay["no"],
            "url": essay["url"], "id": identifier, "text": passage["text"],
            "href": f'{essay["url"]}#{identifier}', "words": passage["words"],
            "passageNo": passage["no"],
            "sectionTitle": next(s["title"] for s in essay["sections"] if s["id"] == passage["section"]),
        }

    questions = []
    for number, theme in enumerate(themes, 1):
        members = [source(row["slug"], entries[row["slug"]]) for row in rows if row["theme"] == theme["name"]]
        if not members:
            raise ValueError(f'Question atlas: {theme["id"]} must contain an essay')
        questions.append({"id": theme["id"], "name": theme["name"], "question": theme["question"],
                          "anchor": f"theme-{number}", "entries": members})
    if any(row["theme"] not in by_name for row in rows):
        raise ValueError("Question atlas: essay outside the existing editorial themes")
    bridges = config.get("bridges")
    if not isinstance(bridges, list) or len(bridges) != 4:
        raise ValueError("Question atlas: exactly four reviewed thematic bridges are required")
    identities, pairs, degrees, resolved = set(), set(), Counter(), []
    for bridge in bridges:
        identifier = bridge.get("id", "")
        left, right = bridge.get("from"), bridge.get("to")
        if (not re.fullmatch(r"[a-z][a-z0-9-]*", identifier) or identifier in identities
                or left not in by_id or right not in by_id or left == right):
            raise ValueError("Question atlas: invalid or duplicate bridge identity/endpoints")
        pair = tuple(sorted((left, right)))
        if pair in pairs:
            raise ValueError("Question atlas: duplicate bridge pair")
        if any(not isinstance(bridge.get(key), str) or not bridge[key].strip() for key in ("label", "reason")):
            raise ValueError("Question atlas: every bridge needs an editorial label and explanation")
        refs = bridge.get("sources")
        if not isinstance(refs, list) or len(refs) != 2:
            raise ValueError("Question atlas: a bridge requires two source passages")
        sources = []
        for endpoint, ref in zip((left, right), refs):
            if not isinstance(ref, dict):
                raise ValueError("Question atlas: invalid bridge source")
            item = source(ref.get("slug"), ref.get("passage"))
            if essays[item["slug"]]["theme"] != by_id[endpoint]["name"]:
                raise ValueError("Question atlas: source does not belong to its bridge endpoint")
            if entries[item["slug"]] != item["id"]:
                raise ValueError("Question atlas: bridge source must be inspectable in the passage index")
            sources.append(item)
        identities.add(identifier)
        pairs.add(pair)
        degrees.update((left, right))
        resolved.append({**bridge, "sources": sources})
    if set(degrees) != set(by_id) or max(degrees.values()) > 2:
        raise ValueError("Question atlas: every question needs a bridge, with at most two neighbors")
    reached, pending = set(), [themes[0]["id"]]
    while pending:
        current = pending.pop()
        if current in reached:
            continue
        reached.add(current)
        pending.extend(b["to"] if b["from"] == current else b["from"]
                       for b in resolved if current in (b["from"], b["to"]))
    if reached != set(by_id):
        raise ValueError("Question atlas: the four bridges must connect all five questions")
    return {"questions": questions, "bridges": resolved}


def render_atlas(atlas):
    def text(value):
        return escape(str(value), quote=True)

    groups = []
    for question in atlas["questions"]:
        entries = []
        for item in question["entries"]:
            entries.append(f"""
            <li class="atlas-entry" data-atlas-entry="{text(item['slug'])}">
              <a class="atlas-essay-title" href="{text(item['url'])}">{text(item['title'])}</a>
              <details class="atlas-source" id="atlas-source-{text(item['slug'])}">
                <summary>Read the source passage <span aria-hidden="true">↗</span></summary>
                <p class="atlas-source-note">Passage {item['passageNo']} / {text(item['sectionTitle'])} · {item['words']} words, unabridged.</p>
                <blockquote cite="{text(item['href'])}">{text(item['text'])}</blockquote>
                <a class="atlas-context" href="{text(item['href'])}">Read in the original essay ↗</a>
              </details>
            </li>""")
        groups.append(f"""
        <section class="atlas-question-group" id="{question['anchor']}" data-atlas-question="{text(question['id'])}">
          <header><p class="label"><span data-atlas-theme>{text(question['name'])}</span> / {len(entries)} essays</p>
            <h3>{text(question['question'])}</h3><p class="micro">Editorial index question</p></header>
          <ol>{"".join(entries)}</ol>
        </section>""")
    bridges = []
    for bridge in atlas["bridges"]:
        links = "".join(
            f'<li><a href="{text(item["href"])}" data-source-slug="{text(item["slug"])}">{text(item["title"])}'
            f' <span>↗ Passage {item["passageNo"]}</span></a></li>'
            for item in bridge["sources"])
        bridges.append(f"""
        <li class="atlas-bridge" id="atlas-bridge-{text(bridge['id'])}" data-atlas-bridge="{text(bridge['id'])}"
            data-from="{text(bridge['from'])}" data-to="{text(bridge['to'])}">
          <h4>{text(bridge['label'])}</h4><p class="atlas-reason">{text(bridge['reason'])}</p>
          <ol aria-label="The two source passages">{links}</ol>
        </li>""")
    jumps = "".join(f'<a href="#{q["anchor"]}">{text(q["name"])}</a>' for q in atlas["questions"])
    return f"""
    <section class="question-atlas" id="by-preoccupation" data-question-atlas aria-labelledby="atlas-title">
      <header class="section-heading">
        <span class="label">Editorial preoccupations</span>
        <h2 id="atlas-title">An atlas of questions.</h2>
      </header>
      <p class="atlas-introduction">Editorial questions and curated routes, not measured similarity.
        <a href="/methods/#question-atlas">Method ↗</a></p>
      <details class="atlas-map-disclosure" data-atlas-map>
        <summary><span>Explore the map</span><span class="atlas-map-invitation">Follow the questions <span aria-hidden="true">↗</span></span></summary>
        <p class="atlas-map-notice" data-atlas-notice role="status">The interactive map needs JavaScript. All questions, passages and connections are readable in the index below.</p>
        <button class="plain" type="button" data-atlas-retry hidden>Retry the map</button>
        <div data-atlas-mount></div>
      </details>
      <nav class="atlas-jumps" aria-label="Question index">{jumps}</nav>
      <div class="atlas-index">{"".join(groups)}</div>
      <details class="atlas-bridges">
        <summary>Curated bridges / Why these questions meet</summary>
        <p class="atlas-bridge-note">Editorial pairings. Each explanation names two original passages. The map’s dashed lines represent these same routes; their position and length are not measurements.</p>
        <ol>{"".join(bridges)}</ol>
      </details>
    </section>"""
