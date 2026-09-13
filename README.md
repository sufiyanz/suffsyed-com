# suffsyed.com

A static, illustrated journal by Suff Syed: twenty complete essays, five editorial
preoccupations, twenty-two photographs, and an optional local reading lens.
Python builds plain HTML, CSS, SVG and small JavaScript modules. GitHub Pages
serves `main` / `docs`; there is no application server, tracking, model API or
runtime dependency on Squarespace.

The shared page shell is full-bleed paper, without an inset sheet, viewport
surround, or outer shadow. Responsive inner padding and narrow essay measures
keep the full-width layout readable. Six exact core colors are centralized in
`site/journal.css`: forest `#1B2915`, green `#305831`, stone `#D7CDB8`, paper
`#EFEDE6`, white `#FFFFFF`, and ink `#191919`. Existing semantic `--cp-*` aliases
use those sources. Stone-on-paper is decorative, never an important text or
control boundary. Engraved theme pigments may vary; original cover and
photograph pixels are never recolored or filtered.

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
| `site/suff-syed-signature.svg` | User-supplied, visually validated vector autograph; exact master paths, not a font or embedded raster. |
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

Home opens with a personal identity cover: the signature, the supplied Microsoft role,
and an inline invitation into writing, the reading plate, photography and open
research. `journal_home.render_cover()` owns that introduction; the shared layout
places its single global header immediately below it on home only. The cover
uses about 60% of the viewport, growing intrinsically on short/narrow screens
rather than clipping the exact copy. The real featured story starts underneath.
With JavaScript, the header is fixed outside the page flow and remains invisible
and inert until the cover leaves view. An `IntersectionObserver`, not scroll
direction, controls that state; returning to the top hides it again. An early
capability marker avoids an initial menu flash or reserved header gap. Without
JavaScript (or the observer API), the same header uses ordinary flow and native
sticky positioning. There is no duplicate menu or animated layout shift.
A `ResizeObserver` updates content-anchor and keyboard-focus clearances when
type or viewport dimensions change; CSS provides responsive fallback clearances.
The header itself is excluded from those offsets, so focusing its links does not
push it away. Other routes retain their ordinary header.

The cover alone has an edge-to-edge forest ground, white signature/link/focus
accents and warm paper/stone supporting text. The story and normal header keep
their light paper ground. Cover hover/visited states are scoped to remain legible.
The autograph is the sole visible masthead inside `h1#cover-title`, with no kicker
or duplicate sign-off mark. The heading retains the accessible name “Suff Syed”
using the existing visually hidden text pattern; the unchanged role sentence
also gives the readable full name. Responsive sizing enlarges the signature
without stretching or cropping it. Its 350×148 viewBox and explicit image
dimensions preserve proportions and avoid a load-time shift. The local SVG has
one compound outline, forest/currentColor ink, and no raster, scripts or external
references. The builder derives a white reversed version for the dark cover by
changing only the SVG's root color; the traced path geometry and source master
are unchanged. The image has an empty alt to avoid repeating the heading's
accessible text. The supplied validated master is preserved byte-for-byte.
In forced-colors mode, the same SVG supplies an alpha mask painted with the
user's `CanvasText` color. The image keeps its layout space but is not painted.
Only the mask preserves its explicit system-color fill; the page retains normal
forced-color adjustment. Both light and dark high-contrast schemes therefore
show the same signature and accessible heading without changing the normal theme.
The current master uses the approved balanced fountain-pen refinement: lighter
broad strokes with the hairlines, entry/exit tips and natural width variation
retained. Its source framing is unchanged; the refinement lives in the outline,
not CSS thinning or a uniform-width stroke. Commit `5d440a7` preserves the previous
heavier master for comparison.

`site/signature.js` optionally fills that exact silhouette with a fixed DM Mono
punctuation grid. The 1.35-second resolve uses at most 6.7 updates/second; afterward,
only two randomly selected glyphs change every 320 ms. A faint original-vector
underlay preserves the hairlines (22% on desktop, 30% on phones). The canvas is
decorative and does not add text to the heading's accessible name. A native
Pause/Resume control sits outside the heading on the existing continuation row.
One timer stops entirely when paused, offscreen, hidden or leaving the page.
Pause intent and resolve progress survive visibility/preference changes; there is
no storage or network service. The grid is capped at 3,000 cells, DPR at 2, and
each of the two canvas surfaces at 600,000 pixels. Mask sampling and font/style
measurements happen during preparation/resizing, never in the animation tick.
The original image remains until the local font and mask are ready. Reduced
motion, forced colors and printing use the static vector with no active control;
unsupported or failed initialization retains it and emits a diagnostic warning.

### A little room to play

The signature is also a native, keyboard-accessible entry into ten ephemeral
cover experiments. `site/playground.js` owns the single registry and host;
`site/playground-api.js` documents the fixed v1 module contract. Opening replaces
only the cover's visible content. The original introduction remains an inert,
invisible layout spacer, preserving its responsive height; the rest of the site
is neither locked nor made inert. Close or Escape returns focus to the signature.
The chooser selects any experiment directly; Another uses a nonrepeating,
in-memory shuffle bag. Closing or switching discards the current work.

Only the selected module and its scoped CSS load on entry. The separately fetched
`playground-data.json` contains all 22 actual gallery photographs at screen-sized
resolution and one complete original reading-plate passage per essay, with real
source anchors. The builder preserves the corpus's inline punctuation and text
joins; it neither fabricates passages nor changes the originals. Material passed
to modules is deeply frozen. No photo, audio, Worker or experience payload is
requested by the host before entry, and it uses no storage or backend.

