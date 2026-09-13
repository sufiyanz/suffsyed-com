"""Deterministic text measurements and explicitly lexical passage connections."""
import hashlib
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import quote, urlencode, urlsplit

from bs4 import BeautifulSoup, NavigableString

TOKEN = re.compile(r"[A-Za-z0-9]+(?:[’'\-][A-Za-z0-9]+)*")
BLOCKS = {"p", "li", "blockquote", "h1", "h2", "h3", "h4", "figcaption", "pre", "table"}
TEXT_BOUNDARIES = BLOCKS | {"td", "th", "tr", "thead", "tbody", "caption"}
PROSE = {"p", "li", "blockquote"}
STOP = set("""
a about above across after again against all almost along already also always am an and
another any anyone anything are aren't around as at away back be because become becomes
been before being below between both but by can can't cannot could couldn't did didn't
do does doesn't doing don't done down during each either else enough even ever every
everyone everything few first for from get gets getting give go going gone got had has
hasn't have haven't having he her here hers herself him himself his how however i i'd
i'll i'm i've if in inside instead into is isn't it it's its itself just keep kind know
last later less let like likely little long look lot made make makes making many may
me means might more most much must my myself need needs never new next no nor not now
of off often on once one only or other others our ours ourselves out over own part
people per perhaps put rather really right same say says see seem set several she
should shouldn't since so some someone something sometimes still such take than that
that's the their theirs them themselves then there there's these they they'd they'll
they're they've thing things think this those though through time to together too
under until up us used using very want was wasn't way we we'd we'll we're we've well
were weren't what what's when where whether which while who why will with within
without won't work would wouldn't yes yet you you'd you'll you're you've your yours
yourself ai
""".split())


def tokens(text):
    return [match.group().lower().replace("’", "'") for match in TOKEN.finditer(text)]


def flat_text(element):
    """Preserve inline joins; give line breaks and block boundaries a space."""
    def visit(node):
        if isinstance(node, NavigableString):
            return str(node)
        if node.name == "br":
            return "\n"
        text = "".join(visit(child) for child in node.children)
        return f"\n{text}\n" if node.name in TEXT_BOUNDARIES else text
    return " ".join(visit(element).split())


def candidates(soup):
    return [el for el in soup.find_all(BLOCKS)
            if not el.find_parent("table") and (el.name == "table" or not el.find(BLOCKS)) and flat_text(el)]


def validate_source(soup, source):
    allowed = BLOCKS | {"ul", "ol", "strong", "em", "b", "i", "a", "br", "code", "figure", "img", "hr", "span", "div", "sup", "sub", "table", "thead", "tbody", "tr", "td", "th", "caption"}
    ids = set()
    for el in soup.find_all(True):
        if el.name not in allowed:
            raise ValueError(f"{source}: disallowed element {el.name}")
        for key in el.attrs:
            if key.startswith("on") or key in {"style", "srcdoc"}:
                raise ValueError(f"{source}: disallowed attribute {key}")
        if "id" in el.attrs:
            if el["id"] in ids:
                raise ValueError(f"{source}: duplicate ID {el['id']}")
            ids.add(el["id"])
        for key in ["href", "src"]:
            url = el.get(key)
            if url and (urlsplit(url).scheme not in {"", "http", "https", "mailto", "tel"} or url.startswith("//")):
                raise ValueError(f"{source}: unsafe {key} URL")
            if url and urlsplit(url).netloc in {"suffsyed.com", "www.suffsyed.com"}:
                parsed = urlsplit(url)
                el[key] = (parsed.path or "/") + (f"?{parsed.query}" if parsed.query else "") + (f"#{parsed.fragment}" if parsed.fragment else "")


def measure(row, root):
    source = root / "content" / "essays" / f"{row['slug']}.html"
    soup = BeautifulSoup(source.read_text(), "html.parser")
    validate_source(soup, source)
    sections, passages = [], []
    section = {"id": "introduction", "title": "Opening", "level": 2, "words": 0, "passages": []}
    sections.append(section)
    for el in candidates(soup):
        text = flat_text(el)
        identifier = el.get("id")
        if not identifier:
            raise ValueError(f"{source}: every passage needs a persistent id; missing on {text[:60]!r}")
        heading = el.name in {"h1", "h2", "h3", "h4"}
        if heading:
            section = {"id": identifier, "title": text, "level": int(el.name[1]), "words": 0, "passages": []}
            sections.append(section)
        terms = Counter(tokens(text))
        passage = {
            "id": identifier, "text": text, "kind": el.name,
            "no": len(passages) + 1,
            "label": el.get("aria-label", ""),
            "section": section["id"], "words": sum(terms.values()),
            "terms": dict(sorted(terms.items())), "related": [],
        }
        section["words"] += passage["words"]
        section["passages"].append(identifier)
        passages.append(passage)
        if el.name == "table":
            wrapper = soup.new_tag("div", attrs={"id": identifier, "data-passage": identifier, "tabindex": "-1", "class": "table-passage"})
            inner = soup.new_tag("div", attrs={"class": "passage-text", "tabindex": "0", "role": "region", "aria-label": el.get("aria-label", "Scrollable table")})
            del el["id"]
            el.wrap(inner)
            inner.wrap(wrapper)
        else:
            el["data-passage"] = identifier
            el["tabindex"] = "-1"
            inner = soup.new_tag("span")
            inner["class"] = "passage-text"
            for child in list(el.contents):
                inner.append(child.extract())
            el.append(inner)
    sections = [section for section in sections if section["passages"]]
    counts = Counter()
    for passage in passages:
        counts.update(passage["terms"])
    words = sum(counts.values())
    return {
        **row, "url": f"/futurememo/{row['slug']}/",
        "words": words, "minutes": max(1, math.ceil(words / 230)),
        "body": str(soup), "sections": sections, "passages": passages,
        "terms": [{"term": term, "count": count} for term, count in counts.most_common() if term not in STOP and len(term) >= 4][:24],
    }


