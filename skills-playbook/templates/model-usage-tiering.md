---
name: model-usage-tiering
description: "Use this as a standing convention (not a one-off skill invocation) for which AI model tier to reach for on which kind of task in this project - [PLACEHOLDER: name your model provider/tiers], applied consistently rather than defaulting to one model for everything."
---

# Model Usage Tiering

Not every task in a project deserves the same model. This is a
generalized version of a convention that wasn't originally written as
its own formal skill - it lived as a section in a project's status file
- but the pattern is clean, fully domain-agnostic, and worth adopting
deliberately rather than reinventing by feel each time.

## The core principle

**Match the model tier to the cost of an undetected mistake, not to raw
task complexity.** A task can be "simple" in the sense of being
mechanical and still deserve a stronger model if a wrong output there
becomes silently-wrong committed data that's expensive to catch later. A
task can look "complex" in the sense of being long or multi-step and
still be fine on a cheaper/faster model if any mistake is immediately,
cheaply checkable (the code runs or it doesn't; the test passes or it
doesn't).

## A three-tier shape (adapt tier names/models to your provider)

**[PLACEHOLDER: cheap/fast tier]** - mechanical, single-correct-answer
tasks with an immediately checkable outcome: running a script and
reading off a count, environment/dependency troubleshooting,
formatting-only edits, writing up a log entry whose content is already
decided. Reasoning depth buys little here; speed and cost efficiency
matter more.

**[PLACEHOLDER: default/mid tier]** - the bulk of real engineering work:
implementing features, drafting documentation once the supporting
research is already in hand, general research and fact-gathering,
routine edits and code review. Sustained work that needs solid reasoning
and quality but isn't the highest-stakes judgment call in the project.

**[PLACEHOLDER: high-reasoning tier]** - high-stakes judgment calls
where a subtle mistake becomes invented or silently-wrong data baked
into the project's actual output: [PLACEHOLDER: your project's own
highest-consequence surfaces - e.g. "assigning a confidence score to a
claim," "designing a schema other components will depend on,"
"reconciling conflicting evidence across sources before committing to a
conclusion"]. **Tie this tier's use to a real, specific incident where
it would have mattered, if you have one** - a documented case is a far
stronger justification for spending more here than an abstract
"important things deserve a smarter model." The project this pattern was
generalized from ties its high-reasoning tier directly to a real,
dated incident: a plausible-sounding but factually reversed causal
relationship between two data points that was committed, pushed, and
only caught later during unrelated research - exactly the failure mode
("plausible but wrong" from a faster/cheaper pass) that tier exists to
prevent from happening again in the same class of task.

## How to apply it

State the convention explicitly in your project's living status file
(see the `build-and-document` template) as a standing rule, not a
per-task decision to re-litigate: "apply this without being re-asked,"
via a session-wide model setting for broad work, or a per-task override
when spawning a sub-agent for one specific high-stakes step.

| Task | Tier | Why |
|---|---|---|
| [PLACEHOLDER] | [PLACEHOLDER] | [PLACEHOLDER] |
| [PLACEHOLDER] | [PLACEHOLDER] | [PLACEHOLDER] |
| [PLACEHOLDER] | [PLACEHOLDER] | [PLACEHOLDER] |

## Do NOT

- Don't default to one model for the entire project out of convenience
  - the whole point is that different tasks carry different real risk.
- Don't reach for the high-reasoning tier reflexively for anything that
  "sounds important" - reserve it for tasks where a wrong output is
  genuinely hard to catch after the fact, not just tasks that feel
  high-stakes emotionally.
- Don't skip the cheap/fast tier for genuinely mechanical work out of
  an instinct that "more reasoning is always better" - it isn't free,
  and it doesn't change the outcome of a task with one checkable right
  answer.
