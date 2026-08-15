# Skills Playbook

This is a set of generalized [Claude Code skill](https://docs.claude.com/en/docs/claude-code)
templates, extracted from the actual skills used to build the parent
project (a MITRE ATT&CK knowledge-graph prototype - see the root
[README.md](../README.md) and [CLAUDE.md](../CLAUDE.md)). Nothing here
is theoretical: every pattern in `templates/` was a real, load-bearing
skill in that project first, and this folder exists so the discipline
behind it - not the ATT&CK-specific content - can travel to a different
project.

## Philosophy

### 1. Skills as quality disciplines, not just task shortcuts

A Claude Code skill is often framed as a shortcut - a way to avoid
re-typing a common instruction. That's not what earned these seven a
place in this playbook. Each one exists because, without it, a specific
class of mistake had already happened once, or was structurally likely
to happen: a decision made and then forgotten, a generated file
hand-edited and then silently overwritten, a claim treated as verified
when it wasn't. A skill, used this way, is a standing check against a
specific failure mode - the same reason a linter or a test suite earns
its place, not because it's faster than writing the code by hand.

### 2. Separate generated from hand-authored content, visibly

**From this project:** `graph/generate_diagrams.py` regenerates several
Mermaid diagrams directly from the project's data. The project's own
`generate-diagrams` skill requires - and this was verified for real, not
just asserted - that running the generator twice with unchanged input
data produces **byte-identical** output, because every graph traversal
is sorted by a stable key rather than relying on iteration order. That
guarantee is what makes the auto-generated/hand-authored boundary
trustworthy: a reviewer can see a diagram diff and know it reflects a
real data change, not generator noise, because the alternative (jitter
on every run) was checked for and ruled out empirically. The generated
regions live inside explicit `<!-- BEGIN GENERATED -->` /
`<!-- END GENERATED -->` markers specifically so the boundary is visible
in the file itself, not just in a skill doc someone might not have read.
See `templates/generate-diagrams.md`.

### 3. Document decisions at the moment they're made, not reconstructed later

**From this project:** while sourcing an unrelated new edge, re-reading
a primary source (Volexity's "Nearest Neighbor Attack" report) revealed
that a previously-committed edge had the causal direction backwards -
and that edge had *already been pushed to `origin/main`*. The fix wasn't
a silent rewrite of history: it was a new commit, with the two affected
documentation case files updated to include an explicit correction note
rather than quietly replacing the old (wrong) claim. The mistake is
still visible in the project's history, on purpose - a defensible,
audited correction is worth more than a record that looks like it was
always right. This is what "document decisions at the moment they're
made" is actually for: not making the log look clean, but making it
*true*. See `templates/build-and-document.md`.

### 4. Defer scope deliberately, with a written trigger - not silently, not "just in case"

**From this project:** `ingestion/` has sat as an empty, deliberately
unbuilt placeholder directory since the project's first session. The
design thinking for what would eventually go there - a multi-agent
continuous data-ingestion pipeline - is written down in full, but gated
behind a skill (`scale-to-continuous-ingestion`) whose entire job is
refusing to trigger on anything short of a real, explicit decision to
build it: not "this would be cool eventually," not routine build
sessions that happen to touch a nearby file. The difference between this
and simply not building something is that the *reasoning* for deferring
it, and the exact condition that would change that, are both written
down where a future reader (including a future session) can find them -
scope stays deliberately small without the thinking behind that
choice getting lost. See `templates/deferred-scope-design-doc.md`.

### 5. Never let output claim something is verified without it actually being verified

**From this project, twice, independently:**

- A supplied fixture file for a future schema design doc cited a named
  report - a specific title and report ID, attributed to a real
  publisher - that turned out not to exist. It would have been easy to
  include it as a labeled "example" and move on; instead, it was
  independently re-checked (two separate searches, for the title and
  for the report ID) before anything permanent got written, and once
  neither search turned up a real match, the fixture was excluded
  entirely - not saved anywhere in the repo, not referenced even as a
  disclaimed example. The project's documented reasoning: a fabricated
  citation in an unbuilt design doc is exactly the kind of thing that
  looks harmless until someone builds against it later, trusting that
  it was checked.
- A public attack-simulation log dataset documented three filtering
  tiers, each claiming to redact more than the last. Its README's
  description of what got filtered was correct as far as it went - but
  only for one file format inside each sample. The project verified this
  directly (diffing file sizes for the same sample across tiers) rather
  than trusting the README's claim, and found the raw log files
  themselves were byte-identical across every tier - completely
  unfiltered - while only a JSON export alongside them actually changed.
  Building test tooling on the README's claimed structure alone would
  have silently used unfiltered data while believing it was using the
  filtered tier.

Both are instances of the same discipline: **a claim about data - a
citation, a documented transformation - gets verified against the real
thing before it's trusted, not accepted because the source seems
credible.** See `templates/tiered-external-data-fetch.md` and
`templates/deferred-scope-design-doc.md`.

## What's here

| Template | Generalizes | Use it for |
|---|---|---|
| `build-and-document.md` | The project's core ADR + status-file + build-log discipline | Capturing real engineering decisions as they happen. **Start here - this is the most broadly useful template in the set.** |
| `entity-case-file-doc.md` | Per-technique attack-pattern case files | A structured write-up per new instance of any domain entity your project accumulates |
| `tiered-external-data-fetch.md` | Fetching real Atomic Red Team-simulated test logs | Pulling real (not synthetic) external test/reference data, especially from a source with multiple fidelity tiers |
| `generate-diagrams.md` | The project's Mermaid diagram generator | Auto-generating diagrams/artifacts from live data while keeping rarely-changing structural diagrams hand-authored, with the line between them visible |
| `red-team-assessment.md` | The project's three-lens (LLM/code/web) security assessment | Growing a security-review discipline one real lens at a time, only as your project actually grows that attack surface |
| `deferred-scope-design-doc.md` | The ingestion and scalability design docs | Writing down a real future direction (scaling, a bigger pipeline) without building it early, with an explicit, checkable trigger for revisiting |
| `model-usage-tiering.md` | The project's Haiku/Sonnet/Opus tiering convention | Matching AI model tier to the cost of an undetected mistake, not to raw task complexity |

## How to use

1. Copy the template(s) you actually need into your own project's
   `.claude/skills/<name>/SKILL.md` - don't adopt all seven on day one.
2. Fill in every `[PLACEHOLDER: ...]` marker with your project's real
   specifics. A template with placeholders still in it isn't ready to
   use - it's a draft.
3. Add skills incrementally, as real needs arise - the way this
   project's own skills were actually built (one added per real gap
   that showed up during real work), not all seven adopted speculatively
   before you know which ones your project will actually need.
4. If you build a new skill (or meaningfully change an existing one) in
   a project that has adopted this playbook, generalize it back the same
   way these seven were generalized - see this project's own
   `.claude/skills/playbook-sync/SKILL.md` for the discipline that keeps
   this playbook synced to the skills actually in use, rather than
   drifting stale.
