# Build Log

## 2026-08-13 - Scaffolding

- Initialized repo structure: graph/, ingestion/, query/, docs/,
  .claude/skills/
- Wrote two Claude Code skills:
  - `build-and-document` - ADR + CLAUDE.md + build log discipline for
    engineering decisions
  - `attack-pattern-doc` - per-technique case file discipline (problem,
    mechanics, gap, how the graph models it, sources)
- Wrote CLAUDE.md (engineering-only, no product-pitch language) and
  NOTES-private.md (gitignored, holds full platform vision separately)
- Nothing built yet. Next session: graph core - pull real structural
  data via mitreattack-python, pick the 10-15 technique / 2-3 group
  seed set, build the NetworkX MultiDiGraph.

## 2026-08-13 - Structural graph (Phase 1)

- Downloaded official MITRE ATT&CK enterprise STIX bundle from MITRE's
  GitHub (data/raw/enterprise-attack.json, ~48MB, gitignored - not
  committing raw upstream data).
- Confirmed all three target groups exist with expected ATT&CK IDs:
  APT29=G0016, APT28=G0007, Lazarus Group=G0032.
- Analyzed technique overlap across the three groups (234 unique
  techniques total) to pick a defensible 13-technique seed set - see
  docs/decisions/001-seed-scope.md.
- Verified the seed set includes the exact techniques used as worked
  examples in the technical brief (T1059.001, T1003.002, T1078),
  confirmed real for these groups against live MITRE data - not
  assumed.
- Built graph/seed_config.py (fixed seed list) and graph/build_graph.py
  (structural MultiDiGraph builder: Technique/Tactic/Group nodes,
  HAS_TACTIC/USES_TECHNIQUE edges, citation sources captured per edge
  where available).
- Ran end-to-end: 26 nodes (13 Technique, 10 Tactic, 3 Group), 54 edges
  (17 HAS_TACTIC, 37 USES_TECHNIQUE - 37 of 39 possible group-technique
  pairs exist, confirming strong real overlap).
- Next: semantic edges (Phase 2) - hand-author TEMPORALLY_PRECEDES /
  CAUSALLY_ENABLES relationships for a subset of technique pairs, each
  with a cited source, alongside the first docs/attack-patterns/ case
  files.

## 2026-08-13 - Semantic edges (Phase 2)

- Environment fix: `mitreattack-python` was not actually installed
  (Kali's system Python is externally managed, `pip install` refuses
  system-wide installs). Created a project `.venv` (already gitignored)
  and installed `requirements.txt` into it - `data/raw/enterprise-attack.json`
  was still present on disk from the Phase 1 session, so no re-download
  needed.
- Researched real, citable evidence for technique-pair sequencing/
  causality before writing any edges - pulled citations already
  verified real via the Phase 1 structural graph (MITRE STIX
  relationship objects), plus two directly-fetched primary reports:
  Volexity's "The Nearest Neighbor Attack" (Nov 2024, APT28 Wi-Fi
  pivot) and CISA AA24-207A (Aug 2024, Lazarus Group). Also confirmed
  Mandiant's UNC2452/APT29 writeup states Domain Admin was reached
  under 12 hours after the initial phishing payload executed - directly
  usable for a high-confidence PowerShell -> Valid Accounts edge.
- Designed the semantic edge schema as group-scoped (a `group_context`
  per edge, not a universal technique-to-technique claim) with
  `confidence` and `sample_size` given literal definitions rather than
  left vague - see docs/decisions/002-semantic-edge-schema.md.
- Built `graph/semantic_edges.py`: 9 edges (4 TEMPORALLY_PRECEDES, 5
  CAUSALLY_ENABLES) across APT29 (4 edges, SolarWinds/SUNBURST
  intrusion), APT28 (3 edges, Nearest Neighbor attack + GRU brute-force
  advisory), and Lazarus Group (2 edges, AA24-207A) - touching 9 of the
  13 seed techniques. Deliberately left T1003.002, T1057, T1105, and
  T1547.001 without edges this pass rather than force weakly-evidenced
  claims.
- Ran end-to-end: combined graph (structural + semantic) is 26 nodes,
  63 edges. `data/structural_graph.json` (Phase 1) untouched; new output
  saved to `data/graph_with_semantics.json`.
