"""Server-rendered journal surfaces; no network access or runtime dependencies.

render_margin() -> section HTML, once per page.
render_research(rows=None) -> body fragment for the layout's /research/ main.
render_research_teaser() -> section HTML linking to /research/.

rows may be an iterable of essay dictionaries, or a corpus dictionary containing
"essays". Only the title of the known starting-essay slug is used, as escaped text.
The owning layout supplies journal.css, questions.css and questions.js.

Stable browser hooks (independent of the owning layout's body.js flag):
- [data-reader-margin][data-margin-ready="true"] signals initialized axes.
- [data-margin-axis] contains input[type=range], [data-margin-output],
  [data-margin-middle], and [data-margin-clear]; [data-margin-reset] clears all.
- [data-margin-notice] exposes storage errors; the root sets
  data-storage-problem="true". Storage key: suff-journal-reader-marks-v1.
- [data-research-study][data-research-ready="true"] signals initialization;
  data-research-state is idle, running, paused, or complete.
- [data-research-start], [data-research-pause], [data-research-resume],
  [data-research-step], [data-research-reset] are the playback controls.
- [data-research-status], [data-research-log], [data-research-artifact], and
  [data-research-result-link] expose the log and outcome; #research-sample
  is the resulting sample's stable anchor.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from html import escape


SOURCE_SLUG = "qubit-teams-the-future-built-by-two-people-using-ai"
SOURCE_URL = f"/futurememo/{SOURCE_SLUG}/"
SOURCE_TITLE = "Qubit Teams: The Future Built by Two"

READER_AXES = (
    (
        "The value of making",
        "When making gets easier, what becomes valuable?",
        "Judgment",
        "Execution",
        "blue",
    ),
    (
        "The scale of capability",
        "Where will the next important thing come from?",
        "An individual",
        "An institution",
        "orange",
    ),
    (
        "The cost of convenience",
        "What should intelligence give us more of?",
        "Understanding",
        "Speed",
        "teal",
    ),
)


def render_margin() -> str:
    """Three optional local reader axes, with no marks or enabled controls."""
    panels = []
    for index, (topic, question, top, bottom, pigment) in enumerate(READER_AXES):
        panels.append(f"""
        <section class="margin-axis margin-axis--{pigment}" data-margin-axis
                 data-top="{escape(top)}" data-bottom="{escape(bottom)}"
                 aria-labelledby="margin-question-{index}">
          <p class="question-label">{escape(topic)}</p>
          <h3 id="margin-question-{index}">{escape(question)}</h3>
          <div class="margin-instrument">
            <span class="margin-pole" id="margin-top-{index}">{escape(top)}</span>
            <div class="margin-track">
              <span class="margin-tick" aria-hidden="true"></span>
              <span class="margin-tick" aria-hidden="true"></span>
              <span class="margin-tick" aria-hidden="true"></span>
              <input type="range" min="0" max="100" step="1" value="50"
                     id="margin-range-{index}" data-margin-control hidden
                     aria-labelledby="margin-question-{index}"
                     aria-describedby="margin-instructions margin-scale-{index}"
                     aria-orientation="vertical" aria-valuetext="No mark placed">
            </div>
            <span class="margin-pole" id="margin-bottom-{index}">{escape(bottom)}</span>
          </div>
          <p class="question-sr-only" id="margin-scale-{index}">
            Higher values favor {escape(top)}; lower values favor {escape(bottom)}.
          </p>
          <output for="margin-range-{index}" data-margin-output aria-live="polite"
                  class="margin-value">No mark placed</output>
          <div class="margin-axis-actions" data-margin-control hidden>
            <button type="button" class="question-link-button" data-margin-middle>
              Place a middle mark
            </button>
            <button type="button" class="question-link-button" data-margin-clear
                    aria-label="Clear mark: {escape(topic)}" disabled>Clear</button>
          </div>
        </section>""")
    return f"""
    <section class="reader-margin" id="readers-margin" data-reader-margin
             aria-labelledby="margin-title">
      <header class="margin-heading">
        <div><p class="question-label">Reader’s margin / an invitation</p>
          <h2 id="margin-title">Where do you find yourself?</h2></div>
        <p>These questions have no correct position. Leave a mark, move it,
          change your mind. Or leave the page untouched.</p>
      </header>
      <p class="margin-instructions" id="margin-instructions">
        Each axis is optional. Your first mark opts into saving these positions in
        this browser only, not a live poll. Nothing is uploaded.
        With controls enabled, touch an axis or use its arrow keys; Home and End
        reach the poles. A middle mark is a choice, not a default.
      </p>
      <p class="question-nojs" data-margin-fallback>
        The questions are here to read without JavaScript. Local marking controls
        appear only when the interaction is available.
      </p>
      <div class="margin-axes">{"".join(panels)}</div>
      <footer class="margin-foot">
        <p data-margin-notice role="status" aria-live="polite">
          No marks have been placed. No storage is written until you make a mark.
        </p>
        <button type="button" class="question-link-button" data-margin-reset
                data-margin-control hidden>Clear all my marks</button>
      </footer>
    </section>"""


def _starting_title(rows: Iterable[Mapping] | Mapping | None) -> str:
    if isinstance(rows, Mapping):
        rows = rows.get("essays", ())
    if not isinstance(rows, Iterable) or isinstance(rows, (str, bytes)):
        return SOURCE_TITLE
    for row in rows:
        if not isinstance(row, Mapping) or row.get("slug") != SOURCE_SLUG:
            continue
        title = row.get("title")
        if isinstance(title, str) and title.strip():
            return title.strip()
    return SOURCE_TITLE


def _role_mark(role: str) -> str:
    """Original static line studies: a lens, a section, and a braided orbit."""
    if role == "scout":
        drawing = """
          <circle cx="48" cy="48" r="31"/><circle cx="48" cy="48" r="25"/>
          <ellipse cx="48" cy="48" rx="14" ry="31" transform="rotate(28 48 48)"/>
          <path d="M17 48h62M48 17v62M26 26l44 44M25 70l45-45"/>
          <circle class="role-pigment" cx="48" cy="48" r="10"/>
          <circle cx="48" cy="48" r="4"/>
          <path d="M8 48h5m70 0h5M48 8v5m0 70v5"/>
        """
    elif role == "skeptic":
        drawing = """
          <path d="M17 67 48 15 79 67ZM24 67l24-41 24 41M31 67l17-29 17 29"/>
          <path d="M11 76h74M21 80v-8m9 6v-4m9 6v-8m9 6v-4m9 6v-4m9 6v-8m9 6v-4"/>
          <circle class="role-pigment" cx="48" cy="52" r="11"/>
          <path d="M9 52h24m30 0h24M48 10v9m0 48v19"/>
          <path d="m39 49 18 6m-18 1 18-8"/>
        """
    else:
        drawing = """
          <ellipse cx="48" cy="48" rx="33" ry="14" transform="rotate(-35 48 48)"/>
          <ellipse cx="48" cy="48" rx="33" ry="14" transform="rotate(35 48 48)"/>
          <ellipse cx="48" cy="48" rx="33" ry="14" transform="rotate(90 48 48)"/>
          <circle cx="48" cy="48" r="30" stroke-dasharray="1 5"/>
          <circle class="role-pigment" cx="48" cy="48" r="9"/>
          <path d="M44 48h8m-4-4v8M9 48h7m64 0h7M48 9v7m0 64v7"/>
          <circle cx="23" cy="30" r="3"/><circle cx="73" cy="65" r="3"/>
        """
    return (
        f'<svg class="role-mark role-mark--{role}" viewBox="0 0 96 96" '
        'aria-hidden="true" focusable="false" fill="none">'
        f'<g stroke-width=".85">{drawing}</g></svg>'
    )


def render_research_teaser() -> str:
    """A home-page invitation; the actual study lives at /research/."""
    return f"""
    <section class="research-teaser" aria-labelledby="research-teaser-title">
      <div><p class="question-label">A proposed research practice</p>
        <h2 id="research-teaser-title">The unfinished.</h2></div>
      <div class="teaser-roles" aria-hidden="true">
        {_role_mark("scout")}{_role_mark("skeptic")}{_role_mark("synthesist")}
      </div>
      <div><p>A possibility, a counterpoint, a better question.
        Follow one authored example—not live agents or new findings.</p>
        <a href="/research/">Open the research notebook ↗</a></div>
    </section>"""


def render_research(rows: Iterable[Mapping] | Mapping | None = None) -> str:
    """Dedicated research body fragment; rows supply a known essay title only."""
    title = escape(_starting_title(rows))
    return f"""
    <div class="research-page" data-research-study>
      <header class="research-opening">
        <p class="question-label">The research notebook / an authored demonstration</p>
        <h1>The unfinished.</h1>
        <div class="research-dek">
          <p>A good essay leaves something unresolved. This is a place to stay
            with the question a little longer.</p>
          <p>Three roles, one small inquiry. A deliberately authored simulation:
            no live agents, external research, credentials, or background jobs.
            Nothing here is a new finding.</p>
        </div>
      </header>

      <section class="research-questions" aria-labelledby="open-questions-title">
        <div class="research-side">
          <p class="question-label">01 / Questions still open</p>
          <h2 id="open-questions-title">What would change<br> our minds?</h2>
          <p>Questions to investigate, not a queue of work being performed.</p>
        </div>
        <ol class="open-questions">
          <li><span class="question-label">Capability</span>
            <h3>What happens after the impressive first demo?</h3>
            <p>Can a two-person AI-assisted team maintain a product when the
              work shifts from making to repairing, supporting, and deciding?</p></li>
          <li><span class="question-label">Judgment</span>
            <h3>When output gets cheaper, where does expertise show up?</h3>
            <p>What would distinguish a well-chosen problem from a well-produced
              answer to the wrong one?</p></li>
          <li><span class="question-label">Accountability</span>
            <h3>Whose work disappears from the picture?</h3>
            <p>How should a claim about small-team capability count platform
              labor, borrowed infrastructure, and people outside the team?</p></li>
        </ol>
      </section>

      <section class="research-cycle" aria-labelledby="cycle-title">
        <header class="research-cycle-heading">
          <div><p class="question-label">02 / A worked example</p>
            <h2 id="cycle-title">One question, three ways of looking.</h2></div>
          <p>Starting position: <a href="{SOURCE_URL}">{title}</a>.
            An essay is an argument to examine, not empirical evidence.</p>
        </header>
        <div class="research-roles" aria-label="Authored research roles">
          <section class="study-role" data-research-role>
            {_role_mark("scout")}
            <p class="question-label">I / Possibility</p>
            <h3>The scout</h3>
            <p>Find the claim worth testing. Separate what an essay proposes
              from what it can establish.</p>
          </section>
          <section class="study-role" data-research-role>
            {_role_mark("skeptic")}
            <p class="question-label">II / Counterpoint</p>
            <h3>The skeptic</h3>
            <p>Look for the missing denominator. Ask what the attractive
              explanation leaves outside the frame.</p>
          </section>
          <section class="study-role" data-research-role>
            {_role_mark("synthesist")}
            <p class="question-label">III / Next question</p>
            <h3>The synthesist</h3>
            <p>Keep the uncertainty. Turn the disagreement into a question
              that evidence could actually answer.</p>
          </section>
        </div>
        <div class="research-observation">
          <div class="research-side">
            <p class="question-label">Milestones / authored sequence</p>
            <ol class="research-milestones">
              <li data-research-milestone>Frame a testable claim
                <span data-milestone-state>Not started</span></li>
              <li data-research-milestone>Expose an assumption
                <span data-milestone-state>Not started</span></li>
              <li data-research-milestone>Leave an investigation brief
                <span data-milestone-state>Not started</span></li>
            </ol>
          </div>
          <div class="research-notebook">
            <p class="question-label">Observe the reasoning, not a live feed</p>
            <p class="question-nojs" data-research-fallback>
              The complete authored sample is readable below without JavaScript.
              Interactive controls, when available, reveal three fixed stages.
            </p>
            <div class="research-controls" data-research-controls hidden>
              <button type="button" data-research-start>Start cycle</button>
              <button type="button" data-research-pause disabled>Pause</button>
              <button type="button" data-research-resume disabled>Resume</button>
              <button type="button" data-research-step>Next step</button>
              <button type="button" class="question-link-button" data-research-reset>Reset</button>
            </div>
            <p class="research-playback-note" data-research-playback>
              Three predetermined stages, about two seconds each. No network
              requests. Step through at your own pace instead.
            </p>
            <p class="research-status" data-research-status role="status"
               aria-live="polite" aria-atomic="true">The demonstration has not started.</p>
            <p class="research-empty" data-research-empty>
              No observations yet. No evidence has been collected.
            </p>
            <ol class="research-log" aria-label="Authored observation log">
              <li data-research-log hidden
                  data-summary="The scout separates a possibility from a finding.">
                <p class="question-label">01 / Scout / authored note</p>
                <h3>Make the claim small enough to test.</h3>
                <p>The essay proposes that AI could expand a very small team’s
                  capabilities. For this example, narrow the inquiry to one
                  product’s maintenance after launch—not every kind of work.</p>
              </li>
              <li data-research-log hidden
                  data-summary="The skeptic identifies work the team-size claim might omit.">
                <p class="question-label">02 / Skeptic / authored note</p>
                <h3>Count the work beyond the demo.</h3>
                <p>A fast launch would not by itself establish durable capability.
                  Support, incidents, vendor services, and help from other people
                  could change the story. These are possible confounders, not
                  observed failures of a particular team.</p>
              </li>
              <li data-research-log hidden
                  data-summary="The synthesist leaves a study proposal, not a conclusion.">
                <p class="question-label">03 / Synthesist / authored note</p>
                <h3>Trade a sweeping claim for a better question.</h3>
                <p>Ask what two people can sustain over time, under what conditions,
                  and with whose help. The resulting sample brief names what to
                  look for, without pretending the study has happened.</p>
              </li>
            </ol>
            <a class="research-result-link" href="#research-sample"
               data-research-result-link hidden>Read the resulting sample ↓</a>
          </div>
        </div>
      </section>

      <article class="research-artifact" id="research-sample" data-research-artifact
               aria-labelledby="sample-title">
        <div class="research-side">
          <p class="question-label">03 / Resulting sample artifact</p>
          <p class="artifact-stamp">Authored simulation<br>Unreviewed study proposal</p>
          <p>No participants, measurements, external evidence, or research
            results are represented here.</p>
        </div>
        <div class="artifact-body">
          <h2 id="sample-title">Beyond the first impressive demo.</h2>
          <p class="artifact-question"><span class="question-label">Explicit question</span>
            Under what conditions can a two-person AI-assisted team sustain
            a product after launch without shifting uncounted work to others?</p>
          <dl>
            <div><dt>Proposed next investigation</dt>
              <dd>Follow consenting teams from launch through a defined maintenance
                period. Document product scope, prior experience, AI use, external
                help, and responsibilities before comparing outcomes.</dd></div>
            <div><dt>Potential evidence needed</dt>
              <dd>Dated maintenance and incident records; support and contractor
                hours; changes in product scope; interviews with the people doing
                the work; and a comparison group with similar responsibilities.
                Include stalled or abandoned projects, not just successes.</dd></div>
            <div><dt>Limitation</dt>
              <dd>This brief is authored in advance from a single essay’s premise.
                No sources have been gathered and no teams studied. Even a future
                comparison could be confounded by experience, product complexity,
                selection bias, or unrecorded help. It would not alone prove that
                AI caused any difference.</dd></div>
            <div><dt>What could change the question?</dt>
              <dd>If maintenance depends mainly on scope and outside support rather
                than headcount, study those conditions instead of treating “two
                people” as the explanation.</dd></div>
          </dl>
          <p class="artifact-source">Original starting essay:
            <a href="{SOURCE_URL}">{title} ↗</a></p>
        </div>
      </article>

      <section class="research-method" aria-labelledby="method-title">
        <div class="research-side">
          <p class="question-label">04 / Method &amp; boundaries</p>
          <h2 id="method-title">What this is.<br> What it is not.</h2>
        </div>
        <div>
          <p>Every role, note, milestone, and sample paragraph is authored and
            committed with the site. Start reveals those same notes in order;
            Pause holds your place, Resume continues, and Reset returns to an
            empty notebook. Switching away pauses playback until you resume.
            Reduced-motion preferences use one step at a time.</p>
          <p>The cycle does not run models, search the web, collect credentials,
            or call external services. Its state lasts only for this page visit.
            The role illustrations are original static line studies, not data
            visualizations or indicators of live activity.</p>
          <h3>Public evidence register: empty.</h3>
          <p>No public-data records have been ingested. A committed boundary in
            <code>content/research-example.json</code> describes a possible
            manually reviewed record: source URL, source title, retrieval timestamp,
            and a plain-text excerpt. It is documentation, not an active importer.
            A source’s provenance would not establish its reliability.</p>
          <p>Any future source record would need validation and editorial review
            before publication. No arbitrary HTML, hidden network access, or
            automated research jobs are part of this demonstration.</p>
        </div>
      </section>
    </div>"""
