#!/usr/bin/env python3
"""draft_gate: post what the boxes of Shape, part two, left, and decide what happens
to the draft. No model, no key.

  draft_gate.py <item.json> <results dir> <line dir> <out dir>

<results dir> holds, when the boxes left them: spec-drafter.json (or .why),
completeness.json, spec-reviewer.json (or .why), and each agent's .ran.json.

The policy, in order:
  return    something the drafter can put right: it left no result, the completeness
            check found gaps, or the reviewer has findings. The draft goes back to the
            drafter with the reasons, for the next round.
  parked    the drafter asks the owner a question, or the rounds are used up and the
            reviewer still has findings: the drafter and the reviewer do not agree,
            and that is a question for a person. The item parks and the owner is
            called. An agent that runs unattended never decides for a person.
  stuck     the rounds are used up on gaps, or evidence is missing for a reason the
            drafter cannot put right: a check or the reviewer left no result, or the
            branch moved after the commit check passed.
  reviewed  no gap, no finding, no question. The draft goes to the item's branch and
            waits for the owner.

Writes <out dir>/effects.json for lib/apply.py and prints outcome=…, round=<next
round>, branch=…, also to $GITHUB_OUTPUT.
"""
import os
import sys

from common import BOX_NAMES, clean, code, data_block, dump, foot, load, ran_line, text


def bullets(lines):
    return "\n" + "\n".join(f"- {l}" for l in lines)


def render_drafter(r):
    out = ["**The draft:** " + ", ".join(f"{code(f['path'])} ({f['content'].count(chr(10)) + 1} lines)" for f in r["files"]) + "."]
    if r["resolved"]:
        out.append("**What it did about the gaps and findings it was given:**"
                   + bullets([f"{clean(x['about'], 120)}: {clean(x['how'], 400)}" for x in r["resolved"]]))
    if r["questions"]:
        out.append("**Questions for the owner:**" + bullets(
            [f"{clean(q['question'], 500)} Why it is open: {clean(q['why'], 400)} Recommended: {clean(q['recommended'], 400)}" for q in r["questions"]]))
    out.append(clean(r["summary"]))
    return "\n\n".join(out)


def render_reviewer(r):
    if not r["findings"]:
        return "**No findings.** " + clean(r["summary"])
    rows = [f"**{clean(f['id'], 8)}** ({f['kind']}, against {code(f['against'], 120)}"
            + (", needs a decision" if f["needs_decision"] else "") + f"): {clean(f['claim'], 600)} ({code(f['where'])})" for f in r["findings"]]
    return f"**{len(r['findings'])} finding(s).**" + bullets(rows) + "\n\n" + clean(r["summary"])


