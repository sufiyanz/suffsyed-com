"""Import externally authored companions only after source/schema validation."""
import argparse
import shutil
from pathlib import Path

from corpus import measure
from reading_guide import load_guides, read_json

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--allow-partial", action="store_true", help="Explicit in-progress import; ordinary builds still require every guide.")
    args = parser.parse_args()
    rows = [measure(row, ROOT) for row in read_json(ROOT / "content/corpus.json")["essays"]]
    guides = load_guides(rows, ROOT, args.directory, allow_partial=args.allow_partial)
    destination = ROOT / "content/reading-guides"
    destination.mkdir(exist_ok=True)
    for slug in guides:
        shutil.copyfile(args.directory / f"{slug}.json", destination / f"{slug}.json")
    print(f"Imported {len(guides)}/{len(rows)} validated AI companions; original sources unchanged.")


if __name__ == "__main__":
    main()
