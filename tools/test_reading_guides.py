"""Strict companion contract, source citations and immutable publication checks."""
import copy
import tempfile
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

from corpus import flat_text, measure
from reading_guide import load_guides, read_json, render_guide, render_notes, validate_guide

ROOT = Path(__file__).resolve().parents[1]


class GuideTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = [measure(row, ROOT) for row in read_json(ROOT / "content/corpus.json")["essays"]]
        cls.guides = load_guides(cls.rows, ROOT)
        cls.row = next(row for row in cls.rows if row["slug"] == "ai-doesnt-create-slop-humans-do")
        cls.source = (ROOT / "content/essays" / f'{cls.row["slug"]}.html').read_bytes()

    def test_complete_source_bound_rendering(self):
        self.assertEqual(len(self.guides), 20)
        blocks = 0
        for row in self.rows:
            guide = self.guides[row["slug"]]
            page = BeautifulSoup((ROOT / "docs" / row["url"].strip("/") / "index.html").read_text(), "html.parser")
            self.assertEqual(page.select_one("#ai-reading-guide")["data-guide-source-sha256"], guide["sourceSha256"])
            self.assertEqual(len(page.select("[data-guide-section]")), len(guide["sections"]))
            self.assertEqual(len(page.select("[data-note-section]")), len(guide["notes"]))
            self.assertFalse(page.select("[data-motion-scene]"))
            passages = page.select("#essay-body [data-passage]")
            self.assertEqual([p["id"] for p in passages], [p["id"] for p in row["passages"]])
            for anchor in page.select("#ai-reading-guide a[href^='#'], #ai-reading-notes a[href^='#']"):
                self.assertIsNotNone(page.select_one("#essay-body").find(id=anchor["href"][1:]))
            original = BeautifulSoup((ROOT / "content/essays" / f'{row["slug"]}.html').read_text(), "html.parser")
            body = page.select_one("#essay-body")
            for tools in body.select(".passage-tools"):
                tools.decompose()
            for block in original.select("[id]"):
                rendered = body.find(id=block["id"])
                self.assertIsNotNone(rendered)
                self.assertEqual(flat_text(rendered), flat_text(block), (row["slug"], block["id"]))
                blocks += 1
        self.assertEqual(blocks, 1592)

    def test_invalid_contracts_fail_closed(self):
        baseline = self.guides[self.row["slug"]]
        changes = [
            lambda g: g.update(version=True),
            lambda g: g.update(sourceSha256="0" * 64),
            lambda g: g.update(authorship="human"),
            lambda g: g.update(extra="not allowed"),
            lambda g: g["sections"][0].update(anchor=g["sections"][1]["anchor"]),
            lambda g: g["sections"].reverse(),
            lambda g: g["sections"][1].update(id=g["sections"][0]["id"]),
            lambda g: g["sections"][0]["bullets"][0].update(sourceIds=["missing-id"]),
            lambda g: g["sections"][0]["bullets"][0].update(sourceIds=[g["sections"][-1]["anchor"]]),
            lambda g: g["sections"][0]["bullets"][0].update(text="<strong>Not plain text</strong>"),
            lambda g: g["sections"][0]["bullets"][0].update(text="x" * 161),
            lambda g: g["sections"][0]["bullets"][0].update(sourceIds=[g["sections"][0]["anchor"]] * 2),
            lambda g: g["notes"][0].update(sectionId=[]),
            lambda g: g["notes"][0].update(kind="reader comment"),
            lambda g: g["notes"][1].update(sectionId=g["notes"][0]["sectionId"]),
            lambda g: g["notes"][1].update(id=g["notes"][0]["id"]),
        ]
        for change in changes:
            guide = copy.deepcopy(baseline)
            change(guide)
            with self.assertRaises(ValueError):
                validate_guide(guide, self.row, self.source)

    def test_coverage_and_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            with self.assertRaisesRegex(ValueError, "coverage"):
                load_guides(self.rows, ROOT, directory)
            (directory / "unexpected.json").write_text("{}")
            with self.assertRaisesRegex(ValueError, "unknown"):
                load_guides(self.rows, ROOT, directory, allow_partial=True)
            (directory / "duplicate.json").write_text('{"version":1,"version":2}')
            with self.assertRaisesRegex(ValueError, "Duplicate JSON key"):
                read_json(directory / "duplicate.json")

    def test_plain_text_is_escaped(self):
        guide = copy.deepcopy(self.guides[self.row["slug"]])
        guide["sections"][0]["label"] = 'A & B "choices"'
        guide["notes"][0]["text"] = "The essay's questions & its limits."
        self.assertIn("A &amp; B", render_guide(guide))
        self.assertIn("questions &amp;", render_notes(guide))


if __name__ == "__main__":
    unittest.main()
