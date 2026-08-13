# Edge Schema Changelog

All notable changes to the semantic edge schema are documented here.
Every design decision is recorded with its reasoning so future contributors understand why the schema is shaped the way it is.

---

## [0.3.0] — 2026-05-10

### Added
- `relationship.semantic_category` — high-level traversal category independent of specific type
- `relationship.human_summary` — replaces `description`; explicitly non-machine-authoritative
- `relationship.source.entity_type` and `relationship.target.entity_type` — self-describing edges
- `confidence.sample_size` — required; a score without sample size is epistemically incomplete
- `confidence.confidence_reasoning` — structured object replacing free-text string
- `confidence_reasoning.basis` — controlled vocab for reasoning basis
- `confidence_reasoning.consistency` — high/medium/low consistency rating
- `context.operational_characteristics` — stealth level, interactive activity, user context
- `context.temporal.std_dev_hours` — required when median present; prevents single-point statistics
- `context.temporal.observed_sequence_window_hours` — min/max distribution window
- `context.objective.category` — maps objective to high-level category for coarse querying
- `context.environment.deployment_model` — cloud_native, hybrid, on_premises, unknown
- `observed_in[].observation_count` — per-group observation count
- `observed_in[].confidence` — per-group confidence distinct from aggregate edge confidence
- `evidence[].evidence_id` — unique identifier per evidence item
- `evidence[].validation` — structured validation block
- `evidence[].extracted_relationships` — which relationship types were extracted from this source
- `inference.components[].version` — pipeline component versioning for reproducibility
- `metadata.updated_at` — tracks last modification
- `metadata.ontology_namespace` — prepares for JSON-LD / RDF integration
- `metadata.tags` — optional free-form tags

### Changed
- `relationship.description` → renamed `relationship.human_summary` — non-authoritative status explicit
- `observed_in[].group_name` — **REMOVED**. Names resolved at query time from graph. Only ATT&CK IDs stored. ATT&CK group aliases change; IDs do not. Storing names causes staleness.
- `confidence.confidence_reasoning` — changed from free-text string to structured object
- `inference.components` — changed from array of strings to typed objects with name + version
- `context.objective` — expanded from flat string to structured object

### Fixed
- `relationship.source` and `relationship.target` now required. Edges without explicit source/target binding are rejected.
- `confidence.score` minimum 0.4 enforced. Edges below threshold rejected at ingestion.

### Critical Design Decisions

**Confidence score is computed by deterministic function, not LLM.**
The `confidence.score` field is the output of `f(source_count, corroboration, source_tier, recency, sample_size)`. Same inputs → same score always. An LLM asked "how confident are you?" gives non-reproducible, drifting numbers. Agents supply qualitative inputs (method, basis, consistency, source_tier judgments) that feed the function. The function does the math. This is what makes confidence scores auditable and trustworthy.

**Group names not stored in observed_in.**
Only `group_id` (ATT&CK pattern G[0-9]{4}) stored. Names resolved at query time from the graph. Prevents staleness — aliases change, IDs don't.

**human_summary retained but clearly non-authoritative.**
Kept for analyst note-taking during review. Renamed from `description` to signal it is not machine-readable truth. Never used for inference, scoring, or graph traversal logic.

**std_dev_hours required when median_dwell_hours present.**
A median without a standard deviation is a point estimate presented as a distribution. Conditional validation enforces this.

**Minimum confidence 0.4.**
Below this threshold, the evidence base is too thin for the edge to provide useful signal. Edges below threshold go to staging for additional evidence gathering, not to the live graph.

---

## [0.2.0] — 2026-05-09

### Added
- Initial `context.environment` block
- Initial `context.objective` as flat string
- Initial `confidence.method` controlled vocabulary
- Initial `observed_in` with group IDs and names
- Initial `evidence` array
- `metadata.schema_version`

### Known Issues (fixed in 0.3.0)
- Group names stored without staleness protection
- No sample_size requirement
- confidence_reasoning was free-text
- No entity_type on source/target

---

## [0.1.0] — 2026-05-08

### Added
- Initial draft
- relationship.type as plain string (no controlled vocabulary)
- confidence as single float
- observed_in as flat array of group names (no IDs)
- evidence as flat array of strings

### Known Issues (fixed in 0.2.0+)
- No entity type on source/target
- No validation pipeline defined
- Group names only, no IDs

---

## Planned — [0.4.0]

### Proposed
- `context.platform` array — maps to ATT&CK platform taxonomy
- `evidence[].ioc_references` — links evidence to specific IOCs
- `inference.llm_model_version` — tracks LLM version for audit
- `context.kill_chain_phase` — explicit ATT&CK tactic phase mapping
- `staging_metadata` block — tracks pending/review state before promotion
- `DETECTED_BY` edge: `coverage_state` field (FULL/PARTIAL/WEAK/NONE/UNKNOWN)
- `DETECTED_BY` edge: `conditions` field (required licensing, config, browser)

### Under Discussion
- Should `RELATED_TO` be deprecated in favour of forcing specific types?
- Should temporal fields move to top-level rather than nested in context?
- Should `observed_in` support campaign IDs in addition to group IDs?
- Should confidence scoring function signature be versioned in schema?
