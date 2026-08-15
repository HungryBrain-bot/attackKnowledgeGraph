---
name: red-team-assessment
description: "Use this skill whenever: (LLM lens) query/ask.py's entity extraction, query/rag.py's prompt construction or system prompt, or query/llm_provider.py changes (including adding a new provider); (code lens) requirements.txt gains a dependency, or code handling file paths/external input changes; (web lens) a new user-facing artifact is added or changed, or a new external data source is wired into any part of the project (a new visualization, a new file format, a new ingestion source). Also on an explicit request to run or extend the assessment. Runs real checks - adversarial LLM queries, static code review, generated-artifact inspection - no mocking, and logs every result to docs/security-assessment.md."
---

# Red Team Assessment

Formerly `ai-security-assessment` - renamed and broadened (2026-08-15) from
a single-lens LLM-injection check into a three-lens, project-wide red-team
skill, on explicit request. This is an expansion, not a rewrite: the LLM
lens below is the original skill's methodology, unchanged in scope, and
`docs/security-assessment.md` continues as the same single append-only log
for all three lenses rather than splitting into separate files - a
security finding is a security finding regardless of which lens caught it,
and one dated log keeps the project's full assessment history in one
place.

This project has three real classes of attack surface, and each grew a
lens here only once the project actually had something to test against
it - **LLM** (`query/`'s retrieval-then-generate pipeline, tested since the
project's first pass), **code** (Python across the whole repo - secrets,
unsafe execution, path handling, dependencies), and **web/frontend**
(`visualize/render_graph.py`'s generated HTML/JS, the project's first
artifact that renders in a browser, added 2026-08-15 alongside this
skill's broadening). A fourth lens is not being pre-emptively stubbed in -
add one only when the project grows a fourth real surface to test.

## Trigger conditions

Run the **LLM lens** whenever:
- `query/ask.py`'s entity extraction changes (how a technique ID or group
  gets pulled from free text).
- `query/rag.py`'s prompt construction or `SYSTEM_PROMPT`/
  `SYSTEM_PROMPT_TEMPLATE` changes - even a wording-only edit, since a
  reworded rule can silently change what an injection attempt can get
  away with.
- `query/llm_provider.py` gains a new provider (a new vendor's SDK/API
  shape can have different susceptibility to the same attack text).

