#!/usr/bin/env python3
"""stage: let an admitted item into Understand, and gather what the agent is given. No model, no key.

  stage.py understand <issue.json> <comments.json> <line dir> <out dir> <round> [<previous dir>]

<issue.json> and <comments.json> are the issue and its comments as GitHub's API
returns them. <previous dir>, on a round after the first, holds what the round
before left: pin-agent.json or pin-agent.why, and mutation-sensor.json.

Writes, into <out dir>:
  item.json      the idea, the type (from the item's "type:" label), the owner, the round
  intake.json    what Intake's boxes posted on the item
  previous.json  on a later round: the agent's earlier result and what was wrong with it
  effects.json   labels, and a comment when the item may not enter

Prints go=yes or go=no, also to $GITHUB_OUTPUT. The item enters when a named
requester filed it through the form, it is admitted and has an owner, and the round
is within the limit policy.json sets.
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
    result = load(agent) if os.path.isfile(agent) else None
    reason = text(why).strip() if os.path.isfile(why) else None
    run = load(sensor) if os.path.isfile(sensor) else None
    return {"round": round_ - 1, "what_was_wrong": understand_gate.problems(result, reason, run)[0],
            "your_result": result, "sensor": run}


def main(argv):
    if len(argv) not in (6, 7) or argv[0] != "understand" or not argv[5].isdigit():
        print(__doc__.split("\n\n")[1], file=sys.stderr)
        return 2
    issue, comments, line, out, round_ = load(argv[1]), load(argv[2]), argv[3], argv[4], int(argv[5])
    policy, people = load(os.path.join(line, "policy.json")), load(os.path.join(line, "people.json"))
    os.makedirs(out, exist_ok=True)
    got, intake, why = enter(issue, comments, policy, people, round_)
    effects = {"comments": [], "add": [], "remove": [], "assign": []}
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
