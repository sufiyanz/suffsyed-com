# suffsyed.com

A static, illustrated journal by Suff Syed: twenty complete essays, five editorial
preoccupations, twenty-two photographs, and an optional local reading lens.
Python builds plain HTML, CSS, SVG and small JavaScript modules. GitHub Pages
serves `main` / `docs`; there is no application server, tracking, model API or
runtime dependency on Squarespace.

## Sage observatory / writing gallery

The approved sage observatory now opens with a direct Gallery entrance:
an integrated autograph masthead, introduction and exact role credit on the
sage/grain field, followed by one generous original artwork and its complete
linked essay title. The four-part **The Future of Design** series follows below;
all twenty essays are at gallery
scale in `/futurememo/`, and full-ratio frontispieces on every essay arrival.
Natural-scroll autograph mastheads, a continuous sage surface, Instrument
Sans / DM Mono hierarchy and dark forest footer form a shared writing-first
frame. Light(works) is no longer a homepage scene; its 22 photographs and
full-view behavior remain intact at the parked `/lightworks/` route, without
primary navigation or footer promotion. The shared main navigation is exactly
**Future (Memo)** (`/futurememo/`) and
**About (Me)** (`/about-me/`), including the preserved renderers. The first link
always opens the complete archive, not a homepage fragment. Primary footer
labels match; the memo description remains in the site-notes disclosure.
The composition applies the
published [Frontend Design Review: Creative Frontend Design](https://raw.githubusercontent.com/microsoft/skills/main/.github/skills/frontend-design-review/SKILL.md)
workflow: explicit observatory concept, asymmetry, scale contrast and matte
material craft. Blink informed the spatial hierarchy, not the artwork or code;
no proprietary fonts, branded diagrams, animation or scroll mechanics are copied.

`tools/foundation_home.py` renders the homepage; `site/gallery-home.css` scopes
the chosen cover and single painted opening surface to that page.
`site/foundation.css` retains the shared fields and lower composition.
`tools/writing_frame.py` and `site/frame.css` share the navigation,
autograph masthead, footer, material/spacing tokens, display section headings and
readable action styles. Primary reading actions use a forest square arrow;
secondary actions have a clear baseline rule. Both have 44px-plus targets, without
restyling authored inline links or source citations.
`site/writing.css` carries the gallery field and typography through all public
pages; `.sheet` is transparent rather than a separate white slab. Newsreader
remains the long-reading face, and internal essay headings retain their scale. Support-page
content is unchanged. All artwork is still, uncropped, untinted and displayed
at its native aspect ratio. Responsive `sizes` match the new scale; sources
include 640/960px derivatives and full original files.
The archive opens on art, not utilities: a native Search & explore disclosure
holds the complete passage search, theme filter and compact-list controls.
Linked searches open the disclosure automatically; without JavaScript it
explains the limitation and retains the complete native essay list.
`/futurememo/` uses aligned, full-width editorial rows: uncropped original art
and a consistent copy/action column, separated by full-width rules. Phone rows
stack the image and copy. There are no arbitrary essay numbers, staggered
offsets or detached arrow-only links. The shared **Read essay** action leads;
measured word counts and word-thread links remain secondary and available.
Compact mode removes the artwork and description, not the reading action or
word-thread link, and uses the full row width without an empty number gutter.
Archive branding and native invitations do not promise a fixed-size
collection. Search/result and theme-member counts derive from the supplied
rows. Passage numbers remain meaningful source references, not archive rankings.

`tools/foundation_art.py` produces original parametric SVG line studies and a
seeded static 160px grain tile. `site/motion.js` combines slow 24-second carrier
transforms with three native SVG `animateMotion` / `mpath` tracers. Each tracer
references an actual visible closed ribbon path in the same carrier coordinate
frame. Opposite eighth-step lanes join through the half-twist; no open half is
closed with a chord. The three cycles take 48, 60 and 72 seconds at constant path
speed. Fixed origin markers explicitly reference their construction axes and
share the axes' carrier, rather than drifting independently.

Each scene has a dedicated paint-contained, clipped field separated from copy
and controls. The page budget is at most two visible scenes, two WAAPI carrier
tracks and three native followers sharing one SVG clock; no JavaScript frame
callbacks, geometry reads, storage or network requests. IntersectionObserver,
document visibility and page lifecycle events pause **both** WAAPI and native
SVG timelines. Reduced/forced/print media remove
native intervals and restore canonical static path positions; returning to
ordinary media starts fresh cycles on resume. Decorative motion initializes
independently of navigation controls, once per document; the requested Pause
button is absent from the markup, with no replacement settings UI or divider.
Reduced motion, forced colors, print and no-JS retain complete static content.
The module is initialized once per document and survives bfcache restoration.
There is no preloader, scroll interception, new app host or runtime model call.
Safe-area insets and native scroll padding keep section headings and keyboard
targets clear, without scroll-state JavaScript or hide/reveal behavior.
At 700px and narrower, the
header has two calm rows with the complete labels at 12px and 48px touch
targets. Shared row-height/count tokens determine its height and clearances.
All public pages have an integrated, left-aligned autograph masthead. It is a
transparent, document-positioned header over reserved cover padding, and scrolls
away with the opening. One continuous cover surface paints the sage/grain wash
behind both masthead and introduction/artwork; there is no independent header
background, pinned strip or transition. The same natural-flow behavior applies
to archive, article and support-page mastheads. Only the reading instruments
remain sticky: desktop rails sit 32px from the safe top; the narrow reader
toolbar sits at the safe top after the masthead leaves, with 56px source clearance.
The opening has one autograph and no separate text-name logo, card or hero
wireform. The series now leads directly to the original closing autograph/footer;
the retired atlas teaser and its decorative scene are gone. The homepage loads
no motion controller; the archive's separate decorative arrival remains.

`render_foundation()` and `archive_page()` receive the same ordered `rows` from
`content/corpus.json`. The cover feature is `rows[0]`, exactly the first rendered
archive entry, with its original image/description, complete title and URL.
This is an editorial ordering contract, **not independently verified chronology**:
all `publicationDate` values are null, and `migrationLastmod` is never used to
infer one. The UI says **Featured essay**. No sample slug controls the feature.

`content/series.json` is the separate, source-backed definition of **The Future
of Design**. Its exact authored order is Hassabis → Surface/Substrate → Design
Leaders → Future Designers (Parts I–IV). The homepage renders all four original
artworks, complete titles and canonical links; it never infers membership from
themes, backfills unrelated recommendations, or truncates the series to three.
The current archive-lead feature is outside this series. Feature selection and
the complete series order are independent.
`tools/series.py` validates the exact schema, explicit ordered part numbers,
known unique members, raw-source SHA256 and local, ordered evidence IDs.
Planned “dropping” dates in the source are not publication dates. Only these four
articles receive a series context, an original author's-note link and genuine
previous/next part navigation outside `#essay-body`; endpoints do not wrap.

Regular **Instrument Sans** supplies the deliberate grotesk hierarchy; the
existing **DM Mono** supplies small technical annotations. A 24KB static
Instrument Sans subset, its SIL OFL1.1 license and pinned source/output hashes
live separately in `site/foundation/`, leaving every original font untouched.
`tools/prepare_foundation_font.py` explicitly imports that pinned public source
using the existing `requirements-fonts.txt` tooling; the ordinary build remains
offline. The homepage requests exactly these two local font files.

The writing templates and shared frame intentionally evolve the static-only
checkpoint. Original essay bodies, metadata, passage IDs, essay themes,
search, compact list mode, gallery and public fonts are preserved. All ten
experiments, host/lifecycle API, scenes, reader margin and research sources are
preserved, but parked off the homepage until the visual direction is approved.
`build_site.journal_home_page()` retains the complete previous composition as an
explicit render function, exercised in memory by the static preservation tests.
The capability notes below describe that preserved implementation, not features
loaded by the new homepage. No alternate public demo route is introduced.

For this proposal, use the ordinary public-font preview, **without**
`--private-fonts` (the evaluation stylesheet overrides heading fonts):

```sh
python3 tools/build_site.py
python3 tools/test_site.py
python3 tools/test_preview.py
python3 tools/test_atlas_retirement.py --static-only
python3 tools/serve.py --port 8774
# In a separate terminal, with the existing Playwright environment:
python tools/test_foundation.py --url http://127.0.0.1:8774 --browser webkit \
  --output /absolute/path/to/review-artifacts
```

`--browser` also supports Chromium (the default) and Firefox. The focused check
covers 320/390/820/1440/1600px, all twenty artwork/title/URL associations, decoded
resource resolution (not WebKit's density-corrected `naturalWidth`), native links,
focus, no-JS, reduced motion and emulated forced colors. It records real changed
pixels, exact paused frames, offscreen/visibility/page lifecycle suspension and
a sampled frame budget (p95 below 50ms in headless WebKit; no site JS frame loop).
Headless visibility is explicitly emulated; offscreen suspension uses real scroll.
It saves desktop/phone compositions, motion frames and machine-readable evidence.
`tools/test_navigation.py --url http://127.0.0.1:8774 --output /absolute/path`
checks the two exact destinations, active states, natural masthead/touch bounds,
sticky reading tools, native source focus and Back at seven widths.
Use `--home-only` for a homepage-only navigation change.
`tools/test_foundation.py --motion-only --output /absolute/path` isolates actual
remaining archive motion/frozen pixels and the frame budget without rerunning
the gallery suite. It does not require a homepage scene.
`tools/test_path_motion.py --url http://127.0.0.1:8774 --output /absolute/path`
adds 2,037 rendered-marker-to-visible-path samples across full cycles at all
seven widths, with a 1 CSS-pixel ceiling, independent carrier poses, forward
progression, loop seams and fixed-origin alignment. It also inspects native
SVG clocks, not only `document.getAnimations()`, through offscreen,
synthetic hidden events, media round trips, Back and no-JS. Inspection maps:
`[data-motion-follower]` names the visible route ID, `data-motion-start` records
its static first vertex, and `[data-motion-anchor]` names an axis path with a
`data-anchor-point`. Helpers require unique stable instance prefixes for IDs.
The older `test_home.py`, cover, hierarchy, signature and playground browser
suites describe the preserved interactive composition, **not** acceptance
criteria for this writing-gallery iteration. Static checks still exercise
its renderer, original reading plates, all essays, links and source assets.
The retained ribbon is now exercised in an in-memory browser fixture, not a
published route or a restored homepage hero. Live checks still exercise the
archive origins with the unchanged motion controller, not the removed home scene.
`tools/test_gallery_entrance.py --output /absolute/path` verifies the real archive
lead, role credit, original image ratios/resolution, responsive caption and
natural header scrolling/focus behavior without rerunning unrelated reader suites.
It also checks the four series artworks at their full ratios/decoded resolution,
display section hierarchy and primary/secondary 44px-plus action affordances.
`tools/test_series.py` checks authored membership/order, source-local evidence,
invalid/stale definitions, escaped output and member-only previous/next links.
`tools/test_archive.py --static-only --fixtures /absolute/path/to/fixtures`
checks the archive renderer and writes a test-only 21-row fixture outside the
published site. Run the same tool with `--browser-only`, the same `--fixtures`
and `--artifacts /absolute/path` in the existing WebKit environment for row
geometry, full-ratio decoded artwork, search/source/error/reset/compact/no-JS
and growth checks. No twenty-first essay is added to the corpus or public site.

## Source-linked article reader

Article detail pages use a centered 640px Newsreader measure on a quiet sage
surface, with an uncropped original frontispiece and its existing full-view
control. The spatial reference was
[Making Software's GPU chapter](https://www.makingsoftware.com/chapters/how-does-a-gpu-work);
its prose, proprietary fonts and book navigation are not copied. Home, archive
and their exact path-following motion are unchanged. Article-only decorative
motion is omitted so nothing moves behind prose or reading notes.

Article presentation uses one opening illustration. The explicitly reviewed
exception in `tools/article_art.py` promotes the complete wide illustration
`9fe1e028baa0.webp` in *How Future Designers Will Win in the Age of AI* to that
opening and omits only its former, uncaptioned leading-body occurrence.
The raw source and portrait metadata cover remain unchanged for archive,
homepage/series and sharing. Raw-source and image SHA256s, metadata identity,
and the exact anchorless opening shape must still match; changes fail for
review rather than silently removing a figure. This is not first-image or
duplicate-image detection. All seven captioned Cowork screenshots stay in place.
Lead dimensions, responsive resources and both full-view links follow the
rendered image, using the existing 640px/390px height-aware sizing.
`tools/test_article_art.py --static-only` audits the 20 leads plus seven supporting
images and exercises stale/changed-source guards. Its `--browser-only --artifacts
/absolute/path` mode checks image ratios/resolution/viewers at 390/1028/1440px
and the affected reader's guide/source/progress/Back/no-JS behavior.

`site/reader-detail.css` supplies the article-only composition. At 1280px and
wider, the left AI reading guide and right progress/AI notes are independent,
sticky grid children. Desktop rails are 188px
wide, with symmetrical 64px gutters at 1280px, 80px at 1440px and 96px at 1600px;
the centered prose remains 640px and sidebar type sizes are unchanged.
On narrower enhanced views, the controller moves those same nodes into a native
Guide & notes disclosure; it never duplicates their
contents or handlers. The mobile/tablet compact progress bar is opaque; the
main masthead remains transparent and scrolls away. Opened tools have their own
bounded scroll area.
Without JavaScript, both rails remain native, in-flow disclosures on narrow
screens and separate columns on desktop; enhancement-only controls are hidden.

All twenty companions in `content/reading-guides/` are explicitly AI-authored
supplements, not published author text or live/community comments. Their 141
sections, 268 concise bullets and 93 observations/questions are individually
source-linked. The active guide section reveals its points; readers can also
open another section manually. Notes follow the current section, with an
explicit empty state and a Show all AI notes option. Complete original headings,
section lengths, word lens, source connections and paragraph controls remain
under Explore the original text. Paragraph tools are also available on focus,
hover and native targets, without a permanent glyph beside every passage.

`tools/reading_guide.py` validates the exact version-1 schema, AI attribution,
raw-source SHA256, unique IDs, ordered original anchors and section-local
citations. Plain data is HTML-escaped. A normal build requires complete,
non-stale coverage; invalid or missing companions fail explicitly. To import
an already authored set, validate/copy it before the ordinary build:

```sh
python tools/import_reading_guides.py /absolute/path/to/authored-guides
python tools/build_site.py
python tools/test_reading_guides.py
python tools/test_reader_detail.py --url http://127.0.0.1:8774 \
  --output /absolute/path/to/reader-review
```

The browser test uses an existing Playwright WebKit runtime. It exercises all
twenty guides and source targets, seven widths from 320 to 1600px, separate rail
placement, body-only 0/mid/100 progress, keyboard/disclosure flows, native
fragments, Back, media, no-JS and idle-work bounds. The static check preserves
all 1,592 original anchored blocks, not just the 1,387 measured leaf passages.
`tools/test_browser.py` continues to cover the original optional reading lens,
archive search and photography viewer.

Reading progress measures scroll position within `#essay-body`, excluding the
arrival artwork/title, rails and footer; it makes no comprehension claim. The
companion uses coalesced event-driven updates, not idle polling, and performs no
model/network/corpus requests or web-storage writes. A namespaced
`history.state.readerPosition` is recorded only on page exit, preserving other
history state. On a history return, one guarded restoration after fonts and the
browser's return frame prevents WebKit from replacing manual reading position
with an old source fragment. It is cancelled by user input or suspension; fresh
fragment navigation stays native and no repeated corrective scrolling occurs.

## Preserved journal design

The internal-page shell is full-bleed paper, without an inset sheet, viewport
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
| `content/reading-guides/*.json` | Reviewed, source-hashed AI guide bullets and supplemental notes for all twenty essays. |
| `content/pages/*.html` | Preserved About, About the Memo, FAQ, report and store content. |
| `content/photograph-descriptions.json` | Descriptions of visible photographs, in original gallery order; not inferred locations or dates. |
| `content/research-example.json` | Public-data record schema and empty evidence register; no live ingestion. |
| `content/question-atlas.json` | Retired historical source-pair configuration; not imported or required by production builds. |
| `docs/assets/img/` | **Committed source image originals from the migration.** The builder reads these; do not delete this directory when rebuilding. |
| `site/` | Authored CSS, ES modules, favicon and fonts; copied to `docs/assets/` except the three explicitly retired atlas assets. |
| `site/suff-syed-signature.svg` | User-supplied, visually validated vector autograph; exact master paths, not a font or embedded raster. |
| `tools/corpus.py` | Deterministic passage extraction, word counts and lexical-neighbor ranking. |
| `tools/reading_guide.py`, `tools/import_reading_guides.py` | Strict companion validation, escaped rendering and validated set import. |
| `tools/build_site.py` | All routes, responsive images, searchable corpus, RSS and sitemap. |
| `tools/foundation_home.py`, `site/foundation.css` | Observatory homepage and curated artwork exhibition. |
| `tools/writing_frame.py`, `site/frame.css`, `site/writing.css`, `site/motion.js` | Shared writing frame, gallery/reading styles and bounded decorative motion. |
| `site/reader-detail.css`, `site/reader.js` | Centered article, responsive AI rails, body progress, history restoration and optional lexical reader. |
| `tools/foundation_art.py`, `site/foundation/` | Original line studies, deterministic grain generator and licensed homepage font/provenance. |
| `tools/journal_home.py`, `tools/journal_questions.py` | Opening artwork and local question/research instruments. |
| `tools/question_atlas.py`, `tools/retired_atlas_checks.py` | Dormant atlas implementation and historical checks, not current-site acceptance. |
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

The preserved journal composition opens with a personal identity cover: the signature, the supplied Microsoft role,
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
Module-reported action errors remain visible without discarding the editor or
last successful result; thrown mount/lifecycle failures tear down the instance.
The signature is suspended separately while the host is open, preserving its
own user-pause choice. Only loaded code and styles are retained between instances.
Each mount waits for the journal stylesheet, then reads and validates an immutable
six-color palette. It is never captured during early module evaluation: WebKit
can execute the host before that stylesheet has arrived. Invalid tokens prevent
mounting with an explicit diagnostic, and Retry reads the restored stylesheet
again rather than retaining bad colors.
The status footer has a reserved height so announcements cannot resize an active
drawing surface or change a composition. All tools scroll inside the cover when
space is tight; no full-screen modal or document scroll lock is used.

The experiment chrome is one 44px utility rail rather than a second journal
heading. Choose, Another and Close retain their native names and hit targets;
entry focuses the visible chooser. A hidden semantic heading still names the
region. The solid rail and 42px status footer protect text contrast from the
decorative field. Each experience now has its own composition, type and material.

| Experiment / world | What happens locally |
| --- | --- |
| Scratch terminal / phosphor workstation | Bounded drawing language, short-lived Worker, three examples, Run/Stop/Reset and line/column errors; never JavaScript or a shell. Phone Code/Drawing views keep the artifact large. |
| Ink studio / tactile drawing desk | Fountain/round nibs, pressure/velocity, erase, undo and PNG export. Tools holds nib/size/color and Clear; arrows and Space draw on the dominant paper. |
| Pocket darkroom / safelight contact print | Exposure, contrast, seeded grain and forest duotone alter only a visitor copy. Develop print exposes controls; original/edited comparison stays in reach. |
| Type garden / kinetic typography poster | Attract, repel or flow the autograph's glyphs on acid paper, then Re-form. This interactive canvas is the sole signature scene; Pause and reduced-motion Step remain. |
| Blackout poetry / cut-paper collage | Keep/remove words from a complete original paragraph with exact order and separators. A pinned visitor-remix slip stays visible; Tools holds brush/reset/source details. |
| Agent terrarium / nocturnal habitat | Seeded rule-based agents, editable food/walls and real Step/Run/Pause/Reset. Rules/World views expose parameters without presenting decorative trails as model results. |
| Assumption lab / scenario instrument | Dominant numerical ledger and calibrated inputs. Readout/Adjust views retain feedback on phones; invented constants, formulas and omissions remain explicit, not forecasts. |
| Sound loom / rhythm machine | Five pitches and eight tactile step keys; Tune/Keys switches views. Only Play creates audio; Stop, inactivity or Close closes it. Real played steps may pulse the backdrop. |
| Generative postcard / postal atelier | A raised print combines a real photograph, exact source sentence and attribution. Edit postcard reveals controls; New variation and PNG export leave originals untouched. |
| Signal / noise / pocket arcade | A seeded 60-second, eight-fragment game with bold clock and steering controls. The functional autograph reveal stays separate from decorative pixel fragments. |

Module CSS is the single source for eight `--pg-world-*` theme tokens and
`color-scheme`. Only that theme block also matches
`#cover-playground[data-world="<id>"]`; all other rules remain scoped to the
module's `[data-experience]` root. The host never has `data-experience`. World
colors do not replace the six semantic `context.palette` colors used for drawing,
image processing or exports. Module-local `--font-display` can select public or
native type without affecting the journal or importing private fonts.

`site/playground/scene-engine.js` and `scene-profiles.js` load only after entry.
Nine profiles use the unchanged autograph mask with code punctuation, dry-ink
stippling, halftones, real passage-word fragments, trails, pixel fragments,
rhythmic columns, coordinates or postal characters. Type garden owns its existing
interactive signature instead. Decorative layers are pointer-transparent,
`aria-hidden`, behind functional surfaces and absent from their exports.
`data-world-signature` identifies the layer; `data-scene-status` becomes `ready`
only after a real first paint or static preference treatment, and `failed` when
an explicit warning retains the already-loaded cover vector as fallback.

Optional `context.pulseSignature()` is backwards-compatible, inactive-safe and
coalesced: a response lasts 500ms, renders no faster than every 90ms, and cannot
restart within 1.1 seconds. Settled, hidden, offscreen and closed scenes schedule
no work. A scene caps at 3,000 cells, DPR 2 and 600,000 backing pixels; pending
image/font/import work is bounded and abortable. Forced colors use a static
system-color vector; reduced motion never starts the response loop.

Ink sheets cap strokes at 96, points per stroke at 900 and total points at 12,000.
The scratch interpreter caps input, syntax, loops and operations, with a 120 ms
execution budget and 1.5-second Worker watchdog; every run releases its Worker.
Canvases cap DPR at 2 and backing pixels at one million. Simulations cap cadence
at 30 fps; sound uses one bounded lookahead timer and at most three notes per
step. Nothing auto-downloads, uploads, records microphone audio or persists work.
The darkroom's optional local brush is not included; its four tonal controls and
original/edited comparison are complete.

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
index, loaded only when needed. Its compact list and theme filters remain useful
alternatives to the illustrated index. Default essays remain calm and complete;
the analytical layer is reversible and closing it removes all highlights.

## Local instruments and privacy

### Retired question atlas

The question atlas has been removed from the public site, including its home
teaser, archive index/map, research entry point and methods explanation. Nothing
replaces the graph. Old external archive fragments naturally open the ordinary
archive; the report's former Design-index link now uses the existing theme filter.
Ordinary questions, essay themes, genuine series navigation, AI reading guides,
notes and measured lexical connections are independent and remain available.

`content/question-atlas.json`, `tools/question_atlas.py`, and the three
`site/atlas*` assets remain historical source only. Production does not import
the implementation, read its configuration or require passage coverage or graph
topology validation when posts change. The builder excludes exactly `atlas.css`,
`atlas.js` and `atlas-map.js` from publishing and removes only those known stale
files under `docs/assets/`; it never cleans the original image directory.
`tools/retired_atlas_checks.py` is explicitly historical and refuses current-site
acceptance runs.

`tools/test_atlas_retirement.py --static-only` audits all public pages and tests
an isolated rebuild with atlas configuration reads/imports blocked and the three
stale assets seeded. Its `--browser-only --artifacts /absolute/path` mode checks
public page requests, the natural home ending and representative series/reader
navigation. The active archive tests retain the unpublished 21-row growth,
search, filters, compact/reset, source-link and no-JS checks without an atlas.

### Reader's Margin and research

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
  --require-all --artifacts /absolute/path/to/session-artifacts
.venv/bin/python tools/test_playground_integration.py \
  --artifacts /absolute/path/to/session-artifacts
.venv/bin/python tools/test_playground_scenes.py \
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
The integration runner performs real primary actions in every module through the
actual host at phone and desktop sizes: pixels, original text, downloads, model
values, simulation state and native audio construction/closure. `--ids` and
`--widths` bound an individual rerun. `--late-palette` delays the real journal
stylesheet response by two seconds without changing its contents; use it with
`--ids scratch-terminal pocket-darkroom` to replay the startup-color regression.
The host suite also checks delayed CSS and invalid-token recovery through Retry.
The scene suite uses route-only control fixtures with the real renderer to check
actual glyph pixels, cell/backing budgets, coalesced pulse cadence, zero settled
or offscreen work, Type exclusion, late imports and explicit static fallback.
World composition is checked separately against the actual modules, not fixtures.
The five `test_playground_<team>.py` suites
cover deeper module algorithms, budgets, failure/abort paths and resource release
using artifact-only loopback harnesses. Controlled PointerEvents validate stylus
pressure; clipboard success/denial tests avoid changing the system clipboard.
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
