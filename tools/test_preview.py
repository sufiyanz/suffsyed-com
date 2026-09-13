"""Exercise public/private preview boundaries without publishing private inputs."""
import hashlib
import http.client
import threading
import unittest
from functools import partial
from http.server import ThreadingHTTPServer

from private_fonts import FONT_FILES, PRIVATE, validate_private_fonts
from serve import DOCS, PreviewHandler


class QuietHandler(PreviewHandler):
    def log_message(self, format, *args):
        pass


class PreviewTests(unittest.TestCase):
    def start(self, private=False):
        directory = validate_private_fonts(PRIVATE) if private else None
        server = ThreadingHTTPServer(("127.0.0.1", 0),
                                     partial(QuietHandler, directory=str(DOCS), private_fonts=directory))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(thread.join)
        self.addCleanup(server.shutdown)
        return server.server_address[1]

    def request(self, port, path, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        connection.request("GET", path, headers=headers or {})
        response = connection.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
        connection.close()
        return result

    def test_public_mode_never_exposes_private_assets(self):
        port = self.start()
        for route in ["/", "/404.html", "/futurememo/"]:
            status, _, body = self.request(port, route)
            self.assertEqual(status, 200)
            self.assertNotIn(b"/__private/", body)
            self.assertNotIn(b"private-evaluation", body)
        for route in ["/__private/type.css", "/__private/fonts/display-medium",
                      "/.private-preview/fonts/PPKyoto-Medium.otf"]:
            self.assertEqual(self.request(port, route)[0], 404)

    @unittest.skipUnless((PRIVATE / "manifest.json").exists(), "No local licensed evaluation inputs.")
    def test_private_mode_is_loopback_only_and_nonpersistent(self):
        original = {path: path.read_bytes() for path in [DOCS / "index.html", DOCS / "404.html"]}
        port = self.start(private=True)
        for route, expected_status in [("/", 200), ("/not-a-page", 404)]:
            status, headers, body = self.request(port, route)
            self.assertEqual(status, expected_status)
            self.assertEqual(headers["Cache-Control"], "no-store")
            self.assertIn(b'data-font-mode="private-evaluation"', body)
            self.assertIn(b"Web licensing required before publication", body)
        for key, filename in FONT_FILES.items():
            status, headers, body = self.request(port, f"/__private/fonts/{key}")
            self.assertEqual(status, 200)
            self.assertEqual(headers["Cache-Control"], "no-store")
            self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
            self.assertEqual(hashlib.sha256(body).digest(),
                             hashlib.sha256((PRIVATE / filename).read_bytes()).digest())
        for route in ["/__private/", "/__private/fonts/", "/__private/fonts/ui-regular"]:
            self.assertEqual(self.request(port, route)[0], 404)
        self.assertEqual(self.request(port, "/", {"Host": f"example.com:{port}"})[0], 403)
        self.assertEqual(self.request(port, "/__private/type.css", {"Sec-Fetch-Site": "cross-site"})[0], 403)
        self.assertEqual(self.request(port, "/__private/fonts/display-medium", {"Sec-Fetch-Site": "same-site"})[0], 403)
        for path, content in original.items():
            self.assertEqual(path.read_bytes(), content)


if __name__ == "__main__":
    unittest.main()
