---
name: entity-case-file-doc
description: "Use this skill whenever a new [PLACEHOLDER: domain entity - e.g. a technique, a component, an API resource, a model card subject] is added to [PLACEHOLDER: the system this project builds - e.g. the graph, the catalog, the registry]. Produces a documented case file per entity explaining what it actually is/does, the gap in existing approaches, and how this project addresses it."
---

# [PLACEHOLDER: Entity Type] Case File Documentation

Every [PLACEHOLDER: entity] added to the project gets a case file in
`[PLACEHOLDER: docs/your-entities-dir/]/<ENTITY_ID>-<short-name>.md`.
This is the domain-knowledge counterpart to engineering ADRs (see the
`build-and-document` template) - it proves you understand the substance
of what you're modeling, not just the plumbing around it.

This template generalizes a pattern originally built for documenting
MITRE ATT&CK techniques in a security knowledge-graph project, but the
shape applies to any domain where a project accumulates a growing set of
named, individually-documentable things: API endpoints, ML model cards,
compliance controls, product features, hardware components.

## Required sections, in this order

```markdown
# <ENTITY_ID> - <Entity Name>

## [PLACEHOLDER: e.g. "The Attack" / "What This Actually Is/Does"]
Plain description of the entity in real use: [PLACEHOLDER: what it does,
what it looks like when observed/used, a real example if one is
publicly documented (cite the source)]. Ground this in fact, not a
generic textbook definition.

## The Present Problem
What existing tools/approaches/docs fail to tell someone about this
specific entity - [PLACEHOLDER: e.g. sequencing, timing, prerequisites,
confidence, coverage - whatever the actual gap is for THIS entity, not a
copy-paste of the project's general pitch]. Keep this specific, not
generic.

## How This [PLACEHOLDER: System] Models It
- [PLACEHOLDER: node(s)/record(s)/field(s) added: type, ID, key
  attributes]
- [PLACEHOLDER: relationship(s) added, if the project models
  relationships: type, source -> target, and whatever confidence/
  evidence structure your project uses]

## Evidence and Sources
Every claim needs a citation - or is explicitly marked
"[PLACEHOLDER: author-estimated, needs validation]" if no source
directly supports it. Never invent a source.

## What This Enables
One or two concrete example uses this entity's data now supports -
tie back to whatever query/consumption layer exists.
```

## Sourcing discipline

- Prefer primary sources (the entity's own authoritative documentation,
  official registry, original publisher) over secondary summaries.
- If a confidence score, metric, or claim isn't backed by a real source,
  label it clearly as an estimate - don't dress up a guess as data. This
  matters for review credibility as much as for correctness.
- Copyright: paraphrase source findings in your own words rather than
  reproducing text verbatim; short factual citations (an ID, a name, a
  published figure) are fine.

## Do NOT

- Don't reuse the project's general problem framing verbatim per entity
  - each case file's "present problem" section should be specific to
  that entity's actual gap.
- Don't fabricate details, dates, or figures. If unsure, say so
  explicitly rather than presenting a guess as fact.
