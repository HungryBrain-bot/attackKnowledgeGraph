---
name: build-and-document
description: "Use this skill whenever building, modifying, or making an architectural decision on [PLACEHOLDER: project name] - [PLACEHOLDER: 2-4 concrete trigger examples specific to this project, e.g. 'adding a new API endpoint,' 'changing a data model,' 'fixing a design flaw']. Ensures every real engineering decision gets captured as we go, not reconstructed later from memory."
---

# Build and Document

**This is the most broadly useful template in this playbook - if you
only adopt one, adopt this one.** Almost every software project benefits
from capturing *why* a decision was made at the moment it's made, rather
than trying to reconstruct the reasoning weeks later from commit
messages alone. This pattern has no dependency on the domain, the
language, or the project's maturity - it's equally useful on day one of
a prototype and on a mature codebase.

[PLACEHOLDER: if this project is also a portfolio/interview artifact,
say so explicitly here - it changes the bar for *why* documentation
matters, the same way the original project this playbook came from
states it up front: "the documentation trail IS part of the
deliverable."]

## Every build session does four things, in this order

### 1. Before writing code - check the living status file
Read [PLACEHOLDER: your living status file - a `CLAUDE.md`/`AGENTS.md`
at repo root, or a "Current status" section in the README] to know what
phase the project is in and what conventions are already established.
Don't re-derive context that's already written down.

### 2. While building - narrate real decisions inline
When a genuine design choice gets made (not a trivial implementation
detail - an actual "we could have done X, we did Y because Z"), say so
before writing the code, not just as a code comment.

### 3. After a logical unit of work is done - write an ADR
Create `[PLACEHOLDER: your decisions directory, e.g. docs/decisions/]/
NNN-short-title.md` (zero-padded, incrementing) whenever a real decision
point was crossed. Trivial choices don't need one; "why we chose
approach X over the more obvious approach Y" does. Format:

```markdown
# NNN. Short title

## Status
Accepted

## Context
What problem/tension made a decision necessary.

## Decision
What we chose.

## Alternatives considered
What else was on the table, and why not.

## Consequences
What this makes easier, harder, or explicitly out of scope now.
```

### 4. Update the living status file and the build log
- Your living status file reflects **current state** - overwrite stale
  sections, don't just append. It should always be readable
  top-to-bottom as an accurate snapshot of the project right now.
- Your build log (`[PLACEHOLDER: e.g. BUILD_LOG.md]`) is **append-only**
  - one entry per session, dated, short: what got built, what's mocked
  vs. real, what's next.
- [PLACEHOLDER: cross-reference any other skills in this playbook you've
  adopted - e.g. "after changing generated content's source data, see
  the generate-diagrams-pattern template" or "after touching a new
  input path, see the red-team-assessment template."]

## Commit conventions

One commit per logical unit, not per file. Commit message explains the
*why*, following the same shape as the ADR:

```
[area]: [what changed], [scoped down how]

[One or two sentences on the actual tradeoff/decision, in plain prose.]
See [PLACEHOLDER: path]/NNN-[short-title].md
```

## Do NOT

- Don't write documentation that describes unbuilt future work as if it
  exists. Every doc reflects only what's actually built - see this
  playbook's `deferred-scope-design-doc` template for how to write down
  real future thinking *without* implying it's done.
- Don't let the living status file or README balloon into aspirational
  pitch-deck language describing the eventual product instead of what
  this codebase actually does today. [PLACEHOLDER: if you keep a
  separate, gitignored notes file for product vision/pitch language, say
  so here - the way the original project keeps `NOTES-private.md`
  entirely separate from anything committed.]
