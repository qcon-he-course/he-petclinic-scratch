#!/usr/bin/env python3
"""stage: let an item into a stage, and gather what the stage's agent is given. No model, no key.

  stage.py understand <issue.json> <comments.json> <line dir> <out dir> <round> [<previous dir>]
  stage.py draft      <issue.json> <comments.json> <line dir> <out dir> <round> [<previous dir>]
  stage.py draft-plan <comments.json> [<previous run>]

Understand:

<issue.json> and <comments.json> are the issue and its comments as GitHub's API
returns them. <previous dir>, on a round after the first, holds what the round
before left: pin-agent.json, or pin-agent.why with pin-agent.rejected.json, and
mutation-sensor.json.

Writes, into <out dir>:
  item.json      the idea, the type (from the item's "type:" label), the owner, the round
  intake.json    what Intake's boxes posted on the item
  previous.json  on a later round: the agent's earlier result and what was wrong with it
  effects.json   labels, and a comment when the item may not enter

Prints go=yes or go=no, also to $GITHUB_OUTPUT. The item enters when a named
requester filed it through the form, it is admitted and has an owner, and the round
is within the limit policy.json sets.

Draft (Shape, part two): the item enters when it is at Shape, the owner marked it
answered, and the commit check passed. Writes item.json (with the commit the check
passed on), pins.json (the pins' names and tests) and, when the draft comes back or
the item was parked, previous.json: the earlier draft, the gaps, the findings and
the questions. draft-plan prints previous=<run>: the run named, or else the run that
parked the item, so that its results can be fetched.
"""
import os
import sys

import item as form
import understand_gate
from common import clean, dump, latest, load, read_results, text


def enter(issue, comments, policy, people, round_):
    """(item, intake, None) or (None, None, reason)."""
    got, why = form.read(issue, people, policy)
    if got is None:
        return None, None, why
    labels = [l["name"] for l in issue["labels"]]
    owners = [a["login"] for a in issue.get("assignees") or []]
    if "admitted" not in labels or not owners:
        return None, None, "The item is not admitted, or has no owner. Understand starts on an admitted item."
    kinds = [l[len("type:"):] for l in labels if l.startswith("type:")]
    if len(kinds) != 1 or kinds[0] not in policy["types"]:
        return None, None, "The item must carry exactly one `type:` label."
    limit = policy["understand"]["max-rounds"]
    if not 1 <= round_ <= limit:
        return None, None, f"Round {round_} is outside the {limit} rounds the policy allows."
    got.update(type=kinds[0], type_name=policy["types"][kinds[0]]["name"], owner=owners[0], round=round_)
    results = read_results(comments)
    intake = {box: latest(results, "intake", box) for box in ("intake-agent", "intake-check", "classifier")}
    return got, intake, None


def previous(folder, round_):
    """What the round before left, for the agent that gets the item back."""
    agent = os.path.join(folder, "pin-agent.json")
    why = os.path.join(folder, "pin-agent.why")
    sensor = os.path.join(folder, "mutation-sensor.json")
    refused = os.path.join(folder, "pin-agent.rejected.json")
    result = load(agent) if os.path.isfile(agent) else None
    reason = text(why).strip() if os.path.isfile(why) else None
    run = load(sensor) if os.path.isfile(sensor) else None
    return {"round": round_ - 1, "what_was_wrong": understand_gate.problems(result, reason, run)[0],
            "your_result": result if result is not None else load(refused) if os.path.isfile(refused) else None,
            "your_result_was_accepted": result is not None, "sensor": run}


