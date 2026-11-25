#!/usr/bin/env python3
"""shape_gate: the gate of Shape. Post the reviewer's result on the owner's refined
draft, and pass the item to Design or return it to the owner. No model, no key.

  shape_gate.py <item.json> <results dir> <line dir> <out effects.json>

<results dir> holds ready-check.json and, when the reviewer left them,
spec-reviewer.json (or .why) and spec-reviewer.ran.json.

The policy:
  returned  the reviewer has a finding. The owner refined the draft, so the finding
            goes to the owner, in a session: nobody else may change the owner's spec.
  stuck     the reviewer left no result. A missing result is a failed check.
  passed    no finding. The spec is ready at the commit the check passed on, and the
            item moves to Design. Ready is not approved: approval waits for Design,
            where the spec is read against a design for the first time.

Prints outcome=returned|stuck|passed, also to $GITHUB_OUTPUT.
"""
import os
import sys

from common import BOX_NAMES, clean, data_block, dump, foot, load, ran_line, text
from draft_gate import render_reviewer


def main(argv):
    if len(argv) != 4:
        print(__doc__.split("\n\n")[1], file=sys.stderr)
        return 2
    item, folder, line, out = load(argv[0]), argv[1], argv[2], argv[3]
    run, url = os.environ.get("RUN_ID", "local"), os.environ.get("RUN_URL", "")
    has = lambda name: os.path.isfile(os.path.join(folder, name))
    get = lambda name: load(os.path.join(folder, name)) if has(name) else None
    check, reviewer, ran = get("ready-check.json"), get("spec-reviewer.json"), get("spec-reviewer.ran.json")
    number, owner, stage = item["number"], item["owner"], "Shape, part three"
    comments = []
    effects = {"comments": comments, "add": [], "remove": ["stuck"], "assign": []}
    session = (f"@{owner}: run the session again (`.github/line/shape/start-session.sh {number}`), settle these with your assistant, "
               "push, and mark the spec ready again.")
    if reviewer is None:
        why = text(os.path.join(folder, "spec-reviewer.why")).strip() if has("spec-reviewer.why") else "its job left nothing"
        comments.append(f"### {BOX_NAMES['spec-reviewer']}\n\n**No result.** {clean(why, 900)}\n\n{foot(stage, ran_line(ran), run, url)}")
        outcome, reasons = "stuck", [f"The reviewer left no result: {why}"]
        words = ("**Stuck.** The reviewer left no result, and a missing result is a failed check. To run it again: the owner takes the "
                 f"label `ready` off item {number} and adds it again.")
        effects.update(add=["stuck"], remove=["ready"])
    else:
        comments.append(f"### {BOX_NAMES['spec-reviewer']}\n\n{render_reviewer(reviewer)}\n\n{foot(stage, ran_line(ran), run, url)}\n"
                        + data_block(reviewer, "shape", "spec-reviewer", run, ran))
        if reviewer["findings"]:
            outcome = "returned"
            reasons = [f"{f['id']} ({f['kind']}, against {f['against']}): {f['claim']} At {f['where']}." for f in reviewer["findings"]]
            words = ("**Returned to the owner.** The reviewer has findings on the draft as it stands:"
                     + "\n" + "\n".join(f"- {clean(r, 700)}" for r in reasons) + "\n\n" + session)
            effects.update(remove=["stuck", "ready"])
        else:
            outcome, reasons = "passed", []
            words = (f"**Shape passed.** The spec is ready at commit `{check['head'][:7]}`: {check['scenarios']} scenario(s) from "
                     f"{check['decisions']} decisions, complete, with no finding from the reviewer and no question open. It is not yet "
                     "approved: approval waits for Design, where the spec meets a design.\n\nNext: Design.")
            effects.update(add=["stage:design"], remove=["stuck", "stage:shape", "answered", "draft-reviewed", "ready", "parked"])
    decision = {"outcome": outcome, "reasons": reasons, "head": check["head"] if check else None, "branch": f"item-{number}"}
    comments.append(f"### {BOX_NAMES['shape-gate']}\n\n{words}\n\n{foot(stage, 'a policy, no model', run, url)}\n"
                    + data_block(decision, "shape", "shape-gate", run))
    dump(out, effects)
    print(f"outcome={outcome}")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
            f.write(f"outcome={outcome}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