- Wrote 9 docs/attack-patterns/ case files, one per touched technique,
  following the attack-pattern-doc skill's five-section format.
- Next: extend semantic edge coverage to the remaining 4 techniques and
  consider cross-group comparison edges once evidence is found: then the
  Graph RAG query layer (traversal + LLM-formatted, cited answers).

## 2026-08-13 - Semantic edge coverage completed (remaining 4 techniques)

- Researched and added 7 new semantic edges covering the 4 techniques
  left out of the first pass (T1003.002, T1057, T1105, T1547.001) - all
  13 seed techniques now have at least one semantic edge.
- Found real sourcing without inventing anything: extended the existing
  APT29/SolarWinds discovery chain (T1078 -> T1057 -> T1083, using
  sources already verified real via the structural graph's MITRE
  citations); fetched Mandiant's UNC3524/"Eye Spy on Your Email" report
  directly, which explicitly narrates ingress tool transfer (QUIETEXIT
  backdoor) enabling SAM/LSA credential dumping via `reg save`; used
  Trend Micro's Pawn Storm Dec 2020 report (co-cited across
  T1059.001/T1105/T1547.001 for APT28) for two lower-confidence
  (0.65) edges, honestly scored lower because the exact mechanism
  couldn't be independently confirmed beyond co-citation.
- **Found and fixed a real error while sourcing the new work**: fetching
  the full Volexity "Nearest Neighbor Attack" report (needed to source
  a new T1078 -> T1003.002 edge) showed the previously-committed
  APT28 T1059.001 -> T1021.001 edge had the causality backwards. The
  actual documented sequence is RDP-into-a-pivot-host first, then the
  PowerShell Wi-Fi enumeration script runs from that foothold - not
  PowerShell enabling RDP as originally modeled. Reversed the edge to
  T1021.001 -> T1059.001, corrected the T1078 -> T1021.001 edge's
  evidence text (the RDP hop is into the intermediate organization's
  pivot host, not directly into the ultimate target), and updated both
  affected case files (T1021.001, T1059.001) with an explicit
  correction note rather than silently overwriting them. This was
  already pushed to origin/main before the error was caught - the fix
  is a new commit, not a rewrite of history.
- Added a new edge (`T1078 -> T1003.002`, APT28, confidence 0.85) for
  the second, distinct use of Valid Accounts in the Nearest Neighbor
  incident (Wi-Fi credentials into the target, separate from the
  earlier RDP credentials into the pivot host) - documented as two
  edges from the same T1078 node rather than inventing per-instance
  nodes, with the simplification called out explicitly in
  T1003.002's case file.
- Wrote 4 new docs/attack-patterns/ case files (T1003.002, T1057,
  T1105, T1547.001) and updated 3 existing ones (T1078, T1021.001,
  T1059.001, T1083) whose edges changed.
- Ran end-to-end: 26 nodes, 70 edges (37 USES_TECHNIQUE, 17 HAS_TACTIC,
  10 CAUSALLY_ENABLES, 6 TEMPORALLY_PRECEDES).
- Next: cross-group comparison edges; consider deeper sourcing for the
  0.65-confidence tier if time allows; then the Graph RAG query layer.

## 2026-08-13 - build_graph.py performance/hygiene pass

- Applied fixes from a performance review of graph/build_graph.py -
  hygiene/readability only, no functional or output change:
  - Extracted `get_mitre_attack_id(obj)`: an early-exit loop replacing
    the two separate `next(generator, None)` call sites (group attack_id,
    technique attack_id) that were pulling the same field out of
    `external_references` in slightly different ways.
  - Extracted `extract_sources(technique_usage)`: replaces the inline
    nested-loop-then-`set()` pattern in the USES_TECHNIQUE edge building
    with a single set comprehension.
  - `graph_summary()` now uses `collections.Counter` instead of a
    manually maintained dict for node/edge type counts.
  - Added a one-line comment on the `MitreAttackData(str(STIX_PATH))`
    call noting the full 48MB-bundle-load-per-run is an accepted
    tradeoff at this prototype's scale (13 seed techniques), not solved
    preemptively.
  - Checked whether `json.dump(..., default=str)` is actually needed:
    ran `json.dumps()` on the graph's `node_link_data()` output without
    a `default=` fallback and confirmed it serializes cleanly as-is - no
    custom encoder added, since nothing is actually failing.
