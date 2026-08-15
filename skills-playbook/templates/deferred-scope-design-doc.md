---
name: deferred-scope-design-doc
description: "Use this skill on an explicit request to plan [PLACEHOLDER: the kind of future expansion this covers - e.g. scaling, a new data-ingestion pipeline, a new domain], or when a genuinely load-bearing signal actually happens ([PLACEHOLDER: your real trigger, e.g. 'real external interest beyond a demo,' 'usage crosses N']). Do NOT trigger automatically, as part of routine build sessions, or just because the design doc exists and is being discussed."
---

# Deferred-Scope Design Doc

Every real project accumulates future work that's genuinely worth
thinking through *before* it's needed - a scaling path, a bigger
ingestion pipeline, a schema migration - but building it before there's
a real reason wastes effort and adds complexity a prototype doesn't need
yet. This template is the discipline for writing that thinking down
without it being mistaken for committed work, and for gating when it
actually gets picked up.

Two real instances of this pattern from the project this playbook was
generalized from: a design doc for replacing hand-authored data with a
multi-agent continuous-ingestion pipeline, and a separate design doc for
vertical/horizontal scaling of the service layer - each gated by its own
skill with its own trigger conditions, so neither could get built by
accident just because the doc existed.

## When to write the design doc in the first place

[PLACEHOLDER: your actual trigger - e.g. "when a real scope question
comes up in review and the honest answer is 'not now, but here's the
real plan if it ever is needed'"]

## The doc itself - structural requirements

1. **Mark it unambiguously as design-only, at the very top, every time
   it's read.** A blockquote callout like:

   ```markdown
   > **DESIGN ONLY - NOT BUILT.** Nothing in this document exists in
   > code. [PLACEHOLDER: name the specific things that don't exist yet].
   > This is deferred design thinking, dated [DATE], written down so
   > it isn't lost or reconstructed from memory later - not a roadmap
   > item, not a claim of progress.
   ```

   If the doc *also* documents something that's genuinely already true
   about the current code (not a future proposal - see the scaling
   example below, which verified the service was already stateless),
   **separate that section explicitly and say so** - don't let an
   already-true fact and a future proposal blur together under one
   "design-only" label; a reader needs to know which parts are real
   right now.

2. **Every proposal gets its own concrete trigger condition, not a
   vague "eventually."** "Worth doing once X is actually true" - stated
   specifically enough that a future reader can check whether the
   condition has actually been met, not just gesture at "someday."
   Compare a weak trigger ("if this ever needs to scale") against a
   strong one ("once the committed data file's own size crosses N MB,
   or a real multi-hop query pattern is needed that a single-process
   traversal can't serve with acceptable latency").

3. **Re-validate assumptions when actually picked up - don't implement
   the doc literally.** It was written at a point in time; treat it as a
   first draft to revise against whatever's actually true when the work
   starts (has the landscape changed, are the proposed numbers/approach
   still right), not a finished spec to build from unchanged.

4. **If a proposed fixture/example turns out to reference something
   that doesn't check out (a citation, a source, a claimed dataset),
   exclude it and say so explicitly in the doc, rather than silently
   dropping it or including it anyway** because it "was probably fine."
   State what was checked and how.

## The gating skill

Write a companion skill (same playbook, `.claude/skills/[name]/
SKILL.md`) whose only job is trigger discipline:

- **Only** trigger on: an explicit, real decision to actually pursue
  this - not "this would be cool eventually" - or a genuine external
  signal (real interest, real load, real data) beyond a hypothetical.
- **Never** trigger automatically, as part of a routine build session,
  or just because the design doc exists and is being read/referenced in
  conversation.
- If in doubt whether a request rises to the bar, ask rather than
  assume - this is the exact kind of scope expansion that's cheap to
  trigger accidentally and expensive to walk back once code exists.
- When actually triggered: treat the work as new engineering, not a
  resume of paused work - follow your `build-and-document` discipline
  from the start (ADRs for real decisions, status file and build log
  kept current), and explicitly restate which of the design doc's
  standing project conventions must NOT bend for the sake of the new
  scope (e.g. "no invented data" doesn't get relaxed just because volume
  is about to grow).

## Do NOT

- Don't build any part of the deferred scope speculatively "since we're
  already touching this area" - see trigger conditions above.
- Don't implement the design doc's proposals literally without
  re-validating them first against current reality.
- Don't let growing scope become a reason to loosen a standing project
  discipline (citation/sourcing rigor, security review, whatever your
  project's own non-negotiables are) "just for the new part."
