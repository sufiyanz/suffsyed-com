"""Authored membership/order, source-bound evidence and static series navigation."""
import copy
import unittest
from pathlib import Path
from unittest.mock import patch

from bs4 import BeautifulSoup

from corpus import measure
from reading_guide import read_json
from series import load_series, render_context, render_part_navigation

ROOT = Path(__file__).resolve().parents[1]
SERIES_SLUGS = (
    "designers-should-look-to-demis-hassabis-not-jony-ive",
    "designers-have-to-move-from-the-surface-to-the-substrate",
    "the-design-leaders-are-lying-to-you",
    "how-future-designers-will-win-in-the-age-of-ai",
)


class SeriesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = [measure(row, ROOT) for row in read_json(ROOT / "content/corpus.json")["essays"]]
        cls.definition = read_json(ROOT / "content/series.json")
        cls.series = load_series(cls.rows, ROOT)

    def test_exact_authored_order_and_complete_static_context(self):
        self.assertEqual(self.series["title"], "The Future of Design")
        self.assertEqual(tuple(part["slug"] for part in self.series["parts"]), SERIES_SLUGS)
        self.assertEqual([part["number"] for part in self.series["parts"]], [1, 2, 3, 4])
        self.assertEqual([part["label"] for part in self.series["parts"]], ["I", "II", "III", "IV"])
        members = 0
        for row in self.rows:
            page = BeautifulSoup((ROOT / "docs" / row["url"].strip("/") / "index.html").read_text(), "html.parser")
            context = page.select_one(".series-context")
            pagination = page.select_one(".series-pagination")
            if row["slug"] not in SERIES_SLUGS:
                self.assertIsNone(context)
                self.assertIsNone(pagination)
                self.assertEqual(render_context(self.series, row["slug"]), "")
                self.assertEqual(render_part_navigation(self.series, row["slug"]), "")
                continue
            members += 1
            index = SERIES_SLUGS.index(row["slug"])
            part = self.series["parts"][index]
            self.assertEqual(context["data-series"], "future-of-design")
            self.assertEqual(context["data-series-part"], str(index + 1))
            self.assertIsNone(context.find_parent(id="essay-body"))
            self.assertIsNone(pagination.find_parent(id="essay-body"))
            self.assertEqual(context.a["href"], "/#writing")
            evidence = context.select_one(".series-evidence")["href"][1:]
            self.assertEqual(evidence, part["sourceIds"][0])
            self.assertIsNotNone(page.select_one("#essay-body").find(id=evidence))
            expected = [self.series["parts"][i] for i in (index - 1, index + 1) if 0 <= i < 4]
            links = pagination.select(".series-step")
            self.assertEqual([link["href"] for link in links], [other["row"]["url"] for other in expected])
            self.assertEqual([link.select_one(".series-step-title").get_text() for link in links],
                             [other["row"]["title"] for other in expected])
            self.assertEqual([link["rel"] for link in links],
                             [["prev" if other["number"] < part["number"] else "next"] for other in expected])
        self.assertEqual(members, 4)
        self.assertTrue(all(row["publicationDate"] is None for row in self.rows))

    def test_invalid_definitions_fail_clearly(self):
        changes = [
            lambda s: s.update(version=True),
            lambda s: s.update(publicationDate="2025-10-07"),
            lambda s: s.update(id="../series"),
            lambda s: s.update(title="<b>Series</b>"),
            lambda s: s.update(description="x" * 181),
            lambda s: s["parts"].pop(),
            lambda s: s["parts"].reverse(),
            lambda s: s["parts"][0].update(number=True),
            lambda s: s["parts"][0].update(date="2025-10-07"),
            lambda s: s["parts"][0].update(slug="unknown"),
            lambda s: s["parts"][0].update(slug=[]),
            lambda s: s["parts"][1].update(slug=s["parts"][0]["slug"]),
            lambda s: s["parts"][0].update(sourceSha256="0" * 64),
            lambda s: s["parts"][0].update(sourceIds=[]),
            lambda s: s["parts"][0].update(sourceIds=["missing-id"]),
            lambda s: s["parts"][0].update(sourceIds=[s["parts"][1]["sourceIds"][0]]),
            lambda s: s["parts"][0].update(sourceIds=s["parts"][0]["sourceIds"] * 2),
            lambda s: s["parts"][1]["sourceIds"].reverse(),
        ]
        for index, change in enumerate(changes):
            data = copy.deepcopy(self.definition)
            change(data)
            with self.subTest(case=index), patch("series.read_json", return_value=data):
                with self.assertRaises(ValueError):
                    load_series(self.rows, ROOT)

    def test_plain_data_is_escaped(self):
        series = copy.deepcopy(self.series)
        series["title"] = 'Design & "intelligence"'
        series["parts"][1]["row"]["title"] = 'A & B "choices"'
        context = render_context(series, SERIES_SLUGS[0])
        navigation = render_part_navigation(series, SERIES_SLUGS[0])
        self.assertIn("Design &amp; &quot;intelligence&quot;", context)
        self.assertIn("A &amp; B &quot;choices&quot;", navigation)


if __name__ == "__main__":
    unittest.main()