Run the **code lens** whenever:
- `requirements.txt` gains a new dependency (check it for known
  vulnerabilities before it's relied on, not after).
- Code anywhere in the repo starts handling a path, filename, or command
  built even partly from external input (an API response, a file
  downloaded from the internet, a future ingestion source) - the pattern
  that matters, not one specific file.

Run the **web lens** whenever:
- `visualize/render_graph.py`'s HTML/JS generation changes - new content
  reaching a tooltip, label, attribute, or inline script.
- Any new artifact that renders in a browser is added to the project.

Run **all three, project-wide**, whenever:
- Any new user-facing artifact or new external data source is wired into
  any part of the project - a new visualization, a new file format, a new
  ingestion source down the line. This is deliberately broader than "the
  LLM prompt path": the project's actual attack surface has already grown
  past that once (the web lens exists because `visualize/render_graph.py`
  did), and the trigger condition should describe the general pattern
  ("something new that renders untrusted-enough content, or reads from
  somewhere less trusted"), not enumerate today's specific files as if
  they're the only ones that will ever matter.
- An explicit request from the user to run or extend the assessment.

It is **not** triggered by changes to `graph/semantic_edges.py`,
`graph/build_graph.py`, or the docs/attack-patterns case files on their
own - those don't touch any of the three lenses' surfaces by themselves.

## Lens 1: LLM security

Unchanged in scope from the original `ai-security-assessment` skill.
Grounded in the [OWASP Top 10 for LLM Applications (2025)](https://genai.owasp.org/llm-top-10/).

### In scope for this pipeline

- **LLM01 Prompt Injection** - primary focus. This pipeline concatenates
  (or, post-ADR-005, role-separates) retrieved facts and the user's raw
  question before sending them to the model - the core injection
  surface. Test both instruction-shaped attacks (override/ignore
  previous instructions) and data-shaped attacks (text formatted to look
  like a real fact, citation, or edge).
- **LLM09 Misinformation** - primary focus, and the reason LLM01 matters
  *here* specifically: this project's entire credibility rests on
  CLAUDE.md's "no invented data" convention. A successful injection that
  gets a fabricated fact cited back in a plausible-sounding, correctly-
  formatted answer is this project's worst-case failure mode, not a
  generic annoyance.
- **LLM07 System Prompt Leakage** - directly tested by the "system-prompt
  extraction" case category. Currently low-severity for this project
  specifically (`SYSTEM_PROMPT_TEMPLATE` holds no secrets and already
  lives in the public repo), but still tested because (a) it's cheap to
  test alongside the other two categories and (b) disclosure is
  reconnaissance value for tuning a Finding-1-style injection payload -
  see docs/security-assessment.md's 2026-08-13 Finding 3.

### Considered, genuinely out of scope for this pipeline right now

Documented here - not just "not tested" - so a future pass doesn't
force-fit a test that doesn't apply, and so "out of scope" reads as a
reasoned decision, not an oversight:

- **LLM02 Sensitive Information Disclosure** - the graph's facts are all
  public CTI report content, hand-cited from real sources; nothing
  sensitive is in the retrieval path. Would become relevant if a
  private/internal-only case study or credential-like data were ever
  added to the graph.
- **LLM03 Supply Chain** - this is the LLM-specific slice of what the
  code lens's dependency check covers more generally now (provider SDKs
  included) - see Lens 2, below.
- **LLM04 Data and Model Poisoning** - no training or fine-tuning happens
  anywhere in this project. The graph's own data-integrity discipline
  (citations, confidence scores, no invented edges) is already governed
  by the project's sourcing conventions, not an LLM-poisoning attack
  surface in the OWASP sense.
- **LLM05 Improper Output Handling** - `query/ask.py` only ever prints
  the answer to a terminal. Would become directly relevant the moment any
  future output path renders the answer as HTML/markdown in a browser or
  feeds it into another system call - at which point it's really the web
  lens's concern (Lens 3), not this one's.
- **LLM06 Excessive Agency** - this pipeline has no tool calls and no
  ability to take actions; it returns text. Would become relevant only
  if the query layer gained tool-use/function-calling.
- **LLM08 Vector and Embedding Weaknesses** - retrieval is deterministic
  NetworkX graph traversal (see docs/decisions/003-query-layer-scope.md),
  not similarity search over embeddings. Not applicable by construction.
- **LLM10 Unbounded Consumption** - a plausible future concern (unbounded
  prompt length, repeated-call cost/DoS) but this is a single-user,
  non-production prototype with no exposed service and no rate-limiting
  scoped in. Worth a real look only if this ever becomes a publicly
  reachable service.

### Adding a new adversarial test case

Test cases live in `tests/test_adversarial_queries.py`. Pattern:

- **Input -> assert against the real response, not a mocked one.** These
  tests call the actual configured LLM provider end-to-end - no
  `unittest.mock` on `LLMProvider.generate()` or the provider SDKs. A
  mocked LLM can't tell you whether a real model resists a real attack;
  that would make the test measure nothing. This makes the suite slow,
  non-deterministic, and cost real API tokens - an accepted tradeoff for
  a security assessment, not something to "fix" by mocking later.
- Skips (doesn't fail) if no LLM provider credentials are configured,
  same pattern as `tests/test_query_layer_against_evtx.py`'s data-
  dependent skip - a fresh clone with no `.env` shouldn't see red.
- A **regression case** (a previously-broken finding, now fixed) gets a
  real assertion against the fixed behavior - e.g.
  `test_fact_injection_is_rejected` asserts the specific `RuntimeError`
  from `_check_no_ungrounded_techniques` is raised for the exact question
  that used to produce a fabricated citation.
- A **novel/exploratory case** (new attack pattern, not yet resolved to a
  pass/fail fix) still gets written as a real test, but document its
  finding honestly in `docs/security-assessment.md` even if that means
  reporting "no assertion added yet, still a known gap" - don't write an
  assertion that happens to pass today just to make the suite green if
  the underlying behavior wasn't actually verified as safe.

High-stakes judgment calls specific to this lens - deciding whether an
injection/extraction attempt actually succeeded, since a wrong call here
either misses a real hole or wastes effort chasing a non-issue - go
through Opus, per CLAUDE.md's Model Usage convention. Feed the reviewer
the exact question, the exact retrieved facts, and the exact model
response; ask for a verdict argued from the transcript, not a general
impression.

## Lens 2: Code security

Static review of the Python codebase, run for real against the actual
repo - grep-based pattern checks plus a real dependency-vulnerability
scan, not a checklist eyeballed from memory. Covers:

- **Hardcoded secrets or keys** - grep for API-key/password/token-shaped
  assignments across the repo (excluding `.venv/`, `data/raw/`, `.git/`);
  confirm `.env` is gitignored and not tracked.
- **Unsafe deserialization** - `eval`/`exec`/`pickle.load(s)`/unsafe
  `yaml.load` anywhere in the codebase.
- **Path traversal** - anywhere a filesystem path is built using a name
  or path fragment that originates outside the codebase (an API
  response, a downloaded file's reported name, a future ingestion
  source's filename) - confirm it's validated as a plain leaf name before
  being joined onto a local path, not merely assumed safe because the
  upstream source is trusted today. See docs/security-assessment.md's
  2026-08-15 entry for a real example (`fetch_test_logs.py`) and its fix.
- **Injection risks (SQL/command/etc.)** - `subprocess`/`os.system`/
  `os.popen` calls, and any database query built via string
  concatenation or an f-string instead of parameterization. **Run this
  check every pass even though this project has no database and no shell
  invocation today** - the point of keeping it in the lens is that it
  doesn't silently stop being checked the day the codebase grows one, the
  same reasoning Lens 1 already applies to documenting genuinely-
  inapplicable OWASP categories as a reasoned decision rather than a
  silent skip.
- **Dependency vulnerabilities** - run a real vulnerability scanner (e.g.
  `pip-audit -r requirements.txt`) against the resolved dependency set,
  not just the top-level pins in `requirements.txt` - transitive
  dependencies carry CVEs too. Record the tool, its version, and the
  exact result (clean, or which packages and advisories) - never assert
  "dependencies are fine" without having actually run something.

## Lens 3: Web/frontend security

Any artifact in this project that renders in a browser -
`docs/graph_visualization.html`, and any future one - gets checked for
XSS and unsafe HTML/JS-injection risk. The methodology here is
specifically **verify the actual rendering mechanism in the generated
output, never assume it from memory of how a library "usually" works** -
this lens exists because the project's first real finding under it came
from exactly that mistake (see docs/security-assessment.md's 2026-08-15
entry: a tooltip bug was originally built assuming vis-network renders
string `title`s via `innerHTML`, when the bundled source actually uses
`innerText` - the opposite assumption would have been a real XSS hole
instead of a display bug).

For every place data reaches HTML/JS output, identify which of these
contexts it actually lands in - each has a different, sometimes
counter-intuitive safety story, and getting the context wrong is the
recurring failure mode this lens exists to catch:

- **Canvas-rendered text** (e.g. vis-network node/edge labels, drawn via
  `fillText`/`strokeText`) - immune to HTML/script injection by
  construction; pixel rendering never parses its input as markup. Worth
  confirming directly in the bundled/generated source (grep for
  `fillText`), not assumed.
- **`element.innerText = value`** - also immune to injection (never
  parses input as HTML), but *requires* the opposite of HTML-escaping:
  escaping content meant for this context actively breaks it (see the
  `<br>` finding). Real newlines (`\n`), not `<br>`, are what render as
  line breaks here.
- **`element.innerHTML = value`** or raw string concatenation into page
  markup - a real HTML-injection context; content here must be
  HTML-escaped (`html.escape()` or equivalent) before insertion.
- **An inline event-handler attribute containing a nested JS string**
  (`onclick="fn('{value}')"`) - the trap: HTML-escaping `value` for the
  *attribute* is necessary but **not sufficient**, because the browser
  HTML-decodes the attribute's text before handing it to the JS parser -
  an escaped quote decodes back to a literal quote that closes the JS
  string early, and content after it becomes executable JS. Verified for
  real in this project (see docs/security-assessment.md's 2026-08-15
  entry) and fixed by not building JS source from data at all: pass data
  via a plain `data-*` attribute and read it with `.dataset.x` /
  `addEventListener` in real JS instead of interpolating it into an
  inline handler string.

Verify claims about all of the above empirically against the real
generated file (grep the bundled/output source for the actual rendering
call, script a DOM assertion in headless Chrome) rather than reasoning
from documentation or memory - this lens's whole premise is that the
memory-based assumption is exactly what goes wrong.

## What "done" looks like for one assessment pass

Every test run gets a dated entry in `docs/security-assessment.md`
(append-only - a new pass is a new dated `##` section, never an
overwrite of a prior one), regardless of which lens(es) it covers. For
every individual finding within a pass, the entry states:
1. **What was checked** - the exact input/check, and which lens.
2. **The actual result** - quoted or shown, not summarized into "it
   worked" or "it didn't" - the reader should be able to judge the
   verdict themselves.
3. **Held/clean or broke** - an explicit verdict, argued from the
   evidence, not asserted.
4. **If broken**: either the fix applied, with its own ADR under
   `docs/decisions/` if it's architecturally significant (per the
   build-and-document skill), and the case re-verified against the fixed
   code for real to confirm it now holds - or an explicit "known gap, not
   yet fixed" note if a fix isn't done this pass. **Never silently drop a
   failing check from the log** - a documented, unfixed gap is honest; a
   disappeared finding is not.

## Do NOT

- Don't mock the LLM call in a Lens-1 adversarial test - this defeats the
  entire point of that lens.
- Don't overwrite a prior dated entry in `docs/security-assessment.md` -
  it's a log, not a living status doc; append a new dated section
  instead, even if a later pass re-tests the same finding.
- Don't force-fit a Lens-1 test for an OWASP category this pipeline's
  current design makes inapplicable (see "genuinely out of scope" above)
  just to look more thorough - document the reasoning instead. The same
  applies to Lens 2/3 checks that don't currently apply (no database, no
  other browser-rendered artifact yet) - keep the check present and run
  it, but report "not applicable, here's why" rather than skip it
  silently.
- Don't paper over a real, verified break with a reworded prompt or a
  narrower escape rule alone. If the finding points at a structural issue
  (untrusted input and trusted data sharing one undifferentiated prompt
  string; a JS-source-from-data pattern that's unsafe regardless of how
  carefully the data is escaped), the fix has to be structural too - see
  docs/decisions/005-prompt-injection-fact-separation.md and the 2026-08-
  15 web-lens finding for what that looked like.
- Don't assume a rendering/escaping mechanism from memory or
  documentation - verify it against the real generated output, per Lens
  3's methodology above. This project has one real, on-the-record
  instance of getting this backwards (the `<br>`/`innerText` bug).
- Don't claim a dependency scan happened without having actually run a
  real tool (Lens 2) - "no known vulnerabilities" is a specific, sourced
  claim (tool + version + what was scanned), not a default assumption.
