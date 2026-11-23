#!/usr/bin/env python3
"""admit: a person added the label "admit". Check that they may, then record the owner. No model.

  admit.py <issue.json> <sender> <line dir> <out effects.json>

<issue.json> is the issue as GitHub's API returns it, after the label was added.
<sender> is the account that added it.

The item is admitted when the gate has called a person for it (a "called:" label) and
the sender holds the role that admits the item's type, as policy.json and people.json
say. The type is read from the item's "type:" label at this moment, so the person who
admits can change the type first. Whoever admits owns the item: they are assigned.
Otherwise the label is taken off again and a comment says why.
"""
import os
import sys

from common import data_block, dump, load


def decide(issue, sender, policy, people):
    """(admitted, role, type, words)."""
    labels = [l["name"] for l in issue["labels"]]
    if "line" not in labels:
        return False, None, None, "This issue is not an item on the line, so there is nothing to admit."
    if not any(l.startswith("called:") for l in labels):
        return False, None, None, "The admission gate has not called a person for this item, so there is nothing to admit."
    kinds = [l[len("type:"):] for l in labels if l.startswith("type:")]
    if len(kinds) != 1 or kinds[0] not in policy["types"]:
        return False, None, None, "The item must carry exactly one `type:` label before it is admitted."
    kind = kinds[0]
    role = policy["types"][kind]["admitted-by"]
    name = policy["types"][kind]["name"]
    if sender not in people[role]:
        return False, role, kind, (f"@{sender} does not hold the role that admits this item. "
                                   f"{name}: admitted by {policy['roles'][role]}.")
    return True, role, kind, (f"**@{sender} admitted this item, as {policy['roles'][role]}, and owns it from here.** "
                              f"Type: {name}.\n\nNext: Understand.")


def main(argv):
    if len(argv) != 4:
        print(__doc__.split("\n\n")[1], file=sys.stderr)
        return 2
    issue, sender, line, out = load(argv[0]), argv[1], argv[2], argv[3]
    policy, people = load(os.path.join(line, "policy.json")), load(os.path.join(line, "people.json"))
    run = os.environ.get("RUN_ID", "local")
    ok, role, kind, words = decide(issue, sender, policy, people)
    effects = {"comments": [], "add": [], "remove": ["admit"], "assign": []}
    if ok:
        record = {"outcome": "admitted", "owner": sender, "role": role, "type": kind}
        effects.update(add=["admitted", "stage:understand"],
                       remove=["admit", "stage:intake", "called:product-owner", "called:tech-lead", "returned", "stuck"],
                       assign=[sender],
                       comments=[f"### Admitted\n\n{words}\n\n<sub>Intake · a person, checked by a job · run {run}</sub>\n"
                                 + data_block(record, "intake", "admission", run)])
    else:
        effects["comments"] = [f"### Not admitted\n\n{words}\n\nThe label `admit` has been taken off again."]
    dump(out, effects)
    print("admitted=" + ("yes" if ok else "no"))
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
            f.write("admitted=" + ("yes" if ok else "no") + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
