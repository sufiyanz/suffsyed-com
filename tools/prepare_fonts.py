"""Explicit, optional font import; the ordinary site build never downloads fonts."""
import hashlib
import io
import json
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

REVISION = "809e4d8b8d7e9364a914909bb777679606c178b8"
BASE = f"https://raw.githubusercontent.com/google/fonts/{REVISION}/ofl"
OUT = Path(__file__).resolve().parents[1] / "site/fonts"
FONTS = [
    ("newsreader", "Newsreader[opsz,wght].ttf", "newsreader-roman.woff2", "Newsreader", "normal", "400 700"),
    ("newsreader", "Newsreader-Italic[opsz,wght].ttf", "newsreader-italic.woff2", "Newsreader", "italic", "400 700"),
    ("dmmono", "DMMono-Regular.ttf", "dm-mono-regular.woff2", "DM Mono", "normal", "400"),
    ("dmmono", "DMMono-Medium.ttf", "dm-mono-medium.woff2", "DM Mono", "normal", "500"),
]
RANGES = [(0, 0x24F), (0x370, 0x3FF), (0x1E00, 0x1EFF), (0x2000, 0x22FF), (0x25A0, 0x25FF)]


def fetch(url):
    with urlopen(url, timeout=30) as response:
        return response.read()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    records = []
    for directory, filename, output, family, style, weight in FONTS:
        url = f"{BASE}/{directory}/{quote(filename)}"
        data = fetch(url)
        font = TTFont(io.BytesIO(data), recalcTimestamp=False)
        if "fvar" not in font:
            assert font["OS/2"].usWeightClass == int(weight)
        options = subset.Options()
        options.recalc_timestamp = False
        options.layout_features = ["*"]
        options.name_IDs = [0, 1, 2, 3, 4, 5, 6, 13, 14, 16, 17]
        subsetter = subset.Subsetter(options=options)
        subsetter.populate(unicodes={code for start, end in RANGES for code in range(start, end + 1)})
        subsetter.subset(font)
        if "fvar" in font:
            font = instantiateVariableFont(font, {"wght": (400, 700)}, inplace=True)
        font.flavor = "woff2"
        font.save(OUT / output)
        records.append({
            "file": output, "family": family, "style": style, "weight": weight,
            "source": url, "sourceSha256": hashlib.sha256(data).hexdigest(),
            "sha256": hashlib.sha256((OUT / output).read_bytes()).hexdigest(),
        })
        print(output, (OUT / output).stat().st_size, "bytes")
    for directory, name in [("newsreader", "Newsreader"), ("dmmono", "DMMono")]:
        (OUT / f"OFL-{name}.txt").write_bytes(fetch(f"{BASE}/{directory}/OFL.txt"))
    (OUT / "provenance.json").write_text(json.dumps({
        "source": "Google Fonts upstream, pinned revision",
        "revision": REVISION, "license": "SIL Open Font License 1.1",
        "processing": "FontTools 4.59.2 + Brotli 1.1.0; Latin/Latin-extended, Greek and typographic symbols; Newsreader weights 400–700 with its optical-size axis preserved; timestamps preserved.",
        "fonts": records,
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()
