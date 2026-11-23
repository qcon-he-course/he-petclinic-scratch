# The line

The delivery line from Week 5's blueprint, tried on this repository. An item is an issue. The orchestrator is GitHub Actions. The source the line works on is the branch `line`, cut from the commit before PC-303 was merged, so that PC-303 can go down the line from its one sentence.

Built so far: **Intake**. The other seven stages are not built.

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

The item's state is its labels: `stage:*`, `type:*`, and one of `called:*`, `returned`, `stuck`, `admitted`. Every result comment ends with the result as data and a marker, `<!-- line:result stage=… box=… run=… -->`, so that later stages can read the item. A stage that reads results must take them only from comments by `github-actions[bot]`.

To run Intake again on an item: Actions, "line: intake", Run workflow, with the item's number.

## What differs from the slides

- The classifier reads the code. On the slide it posted a fact about the code with no read of it.
- A duplicate returns the item to the requester and names the other item. Nothing is written to the other item.
- One job posts for all three boxes, after they finish, so that no job holds both a key and the right to write.
- "Anyone can ask" is narrowed to the requesters in `people.json`.
- The class admitted alone is a confirmed defect. The slide's "inside a budget" is not modelled.

## Not exercised yet

- The path where an item brings a failing test (`intake-check` with a proof). The report reader is tested; the Maven run is not.
- A returned item has no trigger of its own to come back: the requester edits it, and Intake is run again by hand.

## Tests

    python3 -B -m unittest discover -s .github/line/tests -v

No network, no key, no model: every agent output in the tests is written by hand.