def enter_draft(issue, comments, policy, people, round_):
    """(item, pins, None) or (None, None, reason)."""
    got, why = form.read(issue, people, policy)
    if got is None:
        return None, None, why
    labels = [l["name"] for l in issue["labels"]]
    owners = [a["login"] for a in issue.get("assignees") or []]
    if "stage:shape" not in labels or "answered" not in labels or not owners:
        return None, None, "The item is not at Shape, or its owner has not marked it answered."
    limit = policy["shape"]["max-rounds"]
    if not 1 <= round_ <= limit:
        return None, None, f"Round {round_} is outside the {limit} rounds the policy allows."
    results = read_results(comments)
    checked = latest(results, "shape", "commit-check")
    if not checked or not checked.get("passed"):
        return None, None, "The commit check has not passed on the owner's decisions."
    pinned = latest(results, "understand", "pin-agent") or {"pins": []}
    kinds = [l[len("type:"):] for l in labels if l.startswith("type:")]
    got.update(owner=owners[0], round=round_, checked_head=checked["head"], decisions=len(checked["decisions"]))
    if len(kinds) == 1 and kinds[0] in policy["types"]:
        got.update(type=kinds[0], type_name=policy["types"][kinds[0]]["name"])
    pins = [{k: p[k] for k in ("name", "test", "kind", "file", "where")} for p in pinned["pins"]]
    return got, pins, None


def previous_draft(folder, round_):
    """What the round before, or the run that parked the item, left for the drafter."""
    get = lambda name: load(os.path.join(folder, name)) if os.path.isfile(os.path.join(folder, name)) else None
    draft = get("spec-drafter.json")
    refused = get("spec-drafter.rejected.json")
    why = os.path.join(folder, "spec-drafter.why")
    check, review = get("completeness.json"), get("spec-reviewer.json")
    if draft is None and refused is None and check is None and review is None:
        return None
    return {"round": round_ - 1 if round_ > 1 else "the run before the owner answered",
            "your_draft": draft if draft is not None else refused, "your_draft_was_accepted": draft is not None,
            "why_it_was_refused": text(why).strip() if draft is None and os.path.isfile(why) else None,
            "gaps": check["gaps"] if check else [], "findings": review["findings"] if review else [],
            "questions_you_asked": draft["questions"] if draft else []}


def plan_draft(comments, named):
    if named:
        return named
    found = [r for r in read_results(comments) if r[0] == "shape" and r[1] == "draft-gate"]
    return found[-1][2] if found and found[-1][4].get("outcome") == "parked" and found[-1][2].isdigit() else ""


def main(argv):
    if argv[:1] == ["draft-plan"] and len(argv) in (2, 3):
        run = plan_draft(load(argv[1]), argv[2] if len(argv) == 3 else "")
        print(f"previous={run}")
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
                f.write(f"previous={run}\n")
        return 0
    if len(argv) not in (6, 7) or argv[0] not in ("understand", "draft") or not argv[5].isdigit():
        print(__doc__.split("\n\n")[1], file=sys.stderr)
        return 2
    issue, comments, line, out, round_ = load(argv[1]), load(argv[2]), argv[3], argv[4], int(argv[5])
    policy, people = load(os.path.join(line, "policy.json")), load(os.path.join(line, "people.json"))
    os.makedirs(out, exist_ok=True)
    effects = {"comments": [], "add": [], "remove": [], "assign": []}
    if argv[0] == "draft":
        got, pins, why = enter_draft(issue, comments, policy, people, round_)
        if got:
            dump(os.path.join(out, "item.json"), got)
            dump(os.path.join(out, "pins.json"), pins)
            before = previous_draft(argv[6], round_) if len(argv) == 7 else None
            if before:
                dump(os.path.join(out, "previous.json"), before)
            effects.update(remove=["stuck", "parked"])
        elif not why.startswith("quiet:"):
            effects["comments"] = ["### Shape, part two\n\n**Not started.** " + clean(why)]
    else:
        got, intake, why = enter(issue, comments, policy, people, round_)
        if got:
            dump(os.path.join(out, "item.json"), got)
            dump(os.path.join(out, "intake.json"), intake)
            if len(argv) == 7 and round_ > 1:
                dump(os.path.join(out, "previous.json"), previous(argv[6], round_))
            effects.update(add=["stage:understand"], remove=["stuck", "stage:shape"])
        elif not why.startswith("quiet:"):
            effects["comments"] = ["### Understand\n\n**Not started.** " + clean(why)]
    dump(os.path.join(out, "effects.json"), effects)
    go = "yes" if got else "no"
    print(f"go={go}" + ("" if got else f" ({why})"))
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
            f.write(f"go={go}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
