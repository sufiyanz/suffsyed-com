# suffsyed.com

A static, illustrated journal by Suff Syed: twenty complete essays, five editorial
preoccupations, twenty-two photographs, and an optional local reading lens.
Python builds plain HTML, CSS, SVG and small JavaScript modules. GitHub Pages
serves `main` / `docs`; there is no application server, tracking, model API or
runtime dependency on Squarespace.

The shared page shell is edge-to-edge ivory, without an inset sheet, viewport
surround, or outer shadow. Responsive inner padding and narrow essay measures
keep the full-width layout readable.

## Source of truth

| Path | Purpose |
| --- | --- |
| `content/essays/*.html` | Complete, editable essay bodies, with persistent heading and paragraph IDs. |
| `content/corpus.json` | Titles, excerpts, local cover paths, editorial themes, original text fingerprints and migration-date provenance. |
| `content/cover-descriptions.json` | Descriptive alternatives for the original illustrated essay covers. |
| `content/pages/*.html` | Preserved About, About the Memo, FAQ, report and store content. |
| `content/photograph-descriptions.json` | Descriptions of visible photographs, in original gallery order; not inferred locations or dates. |
| `content/research-example.json` | Public-data record schema and empty evidence register; no live ingestion. |
| `docs/assets/img/` | **Committed source image originals from the migration.** The builder reads these; do not delete this directory when rebuilding. |
| `site/` | Authored CSS, ES modules, favicon and self-hosted font assets, copied recursively to `docs/assets/`. |
| `tools/corpus.py` | Deterministic passage extraction, word counts and lexical-neighbor ranking. |
| `tools/build_site.py` | All routes, responsive images, searchable corpus, RSS and sitemap. |
| `tools/journal_home.py`, `tools/journal_questions.py` | Opening artwork and local question/research instruments. |
| `docs/` | Complete generated site and the preserved `CNAME`. Do not hand-edit generated HTML. |

The one-time migration used the existing committed static pages as the full-text
authority. `tools/migrate_content.py` documents that offline extraction; it is
not part of the normal build and deliberately refuses to overwrite existing
content. `tools/lib.py` is the original Squarespace conversion utility, retained
for provenance only. Regeneration no longer needs ignored `scrape/raw/` files,
the original checkout, git history, or remote image downloads.

## Build and preview

Python 3.9+ is supported. Use an isolated environment:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python tools/build_site.py
.venv/bin/python tools/test_site.py
.venv/bin/python tools/serve.py --port 8766
```

Open `http://127.0.0.1:8766/`. The local-only threaded preview serves the same
custom 404 document as Pages. Relative-to-root URLs assume the existing custom
domain; a repository-subpath deployment is not supported.

The build has no network access or current-clock inputs. All twenty full bodies
and image originals remain local. Responsive 640px and 960px derivatives are
generated from committed originals with Pillow. Repeating the build with the
pinned Python dependencies produces the same output bytes.

## Type and editorial structure

**Newsreader** supplies editorial text, introductions and long-form reading;
**DM Mono** supplies restrained technical labels, counts and data controls.
The distributable build also uses Newsreader for display. Both are self-hosted,
openly licensed faces. There are no runtime font CDN or foundry requests.

`site/journal.css` centralizes `--font-display`, `--font-reading`, `--font-ui`
and `--font-technical`. Newsreader has a real 400–700 variable range in
both roman and italic, preserving its optical-size axis with automatic optical
sizing. DM Mono uses actual 400 and 500 roman faces.
`font-synthesis: none` prevents imitation bold/italic, and `font-display: swap`
keeps reading available during loading. Four subset WOFF2 files total about
347 KiB.

The exact upstream revision, source/output SHA256 hashes and processing are in
`site/fonts/provenance.json`. Both SIL OFL 1.1 licenses accompany the fonts in
source and generated output. The ordinary build copies these committed assets
offline. To explicitly reimport the pinned Google Fonts sources (requires
network access, only when updating fonts):

```sh
.venv/bin/pip install -r requirements-fonts.txt
.venv/bin/python tools/prepare_fonts.py
```

Home follows a deliberate sequence: one featured thought with an original cover
and primary reading action; an optional connection instrument; a photographic
pause; then one unfinished research question. All twenty selections synchronize
the opening cover, drawing, title and explicit reading destination. The drawing
key and reader perspective are native disclosures. The phone theme selector is
also a disclosure, fully expanded without JavaScript. The original scientific
drawings, full-bleed paper and full essay text remain.

