# The line

The delivery line from Week 5's blueprint, tried on this repository. An item is an issue. The orchestrator is GitHub Actions. The source the line works on is the branch `line`, cut from the commit before PC-303 was merged, so that PC-303 can go down the line from its one sentence.

Built so far: **Intake**, **Understand** and **Shape**, all three parts. The other five stages are not built.

## Intake

| Box on the slide | Here | Model | May write |
|---|---|---|---|
| Requester files an idea | The issue form "An idea for the line" | none | the issue |
| Intake agent | job `intake-agent`: Claude Code, headless, no shell | Claude | nothing |
| Intake check | job `intake-check`: runs a failing test the item names | none | nothing |
| Classifier agent | job `classifier`: Codex, read-only sandbox | OpenAI | nothing |
| Admission gate | job `admission-gate`: `lib/gate.py`, the policy in `policy.json` | none | the issue |
| A person admits | the label `admit`, then job `admit`: `lib/admit.py` | none | the issue |

The workflow is `.github/workflows/line-intake.yml`.

1. Filing the form starts the workflow. The `door` job reads the issue as an item (`lib/item.py`). Only a requester named in `people.json` starts the agents: the repository is public, and each item spends two API calls.
2. The two agents and the check run side by side. An agent's job holds one API key and has no permission to write. Its output is a result only when `lib/check.py` accepts it: the schema, a size a person can read, and every place it cites must exist in the checkout.
3. The gate's job holds no key. It posts each box's result on the item as a comment, then applies the policy: stuck (a box left no result), returned (not ready), admitted (the narrow class), or called (a person).
4. A person admits by adding the label `admit`. The job checks that the person holds the role that admits the item's type, assigns them as the owner and moves the item to `stage:understand`. To change the type first, swap the `type:` label.

The item's state is its labels: `stage:*`, `type:*`, and one of `called:*`, `returned`, `stuck`, `admitted`. Every result comment ends with the result as data and a marker, `<!-- line:result stage=… box=… run=… -->`, so that later stages can read the item. The data also says what ran the box: the tool, the model, the turns, the cost and the seconds. A stage reads results with `read_results` in `lib/common.py`, which takes them only from comments by `github-actions[bot]`.

Every place an agent cites comes with a quote of at least eight characters, and `lib/check.py` looks for the quote in the cited lines. A place that is not there, or a quote that is not at that place, voids the whole result.

To run Intake again on an item: Actions, "line: intake", Run workflow, with the item's number.

## Understand

| Box on the slide | Here | Model | May write |
|---|---|---|---|
| Pin-requirements agent | job `pin-agent`: Claude Code, headless, no shell | Claude | nothing |
| Mutation sensor | job `mutation-sensor`: writes the agent's files, formats, runs the pins, runs PIT | none | nothing |
| Understand gate | job `understand-gate`: `lib/understand_gate.py`, then a push | none | the issue, the branch `item-<number>` |

The workflow is `.github/workflows/line-understand.yml`. Admission starts it with a dispatch.

1. The `door` job lets an admitted item in (`lib/stage.py`) and gathers the item, what Intake posted on it and, on a later round, what the round before left.
2. The agent holds a key, so it runs nothing and writes nothing. It returns the pins as data: for each behavior, a test that exists (cited) or a new test file, whole (written). `lib/check.py` holds the result to this: a new file under `src/test/java/`, labelled `@Tag("observed")`, and every pin names a test method that is there.
3. The sensor's job holds no key, so it can run the agent's code. It writes the files into a checkout of `line`, formats them, runs the pins, then runs PIT on the production classes the agent named, with every pin run against every mutant. A pin that failed for at least one mutant can fail. A pin that mutants ran under and that failed for none cannot fail. A pin no mutant ran under is not judged: PIT changes Java classes, and the behavior is in a template or a message file.
4. The gate advances the item when every pin passes and none is one that cannot fail: it pushes the written pins to `item-<number>`, cut from `line`, and moves the item to `stage:shape`. It returns the item to the agent, with the reasons, when a pin does not build, does not pass or cannot fail: up to three rounds. It marks the item `stuck` when the rounds are used up or the mutation run left no report.
5. Behavior the agent finds suspect is filed as a new item in the form's shape, labelled `suspect`.

## Shape, part one

| Box on the slide | Here | Model | May write |
|---|---|---|---|
| Product owner and assistant | Claude Code on the owner's computer, in a working folder on the item's branch | the owner's own | the item's branch |
| Refine-requirement skill | `shape/refine-item/SKILL.md`, copied into that folder | | |
| Commit check, in the session | `lib/shape_check.py commit`, as a pre-commit hook | none | nothing |
| Commit check, in the orchestrator | job `commit-check` in `line-shape.yml`: `lib/shape_check.py branch` | none | the issue |