- Verified no behavior change: rebuilt both `data/structural_graph.json`
  (26 nodes, 54 edges) and `data/graph_with_semantics.json` (26 nodes,
  70 edges) after the refactor and diffed against the pre-refactor
  files - byte-identical.
- Added a "Code Review Standards" section to CLAUDE.md capturing the
  reusable principle (extract repeated lookup/extraction logic into
  named helpers, use `Counter` for type-counting, verify before adding
  complexity) rather than a list of the specific fixes made here.

## 2026-08-13 - Graph RAG query layer (Phase 3)

- Built `query/` end to end: `graph_loader.py` loads the already-built
  `data/graph_with_semantics.json` (no need to re-parse the 48MB STIX
  bundle just to run a query); `retrieval.py` does pure-Python graph
  traversal for one technique - its structural `USES_TECHNIQUE` usage
  plus every directly-connected semantic edge, optionally filtered to
  one group - with zero LLM involvement; `rag.py` sends the retrieved
  facts plus the question to Claude (`claude-opus-5`) with a system
  prompt that forbids answering from anything outside the facts block
  and requires cited claims; `ask.py` is the CLI entry point,
  `python -m query.ask "..."`, extracting a technique ID and optional
  group from the question via regex/substring matching rather than a
  second LLM call, since ATT&CK IDs and this project's 3 seed group
  names are unambiguous strings. Scope decision (single-technique/
  one-hop retrieval, no-LLM entity extraction) written up in
  docs/decisions/003-query-layer-scope.md.
- Consulted the claude-api skill before writing any Anthropic SDK code,
  per its trigger rules - confirmed current model IDs/params rather than
  relying on training-data recall (e.g. `claude-opus-5` is on by default
  for adaptive thinking; `output_config`/`thinking` shapes verified
  against the skill's cached docs, not guessed).
- Wired up `python-dotenv` (already a declared but unused dependency in
  requirements.txt) so `rag.py` picks up `ANTHROPIC_API_KEY` from a
  gitignored `.env` file.
- Verified `retrieval.py` + `format_context()` end-to-end against the
  real graph: technique-only query, technique+group-filtered query, and
  the not-in-graph error case all produce correct output (checked by
  hand against the known T1059.001 edges from the Phase 2 session).
- **Could not live-test the actual Claude API call this session** - no
  `ANTHROPIC_API_KEY`/`ANTHROPIC_AUTH_TOKEN` env var and no `ant auth`
  profile are configured on this machine (the `ant` binary present here
  is Apache Ant, unrelated to the Anthropic CLI). Ran the full CLI
  pipeline anyway to confirm the failure is the SDK's own clean
  "could not resolve authentication method" error at client
  construction - not a bug anywhere in this project's code - rather than
  claiming a live test that didn't happen.
- Next: get a real API key into this environment (or hand the CLI to
  someone who has one) and actually read the model's answers for
  quality and citation accuracy, not just confirm the plumbing runs.

## 2026-08-13 - LLM provider abstraction

- Extracted the query layer's LLM call behind a vendor-agnostic
  interface: `query/llm_provider.py` defines `LLMProvider` (one
  abstract method, `generate(prompt, *, system=None) -> str`),
  `ClaudeProvider` (the working implementation, moved out of `rag.py`
  unchanged - same model default, adaptive thinking, refusal handling),
  and `OpenAIProvider`/`KimiProvider` stubs that implement the interface
  but raise `NotImplementedError` naming exactly what's missing (no API
  key configured for either yet). `rag.py` now calls
  `llm_provider.get_provider()` instead of the `anthropic` SDK directly.
- Wrote docs/decisions/004-llm-provider-abstraction.md, including an
  explicit note that this is more structure than the current one-vendor
  reality strictly needs - flagged as a deliberate exception to this
  project's own Code Review Standards (don't add complexity ahead of an
  observed need), made because the project owner explicitly asked for a
  five-minute path to a new provider, not because of a need I inferred
  myself.