The selected story is the opening's dominant headline; the site statement is
quiet editorial context. A full-width mint ground groups the connection
instrument, and a localized deep-ink photographic chapter separates the gallery
from the ivory reading/research areas. These are chapter grounds, not an outer
page frame. The composition was informed by the published
[Frontend Design Review](https://github.com/microsoft/skills/tree/main/.github/skills/frontend-design-review)
framework's frictionless action, craft and trustworthy-behavior principles.
There is no Figma design system or claim of Figma compliance.

### Private Kyoto purchase evaluation

The supplied PP Kyoto free/personal-use EULA permits private purchase evaluation,
**not a public website or public font redistribution**. The optional loopback
preview uses unmodified, user-supplied Kyoto Medium, Medium Italic and Extrabold
OTFs for display. It does not install them system-wide. Museum is not used.
Only use this mode with authorized local inputs and never expose or tunnel it:

```sh
python3 tools/private_fonts.py --kyoto '/absolute/path/to/PP_Kyoto_-_Free_for_Personal_Use_v1.0.zip'
python3 tools/serve.py --port 8766 --private-fonts
```

The importer checks the supplied license and records hashes in ignored
`.private-preview/fonts/`. The server binds only to `127.0.0.1`, rejects other
Host names and cross-site font requests, and applies `tools/preview_typography.css`
only to in-memory responses. Private responses are not cached. Proprietary
binaries and evaluation CSS never enter `docs/`; the normal build has no dependency
on them. The local preview explicitly labels the evaluation. A proper web license
and a deliberate production integration are required before publishing Kyoto.
Keep `.private-preview/` ignored and do not copy it into public assets.

## Editing and adding writing

1. Edit `content/essays/<existing-slug>.html` and its metadata in
   `content/corpus.json`. Preserve IDs on existing passages even when correcting
   their text: those IDs are public deep links.
2. For a new paragraph or heading, choose a new, unique, permanent ID, such as
   `p-maintenance-cost` or `h-the-next-question`. Headings, paragraphs, standalone
   list items, quotations, captions and nonempty preformatted text need IDs.
   Nested list items containing paragraphs are measured at paragraph level.
3. For a new essay, add a metadata entry and full HTML body. `slug` is its
   canonical URL suffix; `no` is a stable collection identifier, **not a
   publication ranking**. Choose one of the five editorial themes. Put its local
   image in `docs/assets/img/`; use a substantial cover, not a gallery photograph.
4. `originalTextSha256` protects the migrated text from accidental loss. An
   intentional author edit requires explicitly accepting the new fingerprint:
   `corpus.content_digest()` computes normalized HTML text. Review the textual
   diff before updating it. Never update a fingerprint just to silence a failing
   preservation check.
5. Build and run the checks. Adding new essays intentionally requires updating
   the migration-baseline assertions (20 essays / 22 photographs) in the tests.

Sources allow ordinary semantic HTML, lists, links, images and inline emphasis;
active markup and unsafe URL schemes fail the build. Keep citations as original
links and footnote IDs/backlinks as authored HTML. There is no automatic claim
rewriting or generated article text.

Unverified publication dates remain `null`. `migrationLastmodLabel` describes
the historical sitemap field only. The site does not claim those are publication
dates, and RSS omits `pubDate` rather than inventing one.

## The reading model

All 1,387 nonempty text passages are modeled, not just introductions or excerpts.
The current complete corpus measures **45,284 words** under the shared tokenizer:
runs of English letters/digits with optional internal apostrophes or hyphens.
The older loose HTML counter reported 45,308. The difference is tokenization,
not abridgement; normalized full text is checked for every essay.

Each heading starts a section; the opening is its own section. Section weights
include headings and captions. The map and text index jump to the same stable
anchors. The optional lens supports exact, case-insensitive full-word recurrence,
section-scoped counts, original passage jumps and transparent cross-essay
connections. Curly and straight apostrophes compare equally; plurals and
hyphenated terms are not stemmed. Counts, highlighting and selection use this
same rule. Search and storage strings never become HTML.

Lexical neighbors compare prose paragraphs, list items and quotations of at least
20 words in different essays. Tables, code, captions and headings remain fully
counted and searchable but are excluded from prose-neighbor suggestions. Four
tables flattened by the previous migration have been restored from the original
raw HTML, with unchanged text and stable passage IDs; their source structure is
now committed and needs no raw files to rebuild.
Two shared eligible words are required; function words, numbers, short words and
“AI” are excluded. Ranking sums squared `log(1 + N / df)` weights over shared
words, divided by the geometric mean of the vocabulary sizes. Ties use slug and
ID. At most three different essays are returned. Every suggestion names its
shared words and links directly to its source passage. This is not semantic
truth, agreement, confidence, influence or fact-checking.

The archive searches case-insensitive literal phrases through the full passage
index, loaded only when needed. Its compact list and theme index remain useful
alternatives to the illustrated index. Default essays remain calm and complete;
the analytical layer is reversible and closing it removes all highlights.

## Local instruments and privacy

Reader’s Margin positions are optional browser-only marks, not a poll. Storage
is validated, errors are visible, and marks can be reset. No data is uploaded.
The research page is an explicitly authored scout/skeptic/synthesist
demonstration with pause/resume, milestones, reset and a visible sample result.
No external research job, live agent, credential or API key is connected.

Gallery photographs and essay covers open uncropped in a keyboard-accessible
dialog. The originals remain ordinary image links without JavaScript.
Decorative movement respects reduced motion, visibility and pause controls.
Reading, original text, section/paragraph anchors, legacy routes and full-image
links work without JavaScript; search and local instruments require it.

## Checks

```sh
.venv/bin/python tools/test_site.py
.venv/bin/python tools/test_preview.py

# Optional browser suite (install into your own environment):
.venv/bin/pip install -r requirements-browser.txt
.venv/bin/playwright install chromium
.venv/bin/python tools/test_browser.py \
  --url http://127.0.0.1:8766 \
  --artifacts /absolute/path/to/session-artifacts
.venv/bin/python tools/test_instruments.py \
  --artifacts /absolute/path/to/session-artifacts
.venv/bin/python tools/test_home.py
.venv/bin/python tools/test_shell.py \
  --artifacts /absolute/path/to/session-artifacts
.venv/bin/python tools/test_hierarchy.py \
  --artifacts /absolute/path/to/session-artifacts
.venv/bin/python tools/capture_review.py \
  --artifacts /absolute/path/to/session-artifacts
```

The static suite checks all full-text fingerprints; passage, section and term
counts; every related-passage reason and destination; covers and 22 photographs;
local links/assets/anchors; RSS; canonical URLs; legacy redirects; and unchanged
CNAME. Browser checks exercise real reading/search/inspection/gallery controls
at desktop, tablet and phone sizes, full-word/query safety, reduced motion,
no-JavaScript reading, and missing assets/browser errors. Additional instrument
checks exercise corrupt/denied storage, keyboard/touch axes, research playback,
pause/resume/reset and reduced motion. The home suite traverses all twenty
selections and verifies their exact tallies, covers, canonical links and
offscreen/paused motion. The hierarchy suite verifies actual custom-font glyph
rendering, the four public font files (plus three Kyoto faces when explicitly
run with `--private-fonts`), controls, current-section orientation and all
twenty selections at 320/390/820/1600/1920px, plus 200%/400% zoom-equivalent CSS
viewport and device-scale reflow (not browser-toolbar zoom automation).
It also checks the initial phone reading action/artwork and synchronized selected
destinations. Preview tests check public/private isolation, rejected embedding,
hash-identical evaluation bytes and nonpersistent response injection.
Capture utilities scroll to load every lazy image before saving full pages,
readable viewport studies and individual home chapter crops; `--devices desktop
phone` limits capture to those two sizes.

## Publishing

Review and commit both sources and regenerated `docs/` output to a branch. Only
after approval should that branch be merged to `main`, which GitHub Pages serves
from `/docs`. This redesign does **not** alter deployment settings, DNS or
`docs/CNAME`; the builder deliberately never writes CNAME. Keep the existing
domain configuration unchanged.

Legacy home, tag and commerce paths redirect to their retained destinations.
Both `/rss.xml` and `/futurememo/rss.xml`, sitemap, robots, `.nojekyll` and custom
404 remain available. The store is intentionally a closed-shop placeholder,
not a checkout; subscriptions link to the existing Substack. Payment credentials,
third-party tracking, an external ingestion pipeline and live agents are outside
the static site’s scope.
