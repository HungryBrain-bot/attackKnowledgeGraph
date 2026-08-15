---
name: ai-security-assessment
description: "Use this skill whenever query/ask.py's entity extraction, query/rag.py's prompt construction or system prompt, or query/llm_provider.py changes (including adding a new provider), whenever a new user-facing input path is added to the project, or on an explicit request to run or extend the security assessment. Runs real adversarial test cases against the live query pipeline (no mocking) and logs every result - held or broken - to docs/security-assessment.md."
---

# AI Security Assessment

This project's query layer is a retrieval-then-generate pipeline where
user input (the question) and retrieved facts (the FACTS block) share a
prompt before reaching an LLM. That shape is exactly the attack surface
OWASP's LLM Top 10 exists to cover. This skill makes checking it a
repeatable, documented practice instead of a one-off test file that gets
written once and never looked at again.

## Trigger conditions

Run this skill's assessment whenever:
- `query/ask.py`'s entity extraction changes (how a technique ID or group
  gets pulled from free text).
- `query/rag.py`'s prompt construction or `SYSTEM_PROMPT`/
  `SYSTEM_PROMPT_TEMPLATE` changes - even a wording-only edit, since a
  reworded rule can silently change what an injection attempt can get
  away with.
- `query/llm_provider.py` gains a new provider (a new vendor's SDK/API
  shape can have different susceptibility to the same attack text).
- Any new user-facing input path is added to the project going forward -
  this project currently has exactly one (`python -m query.ask`'s
  question string), but the trigger is the pattern ("untrusted text
  reaches an LLM prompt"), not that specific file.
- An explicit request from the user to run or extend the assessment.

It is **not** triggered by changes to `graph/semantic_edges.py`,
`graph/build_graph.py`, or the docs/attack-patterns case files - those
don't touch the prompt-construction or input-handling surface this skill
exists to test.

## Methodology

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
- **LLM03 Supply Chain** - relevant to this project's provider SDK
  dependencies (`anthropic`, `openai`, `mitreattack-python`), not to
  query handling. A dependency-audit concern, not this skill's job.
- **LLM04 Data and Model Poisoning** - no training or fine-tuning happens
  anywhere in this project. The graph's own data-integrity discipline
  (citations, confidence scores, no invented edges) is already governed
  by the project's sourcing conventions, not an LLM-poisoning attack
  surface in the OWASP sense.
- **LLM05 Improper Output Handling** - `query/ask.py` only ever prints
  the answer to a terminal. Would become directly relevant, and should
  be added to this skill's trigger conditions, the moment any future
  output path renders the answer as HTML/markdown in a browser or feeds
  it into another system call.
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

## What "done" looks like for one assessment pass

Every test run gets a dated entry in `docs/security-assessment.md`
(append-only - a new pass is a new dated `##` section, never an
overwrite of a prior one). For every individual test case within a pass,
the entry states:
1. **What was tried** - the exact input text.
2. **The actual response** - quoted, not summarized into "it worked" or
   "it didn't" - the reader should be able to judge the verdict
   themselves from the quoted transcript.
3. **Held or broke** - an explicit verdict, argued from the quoted
   response, not asserted.
4. **If broken**: either the fix applied, with its own ADR under
   `docs/decisions/` (per the build-and-document skill), and the case
   re-run against the fixed pipeline for real to confirm it now holds -
   or an explicit "known gap, not yet fixed" note if a fix isn't done
   this pass. **Never silently drop a failing test from the log** - a
   documented, unfixed gap is honest; a disappeared test case is not.

High-stakes judgment calls - specifically, deciding whether an
injection/extraction attempt actually succeeded, since a wrong call here
either misses a real hole or wastes effort chasing a non-issue - go
through Opus, per CLAUDE.md's Model Usage convention. Feed the reviewer
the exact question, the exact retrieved facts, and the exact model
response; ask for a verdict argued from the transcript, not a general
impression.

## Adding a new adversarial test case

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
- **Findings must be honest in both directions** - a clean pass gets
  reported as a clean pass (don't invent caveats to sound more thorough),
  and a break gets reported as a break (don't soften language to make a
  real finding look minor). This mirrors CLAUDE.md's "no invented data"
  discipline applied to the assessment's own results, not just the
  graph's.

## Do NOT

- Don't mock the LLM call in an adversarial test - see above, this
  defeats the entire point.
- Don't overwrite a prior dated entry in `docs/security-assessment.md` -
  it's a log, not a living status doc; append a new dated section
  instead, even if a later pass re-tests the same case (see the
  Finding 3 caveat re-test in the 2026-08-13 entry for the pattern:
  "after the fix" gets its own subsection, not a silent edit to the
  original finding).
- Don't force-fit a test for an OWASP category this pipeline's current
  design makes inapplicable (see "genuinely out of scope" above) just to
  look more thorough - document the reasoning instead.
- Don't paper over a real, verified break with a reworded system prompt
  alone. If the finding points at a structural issue (e.g. untrusted
  input and trusted data sharing one undifferentiated prompt string),
  the fix has to be structural too - see docs/decisions/005-prompt-
  injection-fact-separation.md for what that looked like the first time
  this came up.