- Added an "Adding an LLM Provider" section to CLAUDE.md: implement
  `LLMProvider`, add one line to the `PROVIDERS` dict, done - `rag.py`/
  `ask.py` need no changes.
- Verified the refactor didn't change behavior: `PROVIDERS` and
  `get_provider()` resolve correctly, both stub providers instantiate
  fine and raise `NotImplementedError` only on `generate()`, and the
  full `query/ask.py` CLI pipeline still runs through retrieval and
  fails at the same point (the SDK's clean auth error, no credentials
  configured on this machine) as before the refactor.

## 2026-08-13 - fetch-test-logs skill (real EVTX test data)

- Researched the requested dataset - github.com/arniki/atomic-evtx -
  directly against the live repo (GitHub API contents listing, raw
  README.md, raw `full_list_of_attacks_simulated.csv`) rather than
  assuming its structure. Confirmed real: 1,064 Atomic Red Team-
  simulated attack scenarios across 12 ATT&CK tactic categories, three
  filtering-tier directories (`attacks_by_category_unfiltered`,
  `attacks_by_category_atomic_removed`,
  `attacks_by_category_atomic_and_tools_removed`), and the CSV's real
  column names (`Category`, `TTP ID`, `Description`).
- **Found a non-obvious, load-bearing fact by testing rather than
  trusting the README summary**: compared file sizes for the same
  scenario across two tiers and confirmed the top-level `.evtx`/`.csv`/
  `.txt` files are byte-identical regardless of tier - the tier-specific
  filtering (framework artifacts, tool names) only touches the JSON
  representations in each scenario's `json/` subdirectory. My first
  draft of the fetch script skipped `json/` entirely to keep the
  default download small, which would have made every "sanitized tier"
  fetch silently return the same unfiltered content as "raw." Fixed
  before writing any documentation that claimed otherwise.
- Computed the real cross-reference against `graph/seed_config.py`'s
  `SEED_TECHNIQUES` by parsing the actual CSV: 11 of 13 seed techniques
  have matching scenarios (96 total); T1078 and T1074.002 have none -
  documented as a real gap, not silently dropped.
- Wrote `.claude/skills/fetch-test-logs/SKILL.md` (tier tradeoffs, which
  tier for which purpose, the cross-reference table, the byte-identical-
  EVTX caveat above) and `fetch_test_logs.py` (stdlib-only, no new
  project dependency; imports `SEED_TECHNIQUES` directly from
  `graph/seed_config.py` rather than duplicating the list).
- Verified the script for real, not just read through it: ran it in
  list-only mode (output matched the hand-computed cross-reference
  exactly) and with `--fetch --tier sanitized --limit 1` (successfully
  downloaded real log files, including `json/`, for all 11 matched
  techniques - confirmed via `du`/`find`, then deleted the local
  download afterward since it's test output, not something to keep
  lying around).
- Added `data/test_logs/` to `.gitignore` and a note in CLAUDE.md that
  this is future test/validation data for the query layer once it
  exists - not wired into the query layer, a test suite, or anything
  else yet.
- No sub-agent built for this, per instruction - just the skill and the
  script.

## 2026-08-13 - OpenAIProvider implemented

- User supplied an `OPENAI_API_KEY` and asked to store it locally,
  gitignored - written to `.env` (already git-ignored, verified with
  `git check-ignore`), never echoed back or logged elsewhere.
- Implemented `OpenAIProvider.generate()` for real, closing the stub
  left in place by the LLM provider abstraction session. The installed
  `openai` package is v3.0.0 - far past what training-data knowledge of
  that SDK covers - so rather than guess at a shape, installed it and
  read the actual source (`_client.py`'s constructor for env-var API
  key resolution, `types/responses/response.py` for `output_text` and
  `status`, `types/shared/chat_model.py` for real model IDs). Uses the
  Responses API (`client.responses.create`, not the older Chat
  Completions shape).
- Model default: `gpt-5.1` - confirmed real against the SDK's own type
  definitions, but deliberately not the newest-looking undated entries
  (`gpt-5.6-sol`/`-terra`/`-luna`) since no public documentation
  distinguishes what each is for. Guessing among three undocumented
  names would have been exactly the kind of invented-data mistake this
  project's conventions exist to prevent - `OPENAI_MODEL` is there for
  whoever verifies that disambiguation later.
