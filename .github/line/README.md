# The line

The delivery line from Week 5's blueprint, tried on this repository. An item is an issue. The orchestrator is GitHub Actions. The source the line works on is the branch `line`, cut from the commit before PC-303 was merged, so that PC-303 can go down the line from its one sentence.

Built so far: **Intake**, **Understand** and **Shape, part one**. Shape's parts two and three and the other five stages are not built.

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

## Not exercised yet

- The path where an item brings a failing test (`intake-check` with a proof). The report reader is tested; the Maven run is not.
- A returned item has no trigger of its own to come back: the requester edits it, and Intake is run again by hand.
- At Understand: a round that hands the agent its refused result.
- At Shape: everything on GitHub, and the session itself.

## Tests

    python3 -B -m unittest discover -s .github/line/tests -v

No network, no key, no model: every agent output in the tests is written by hand. The Understand pipeline (write, format, run, PIT, read) was also run once by hand on a checkout of `line`, with stand-in pins.
