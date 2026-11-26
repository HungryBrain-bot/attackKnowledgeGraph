# Provenance: where each fact in the graph comes from

Written 2026-11-26 from the code as it stands (`graph/build_graph.py`,
`graph/semantic_edges.py`, `query/retrieval.py`) and the 2026-10-26
audit (docs/edge-audit.md, ADR 010). It describes what is built, not a
target design.

## Two kinds of fact, two kinds of provenance

| | Structural | Semantic |
|---|---|---|
| What | Technique, Tactic and Group nodes; `HAS_TACTIC`, `USES_TECHNIQUE` edges | `TEMPORALLY_PRECEDES`, `CAUSALLY_ENABLES` edges between two techniques, for one group |
| Count | 26 nodes, 54 edges | 5 edges (4 CAUSALLY_ENABLES, 1 TEMPORALLY_PRECEDES) |
| Author | MITRE, via `mitreattack-python` | Hand-written in `SEMANTIC_EDGES`, one dict per edge |
| Source | The enterprise STIX bundle (`data/raw/enterprise-attack.json`) | One fetched report per edge, by URL |
| Who decides it is true | MITRE | The author, under the rules below |

Nothing in the graph comes from an LLM. The LLM only formats facts that
retrieval has already pulled out, and its reply is checked by the guards
in `query/rag.py` (ADR 005).

## Structural facts

`build_structural_graph()` looks up each ID in `graph/seed_config.py` in
the STIX bundle and raises if one is missing. Technique names, tactics
and a 500-character description are copied from the STIX object. Group
names and aliases are copied from the intrusion-set object.

A `USES_TECHNIQUE` edge exists only where ATT&CK itself records the
group using the technique. Its `sources` field holds the citation names
STIX attaches to that relationship, as `extract_sources()` reads them.
When STIX attaches none, the field is `["MITRE ATT&CK"]`. These are
names, not URLs or quotes, and they say only that the group used the
technique, never in what order.

## Semantic facts

Each edge in `SEMANTIC_EDGES` carries these fields, defined in the
module docstring:

- `source_url`, `source_date`, `sources`: the one report the edge rests
  on, and its publication date.
- `quote`: under 25 words copied from that report, narrating this order
  or dependency for this group.
- `incident_id`: our label for the one intrusion (or, for the GRU edge,
  one campaign) the quote describes. Chains warn when hops come from
  different incidents (ADR 009).
- `evidence`: our own words on how the quote supports the edge, saying
  what is inferred rather than stated.
- `confidence`: the author's judgment, 0 to 1, of how directly the quote
  supports the edge. A hand-typed number. No function computes it.
- `sample_size`: how many listed sources narrate the claim themselves.
  All 5 edges have 1.

The rules for adding one are in CLAUDE.md, "Adding or changing an edge".
In short, an edge is not added when:

- the source cannot be fetched;
- the two techniques are only named in the same report (co-citation);
- the order is true by definition (an attachment is delivered, then
  opened);
- the report attributes the activity to another group, even a related
  one (Andariel is not Lazarus Group);
- the quoted behavior is a neighboring technique, not the stated one.

The 2026-10-26 audit applied these rules to the 17 edges that existed
then and kept 5. docs/edge-audit.md has the row, quote and reason for
each of the 17.

## How provenance reaches the user

`format_context()` and `format_chain_context()` print, for every
semantic edge, its group, confidence, sample_size, incident, quote and
URL. The CLI and API show this facts block whether or not an LLM is
configured. The guards check that a reply names only techniques and
edges present in the facts, under a group the facts record, with any
stated confidence or sample_size matching the stored value. They do not
check that a quote or URL in the reply is real (ADR 005, Known
limitations).

## Gaps in provenance today

- **Quotes are not checked character by character.** They came through
  a summarising fetch tool on 2026-10-26 and no person has compared them
  to the pages yet (docs/edge-audit.md).
- **Which ATT&CK release built the snapshot is not recorded.** The
  exported JSON carries `schema_version` (the field format) but not the
  STIX bundle's version or hash. Structural facts can only be traced to
  "the bundle CI or the author downloaded at the commit date".
- **Structural citations are names only.** No URL or quote is kept for
  `USES_TECHNIQUE`.
- **`confidence` is one person's judgment**, not reproducible by anyone
  else from the inputs. The deterministic scoring function in
  docs/future/schema_reference/ is a design that was never built.
- **One source per edge.** No edge is corroborated by a second report.