- Verified against the real API before calling it done, not just
  "didn't throw": a direct `OpenAIProvider().generate(...)` call
  returned the expected short reply, and a full
  `query.rag.answer(question, facts, provider=get_provider("openai"))`
  call using real T1059.001/APT29 graph facts returned a correct,
  correctly-cited answer - confirming the whole provider abstraction
  works with a second real vendor now, not just in theory.
- Added `openai>=3.0` to requirements.txt. Confirmed the default
  provider (Claude, via `get_provider()` with no `LLM_PROVIDER` set) is
  unchanged.
- Updated docs/decisions/004-llm-provider-abstraction.md with a dated
  addendum (not a new ADR - no new decision was made, this was already
  scoped as "implement `generate()`, done" in the original decision) and
  CLAUDE.md's provider descriptions to reflect `OpenAIProvider` as
  implemented, not stubbed.

## 2026-08-13 - Query CLI end-to-end test (via OpenAIProvider)

- Ran `python -m query.ask` end-to-end for real, through the actual CLI
  entry point (`LLM_PROVIDER=openai` set for the invocation, not
  hardcoded into any test script) - the first time the full pipeline
  (entity extraction -> graph loading -> retrieval -> format_context ->
  provider resolution -> live LLM call -> printed answer) was exercised
  as a user would actually run it, rather than via direct Python calls
  to individual functions.
- Three cases, all passed:
  - `"what happens after T1059.001 for APT29?"` - correct facts
    retrieved, correct group filter applied, and the OpenAI-backed
    answer correctly distinguished edge direction on its own (excluded
    the incoming `T1204.002 --CAUSALLY_ENABLES--> T1059.001` edge from
    "what happens after," since it points into T1059.001, not out of
    it - the system prompt's TEMPORALLY_PRECEDES/CAUSALLY_ENABLES
    distinction held up against a real model, not just in the prompt
    text).
  - `"what did Lazarus Group do with T1560.001?"` - group correctly
    inferred from the question text (no explicit "for X" phrasing
    needed), and the answer correctly synthesized both an incoming
    (`T1083 --TEMPORALLY_PRECEDES--> T1560.001`) and an outgoing
    (`T1560.001 --CAUSALLY_ENABLES--> T1071.001`) edge into one
    coherent, fully-cited answer.
  - `"what happens after phishing?"` (no technique ID) - failed cleanly
    with the expected error message and exit code 1, no crash.
- Confirmed this closes the loop on docs/decisions/004's claim that the
  provider abstraction "works with a second real vendor, not just in
  theory" - that claim was previously verified only via direct Python
  calls (`OpenAIProvider().generate(...)`, `rag.answer(...,
  provider=...)`), not via the actual CLI a user runs. Now it has been.
- No files changed - Claude remains the default provider
  (`LLM_PROVIDER` unset in `.env`); this session only set the env var
  for the test invocations, it wasn't made the persistent default.

## 2026-08-13 - First automated test: query layer vs. real EVTX telemetry

- Wrote `tests/test_query_layer_against_evtx.py`, the project's first
  automated test - connects the two pieces built earlier this session
  (the query layer, the fetch-test-logs skill) that had been built in
  parallel but never actually touched each other. For every locally
  fetched atomic-evtx scenario: reads the scenario's own `.csv`
  metadata (real data, not authored by this project) and cross-checks
  its self-reported `Technique` column against the technique ID our
  fetch script filed the scenario under; confirms that technique has
  real structural usage and at least one semantic edge in the graph;
  confirms `format_context()` produces well-formed output. Deliberately
  exercises `query/retrieval.py` only, not `rag.py`'s LLM call - a live
  LLM call would be costly and non-deterministic for an automated test.
- Installed `pytest` (added to requirements.txt) - this project had no
  test runner before now. Found an empty, untracked `tests/` directory
  already present at the repo root (no git history) and used it rather
  than creating a new one.
