# suffsyed.com

Static rebuild of suffsyed.com, migrated off Squarespace hosting. Content (all `future(memo)` posts, About Me, About the Memo, FAQs, light(works) gallery, The End of Design Report) was scraped from the live Squarespace site and regenerated as plain static HTML/CSS — no framework, no build step, no server.

The domain stays registered/managed at Squarespace; only DNS is pointed here so Squarespace hosting can be cancelled/downgraded.

## Structure

- `docs/` — the generated static site. This is what gets served (GitHub Pages point-of-truth is the `docs/` folder on `main`).
- `docs/assets/atlas.css` — the one stylesheet. Design language ("the atlas"): system serif (Iowan Old Style / Baskerville), system mono for micro-labels, one vermillion accent, hairline-ruled cells, tabular figures, every essay also rendered as a miniature typeset sheet.
- `tools/build_site.py` — builds every page in `docs/` from the raw scraped HTML in `scrape/raw/` (not committed — see below). Essay themes, the "start here" pick, and social links live at the top of this file.
- `tools/lib.py` — Squarespace-block-to-clean-HTML conversion + image downloader/optimizer (WebP, max 1600px wide, cached by URL hash).
- `scrape/` — raw scraped pages from the live Squarespace site, used as generator input. Gitignored (large, and only needed for regeneration).

## Adding or editing a post

The builder reads from `scrape/raw/*.html`, one-time snapshots of the live Squarespace pages, so there's no ongoing dependency on Squarespace. For a new essay, the cleanest path is to add a markdown/HTML source and a small loader to `tools/build_site.py` (the essay template is `gen_essay`); until then, a new essay can be hand-written as `docs/futurememo/<slug>/index.html` using any existing essay as the template. Remember to add its slug to `THEMES` so it appears in the index, sheets, and theme lists.

Dates shown on the site are the sitemap `lastmod` from the migration (most read Nov 2025). Real publish dates can be restored from a Squarespace content export and dropped into `LASTMOD` in the builder.

To regenerate from scratch (re-run the whole scrape → build pipeline):

```bash
pip3 install --user beautifulsoup4 lxml Pillow
python3 tools/build_site.py
```

## Local preview

```bash
cd docs && python3 -m http.server 8080
```

## Deploying (GitHub Pages)

1. Push this repo to GitHub.
2. Repo Settings → Pages → Source: **Deploy from a branch** → Branch: `main` → Folder: `/docs`.
3. Wait a minute for the first deploy, confirm it works at `https://<user>.github.io/<repo>/`.
4. Point the custom domain (see DNS below) and set it under Settings → Pages → Custom domain → `suffsyed.com`. GitHub will auto-detect the `docs/CNAME` file already in this repo.

## DNS (keep the domain at Squarespace, host the site here)

In Squarespace: **Settings → Domains → suffsyed.com → DNS Settings** (this works whether or not you keep a Squarespace website plan — domain-only accounts still let you manage DNS).

Remove any existing A/CNAME/ALIAS records pointing at Squarespace's web hosting, and add:

| Type  | Host | Value |
|-------|------|-------|
| A     | @    | 185.199.108.153 |
| A     | @    | 185.199.109.153 |
| A     | @    | 185.199.110.153 |
| A     | @    | 185.199.111.153 |
| CNAME | www  | `<your-github-username>.github.io` |

Then in GitHub repo Settings → Pages, set custom domain to `suffsyed.com` and enable "Enforce HTTPS" once the certificate provisions (can take up to 24h after DNS propagates).

## Known gaps vs. the old Squarespace site

- **`/store` (Buy Me a Coffee / Chemex / Iced Coffee / Pour Over products)** — this was Squarespace Commerce with real checkout. A static site can't process payments. Recommend either a [Stripe Payment Link](https://stripe.com/payments/payment-links) (free, no code, embeds as a plain link/button) or an external tip page (Buy Me a Coffee, Ko-fi). Not rebuilt here — needs a decision on which payment path to use.
- **Newsletter subscribe / signup forms** — Squarespace's built-in email capture forms won't work on a static host. "Subscribe" now links straight to the Substack (`substack.com/@suffsyed`), which already has its own working signup.
- **`/futurememo/tag/...` tag-filter pages** and the unused Squarespace boilerplate page (`member-site-homepage-1`, a never-customized template page) were intentionally not migrated — they weren't real content.
