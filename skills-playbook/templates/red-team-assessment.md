---
name: red-team-assessment
description: "Use this skill whenever: (LLM lens) [PLACEHOLDER: your prompt-construction/entity-extraction/provider code] changes; (code lens) a dependency is added, or code handling file paths/external input changes; (web lens) a new user-facing artifact is added or changed, or a new external data source is wired in. Also on an explicit request to run or extend the assessment. Runs real checks - no mocking - and logs every result to a single append-only findings log."
---

# Red Team Assessment

A project's real attack surface grows one piece at a time, and a
security-assessment skill should grow with it - not be stubbed out with
every lens a project *might* eventually need. This template generalizes
a three-lens pattern (LLM/AI-interaction, code, web/frontend) that each
grew a lens only once the project actually had something real to test
against it. **Add a lens only when your project grows a real surface for
it; don't pre-emptively stub one in.** [PLACEHOLDER: if your project has
a fourth real surface this doesn't cover - e.g. a mobile client, a CLI
with elevated-privilege operations - add a fourth lens the same way: only
once it's real.]

## Trigger conditions

Run the **[PLACEHOLDER: e.g. "LLM"]** lens whenever:
- [PLACEHOLDER: your prompt-construction code, or the equivalent
  "untrusted input reaches a probabilistic system" surface] changes -
  even a wording-only edit, since a reworded rule can silently change
  what an attack can get away with.
- [PLACEHOLDER: your provider abstraction] gains a new backend (a new
  vendor/model can have different susceptibility to the same attack
  text).