- Fetched a fresh real sample set (`--fetch --tier sanitized --limit 1`,
  11 techniques) to actually run the test against, rather than writing
  it against a hypothetical. Verified for real, not just read through:
  - Full suite passes: 12/12 (11 parametrized scenarios + 1 sanity
    check that fails loudly, not silently, if fetched coverage ever
    drops below 5 techniques).
  - Skip behavior verified by temporarily moving `data/test_logs/`
    aside and re-running - skips cleanly (not a failure), matching the
    intended behavior on a fresh clone or in CI before anyone runs the
    fetch script.
  - **The CSV cross-check assertion was proven non-decorative**:
    deliberately corrupted one scenario's `.csv` (changed its
    self-reported `Technique` field to a fake ID) and confirmed the
    test actually fails with a clear message, then restored the
    original file and re-confirmed the suite passes clean again.
- Left the fetched sample data in place under `data/test_logs/`
  (gitignored, so this doesn't affect what's committed) specifically so
  the test suite runs for real rather than sitting permanently skipped
  - a deliberate change from the fetch-test-logs session, which deleted
  its test download afterward since nothing depended on it existing yet.
- Updated CLAUDE.md: added `tests/` to Architecture, updated the
  fetch-test-logs status bullet (no longer "not wired into anything"),
  and corrected the stale "Next: live-test query/ask.py" line, which
  was already partially done as of the previous session's entry.

## 2026-08-13 - Mermaid diagrams, split generated vs. hand-authored

- New skill `.claude/skills/generate-diagrams/SKILL.md`: documents the
  trigger conditions (`SEMANTIC_EDGES`/`SEED_TECHNIQUES` changes, or an
  explicit request), the idempotency guarantee, and - the part that
  actually matters for not breaking this later - an unambiguous
  auto-generated-vs-hand-authored split enforced by `<!-- BEGIN
  GENERATED -->`/`<!-- END GENERATED -->` HTML comment markers in the
  files themselves, not just documented in prose. Added a one-line
  cross-reference from build-and-document's SKILL.md rather than
  duplicating the instructions across both files.
- `graph/generate_diagrams.py`: reads `data/graph_with_semantics.json`
  (via `query.graph_loader`, reused rather than re-implemented) and
  writes two kinds of diagram inside those markers - a per-technique
  Mermaid flowchart of direct semantic edges into each
  `docs/attack-patterns/<ID>-*.md` file's `## Flow` section, and a
  master kill-chain diagram (13 techniques, all 16 semantic edges,
  colored by `group_context`, dashed/solid by edge type) into README's
  new "Technique Relationship Graph" section.
- **Found and fixed a real placement bug before calling this done**: the
  first-run insertion logic put a new `## Flow`/section's GENERATED
  block immediately after the heading line, which stranded a
  hand-written intro paragraph I'd pre-placed in README.md *below* the
  diagram instead of above it. Fixed `_upsert_generated_section()` to
  insert at the end of the section (after any existing hand-written
  prose, before the next `## ` heading) instead, and corrected README.md
  by hand since the already-existing markers meant a re-run wouldn't
  reorder content around them.
- **Verified idempotency for real, not just asserted**: snapshotted
  `docs/attack-patterns/` and `README.md` after a run, ran the generator
  again, and diffed - `diff -rq` reported zero differences, exit code 0.
- **Verified the diagram content is correct, not just well-formed**:
  inspected a multi-edge case file (`T1078`, 5 semantic edges, both
  incoming and outgoing) and confirmed every edge appeared exactly once
  with the right direction, group, and confidence; confirmed the
  README's master diagram has exactly 16 `linkStyle` lines, matching the
  graph's real semantic edge count.
