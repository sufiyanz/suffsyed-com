"""Offline build invariants. Run after tools/build_site.py."""
import hashlib
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup

from corpus import content_digest, flat_text, tokens

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs"
DATA = json.loads((ROOT / "content/corpus.json").read_text())


def load(path):
    return BeautifulSoup(path.read_text(), "html.parser")


class JournalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pages = {p: load(p) for p in sorted(OUT.rglob("*.html"))}

    def test_full_bodies_and_stable_anchors(self):
        self.assertEqual(len(DATA["essays"]), 20)
        for row in DATA["essays"]:
            with self.subTest(essay=row["slug"]):
                soup = self.pages[OUT / "futurememo" / row["slug"] / "index.html"]
                body = BeautifulSoup(str(soup.select_one("#essay-body")), "html.parser")
                for el in body.select(".passage-tools"):
                    el.decompose()
                self.assertEqual(content_digest(str(body)), row["originalTextSha256"])
                source = load(ROOT / "content/essays" / f'{row["slug"]}.html')
                self.assertEqual(content_digest(str(source)), row["originalTextSha256"])
                original_ids = {el["id"] for el in source.select("[id]")}
                self.assertTrue(original_ids <= {el["id"] for el in body.select("[id]")})
                all_tokens = tokens(flat_text(source))
                passage_tokens = [token for passage in body.select(".passage-text") for token in tokens(flat_text(passage))]
                self.assertEqual(all_tokens, passage_tokens, "Every written word must belong to exactly one measured passage")
                self.assertEqual(soup.select_one(".essay-artwork > a")["href"], row["cover"])
                self.assertEqual(soup.select_one('link[rel="canonical"]')["href"], f'https://suffsyed.com/futurememo/{row["slug"]}/')

    def test_every_measured_passage_and_connection(self):
        essays = {}
        for row in DATA["essays"]:
            soup = self.pages[OUT / "futurememo" / row["slug"] / "index.html"]
            model = json.loads(soup.select_one("#essay-data").string)
            essays[row["slug"]] = model
            self.assertEqual(sum(section["words"] for section in model["sections"]), model["words"])
            self.assertEqual(sum(passage["words"] for passage in model["passages"]), model["words"])
            for p in model["passages"]:
                text = flat_text(soup.find(id=p["id"]).select_one(".passage-text"))
                self.assertEqual(text, p["text"])
                observed = tokens(text)
                self.assertEqual(len(observed), p["words"])
                self.assertEqual(dict(__import__("collections").Counter(observed)), p["terms"])
            for term in model["terms"]:
                self.assertEqual(term["count"], sum(p["terms"].get(term["term"], 0) for p in model["passages"]))
        for slug, essay in essays.items():
            for passage in essay["passages"]:
                for related in passage["related"]:
                    self.assertNotEqual(related["slug"], slug)
                    dest = next(p for p in essays[related["slug"]]["passages"] if p["id"] == related["id"])
                    self.assertIn(dest["kind"], {"p", "li", "blockquote"})
                    self.assertIn(passage["kind"], {"p", "li", "blockquote"})
                    self.assertEqual(dest["text"], related["excerpt"])
                    self.assertTrue(set(related["shared"]) <= passage["terms"].keys() & dest["terms"].keys())
                    self.assertGreaterEqual(len(related["shared"]), 2)

    def test_all_internal_links_images_and_unique_ids(self):
        errors = []
        for path, soup in self.pages.items():
            if len(soup.select("main")) != 1:
                errors.append(f"{path.relative_to(OUT)}: expected one main landmark")
            ids = [node["id"] for node in soup.select("[id]")]
            if len(ids) != len(set(ids)):
                errors.append(f"{path.relative_to(OUT)}: duplicate IDs")
            for node in soup.select("[href], [src]"):
                for attr in ["href", "src"]:
                    if not node.get(attr):
                        continue
                    parsed = urlsplit(node[attr])
                    if parsed.scheme in {"data", "mailto", "tel"} or parsed.netloc not in {"", "suffsyed.com", "www.suffsyed.com"}:
                        continue
                    if not parsed.path:
                        target = path
                    elif parsed.path.startswith("/"):
                        target = OUT / unquote(parsed.path).lstrip("/")
                    else:
                        target = path.parent / unquote(parsed.path)
                    if target.is_dir():
                        target = target / "index.html"
                    if not target.exists():
                        errors.append(f"{path.relative_to(OUT)}: missing {node[attr]}")
                    elif parsed.fragment and target.suffix == ".html":
                        dest = self.pages.get(target) or load(target)
                        if not dest.find(id=unquote(parsed.fragment)):
                            errors.append(f"{path.relative_to(OUT)}: missing anchor {node[attr]}")
        self.assertEqual(errors, [])

    def test_gallery_complete_uncropped(self):
        soup = self.pages[OUT / "lightworks/index.html"]
        imgs = soup.select(".photograph img")
        self.assertEqual(len(imgs), 22)
        self.assertEqual([img["src"] for img in imgs], [photo["src"] for photo in DATA["gallery"]])
        self.assertTrue(all(img.get("alt") and img.get("width") and img.get("height") for img in imgs))

    def test_search_covers_complete_corpus(self):
        index = json.loads((OUT / "assets/search-index.json").read_text())
        self.assertEqual(len(index), 20)
        for essay in index:
            soup = self.pages[OUT / "futurememo" / essay["slug"] / "index.html"]
            model = json.loads(soup.select_one("#essay-data").string)
            self.assertEqual(essay["passages"], [{"id": p["id"], "text": p["text"], "kind": p["kind"], "label": p["label"]} for p in model["passages"]])

    def test_original_tables_restored(self):
        tables = [table for path, soup in self.pages.items() if "/futurememo/" in str(path) for table in soup.select("#essay-body table")]
        self.assertEqual(len(tables), 4)
        self.assertEqual(sorted(len(table.select("tr")) for table in tables), [4, 4, 4, 5])
        self.assertTrue(all(table.select("thead th[scope=col]") for table in tables))

    def test_dates_feeds_and_legacy_routes(self):
        self.assertEqual(sum(row["legacyWords"] for row in DATA["essays"]), 45308)
        for name in ["rss.xml", "futurememo/rss.xml"]:
            xml = ET.parse(OUT / name)
            self.assertEqual(len(xml.findall(".//item")), 20)
            self.assertEqual(len(xml.findall(".//pubDate")), 0)
        xml = ET.parse(OUT / "sitemap.xml")
        self.assertEqual(len(xml.findall("{*}url")), 30)
        for route in ["home", "member-site-homepage-1", "futurememo/tag", "futurememo/tag/June+2024+Edition", "store/p/buy-me-a-coffee", "store/p/chemex", "store/p/iced-coffee", "store/p/pour-over"]:
            self.assertTrue((OUT / route / "index.html").exists())
        self.assertTrue((OUT / ".nojekyll").exists())
        self.assertEqual((OUT / "CNAME").read_bytes(), subprocess.check_output(["git", "show", "HEAD:docs/CNAME"], cwd=ROOT))

    def test_no_remote_scripts_or_inline_handlers(self):
        for path, soup in self.pages.items():
            with self.subTest(page=str(path)):
                self.assertFalse(soup.select("script[src^='http']"))
                self.assertFalse(soup.select("script:not([src]):not([type='application/json'])"))
                for el in soup.find_all(True):
                    self.assertFalse(any(key.startswith("on") for key in el.attrs))

    def test_tokenizer_edges(self):
        self.assertEqual(tokens("AI said: team's, team’s, teams; AI-native. -- ' ”"), ["ai", "said", "team's", "team's", "teams", "ai-native"])
        self.assertEqual(tokens("<img> [a-z]* & systems"), ["img", "a-z", "systems"])


if __name__ == "__main__":
    unittest.main()
