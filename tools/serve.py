"""Local-only preview with the same custom 404 document as GitHub Pages."""
import argparse
import io
import re
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from private_fonts import FONT_FILES, PRIVATE, validate_private_fonts

DOCS = Path(__file__).resolve().parents[1] / "docs"


class PreviewHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, private_fonts=None, **kwargs):
        self.private_fonts = private_fonts
        super().__init__(*args, **kwargs)

    def local_response(self, content, mime):
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        return io.BytesIO(content)

    def html_bytes(self, source):
        if self.private_fonts:
            source = re.sub(r'<link rel="preload"[^>]+as="font"[^>]*>\n?', "", source)
            source = source.replace('<html lang="en"', '<html lang="en" data-font-mode="private-evaluation"')
            source = source.replace("</head>", '<link rel="stylesheet" href="/__private/type.css"></head>')
            source = source.replace("Independent writing · No tracking", "Private font evaluation · Web licensing required before publication")
        return source.encode()

    def send_head(self):
        route = urlsplit(self.path).path
        if self.private_fonts:
            port = self.server.server_address[1]
            if self.headers.get("Host") not in {f"127.0.0.1:{port}", f"localhost:{port}"}:
                self.send_error(403, "Private evaluation requires a loopback host.")
                return None
        if route.startswith("/__private/"):
            if not self.private_fonts:
                self.send_error(404)
                return None
            if self.headers.get("Sec-Fetch-Site", "none") not in {"same-origin", "none"}:
                self.send_error(403, "Private fonts cannot be embedded by another site.")
                return None
            if route == "/__private/type.css":
                return self.local_response(Path(__file__).with_name("preview_typography.css").read_bytes(), "text/css")
            key = route.removeprefix("/__private/fonts/")
            if key in FONT_FILES and route == f"/__private/fonts/{key}":
                return self.local_response((self.private_fonts / FONT_FILES[key]).read_bytes(), "font/otf")
            self.send_error(404)
            return None
        if self.private_fonts:
            target = Path(self.translate_path(self.path))
            if target.is_dir() and route.endswith("/"):
                target = target / "index.html"
            if target.is_file() and target.suffix == ".html":
                return self.local_response(self.html_bytes(target.read_text()), "text/html; charset=utf-8")
        return super().send_head()

    def log_message(self, format, *args):
        if not urlsplit(self.path).path.startswith("/__private/"):
            super().log_message(format, *args)

    def send_error(self, code, message=None, explain=None):
        if code != 404:
            return super().send_error(code, message, explain)
        content = self.html_bytes((DOCS / "404.html").read_text())
        self.send_response(404)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        if self.private_fonts:
            self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(content)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--private-fonts", action="store_true", help="Use ignored, licensed-for-private-evaluation PP inputs; never for publication.")
    args = parser.parse_args()
    private = validate_private_fonts(PRIVATE) if args.private_fonts else None
    server = ThreadingHTTPServer(("127.0.0.1", args.port), partial(PreviewHandler, directory=str(DOCS), private_fonts=private))
    print(f"Journal preview: http://127.0.0.1:{args.port}/ ({'private font evaluation' if private else 'distributable open-font build'})", flush=True)
    server.serve_forever()
