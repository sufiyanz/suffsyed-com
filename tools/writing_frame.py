"""Shared writing-first navigation and the approved closing autograph."""


PRIMARY_NAV = (
    ("Future (Memo)", "/futurememo/", "writing"),
    ("Light (works)", "/lightworks/", "light"),
    ("About (Me)", "/about-me/", "about"),
)


def primary_links(current=""):
    return "".join(
        f'<a href="{url}"' + (' aria-current="page"' if key == current else "") + f'>{label}</a>'
        for label, url, key in PRIMARY_NAV
    )


def header(current=""):
    return f'''<header class="site-header">
<a class="site-name" href="/" aria-label="Suff Syed, home">Suff Syed</a>
<nav aria-label="Main navigation">{primary_links(current)}</nav></header>'''


def footer():
    return f'''<footer class="site-footer">
<p class="footer-note">An independent point of view.<br>Thanks for spending a little time here.</p>
<nav aria-label="Further reading">{primary_links()}
<a href="/futurememo/rss.xml">RSS</a><a href="#top">Back to top <span aria-hidden="true">↑</span></a></nav>
<a class="footer-signature" href="/" aria-label="Suff Syed, home"><span class="signature-ink">
<img src="/assets/suff-syed-signature-reversed.svg" width="350" height="148" alt="" loading="lazy">
</span></a>
<p class="footer-colophon">Independent writing<br>by Suff Syed</p>
<details class="footer-more"><summary>Elsewhere &amp; site notes</summary>
<nav aria-label="Site notes"><a href="/about-the-memo/">The memo</a><a href="/research/">The unfinished</a>
<a href="/faqs/">FAQs</a><a href="/the-end-of-design-report/">The End of Design</a>
<a href="/store/">A coffee, perhaps</a><a href="/methods/">How to read the data</a>
<a href="https://substack.com/@suffsyed">Substack ↗</a><a href="https://x.com/suff_syed">X ↗</a>
<a href="https://www.linkedin.com/in/suffsyed/">LinkedIn ↗</a></nav></details>
</footer>'''