def main(argv):
    if len(argv) != 4:
        print(__doc__.split("\n\n")[1], file=sys.stderr)
        return 2
    item, folder, line, out = load(argv[0]), argv[1], argv[2], argv[3]
    policy, people = load(os.path.join(line, "policy.json")), load(os.path.join(line, "people.json"))
    run, url = os.environ.get("RUN_ID", "local"), os.environ.get("RUN_URL", "")
    has = lambda name: os.path.isfile(os.path.join(folder, name))
    get = lambda name: load(os.path.join(folder, name)) if has(name) else None
    why = lambda name: text(os.path.join(folder, name)).strip() if has(name) else "its job left nothing"
    drafter, check, reviewer = get("spec-drafter.json"), get("completeness.json"), get("spec-reviewer.json")
    round_, limit, number = item["round"], policy["shape"]["max-rounds"], item["number"]
    stage, branch, owner = f"Shape, part two, round {round_}", f"item-{number}", item["owner"]
    again = (f"To start it again: the owner takes the label `answered` off item {number} and adds it again.")

    comments = []
    if drafter is None:
        comments.append(f"### {BOX_NAMES['spec-drafter']}\n\n**No result.** {clean(why('spec-drafter.why'), 900)}\n\n"
                        + foot(stage, ran_line(get("spec-drafter.ran.json")), run, url))
    else:
        slim = {**drafter, "files": [{"path": f["path"], "lines": f["content"].count("\n") + 1} for f in drafter["files"]]}
        comments.append(f"### {BOX_NAMES['spec-drafter']}\n\n{render_drafter(drafter)}\n\n"
                        f"{foot(stage, ran_line(get('spec-drafter.ran.json')), run, url)}\n"
                        + data_block(slim, "shape", "spec-drafter", run, get("spec-drafter.ran.json")))
    if check is not None:
        body = (f"**Complete.** {check['scenarios']} scenario(s) in {len(check['specs'])} delta spec(s), and every one of the "
                f"{check['decisions']} decisions is in the draft." if check["passed"] else
                "**Gaps.** The reviewer does not run on an incomplete draft." + bullets([clean(g, 400) for g in check["gaps"]]))
        comments.append(f"### {BOX_NAMES['completeness-check']}\n\n{body}\n\n{foot(stage, 'a job, no model', run, url)}\n"
                        + data_block(check, "shape", "completeness-check", run))
    if reviewer is not None:
        comments.append(f"### {BOX_NAMES['spec-reviewer']}\n\n{render_reviewer(reviewer)}\n\n"
                        f"{foot(stage, ran_line(get('spec-reviewer.ran.json')), run, url)}\n"
                        + data_block(reviewer, "shape", "spec-reviewer", run, get("spec-reviewer.ran.json")))
    elif check is not None and check["passed"]:
        comments.append(f"### {BOX_NAMES['spec-reviewer']}\n\n**No result.** {clean(why('spec-reviewer.why'), 900)}\n\n"
                        + foot(stage, ran_line(get("spec-reviewer.ran.json")), run, url))

    effects = {"comments": comments, "add": [], "remove": ["stuck"], "assign": []}
    reasons, questions = [], []
    session = (f"@{owner}: run the session again (`.github/line/shape/start-session.sh {number}`), decide, and mark the item answered. "
               "The answer starts the drafter again.")
    if drafter is None:
        outcome, reasons = "return", [f"The drafter left no result: {why('spec-drafter.why')}"]
    elif check is None:
        outcome, reasons = "stuck", ["The completeness check left no result."]
    elif check["head"] != item["checked_head"]:
        outcome, reasons = "stuck", [f"The branch `{branch}` moved after the commit check passed. The owner marks the item answered again."]
    elif drafter["questions"]:
        outcome, questions = "parked", [q["question"] for q in drafter["questions"]]
    elif not check["passed"]:
        outcome, reasons = "return", check["gaps"]
    elif reviewer is None:
        outcome, reasons = "stuck", [f"The reviewer left no result: {why('spec-reviewer.why')}"]
    elif reviewer["findings"]:
        outcome, reasons = "return", [f"{f['id']} ({f['kind']}, against {f['against']}): {f['claim']} At {f['where']}." for f in reviewer["findings"]]
    else:
        outcome = "reviewed"
    used_up = False
    if outcome == "return" and round_ >= limit:
        if reviewer is not None and reviewer["findings"] and check is not None and check["passed"]:
            outcome, questions = "parked", [f"The drafter and the reviewer do not agree on {f['id']}: {f['claim']}" for f in reviewer["findings"]]
        else:
            outcome, used_up = "stuck", True

    if outcome == "reviewed":
        words = (f"**Draft reviewed.** The draft is complete, the reviewer has no finding and no question is open. It is on the branch "
                 f"`{branch}`.\n\nNext: the owner reads the draft and refines it.")
        effects.update(add=["draft-reviewed"], remove=["stuck", "parked"])
    elif outcome == "parked":
        words = ("**Parked. Called: the item's owner.** The draft cannot be right without a decision:"
                 + bullets([clean(q, 600) for q in questions]) + "\n\n" + session)
        effects.update(add=["parked"], remove=["stuck", "answered", "draft-reviewed"])
    elif outcome == "return":
        words = (f"**Returned to the drafter.** Round {round_ + 1} of {limit} starts now, with these reasons:"
                 + bullets([clean(r, 700) for r in reasons]))
    else:
        words = ("**Stuck.** " + ("The rounds the policy allows are used up, and the draft is still not complete:" if used_up
                                  else "The draft cannot go on:")
                 + bullets([clean(r, 700) for r in reasons]) + "\n\n" + again)
        effects.update(add=["stuck"], remove=[])
    decision = {"outcome": outcome, "round": round_, "branch": branch, "reasons": reasons, "questions": questions}
    comments.append(f"### {BOX_NAMES['draft-gate']}\n\n{words}\n\n{foot(stage, 'a policy, no model', run, url)}\n"
                    + data_block(decision, "shape", "draft-gate", run))
    os.makedirs(out, exist_ok=True)
    dump(os.path.join(out, "effects.json"), effects)
    lines = [f"outcome={outcome}", f"round={round_ + 1}", f"branch={branch}"]
    print(" ".join(lines))
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
