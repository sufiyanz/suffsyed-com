"""Shared writing-first navigation and the approved closing autograph."""


def header(home=False, current="", motion=False):
    writing = "#writing" if home else "/futurememo/"
    active = ' aria-current="page"' if current == "writing" else ""
    about = ' aria-current="page"' if current == "about" else ""
    control = '''<button type="button" class="motion-toggle" data-motion-toggle hidden
aria-label="Pause decorative motion" aria-pressed="false"><span data-motion-label>Pause</span></button>''' if motion else ""
    return f'''<header class="site-header">
<a class="site-name" href="/" aria-label="Suff Syed, home">Suff Syed</a>
<nav aria-label="Main navigation"><a href="{writing}"{active}>Writing</a><a href="/about-me/"{about}>About</a></nav>
{control}</header>'''


def footer():
    return '''<footer class="site-footer">
<p class="footer-note">An independent point of view.<br>Thanks for spending a little time here.</p>
<nav aria-label="Further reading"><a href="/futurememo/">Writing</a><a href="/about-the-memo/">The memo</a>
<a href="/futurememo/rss.xml">RSS</a><a href="#top">Back to top <span aria-hidden="true">↑</span></a></nav>
<a class="footer-signature" href="/" aria-label="Suff Syed, home"><span class="signature-ink">
<img src="/assets/suff-syed-signature-reversed.svg" width="350" height="148" alt="" loading="lazy">
</span></a>
<p class="footer-colophon">Independent writing<br>by Suff Syed</p>
<details class="footer-more"><summary>Elsewhere &amp; site notes</summary>
<nav aria-label="Site notes"><a href="/research/">The unfinished</a>
<a href="/faqs/">FAQs</a><a href="/the-end-of-design-report/">The End of Design</a>
<a href="/store/">A coffee, perhaps</a><a href="/methods/">How to read the data</a>
<a href="https://substack.com/@suffsyed">Substack ↗</a><a href="https://x.com/suff_syed">X ↗</a>
<a href="https://www.linkedin.com/in/suffsyed/">LinkedIn ↗</a></nav></details>
</footer>'''
