"""Offline build invariants. Run after tools/build_site.py."""
import hashlib
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup

from corpus import content_digest, flat_text, reading_plate, tokens
from build_site import journal_home_page
from foundation_art import orbit, ribbon
from foundation_home import DESCRIPTION, IDENTITY, render_foundation
from series import load_series
from article_art import PROMOTED_IMAGE, PROMOTED_SLUG
from test_series import SERIES_SLUGS

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs"
DATA = json.loads((ROOT / "content/corpus.json").read_text())


def load(path):
    return BeautifulSoup(path.read_text(), "html.parser")


class JournalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pages = {p: load(p) for p in sorted(OUT.rglob("*.html"))}
        rows = [json.loads(cls.pages[OUT / "futurememo" / row["slug"] / "index.html"].select_one("#essay-data").string)
                for row in DATA["essays"]]
        public_rows = [{**{key: value for key, value in row.items() if key != "passages"},
                        "readingPlate": reading_plate(row)} for row in rows]
        cls.journal_home = BeautifulSoup(journal_home_page(public_rows, DATA), "html.parser")

    def test_foundation_identity_and_writing_gallery(self):
        home = self.pages[OUT / "index.html"]
        self.assertEqual(home.h1.get_text(strip=True), DESCRIPTION)
        self.assertEqual(len(home.select("h1")), 1)
        self.assertEqual(home.select_one(".cover-role").get_text(), IDENTITY)
        self.assertEqual(home.select_one(".cover-description").get_text(), DESCRIPTION)
        self.assertEqual([a["href"] for a in home.select(".site-header nav a")],
                         ["/futurememo/", "/about-me/"])
        self.assertEqual([link["href"] for link in home.select('link[rel="stylesheet"]')],
                         ["/assets/foundation.css", "/assets/frame.css", "/assets/gallery-home.css"])
        self.assertFalse(home.select("canvas, dialog, iframe, form"))
        self.assertEqual([script["src"] for script in home.select("script")], ["/assets/motion.js"])
        self.assertFalse(home.select("button, [data-motion-toggle]"))
        self.assertFalse(home.select("h1 a, h1 button"))
        self.assertEqual(len(home.select("main > section")), 3)
        self.assertEqual(len(home.select("svg.line-study")), 1)
        self.assertFalse(home.select(".hero-geometry, .hero-field, .editorial-plane, .site-name"))
        self.assertEqual(len(home.select(".gallery-masthead .cover-signature")), 1)
        self.assertFalse(home.select(".gallery-cover .cover-signature"))
        lead = DATA["essays"][0]
        feature = home.select_one(".featured-essay")
        self.assertEqual(feature["data-featured-slug"], lead["slug"])
        self.assertEqual(feature.h2.get_text(), lead["title"])
        self.assertEqual(feature.img["src"], lead["cover"])
        self.assertEqual(feature.select_one(".exhibition-label").get_text(), "Featured essay")
        self.assertEqual(feature.a["href"], f'/futurememo/{lead["slug"]}/')
        self.assertEqual(feature.img["alt"], json.loads((ROOT / "content/cover-descriptions.json").read_text())[lead["slug"]])
        for svg in home.select("svg.line-study"):
            self.assertEqual(svg["aria-hidden"], "true")
            self.assertEqual(svg["focusable"], "false")
        self.assertLess(len(str(home).encode()), 100 * 1024)
        self.assertEqual((ROOT / "site/foundation.css").read_bytes(),
                         (OUT / "assets/foundation.css").read_bytes())
        rows = {row["slug"]: row for row in DATA["essays"]}
        selections = home.select(".writing-list li")
        self.assertEqual(len(selections), 4)
        self.assertEqual(home.select_one("#writing h2").get_text(), "The Future of Design")
        self.assertNotIn(lead["slug"], SERIES_SLUGS)
        for index, (item, slug) in enumerate(zip(selections, SERIES_SLUGS), 1):
            self.assertEqual(item["data-series-part"], str(index))
            self.assertEqual(item["data-series-slug"], slug)
            self.assertEqual(item.h3.a["href"], f"/futurememo/{slug}/")
            self.assertEqual(item.h3.get_text(), rows[slug]["title"])
            self.assertTrue(rows[slug]["description"].startswith(item.p.get_text()))
            self.assertEqual(item.select_one(".exhibition-art")["href"], item.h3.a["href"])
            self.assertEqual(item.img["src"], rows[slug]["cover"])
            for source in item.img["srcset"].split(", "):
                self.assertTrue((OUT / source.split()[0].lstrip("/")).is_file())
        self.assertFalse(home.select(".photo-pair, #photography"))
        self.assertFalse(home.select('main a[href^="/lightworks/"]'))
        self.assertEqual(len(home.select("[data-motion-scene]")), 1)
        archive = self.pages[OUT / "futurememo/index.html"]
        for entry, row in zip(archive.select(".archive-entry"), DATA["essays"]):
            self.assertEqual(entry.select_one(".archive-art")["href"], f'/futurememo/{row["slug"]}/')
            self.assertEqual(entry.img["src"], row["cover"])
            self.assertEqual(entry.h2.get_text(), row["title"])

    def test_motion_routes_and_anchors_are_explicit(self):
        home = self.pages[OUT / "index.html"]
        self.assertFalse(home.select("[data-motion-follower]"))
        fixture = BeautifulSoup(ribbon("fixture-ribbon"), "html.parser")
        followers = fixture.select("[data-motion-follower]")
        self.assertEqual(len(followers), 3)
        self.assertEqual(len(fixture.select("[data-motion-route]")), 9)
        for follower in followers:
            route = fixture.find(id=follower["data-motion-follower"])
            self.assertEqual(route["data-motion-route"], "closed")
            self.assertTrue(route["d"].endswith(" Z"))
            self.assertIs(route.parent, follower.parent)
            self.assertEqual(follower.mpath["href"], "#" + route["id"])
            self.assertEqual(follower.find("animatemotion")["begin"], "indefinite")
            start = re.match(r"M([-\d.]+),([-\d.]+)", route["d"]).groups()
            self.assertEqual(follower["data-motion-start"].split(), list(start))
            self.assertEqual(follower["transform"], f'translate({" ".join(start)})')
        for page in self.pages.values():
            for marker in page.select("[data-motion-anchor]"):
                axes = page.find(id=marker["data-motion-anchor"])
                self.assertIs(axes.parent, marker.parent)
                self.assertEqual(marker["data-anchor-point"].split(), [marker["cx"], marker["cy"]])
        repeated = BeautifulSoup(ribbon("first") + ribbon("second") + orbit("third") + orbit("fourth"), "html.parser")
        ids = [node["id"] for node in repeated.select("[id]")]
        self.assertEqual(len(ids), len(set(ids)))

    def test_gallery_feature_follows_archive_order_without_dates(self):
        rows = []
        for source in DATA["essays"]:
            page = self.pages[OUT / "futurememo" / source["slug"] / "index.html"]
            rows.append({**source, "url": f'/futurememo/{source["slug"]}/',
                         "coverAlt": page.select_one(".essay-artwork img")["alt"]})
        series = load_series(rows, ROOT)
        for slug in (rows[0]["slug"], SERIES_SLUGS[0], SERIES_SLUGS[1]):
            ordered = sorted(rows, key=lambda row: row["slug"] != slug)
            page = BeautifulSoup(render_foundation(ordered, lambda src, alt, **kw: "<img>", series), "html.parser")
            self.assertEqual(page.select_one(".featured-essay")["data-featured-slug"], slug)
            following = [a["href"] for a in page.select(".writing-list .exhibition-art")]
            self.assertEqual(following, [f"/futurememo/{part}/" for part in SERIES_SLUGS])
        self.assertTrue(all(row["publicationDate"] is None for row in rows))
        with self.assertRaisesRegex(ValueError, "archive lead"):
            render_foundation([], lambda *args, **kwargs: "", series)

    def test_preserved_journal_cover_and_internal_header(self):
        home = self.journal_home
        cover = home.select_one(".home-cover")
        self.assertEqual(cover.h1.get_text(), "Suff Syed")
        self.assertEqual(cover.h1["id"], "cover-title")
        self.assertEqual(cover.h1.span["class"], ["sr-only"])
        self.assertEqual(len(cover.select(".cover-signature")), 1)
        self.assertIs(cover.select_one(".cover-signature").parent, cover.h1)
        self.assertIsNone(cover.select_one(".cover-kicker"))
        controls = cover.select("button.signature-motion")
        self.assertEqual(len(controls), 1)
        self.assertTrue(controls[0].has_attr("hidden"))
        self.assertEqual(controls[0]["aria-label"], "Pause signature animation")
        self.assertIsNone(controls[0].find_parent("h1"))
        self.assertEqual(cover.select_one(".cover-role").get_text(),
                         "Suff Syed is a Member of Technical Staff building across AI frontiers at Microsoft.")
        self.assertEqual(cover.select_one(".cover-description").get_text(),
                         "Essays on intelligence, creative work, and what remains human.")
        self.assertEqual([a["href"] for a in cover.select(".cover-path a")],
                         ["#featured-story", "#connections", "#lightworks", "#unfinished"])
        self.assertEqual(cover.find_next_sibling().get("class"), ["mast"])
        self.assertEqual(home.select_one(".mast").find_next_sibling().get("id"), "main")
        self.assertEqual(len(home.select("h1")), 1)
        self.assertEqual([a.get_text() for a in home.select(".mast nav a")],
                         ["Future (Memo)", "About (Me)"])
        for path, soup in self.pages.items():
            self.assertEqual(len(soup.select(".site-header")), 1)
            self.assertEqual([a["href"] for a in soup.select(".site-header nav a")],
                             ["/futurememo/", "/about-me/"])
            self.assertEqual([a.get_text() for a in soup.select(".site-header nav a")],
                             ["Future (Memo)", "About (Me)"])
            self.assertEqual(len(soup.select(".site-header .site-signature")), 1)
            self.assertFalse(soup.select(".site-header .site-name"))
            self.assertEqual(len(soup.select(".site-footer")), 1)
            self.assertEqual([a.get_text() for a in soup.select(".site-footer > nav a")[:2]],
                             ["Future (Memo)", "About (Me)"])
            self.assertFalse(soup.select('.site-header a[href="/lightworks/"], .site-footer a[href="/lightworks/"]'))
            self.assertFalse(soup.select("[data-motion-toggle], .motion-toggle"))
            if path != OUT / "index.html":
                self.assertIsNone(soup.select_one(".home-cover"))

    def test_foundation_text_contrast(self):
        css = (ROOT / "site/frame.css").read_text()
        palette = dict(re.findall(r"--(site-[a-z-]+):\s*(#[0-9a-f]{6});", css))

        def luminance(value):
            components = [int(value[i:i + 2], 16) / 255 for i in (1, 3, 5)]
            linear = [c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4 for c in components]
            return sum(c * weight for c, weight in zip(linear, (.2126, .7152, .0722)))

        for foreground, background in (("site-ink", "site-ground"),
                                       ("site-muted", "site-ground"),
                                       ("site-muted", "site-paper"),
                                       ("site-ink", "site-selection"),
                                       ("site-dark-text", "site-dark"),
                                       ("site-dark-muted", "site-dark")):
            levels = sorted((luminance(palette[foreground]), luminance(palette[background])))
            self.assertGreaterEqual((levels[1] + .05) / (levels[0] + .05), 4.5,
                                    (foreground, background))

    def test_foundation_font_provenance(self):
        source = ROOT / "site/foundation"
        output = OUT / "assets/foundation"
        record = json.loads((source / "font-provenance.json").read_text())
        self.assertEqual(record["family"], "Instrument Sans")
        self.assertEqual(record["license"], "SIL Open Font License 1.1")
        self.assertIn(record["revision"], record["source"])
        self.assertEqual(record["weight"], "400")
        font = (source / record["file"]).read_bytes()
        self.assertEqual(font[:4], b"wOF2")
        self.assertEqual(hashlib.sha256(font).hexdigest(), record["sha256"])
        license_text = (source / "OFL-InstrumentSans.txt").read_bytes()
        self.assertIn(b"SIL OPEN FONT LICENSE Version 1.1", license_text)
        self.assertEqual(hashlib.sha256(license_text).hexdigest(), record["licenseSha256"])
        for path in source.iterdir():
            self.assertEqual(path.read_bytes(), (output / path.name).read_bytes())

    def test_signature_is_the_validated_vector(self):
        vector = (ROOT / "site/suff-syed-signature.svg").read_bytes()
        self.assertEqual(hashlib.sha256(vector).hexdigest(),
                         "60e67da798d9be5bc743cc65adf46c6c236266f2f7cdc085f2914aae70695084")
        self.assertEqual(vector, (OUT / "assets/suff-syed-signature.svg").read_bytes())
        svg = ET.fromstring(vector)
        self.assertEqual(svg.attrib["viewBox"], "0 0 350 148")
        self.assertEqual(svg.attrib["color"], "#1B2915")
        paths = svg.findall("{http://www.w3.org/2000/svg}path")
        self.assertEqual(len(paths), 1)
        self.assertEqual(paths[0].attrib["d"].count("M"), 1)
        self.assertTrue(paths[0].attrib["d"].rstrip().endswith("Z"))
        for element in svg.iter():
            self.assertIn(element.tag.split("}")[-1], {"svg", "title", "path"})
            self.assertFalse(any(key.lower().startswith("on") or key.lower().endswith("href") for key in element.attrib))
        reversed_svg = ET.parse(OUT / "assets/suff-syed-signature-reversed.svg").getroot()
        self.assertEqual(reversed_svg.attrib["color"], "#FFFFFF")
        reversed_svg.set("color", svg.attrib["color"])
        self.assertEqual(ET.tostring(reversed_svg), ET.tostring(svg))
        image = self.pages[OUT / "index.html"].select_one(".cover-signature")
        self.assertEqual(image["src"], "/assets/suff-syed-signature.svg")
        self.assertEqual((image["width"], image["height"], image["alt"]), ("350", "148", ""))
        self.assertEqual(self.journal_home.select_one(".cover-signature")["src"],
                         "/assets/suff-syed-signature-reversed.svg")

    def test_self_hosted_font_provenance(self):
        fonts = ROOT / "site/fonts"
        manifest = json.loads((fonts / "provenance.json").read_text())
        self.assertEqual(len(manifest["fonts"]), 4)
        self.assertEqual({font["family"] for font in manifest["fonts"]}, {"Newsreader", "DM Mono"})
        for font in manifest["fonts"]:
            binary = (fonts / font["file"]).read_bytes()
            self.assertEqual(binary[:4], b"\x00\x01\x00\x00" if font["file"].endswith(".ttf") else b"wOF2")
            self.assertEqual(hashlib.sha256(binary).hexdigest(), font["sha256"])
            self.assertEqual(binary, (OUT / "assets/fonts" / font["file"]).read_bytes())
            self.assertIn(manifest["revision"], font["source"])
        for family in ["Newsreader", "DMMono"]:
            license_text = (fonts / f"OFL-{family}.txt").read_text()
            self.assertIn("SIL OPEN FONT LICENSE Version 1.1", license_text)
            self.assertIn("Copyright", license_text)
        self.assertFalse(list(OUT.rglob("*.otf")))
        self.assertFalse(list((ROOT / "site").rglob("*.otf")))
        self.assertEqual({p.name for p in fonts.iterdir()},
                         {font["file"] for font in manifest["fonts"]} |
                         {"OFL-Newsreader.txt", "OFL-DMMono.txt", "provenance.json"})
        self.assertEqual({p.name for p in fonts.iterdir()},
                         {p.name for p in (OUT / "assets/fonts").iterdir()})
        for soup in self.pages.values():
            self.assertNotIn("/__private/", str(soup))
            self.assertIsNone(soup.html.get("data-font-mode"))

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
                lead = PROMOTED_IMAGE if row["slug"] == PROMOTED_SLUG else row["cover"]
                self.assertEqual(soup.select_one(".essay-artwork > a")["href"], lead)
                expected_images = source.select("img")
                if row["slug"] == PROMOTED_SLUG:
                    self.assertEqual(len(expected_images), 1)
                    self.assertEqual(expected_images[0]["src"], PROMOTED_IMAGE)
                    self.assertFalse(expected_images[0].parent.get_text(strip=True))
                    expected_images = []
                self.assertEqual([img["src"] for img in body.select("img")], [img["src"] for img in expected_images])
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

    def test_reading_plates_are_original_and_exact(self):
        home = self.journal_home
        entries = json.loads(home.select_one("#home-data").string)["essays"]
        self.assertEqual(len(entries), 20)
        for entry in entries:
            model = json.loads(self.pages[OUT / "futurememo" / entry["slug"] / "index.html"].select_one("#essay-data").string)
            plate = entry["readingPlate"]
            self.assertEqual(plate, reading_plate(model))
            passage = next(p for p in model["passages"] if p["id"] == plate["passage"]["id"])
            self.assertIn(passage["kind"], {"p", "li", "blockquote"})
            self.assertEqual(plate["passage"]["text"], passage["text"])
            self.assertEqual(plate["url"], entry["url"] + "#" + passage["id"])
            for word in plate["terms"]:
                self.assertEqual(word["here"], passage["terms"][word["term"]])
                self.assertEqual(word["count"], sum(p["terms"].get(word["term"], 0) for p in model["passages"]))
                self.assertEqual(sum(section["count"] for section in word["sections"]), word["count"])
                self.assertEqual(parse_qs(urlsplit(word["url"]).query), {"term": [word["term"]]})
                for section in word["sections"]:
                    parsed = urlsplit(section["url"])
                    self.assertEqual(parse_qs(parsed.query), {"term": [word["term"]], "section": [section["id"]]})
                    first = next(p for p in model["passages"] if p["section"] == section["id"] and p["terms"].get(word["term"]))
                    self.assertEqual(parsed.fragment, first["id"])
                    self.assertEqual(section["count"], sum(p["terms"].get(word["term"], 0) for p in model["passages"] if p["section"] == section["id"]))
            for neighbor in plate["related"]:
                destination = json.loads(self.pages[OUT / "futurememo" / neighbor["slug"] / "index.html"].select_one("#essay-data").string)
                target = next(p for p in destination["passages"] if p["id"] == neighbor["id"])
                self.assertIn(target["kind"], {"p", "li", "blockquote"})
                self.assertTrue(set(neighbor["shared"]) <= passage["terms"].keys() & target["terms"].keys())
        initial = next(entry["readingPlate"] for entry in entries if "qubit-teams" in entry["slug"])
        self.assertEqual(home.select_one("[data-home-passage-text]").get_text(), initial["passage"]["text"])

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
