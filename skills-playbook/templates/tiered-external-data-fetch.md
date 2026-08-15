---
name: tiered-external-data-fetch
description: "Use this skill when you need real [PLACEHOLDER: external test/reference data - e.g. sample logs, fixture datasets, reference documents] to test or validate [PLACEHOLDER: the system this fetches data for], sourced from [PLACEHOLDER: the external dataset/repo]. Documents which of your project's own entities have matching real samples, which fidelity tier to use for which purpose, and a script to pull them."
---

# Tiered External Data Fetch

A pattern for pulling real external data (not synthetic/invented
fixtures) to validate a project against, when that external source
offers multiple versions of the same underlying data at different
levels of fidelity or redaction - e.g. raw vs. partially-filtered vs.
fully-sanitized.

## Source

`[PLACEHOLDER: source URL/repo]` - **verify this against the live
source while writing the skill, not from memory or from the source's
own marketing description.** [PLACEHOLDER: what you actually verified -
its README, its own manifest/index file, its directory structure via
the source's API - and the real, current scale, e.g. "N items across M
categories."]

## The tiers - and the cautionary lesson this template exists to encode

If your source offers multiple tiers/variants of the same data (e.g. a
"raw" version and one or more "filtered" versions), document each
tier's real scope in a table like this:

| Tier | [PLACEHOLDER: directory/flag] | What's removed | What remains |
|---|---|---|---|
| [PLACEHOLDER] | | | |

**The load-bearing lesson: verify a dataset's real structure yourself -
don't trust its README's claimed structure at face value.** A dataset's
documentation describes what it *intends* to do; it doesn't always
describe *where exactly* that applies. The specific, real precedent this
template generalizes from: a security-testing project fetching a public
attack-simulation log dataset found that a tier's documented "sanitized"
filtering (stripping offensive-tool names from log content) only applied
to one file format within each scenario folder - the raw log files
sitting alongside it were byte-identical across every tier, unfiltered,
because the redaction step only ever touched a JSON export, not the
original files it was exported from. This was only caught by actually
diffing file sizes across tiers for the same sample, not by reading the
README. **If you don't independently verify which specific files a
claimed transformation actually touches, you can build validation
tooling that silently uses unfiltered data while believing it's using
the filtered tier** - the exact failure mode this caution exists to
prevent. Do the equivalent check for your own source before writing
anything that depends on a tier boundary: fetch one sample from each
tier, diff/compare the actual files (sizes, byte-for-byte where
feasible), and confirm the redaction/filtering you're relying on is
present in every file your consumer actually reads - not just the ones
you assumed it would touch.

## Which tier for which purpose

[PLACEHOLDER: for each tier, state the concrete reason to pick it - e.g.
"use the most-redacted tier when testing whether your logic holds up
without relying on literal [PLACEHOLDER] strings" / "use raw only when
the literal, unmodified ground truth is needed."]

## Cross-reference against this project's own entity set

Compute which of your project's own entities (e.g. your seed set, your
catalog) have matching real samples in the external source - by matching
IDs/keys, not eyeballing. State the real, verified result (e.g. "N of M
entities have matching samples"), and **do not invent samples for the
entities that don't have any** - note the gap honestly; if coverage for
those is ever needed, it has to come from a different source.

## Fetching samples

`[PLACEHOLDER: path to your fetch script]` - [PLACEHOLDER: stdlib-only
if you can manage it, so this doesn't add a new project dependency just
for test-data fetching]. Suggested CLI shape:

```bash
# list which of your entities have matches - no download
python [PLACEHOLDER: script] 

# download N samples per matched entity, default tier
python [PLACEHOLDER: script] --fetch

# more samples, a different tier
python [PLACEHOLDER: script] --fetch --tier [PLACEHOLDER] --limit N
```

Output lands in `[PLACEHOLDER: e.g. data/test_logs/<tier>/<entity>/]`
(gitignored - this is fetched test data, not committed). If the source
has an API rate limit, note the auth-token override that raises it.

## Scope - what this is not

This is a data-fetching utility, not automatically wired into a test
suite or CI. It exists so real test/validation data is one command away
whenever it's actually needed - not because that consuming work has
started. [PLACEHOLDER: if/when this does get wired into an automated
test, cross-reference that test file here.]
