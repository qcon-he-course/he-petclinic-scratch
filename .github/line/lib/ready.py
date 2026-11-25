#!/usr/bin/env python3
"""ready: the owner marked the item ready. Check that they may, run the ready check on
the item's branch, and gather what the reviewer is given. No model, no key.

  ready.py <issue.json> <comments.json> <sender> <clone or missing> <line ref> <line dir> <out dir>

<clone> is a checkout of the item's branch with its history. <sender> is the account
that added the label "ready".

Writes into <out dir>: ready-check.json (the check's result), effects.json and, when
the check passed, item.json, pins.json and changes.diff (what changed since the draft
the reviewer last saw). Prints passed=yes|no, also to $GITHUB_OUTPUT.

The check runs when the item is at Shape with a reviewed draft and the sender is the
item's owner. When it fails, or may not run, the label is taken off again and a
comment says why: the draft goes back to the session.
"""
import os
import subprocess
import sys

import item as form
import ready_check
from common import BOX_NAMES, clean, data_block, dump, foot, latest, load, read_results


def main(argv):
    if len(argv) != 7:
        print(__doc__.split("\n\n")[1], file=sys.stderr)
        return 2
    issue, comments, sender, clone, line_ref, line, out = load(argv[0]), load(argv[1]), argv[2], argv[3], argv[4], argv[5], argv[6]
    policy, people = load(os.path.join(line, "policy.json")), load(os.path.join(line, "people.json"))
    run, url = os.environ.get("RUN_ID", "local"), os.environ.get("RUN_URL", "")
    os.makedirs(out, exist_ok=True)
    number = issue["number"]
    labels = [l["name"] for l in issue["labels"]]
    owners = [a["login"] for a in issue.get("assignees") or []]
    effects = {"comments": [], "add": [], "remove": ["ready"], "assign": []}
    got, why = form.read(issue, people, policy)
    refused = None
    if got is None:
        refused = None if why.startswith("quiet:") else why
        if refused is None:
            dump(os.path.join(out, "effects.json"), {"comments": [], "add": [], "remove": [], "assign": []})
            print("passed=no (not an item)")
            return 0
    elif "stage:shape" not in labels or "draft-reviewed" not in labels:
        refused = "The item is not at Shape with a reviewed draft, so there is nothing to mark ready."
    elif sender not in owners:
        refused = f"@{sender} is not the item's owner. The owner marks the spec ready."
    elif not os.path.exists(os.path.join(clone, ".git")):
        refused = f"There is no branch `item-{number}` to check."
    passed = False
    if refused:
        effects["comments"] = [f"### {BOX_NAMES['ready-check']}\n\n**Not run.** {clean(refused, 400)}\n\nThe label `ready` has been taken off again."]
    else:
        try:
            result = ready_check.check_branch(clone, number, line_ref)
        except RuntimeError as e:
            result = {"passed": False, "problems": [f"the check could not read the branch: {e}"], "decisions": 0, "scenarios": 0, "specs": [],
                      "glossary_terms": [], "draft_commit": None, "changed_since_the_reviewed_draft": [], "head": None}
        dump(os.path.join(out, "ready-check.json"), result)
        end = foot("Shape, part three", "a job, no model", run, url) + "\n" + data_block(result, "shape", "ready-check", run)
        passed = result["passed"]
        if passed:
            changed = result["changed_since_the_reviewed_draft"]
            said = ("The owner changed nothing since the reviewed draft." if not changed else
                    "Since the reviewed draft the owner changed: " + ", ".join(f"`{c}`" for c in changed[:8]) + ".")
            body = (f"**Passed.** Every commit on `item-{number}` touches only the draft, the decisions log, the glossary and decision "
                    f"records. The log is well formed with no question open, and the draft is complete: {result['scenarios']} scenario(s), "
                    f"all {result['decisions']} decisions in it. {said}\n\nAt commit `{result['head'][:7]}`. The reviewer reads it next.")
            effects["remove"] = []
            pinned = latest(read_results(comments), "understand", "pin-agent") or {"pins": []}
            kinds = [l[len("type:"):] for l in labels if l.startswith("type:")]
            got.update(owner=owners[0], checked_head=result["head"], decisions=result["decisions"], round=1)
            if len(kinds) == 1 and kinds[0] in policy["types"]:
                got.update(type=kinds[0], type_name=policy["types"][kinds[0]]["name"])
            dump(os.path.join(out, "item.json"), got)
            dump(os.path.join(out, "pins.json"), [{k: p[k] for k in ("name", "test", "kind", "file", "where")} for p in pinned["pins"]])
            if result["draft_commit"] and changed:
                diff = subprocess.run(["git", "-C", clone, "diff", f"{result['draft_commit']}..HEAD"], capture_output=True, text=True).stdout
                with open(os.path.join(out, "changes.diff"), "w", encoding="utf-8") as f:
                    f.write(diff[:60000])
        else:
            body = ("**Failed.** The draft goes back to the session:\n" + "\n".join(f"- {clean(p, 400)}" for p in result["problems"])
                    + "\n\nThe label `ready` has been taken off again. Put these right in the session, push, and mark the spec ready again.")
        effects["comments"] = [f"### {BOX_NAMES['ready-check']}\n\n{body}\n\n{end}"]
    dump(os.path.join(out, "effects.json"), effects)
    print("passed=" + ("yes" if passed else "no"))
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
            f.write("passed=" + ("yes" if passed else "no") + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
