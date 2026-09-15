"""One reviewed article presentation exception; publication inputs stay intact."""
import hashlib

from bs4 import BeautifulSoup

PROMOTED_SLUG = "how-future-designers-will-win-in-the-age-of-ai"
PROMOTED_IMAGE = "/assets/img/9fe1e028baa0.webp"
METADATA_COVER = "/assets/img/717a44366c7b.webp"
SOURCE_SHA256 = "cfc74e625bfaf69771eb2856a57401aa87c6985e0072a980bc547c7465b2cb3b"
IMAGE_SHA256 = {
    PROMOTED_IMAGE: "199e1e3b3eef3b402ae4059ce5a36f92d1e930cfd36dc5e3bd4b68a58b1f8b87",
    METADATA_COVER: "90e4cd96b2438909dd266f8026e893a3105e634c6d9f92b61cb34b1c53c405b5",
}


def article_artwork(row, root):
    body = BeautifulSoup(row["body"], "html.parser")
    if row["slug"] != PROMOTED_SLUG:
        return row["cover"], body
    source = (root / "content/essays" / f"{PROMOTED_SLUG}.html").read_bytes()
    if hashlib.sha256(source).hexdigest() != SOURCE_SHA256 or row["cover"] != METADATA_COVER:
        raise ValueError("Article artwork: Future Designers source/cover changed; review its presentation rule")
    for path, expected in IMAGE_SHA256.items():
        if hashlib.sha256((root / "docs" / path.lstrip("/")).read_bytes()).hexdigest() != expected:
            raise ValueError(f"Article artwork: reviewed image identity changed: {path}")
    figure = body.find(recursive=False)
    opening = next((node for node in body.contents if str(node).strip()), None)
    image = figure.find("img", recursive=False) if figure else None
    following = figure.find_next_sibling() if figure else None
    if (figure is None or opening is not figure or figure.name != "figure" or figure.attrs or figure.get_text(strip=True)
            or image is None or figure.find_all(recursive=False) != [image]
            or image.attrs != {"alt": "", "loading": "lazy", "src": PROMOTED_IMAGE}
            or len(body.find_all("img", src=PROMOTED_IMAGE)) != 1
            or following is None or following.name != "p" or following.get("id") != "p-93486e8954"):
        raise ValueError("Article artwork: reviewed uncaptioned opening figure changed; refusing to omit it")
    figure.decompose()
    return PROMOTED_IMAGE, body