- **Validated Mermaid syntax against a real renderer, not just eyeballed
  it - and caught my own false-positive along the way**: extracted all
  18 embedded `\`\`\`mermaid` blocks (13 per-technique + kill-chain +
  architecture + query-flow sequence + provider class diagram).
  `mermaid.parse()` with a minimal DOM stub cleanly validated the
  sequence diagram but couldn't get far enough for flowchart/
  classDiagram (its internal DOMPurify step needs a fuller DOM than the
  stub provided). Moved to `@mermaid-js/mermaid-cli` for real headless-
  Chromium rendering - the first attempt silently failed on every block
  (puppeteer 25.x hard-requires Node ≥22.12, this machine has 20.19.4),
  but a loop bug in my own check (`$?` after a `| tail -3` pipe captures
  `tail`'s exit code, not the render command's) made every failure read
  as `exit:0`. Caught by testing one render directly without the pipe
  and seeing the real `exit 1`, not by trusting the first "all green"
  result. Fixed by pinning `@mermaid-js/mermaid-cli@11.4.3` +
  `puppeteer@23` (compatible with Node 20) - all 18 diagrams then
  rendered for real, producing non-trivial SVGs (11-35KB, each
  confirmed to contain the diagram's actual node labels, e.g.
  `ClaudeProvider` in the provider class diagram's SVG) with correctly-
  captured exit codes this time, not the masked ones from the first
  pass.
- Hand-authored three structural diagrams, none touched by the
  generator: a system architecture pipeline diagram (STIX bundle through
  `llm_provider.py`'s branch to Claude/OpenAI/Kimi through the `ask.py`
  CLI) in both README.md and CLAUDE.md; a query-flow sequence diagram
  (user question through entity extraction, retrieval, `format_context`,
  provider `generate()`, cited answer) in
  docs/decisions/003-query-layer-scope.md; a provider-abstraction class
  diagram (LLMProvider + its three implementations, Claude/OpenAI real,
  Kimi stubbed) in docs/decisions/004-llm-provider-abstraction.md.
- Updated CLAUDE.md's Architecture section with the pipeline diagram and
  an explicit "Diagrams: auto-generated vs. hand-authored" subsection
  naming exactly which diagram lives where and in which category,
  matching the new skill.
- Three separate commits (skill; generator + its data-driven output;
  hand-authored structural diagrams) - different provenance, different
  risk if something about any one of them turns out wrong.

## 2026-08-13 - README presentation pass (no functional changes)

- Rewrote README.md's structure following the section patterns from
  github.com/HungryBrain-bot/opsmind-hackathon's README (structure only,
  no content borrowed - different project): badges row, a "see it run"
  proof section before any prose, a comparison table, a working Quick
  Start, a repository-structure tree, and a versioned Current/Planned
  roadmap. Confirmed via `git diff --stat` that only `README.md` changed
  and no code under `graph/`, `query/`, or `tests/` was touched.
- Added Python/NetworkX/Tests/License badges. The License badge
  surfaced a real gap: this repo had no LICENSE file, and shipping an
  "MIT" badge without one would have been an invented claim - flagged
  to the project owner rather than assumed. Owner chose to add a real
  MIT `LICENSE` file, so the badge now reflects something real, not a
  guess.
- "See it run" section uses an actual captured transcript from running
  `python -m query.ask "what happens after T1059.001 for APT29?"`
  (`LLM_PROVIDER=openai`) against the real graph - not a mockup or
  hand-written example. This is the same case already verified in this
  file's "Query CLI end-to-end test" entry; re-ran it live rather than
  copying that entry's prose description, so the README shows the
  literal terminal output, retrieved-facts block included. No GIF/image
  tooling was available in this environment, so a real, verifiable text
  transcript was used instead of a mockup screenshot.
- Comparison table ("ATT&CK Navigator / static lookup" vs. this project)
  pulls its four rows directly from four `docs/attack-patterns/*.md`
  case files' existing "The Present Problem" sections (T1566.001,
  T1059.001, T1078, T1057) - no new claims written for the table itself.
- Repository-structure tree mirrors CLAUDE.md's Architecture section
  bullets exactly (verified against a real `find` of the repo, not
  reconstructed from memory) so the two documents can't silently drift
  apart on what the structure actually is.
- Quick Start's `pytest tests/` step deliberately doesn't promise a
  fixed pass count, since the EVTX cross-check tests' count depends on
  how many seed techniques a given checkout has fetched samples for
  (`fetch_test_logs.py --fetch`) - a fixed number would go stale the
  moment someone fetches a different subset.
- Roadmap's "Planned" section pulled straight from this file's own
  "Next" notes (cross-group comparison edges, KimiProvider, 0.65-tier
  re-sourcing, multi-hop retrieval, extending test coverage/CI) rather
  than any broader platform-pitch language - consistent with CLAUDE.md's
  "Do NOT" section.
