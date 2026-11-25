#!/usr/bin/env python3
"""shape_answered: the owner marked the item answered. Run the commit check on the
item's branch, in CI, and post the result. No model, no key.

  shape_answered.py <issue.json> <sender> <clone or missing> <line ref> <line dir> <out effects.json>

<clone> is a checkout of the item's branch with its history. <sender> is the account
that added the label "answered".

The check runs when the item is at Shape and the sender is the item's owner. When it
passes, the decisions are listed on the item and the label stays. When it fails, or
may not run, the label is taken off again and a comment says why: the change goes
back to the session.
"""
import os
import sys

import shape_check
from common import BOX_NAMES, clean, data_block, dump, foot, load


def main(argv):
    if len(argv) != 6:
        print(__doc__.split("\n\n")[1], file=sys.stderr)
        return 2
    issue, sender, clone, line_ref, line, out = load(argv[0]), argv[1], argv[2], argv[3], argv[4], argv[5]
    run, url = os.environ.get("RUN_ID", "local"), os.environ.get("RUN_URL", "")
    number = issue["number"]
    labels = [l["name"] for l in issue["labels"]]
    owners = [a["login"] for a in issue.get("assignees") or []]
    effects = {"comments": [], "add": [], "remove": ["answered"], "assign": []}
    refused = None
    if "line" not in labels or "stage:shape" not in labels:
        refused = "The item is not at Shape, so there is nothing to mark answered."
    elif "draft-reviewed" in labels:
        refused = ("The item has a reviewed draft. The owner refines the draft in a session and marks the spec `ready`; "
                   "a change of a decision is made there, with the draft.")
    elif sender not in owners:
        refused = f"@{sender} is not the item's owner. The owner marks the item answered."
    elif not os.path.exists(os.path.join(clone, ".git")):
        refused = f"There is no branch `item-{number}` to check."
    if refused:
        effects["comments"] = [f"### {BOX_NAMES['commit-check']}\n\n**Not run.** {refused}\n\nThe label `answered` has been taken off again."]
        dump(out, effects)
        print("passed=no (not run)")
        return 0
    try:
        result = shape_check.check_branch(clone, number, line_ref)
    except RuntimeError as e:
        result = {"passed": False, "problems": [f"the check could not read the branch: {e}"], "decisions": [], "facts": 0, "open": [],
                  "glossary_terms": [], "adrs": [], "commits": 0, "pins_commit": None, "head": None}
    end = foot("Shape, part one", "a job, no model", run, url) + "\n" + data_block(result, "shape", "commit-check", run)
    if result["passed"]:
        wrote = [f"{len(result['decisions'])} decision(s)", f"{result['facts']} fact(s) they rest on"]
        if result["glossary_terms"]:
            wrote.append("the glossary: " + ", ".join(clean(t, 60) for t in result["glossary_terms"]))
        if result["adrs"]:
            wrote.append(f"{len(result['adrs'])} decision record(s)")
        body = (f"**Passed.** The change on `item-{number}` touches only the decisions log, the glossary and decision records, "
                f"each is well formed, and no question is open. It holds " + "; ".join(wrote) + ".\n\n**Decided by the owner:**\n"
                + "\n".join(f"- **{d['id']}** {clean(d['text'], 500)}" for d in result["decisions"])
                + f"\n\nAt commit `{result['head'][:7]}`. The item is answered. Next: a spec is drafted from these decisions.")
        effects["remove"] = []
    else:
        body = ("**Failed.** The change goes back to the session:\n" + "\n".join(f"- {clean(p, 400)}" for p in result["problems"])
                + "\n\nThe label `answered` has been taken off again. Put these right in the session, push, and add the label again.")
    effects["comments"] = [f"### {BOX_NAMES['commit-check']}\n\n{body}\n\n{end}"]
    dump(out, effects)
    print("passed=" + ("yes" if result["passed"] else "no"))
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
            f.write("passed=" + ("yes" if result["passed"] else "no") + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
