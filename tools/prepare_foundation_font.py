"""Explicit OFL font import for the observatory; never part of the offline build."""
import hashlib
import io
import json
from pathlib import Path
from urllib.parse import quote

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

from prepare_fonts import BASE, RANGES, REVISION, fetch

OUT = Path(__file__).resolve().parents[1] / "site/foundation"


def main():
    url = f"{BASE}/instrumentsans/{quote('InstrumentSans[wdth,wght].ttf')}"
    source = fetch(url)
    license_text = fetch(f"{BASE}/instrumentsans/OFL.txt")
    if b"SIL OPEN FONT LICENSE Version 1.1" not in license_text:
        raise ValueError("Expected the pinned Instrument Sans OFL license")
    font = TTFont(io.BytesIO(source), recalcTimestamp=False)
    font = instantiateVariableFont(font, {"wght": 400, "wdth": 100}, inplace=True)
    options = subset.Options()
    options.recalc_timestamp = False
    options.layout_features = ["*"]
    options.name_IDs = [0, 1, 2, 3, 4, 5, 6, 13, 14, 16, 17]
    subsetter = subset.Subsetter(options=options)
    subsetter.populate(unicodes={code for start, end in RANGES for code in range(start, end + 1)})
    subsetter.subset(font)
    font.flavor = "woff2"
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / "instrument-sans-regular.woff2"
    font.save(target)
    (OUT / "OFL-InstrumentSans.txt").write_bytes(license_text)
    (OUT / "font-provenance.json").write_text(json.dumps({
        "family": "Instrument Sans", "style": "normal", "weight": "400",
        "license": "SIL Open Font License 1.1", "revision": REVISION,
        "source": url, "sourceSha256": hashlib.sha256(source).hexdigest(),
        "file": target.name, "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "licenseSha256": hashlib.sha256(license_text).hexdigest(),
        "processing": "FontTools 4.59.2 + Brotli 1.1.0; static weight400, width100; "
                      "existing Latin/Greek/typographic subset; timestamps preserved.",
    }, indent=2) + "\n")
    print(f"{target.name}: {target.stat().st_size} bytes; pinned OFL source and license recorded.")


if __name__ == "__main__":
    main()