Run the **code** lens whenever:
- A dependency file gains a new package (check it for known
  vulnerabilities before it's relied on, not after).
- Code anywhere in the repo starts handling a path, filename, or command
  built even partly from external input (an API response, a downloaded
  file's reported name, any future ingestion source) - the pattern that
  matters, not one specific file.

Run the **web/frontend** lens whenever:
- Any generated HTML/JS output changes - new content reaching a
  tooltip, label, attribute, or inline script.
- Any new artifact that renders in a browser is added.

Run **all lenses, project-wide**, whenever:
- Any new user-facing artifact or new external data source is wired into
  any part of the project - deliberately broader than any one lens's
  specific files, since the point is "something new that renders
  untrusted-enough content, or reads from somewhere less trusted," not
  an enumeration of today's specific files as if they're the only ones
  that will ever matter.
- An explicit request to run or extend the assessment.

## Lens 1: [PLACEHOLDER - your AI/LLM interaction surface] security

Ground this in a real, current framework rather than inventing your own
checklist - e.g. the [OWASP Top 10 for LLM Applications](https://genai.owasp.org/llm-top-10/)
if your project has an LLM in the loop. For each category:

- **State explicitly which categories are in scope for THIS pipeline**
  (e.g. prompt injection, if untrusted input and instructions share any
  part of the same prompt) **and which are genuinely out of scope, with
  a reasoned "why," not just "not tested."** Document the out-of-scope
  ones as a reasoned decision (e.g. "no training/fine-tuning happens
  anywhere in this project, so data-poisoning categories don't apply")
  so a future pass doesn't force-fit a test that doesn't apply, and so
  "out of scope" reads as a decision, not an oversight.
- **Test cases call the real system end-to-end, never mocked.** A
  mocked LLM/model call can't tell you whether a real model resists a
  real attack - that defeats the entire point of this lens. Accept that
  this makes the suite slow, non-deterministic, and cost real API
  tokens; that's the tradeoff, not a bug to fix by mocking later.
- **A regression case** (a previously-broken finding, now fixed) gets a
  real, permanent assertion against the fixed behavior.
- **A novel/exploratory case** (new attack pattern, not yet resolved)
  still gets written as a real test, but its finding is reported
  honestly even if that means "no assertion added yet, still a known
  gap" - never write an assertion that happens to pass today without
  the underlying behavior actually being verified safe.
- [PLACEHOLDER: if a judgment call here is genuinely high-stakes - e.g.
  deciding whether an attack actually succeeded - route it through a
  stronger/more careful model reviewer per your project's own
  model-usage-tiering convention (see that template), fed the exact
  transcript, not a summary.]

## Lens 2: Code security

Static review, run for real against the actual repo - pattern checks
plus a real dependency-vulnerability scan, not a checklist eyeballed
from memory:

- **Hardcoded secrets or keys** - grep for API-key/password/token-shaped
  assignments across the repo; confirm your secrets file is gitignored
  and not tracked.
- **Unsafe deserialization** - `eval`/`exec`/`pickle.load(s)`/unsafe
  YAML loading anywhere.
- **Path traversal** - anywhere a filesystem path is built using a name
  that originates outside the codebase; confirm it's validated as a
  plain leaf name before being joined onto a local path, not merely
  assumed safe because the upstream source is trusted today.
- **Injection risks (SQL/command/etc.)** - shell-invocation calls, and
  any query built via string concatenation instead of parameterization.
  **Run this check every pass even if the project has neither today** -
  the point is that it doesn't silently stop being checked the day the
  codebase grows one.
- **Dependency vulnerabilities** - run a real vulnerability scanner
  (e.g. `pip-audit`, `npm audit`, or your ecosystem's equivalent)
  against the resolved dependency set, not just top-level pins. Record
  the tool, its version, and the exact result - never assert
  "dependencies are fine" without having actually run something.

## Lens 3: Web/frontend security

Any artifact that renders in a browser gets checked for XSS/unsafe
HTML-JS-injection risk. **The methodology here is specifically: verify
the actual rendering mechanism in the generated output, never assume it
from memory of how a library "usually" works.** For every place data
reaches HTML/JS output, identify which context it actually lands in -
each has a different, sometimes counter-intuitive safety story:

- **Canvas-rendered text** (`fillText`/`strokeText`) - immune to
  injection by construction; confirm this directly in the generated
  source rather than assuming.
- **`element.innerText = value`** - also immune to injection, but
  *requires the opposite* of HTML-escaping: escaping content meant for
  this context can actively break it (real newlines, not `<br>`, are
  what render as line breaks here).
- **`element.innerHTML = value`** or raw string concatenation into page
  markup - a real HTML-injection context; content here must be
  HTML-escaped before insertion.
- **An inline event-handler attribute with a nested JS string**
  (`onclick="fn('{value}')"`) - the trap: HTML-escaping the value for
  the *attribute* is necessary but **not sufficient**, because the
  browser HTML-decodes the attribute's text before handing it to the JS
  parser - an escaped quote decodes back to a literal quote that closes
  the JS string early. Fix by not building JS source from data at all:
  pass data via a plain `data-*` attribute and read it in real JS via
  `addEventListener` instead of interpolating it into an inline handler
  string.

Verify every claim above empirically against the real generated file
(grep the bundled/output source for the actual rendering call, script a
DOM assertion in a headless browser) rather than reasoning from
documentation or memory.

## What "done" looks like for one assessment pass

Every run gets a dated entry in your findings log (append-only - a new
pass is a new dated section, never an overwrite of a prior one),
regardless of which lens(es) it covers. For every finding:
1. **What was checked** - the exact input/check, and which lens.
2. **The actual result** - quoted or shown, not summarized into "it
   worked"/"it didn't" - the reader should be able to judge the verdict
   themselves.
3. **Held/clean or broke** - an explicit verdict, argued from the
   evidence, not asserted.
4. **If broken**: the fix applied (with an ADR if architecturally
   significant, per `build-and-document`) and re-verified against the
   fixed code - or an explicit "known gap, not yet fixed" note. **Never
   silently drop a failing check from the log.**

## Do NOT

- Don't mock the model/LLM call in a Lens-1 adversarial test.
- Don't overwrite a prior dated entry in the findings log.
- Don't force-fit a test for a category your project's actual design
  makes inapplicable - document the reasoning instead.
- Don't paper over a real, verified break with a reworded prompt or a
  narrower escape rule alone, if the finding points at a structural
  issue - the fix has to be structural too.
- Don't assume a rendering/escaping mechanism from memory or
  documentation - verify it against the real generated output.
- Don't claim a dependency scan happened without having actually run a
  real tool.
