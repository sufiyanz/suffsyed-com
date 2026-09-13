"""Private purchase-evaluation inputs; never part of the distributable build."""
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / ".private-preview/fonts"
LICENSE_HASH = "f2ef571bf670748a4a585e84e28ae9061ec88ddc1b5e84349fae772b3c8bdaa9"
FONT_FILES = {
    "display-medium": "PPKyoto-Medium.otf",
    "display-strong": "PPKyoto-Extrabold.otf",
    "display-italic": "PPKyoto-MediumItalic.otf",
}


def validate_private_fonts(directory):
    directory = Path(directory).resolve()
    if directory != PRIVATE.resolve():
        raise ValueError("Private fonts must remain in the ignored .private-preview/fonts directory.")
    manifest = json.loads((directory / "manifest.json").read_text())
    if manifest["licenseSha256"] != LICENSE_HASH or set(manifest["fonts"]) != set(FONT_FILES):
        raise ValueError("The private font pack or its license does not match this evaluation profile.")
    for key, filename in FONT_FILES.items():
        if hashlib.sha256((directory / filename).read_bytes()).hexdigest() != manifest["fonts"][key]:
            raise ValueError(f"The supplied {key} face has changed; reimport the original pack.")
    return directory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kyoto", type=Path, required=True)
    args = parser.parse_args()
    imported = {}
    for path, family in [(args.kyoto, "Kyoto")]:
        prefix = f"PP {family} - Free for Personal Use v1.0"
        with ZipFile(path) as archive:
            license_bytes = archive.read(f"{prefix}/EULA-PangramPangram-FreeForPersonalUse-MAY2021.pdf")
            if hashlib.sha256(license_bytes).hexdigest() != LICENSE_HASH:
                raise ValueError("Different licensing terms: inspect them before importing this pack.")
            for key, filename in FONT_FILES.items():
                if filename.startswith(f"PP{family}-"):
                    imported[key] = archive.read(f"{prefix}/otf/{filename}")
    PRIVATE.mkdir(parents=True, exist_ok=True)
    for key, data in imported.items():
        (PRIVATE / FONT_FILES[key]).write_bytes(data)
    (PRIVATE / "manifest.json").write_text(json.dumps({
        "licenseSha256": LICENSE_HASH,
        "purpose": "Private purchase evaluation only; no public use or redistribution.",
        "fonts": {key: hashlib.sha256(data).hexdigest() for key, data in imported.items()},
    }, indent=2) + "\n")
    validate_private_fonts(PRIVATE)
    print("Imported three unmodified display faces into ignored, local-only evaluation storage.")


if __name__ == "__main__":
    main()
