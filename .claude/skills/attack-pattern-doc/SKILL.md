---
name: attack-pattern-doc
description: "Use this skill whenever a new ATT&CK technique or sub-technique is added to the graph as a seed node, or when its semantic edges (TEMPORALLY_PRECEDES, CAUSALLY_ENABLES, etc.) are authored. Produces a documented case file per technique explaining the real-world attack, the gap in existing tools, and how this project's graph closes it."
---

# Attack Pattern Documentation

Every technique added to the graph gets a case file in
`docs/attack-patterns/<TECHNIQUE_ID>-<short-name>.md`. This is the
domain-knowledge counterpart to the engineering ADRs - it proves you
understand the security substance, not just the graph plumbing.

## Required sections, in this order

```markdown
# <TECHNIQUE_ID> - <Technique Name>

## The Attack - What Actually Happens
Plain description of the technique in a real intrusion: what the
attacker does, what it looks like on the wire/endpoint, a real
campaign example if one is publicly documented (cite the source -
CTI report, MITRE group page, vendor writeup). Ground this in fact,
not a generic textbook definition.

## The Present Problem
What existing tools (ATT&CK Navigator, a plain SIEM rule, a static
lookup) fail to tell a defender about this technique - sequencing,
timing, prerequisites, confidence, coverage. Keep this specific to
THIS technique, not a copy-paste of the general platform pitch.

## How This Graph Models It
- Node(s) added: type, ATT&CK ID, key attributes
- Edge(s) added: type (e.g. TEMPORALLY_PRECEDES), source -> target,
  confidence score, sample_size, and the evidence backing it
- Any DETECTED_BY coverage mapping, if modeled

## Evidence and Sources
Every claim needs a citation - CTI report name/publisher, MITRE ID,
or explicitly mark as "author-estimated, needs validation" if no
public source directly supports the confidence value used. Never
invent a source.

## What This Enables
One or two concrete example queries this technique's data now
supports (tie back to the query layer once it exists), e.g. "if
T1059.001 is observed, what's the likely next step and do we have
detection coverage."
```

## Sourcing discipline

- Prefer MITRE ATT&CK's own group/software pages and linked CTI
  reports over secondary summaries.
- If a confidence score or timing figure isn't backed by a real
  source, label it clearly as an estimate - don't dress up a guess as
  data. This matters for interview credibility as much as for
  correctness.
- Copyright: paraphrase CTI report findings in your own words, don't
  reproduce report text; short factual citations (technique ID, group
  name, published confidence assessment) are fine.

## Do NOT

- Don't reuse the platform pitch's problem framing verbatim per
  technique - each case file's "present problem" should be specific
  to that technique's actual gap, not generic copy.
- Don't fabricate campaign details or dates. If unsure, say so.
