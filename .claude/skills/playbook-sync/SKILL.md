---
name: playbook-sync
description: "Use this skill any time a new skill is created under .claude/skills/, or an existing skill's SKILL.md changes meaningfully (a real change to its trigger conditions or methodology - not a typo fix or wording polish). Generalizes the skill into a domain-agnostic template in skills-playbook/templates/, the same way the original six skills were generalized, and keeps skills-playbook/README.md's template index in sync with what's actually in that folder."
---

# Playbook Sync

`skills-playbook/` (see its own `README.md`) exists to stay a live
reflection of the skills actually built and used in this project - not
a one-time snapshot from the day it was created. This skill is the
discipline that keeps it that way: every time this project's own skill
set changes in a way that matters, the corresponding template gets
generalized or updated too, in the same session, not "eventually."

## When to trigger

- **A new skill is created** under `.claude/skills/<name>/SKILL.md`.
- **An existing skill's SKILL.md changes meaningfully** - a real change
  to its trigger conditions (when it fires) or its methodology (what it
  actually does when triggered). This is a judgment call, not every
  edit: a typo fix, a wording polish, or a factual update to an example
  (e.g. an edge count changing after new data is added) does **not**
  count. A change to *what the skill covers* or *when it runs* does.

**Not** triggered by:
- Routine use of an existing, unchanged skill.
- Changes to files a skill produces (e.g. a new ADR, a new case file) -
  those are the skill working as designed, not the skill itself
  changing.

## What to do when actually triggered

1. **Read the new/changed `SKILL.md` in full**, plus (if it exists) the
   corresponding template already in `skills-playbook/templates/` - you
   may be updating an existing generalization, not creating a new one.
2. **Generalize it the same way the original six were generalized** (see
   any existing template in `skills-playbook/templates/` for the
   pattern to match):
   - Strip project-specific content (this project's exact file paths,
     domain terms, data shapes) down to the reusable pattern underneath
     it.
   - Insert `[PLACEHOLDER: ...]` markers exactly where a new project's
     specifics need to go - specific enough that filling them in is
     obvious, not so vague the placeholder itself needs explaining.
   - Preserve the *reasoning*, not just the mechanics - a template that
     says what to do without saying why is worth much less than one
     that carries the "why" forward. Where the original skill's
     reasoning is tied to a real incident in this project (the way
     `red-team-assessment`'s methodology is tied to a real prompt-
     injection finding, or `generate-diagrams`'s idempotency requirement
     is tied to a real verified guarantee), keep that as a concrete,
     attributed example in the template - genericizing away the *proof*
     that a pattern works is a real loss, not just a style choice.
   - Frontmatter (`name`/`description`) gets genericized the same way -
     the `description` should read as a template's usage note (who
     should reach for this and when), with placeholders for whatever is
     project-specific about the trigger conditions.
3. **Save or update the file** at
   `skills-playbook/templates/<generalized-name>.md`. If this is an
   update to an existing template (the original skill already had one),
   edit it in place rather than creating a second file - the template
   should track the current, real skill, not accumulate stale versions.
4. **Update `skills-playbook/README.md`'s template table** whenever a
   template is added or its purpose changes meaningfully - the README's
   index and the actual contents of `templates/` must never drift apart.
   A template file that exists but isn't listed, or a README row
   pointing at a template that no longer matches what the file actually
   contains, is exactly the kind of staleness this skill exists to
   prevent.
5. **Follow `build-and-document`'s discipline** for the sync itself:
   this is a real, if small, engineering decision each time it happens -
   update CLAUDE.md and the build log the same session, not deferred.

## What NOT to do

- **Don't force-generalize a skill that's genuinely too domain-specific
  to be reusable elsewhere.** Not every skill in a project is a
  transferable pattern - some are tied to a specific external dataset,
  a specific vendor's API shape, or a specific regulatory requirement in
  a way that no amount of `[PLACEHOLDER: ...]` markers meaningfully
  generalizes. When this is the case, **say so explicitly** - a short
  note in this skill's own trigger log (or a comment in the relevant
  CLAUDE.md/build-log entry) stating which skill was reviewed and why it
  was judged not worth templating, rather than silently skipping it or,
  worse, templating it anyway just to keep the count even. A playbook
  with six genuinely useful templates is worth more than one with ten
  where four are unusable boilerplate because the domain-specific parts
  couldn't actually be stripped out.
- Don't generalize a skill that hasn't stabilized yet - if a skill is
  still being actively reshaped across sessions (trigger conditions
  still being tuned, methodology still changing), wait until it's
  reasonably settled rather than generalizing a moving target and
  needing to redo the template every time the source skill changes
  again.
- Don't let the template drift from the real skill's current behavior -
  if in doubt whether a template is still accurate, re-read the current
  `SKILL.md` it was generalized from rather than trusting the template's
  own age.

## Cross-references

- `.claude/skills/build-and-document/SKILL.md` links to this skill,
  same pattern as its existing links to `red-team-assessment` and
  `scale-to-continuous-ingestion`.
- `skills-playbook/README.md`'s "How to use" section points back here as
  the discipline that keeps the playbook synced going forward.