Each fresh mount gets an AbortSignal, seeded PRNG, palette, material and explicit
status/error callbacks. Controllers start inactive; the host distributes available
dimensions, preferences and visibility. Switch/Close abort pending fetches and
mounts, deactivate and destroy the old controller, and dispose any controller that
arrives after cancellation. Loading failures are visible with Retry and Close.
The signature is suspended separately while the host is open, preserving its
own user-pause choice. Only loaded code and styles are retained between instances.

Below the cover, home keeps its deliberate sequence: one featured thought with an original cover
and primary reading action; an optional connection instrument; a photographic
pause; then one unfinished research question. All twenty selections synchronize
the opening cover, drawing, title and explicit reading destination. The drawing
key and reader perspective are native disclosures. The phone theme selector is
also a disclosure, fully expanded without JavaScript. The original scientific
drawings, full-bleed paper and full essay text remain.

The selected story is the opening's dominant headline; the site statement is
quiet editorial context. A warm stone field groups the reading plate,
and a localized forest photographic chapter separates the gallery
from the paper reading/research areas. These are chapter grounds, not an outer
page frame. The composition was informed by the published
[Frontend Design Review](https://github.com/microsoft/skills/tree/main/.github/skills/frontend-design-review)
framework's frictionless action, craft and trustworthy-behavior principles.
There is no Figma design system or claim of Figma compliance.

The reading plate follows the illustrated-field-guide principle of placing a
figure beside the prose it helps navigate, rather than treating every
illustration as an independent feature. It reuses the original engraving and
essay analysis, not another site's assets, code or fonts.

`corpus.reading_plate()` deterministically selects one complete prose passage per
essay. It prefers 35–100-word paragraphs containing at least three recurring
eligible terms; it favors up to four distinct terms, then length nearest 65
words, then the earliest passage. The fallback is eligible prose of at least
20 words. This is a mechanical entry point, not a generated summary. Up to four
words reuse the full essay's ranked vocabulary. A selection highlights the
original casing, shows exact passage/full-body counts, and traces the three most
frequent matching sections. Section links carry the exact word, section and first
matching passage into the existing lens; the full-count link carries the word and
quoted passage. The optional detour reuses the existing lexical-neighbor model.
All states change with the selected essay. A no-JavaScript visitor still gets
the whole quoted passage, measurements and native original-source links.
`site/text.js` shares token normalization with the essay reader.

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
.venv/bin/python tools/test_cover.py \
  --artifacts /absolute/path/to/session-artifacts
.venv/bin/python tools/test_forced_colors.py \
  --artifacts /absolute/path/to/session-artifacts
.venv/bin/python tools/test_signature.py \
  --artifacts /absolute/path/to/session-artifacts
.venv/bin/python tools/test_playground_host.py \
  --artifacts /absolute/path/to/session-artifacts
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
selections and their measured words, verifying original-case passage highlights,
exact counts, section/source links, selection resets, covers and offscreen/paused
motion. The hierarchy suite verifies actual custom-font glyph
rendering, the four public font files (plus three Kyoto faces when explicitly
run with `--private-fonts`), controls, current-section orientation and all
twenty selections at 320/390/820/1600/1920px, plus 200%/400% zoom-equivalent CSS
viewport and device-scale reflow (not browser-toolbar zoom automation).
It also checks the initial phone reading action/artwork and synchronized selected
destinations. Preview tests check public/private isolation, rejected embedding,
hash-identical evaluation bytes and nonpersistent response injection.
The cover suite verifies the exact introductory copy, the visible start of the
featured story, gap-free header reveal/inert states, four section invitations,
keyboard/touch, back/scroll restoration, direct
fragments, resize, and smooth/reduced motion at six widths with and without
JavaScript. It captures readable desktop/phone openings, boundary transitions,
the header over the story and reading plate, and the restored top state.
The forced-colors check samples actual screenshots in light/dark schemes,
verifies black/white signature contrast and compares the painted silhouette with
the normal SVG at four widths. It also checks the heading's accessible name and
confirms that page-wide forced-color adjustment remains enabled.
The character-field check records actual canvas glyph calls and frame pixels,
checks sparse substitutions on fixed coordinates, frozen pause/lifecycle states,
runtime preferences and failure/no-JS fallbacks, and captures six viewport sizes.
The cover, forced-colors and signature runners accept `--browser-channel chromium`
to use a separately installed full Chromium engine instead of headless shell.
They also accept `--browser webkit`. WebKit can verify the character field and its
forced-media stop/fallback controller, but cannot validate native forced-palette
contrast when `forced-color-adjust` is unsupported; the strict contrast runner
must still pass in a capable engine. `test_signature.py --widths 320 1600
--no-captures` runs focused phone/desktop lifecycle, painted-shape and fallback
checks without recapturing all viewport studies; `--fallbacks-only` limits it to
initialization failures, static preferences, no-JS and deep-link suspension.
The playground host runner validates source material and payload budgets, then
uses explicitly test-only route fixtures to exercise cover geometry, the complete
registry, focus/IME/Escape, signature-pause preservation, nonrepeating selection,
late-mount disposal, retry and no-JS. Fixtures are never shipped or registered as
finished experiences. `--static-only` and `--browser-only` allow separate Python
environments; module-specific tests exercise the actual creative tools.
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