def connect(rows):
    """Top shared-vocabulary passages, with corpus-rarity weighting; not semantics."""
    all_passages = []
    postings = defaultdict(set)
    for essay in rows:
        for passage in essay["passages"]:
            if passage["words"] < 20 or passage["kind"] not in PROSE:
                continue
            terms = {term for term in passage["terms"] if term not in STOP and len(term) >= 4 and not term.isdigit()}
            idx = len(all_passages)
            all_passages.append((essay, passage, terms))
            for term in terms:
                postings[term].add(idx)
    total = len(all_passages)
    rarity = {term: math.log(1 + total / len(indices)) for term, indices in postings.items()}
    for i, (essay, passage, terms) in enumerate(all_passages):
        eligible = set().union(*(postings[term] for term in terms)) if terms else set()
        matches = []
        for j in eligible:
            other, target, other_terms = all_passages[j]
            if other["slug"] == essay["slug"]:
                continue
            shared = terms & other_terms
            if len(shared) < 2:
                continue
            score = sum(rarity[term] ** 2 for term in sorted(shared)) / math.sqrt(max(1, len(terms) * len(other_terms)))
            matches.append((score, other["slug"], target["id"], shared, other, target))
        matches.sort(key=lambda match: (-match[0], match[1], match[2]))
        used = set()
        for _, slug, identifier, shared, other, target in matches:
            if slug in used:
                continue
            used.add(slug)
            passage["related"].append({
                "slug": slug, "id": identifier, "title": other["title"],
                "url": f"{other['url']}#{identifier}",
                "shared": sorted(shared, key=lambda term: (-rarity[term], term))[:6],
                "excerpt": target["text"],
            })
            if len(used) == 3:
                break


def reading_plate(essay):
    """One whole prose passage and exact recurrence, never a generated summary."""
    recurring = [item for item in essay["terms"] if item["count"] >= 2 and not item["term"].isdigit()]
    candidates = []
    for passage in essay["passages"]:
        found = [item for item in recurring if passage["terms"].get(item["term"])]
        if passage["kind"] in PROSE and passage["words"] >= 20 and found:
            candidates.append((passage, found))
    preferred = [(p, terms) for p, terms in candidates
                 if p["kind"] == "p" and 35 <= p["words"] <= 100 and len(terms) >= 3]
    if not candidates:
        raise ValueError(f'{essay["slug"]}: no complete prose passage with recurring vocabulary')
    passage, recurring = min(preferred or candidates,
                             key=lambda item: (-min(len(item[1]), 4), abs(item[0]["words"] - 65), item[0]["no"]))
    sections = {section["id"]: section for section in essay["sections"]}
    words = []
    for item in recurring[:4]:
        term = item["term"]
        traces = []
        for section in essay["sections"]:
            matches = [p for p in essay["passages"] if p["section"] == section["id"] and p["terms"].get(term)]
            if matches:
                traces.append({
                    "id": section["id"], "title": section["title"],
                    "count": sum(p["terms"][term] for p in matches),
                    "url": f'{essay["url"]}?{urlencode({"term": term, "section": section["id"]})}#{quote(matches[0]["id"])}',
                })
        words.append({
            **item, "here": passage["terms"][term],
            "url": f'{essay["url"]}?{urlencode({"term": term})}#{quote(passage["id"])}',
            "sections": sorted(traces, key=lambda trace: -trace["count"]),
        })
    return {
        "passage": {key: passage[key] for key in ["id", "no", "kind", "text", "words", "section"]},
        "sectionTitle": sections[passage["section"]]["title"],
        "url": f'{essay["url"]}#{quote(passage["id"])}',
        "terms": words,
        "related": passage["related"][:1],
    }


def content_digest(fragment):
    normalized = " ".join(BeautifulSoup(fragment, "html.parser").get_text(" ", strip=True).split())
    return hashlib.sha256(normalized.encode()).hexdigest()