1. The owner runs `.github/line/shape/start-session.sh <item>` from a clone on the default branch. It makes a working folder on `item-<number>` beside the clone, writes `.line/item.md` (the idea, the pins, the suspects, Intake's notes: `lib/brief.py`), copies the skill in and installs the hook.
2. In Claude Code the owner says: "Refine item <number> with me. Use the refine-item skill." The skill asks in rounds and writes each decision to `openspec/changes/item-<number>/decisions.md`, terms to `GLOSSARY.md`, and a hard-to-reverse trade-off to `docs/adr/`.
3. The check allows a commit to change only those files, and holds the log to its form. The hook runs it before each commit, and `git commit --no-verify` skips it.
4. The owner adds the label `answered`. The job checks that they are the item's owner, then runs the check on every commit of the branch since Understand's pins, and requires that no question is open. A pass lists the decisions on the item. A failure takes the label off again.

## Shape, part two

| Box on the slide | Here | Model | May write |
|---|---|---|---|
| Spec-drafter agent | job `spec-drafter`: Claude Code, headless, no shell | Claude | nothing |
| Completeness check | job `completeness-check`: `lib/spec_check.py` | none | nothing |
| Reviewer | job `reviewer`: Codex, read-only sandbox, a fresh session | OpenAI | nothing |
| Resolves, or asks; the owner decides when asked | job `draft-gate`: `lib/draft_gate.py`, then a push | none | the issue, the branch |

The workflow is `.github/workflows/line-shape-draft.yml`. A passing commit check starts it with a dispatch.

1. The drafter reads the decisions log, the glossary, the pins and the templates in `openspec/schemas/baseline/templates/` on the item's branch, and returns `proposal.md` and each delta spec, whole. Every scenario carries `CHECKED AT <level>` and `DECIDED BY <decisions>`.
2. The completeness check writes the draft into a checkout and holds it to the template's form. Every decision of the log is named by a scenario's DECIDED BY or listed in the proposal under "Decisions with no scenario". Every pin a decision changes is named in the proposal's Impact.
3. The reviewer runs only on a complete draft, with the draft in its checkout and nothing of the drafter's earlier rounds. It checks each decision against its scenarios and the draft against the pins. Each finding quotes the draft.
4. The gate returns gaps and findings to the drafter, up to three rounds. A question from the drafter parks the item and calls the owner. So do findings that stand after the last round: the drafter and the reviewer do not agree, and that is a question for a person. The owner answers in a session as in part one, and marking the item answered starts the drafter again, from the draft it had.
5. With no gap, no finding and no question, the gate commits the draft to `item-<number>` and labels the item `draft-reviewed`.

## Shape, part three

| Box on the slide | Here | Model | May write |
|---|---|---|---|
| Product owner and assistant | Claude Code on the owner's computer, in the working folder on the item's branch | the owner's own | the item's branch |
| The skill | `shape/refine-draft/SKILL.md` | | |
| Completeness check, in the session | `lib/session_check.py commit`, as the pre-commit hook: at this stage `lib/ready_check.py` | none | nothing |
| Completeness check, in the orchestrator | job `ready-check` in `line-shape-ready.yml` | none | the issue |
| Reviewer | job `reviewer`: Codex, a fresh session, the owner's changes first | OpenAI | nothing |
| Shape gate | job `shape-gate`: `lib/shape_gate.py` | none | the issue |

1. `start-session.sh <item>` reads the item's labels. With a reviewed draft it sets the session up for part three: the brief names the draft, and the hook runs this stage's check.
2. In Claude Code the owner says: "Read the draft spec of item <number> with me. Use the refine-draft skill." The skill walks the owner through the draft, changes what they ask, and keeps the log in step: a change of behavior is a change of a decision, and goes into the log first.
3. The check allows a commit to change the draft and what part one may change. The log must be well formed with no question open, and the draft must pass the completeness check.
4. The owner marks the spec `ready`. The job runs the check on every commit of the branch. The reviewer then reads the draft as the owner left it, whether or not the owner changed it.
5. The gate returns a finding to the owner, in a session: nobody else changes the owner's spec. With no finding the item moves to `stage:design`. Ready is not approved: approval waits for Design.

## Every agent gets its result back once

When `lib/check.py` refuses what an agent returned, `lib/agent.sh` hands the result back to the same agent once, with the reasons, in `refused.json`. A misplaced quote is put right there and does not cost the stage a round. The record of what ran adds up both tries.

## What differs from the slides

- The classifier reads the code. On the slide it posted a fact about the code with no read of it.
- A duplicate returns the item to the requester and names the other item. Nothing is written to the other item.
- One job posts for all three boxes, after they finish, so that no job holds both a key and the right to write.
- "Anyone can ask" is narrowed to the requesters in `people.json`.
- The class admitted alone is a confirmed defect. The slide's "inside a budget" is not modelled.
- The pin-requirements agent does not write to the branch. It returns the files, a job with no key runs them, and the gate's job pushes them only when they hold. On the slide the agent writes first and the sensor runs after.
- A suspect pin is filed as an item, and Intake does not start for it by itself: the line's own account is not a named requester.
- "Can fail" means some mutant of the named classes fails the pin. It does not show that the pin's own assertion is the one that failed.
- At Shape the push does not start the check in CI. GitHub runs a push's workflow from the pushed branch, so an item's branch would judge itself. The label `answered` starts it from the default branch.
- The decisions are in the log on the branch, and are posted on the item when the check passes. On the slide each is saved on the item as it is made.
- At Shape, part three, the reviewer reads the whole draft every time, with the owner's changes first. On the slide it reviews what changed. The line has no record it can trust of which commit the reviewer last read.

## Not exercised yet

- The path where an item brings a failing test (`intake-check` with a proof). The report reader is tested; the Maven run is not.
- A returned item has no trigger of its own to come back: the requester edits it, and Intake is run again by hand.
- At Understand: a round that hands the agent its refused result.
- At Shape, part three: everything on GitHub, and the session. The check and the gate ran here against item 12's real branch.
- An agent's second try, on GitHub. A test runs it here with a stand-in for the agent's command.

## Tests

    python3 -B -m unittest discover -s .github/line/tests -v

No network, no key, no model: every agent output in the tests is written by hand. The Understand pipeline (write, format, run, PIT, read) was also run once by hand on a checkout of `line`, with stand-in pins. One test runs `lib/agent.sh` with a stand-in for the `claude` command.
