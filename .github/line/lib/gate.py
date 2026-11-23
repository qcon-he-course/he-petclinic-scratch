#!/usr/bin/env python3
"""gate: post what Intake's boxes left, then apply the admission policy. No model, no key.

  gate.py <item.json> <results dir> <line dir> <out effects.json>

<results dir> holds, for each box (intake-agent, intake-check, classifier), either
<box>.json, the result lib/check.py accepted, or <box>.why, the reason there is none.
A box with neither file left nothing, and that is also no result. <box>.ran.json,
when present, says what ran the box. RUN_ID and RUN_URL name the workflow run.

The policy, in order:
  stuck      a box left no result. A missing result is a failed check: the item is
             neither admitted nor returned, and the stage is run again.
  returned   the item is not ready: more than one idea, a duplicate of another item,
             or a question only the requester can answer.
  admitted   the narrow class policy.json names: a defect whose attached test fails as
             claimed, with the classifier in agreement and no standing decision reversed.
  called     everything else waits for a person: the role policy.json names for the type.

Writes the effects (comments, labels, assignee) for lib/apply.py and prints the outcome.
"""
import os
import sys

from common import BOXES, BOX_NAMES, clean, code, data_block, dump, foot, load, ran_line, text


def bullets(lines, none="none."):
    return "\n" + "\n".join(f"- {l}" for l in lines) if lines else " " + none


def render_intake_agent(r, item, others):
    if r["one_idea"]:
        out = [f"**One idea:** yes. {clean(r['ideas'][0])}"]
    else:
        out = [f"**One idea:** no. The item states {len(r['ideas'])} ideas:" + bullets([clean(i) for i in r["ideas"]])]
    if r["terms"]:
        rows = [f"| {clean(t['word'], 80)} | {clean(t['team_word'], 80)} | {code(t['where'])} |" for t in r["terms"]]
        out.append("**The team's words**\n\n| The requester's word | The team's word | Where |\n|---|---|---|\n" + "\n".join(rows))
    else:
        out.append("**The team's words:** the constitution defines none of the idea's words.")
    out.append("**Duplicates:**" + bullets([f"#{d['item']}: {clean(d['why'])}" for d in r["duplicates"]],
                                           f"none among the {others} other item(s) on the line."))
    out.append("**Related work:**" + bullets([f"{code(e['where'])}: {clean(e['why'])}" for e in r["related"]], "none found."))
    out.append("**Standing decisions it would reverse:**"
               + bullets([f"{clean(e['decision'])} ({code(e['where'])}): {clean(e['why'])}" for e in r["reversed_decisions"]],
                         "none found."))
    out.append("**Questions for the requester:**" + bullets([clean(q) for q in r["questions_for_requester"]]))
    out.append("**Open points for the person who admits:**" + bullets([clean(q) for q in r["open_points"]]))
    out.append("**Gaps in the constitution:**" + bullets([clean(q) for q in r["gaps"]]))
    out.append(clean(r["summary"]))
    return "\n\n".join(out)


def render_intake_check(r, item, others):
    head = {"nothing to run": "Nothing to run.", "fails as claimed": "The attached test fails, as claimed.",
            "passes": "The attached test passes. The claim is not confirmed.",
            "could not run": "The attached test could not be run."}[r["outcome"]]
    return f"**{head}** {clean(r['detail'])}" + (f" Proof: {code(r['proof'])}." if r["proof"] else "")


def render_classifier(r, item, others, policy=None):
    name = policy["types"][r["type"]]["name"]
    if r["agrees"]:
        head = f"**Type: {name}.** That is the type the requester picked."
    else:
        head = (f"**The classifier reads this as: {name}.** The requester picked {item['type_name']}. "
                "The requester's choice stands until the person who admits changes it.")
    return head + "\n\n**The facts behind it:**" + bullets([f"{clean(f['fact'])} ({code(f['where'])})" for f in r["facts"]]) \
        + "\n\n" + clean(r["summary"])


def comment(box, results, whys, by, item, others, policy, run, url):
    end = foot("Intake", ran_line(by.get(box)), run, url)
    if box not in results:
        return f"### {BOX_NAMES[box]}\n\n**No result.** {clean(whys[box], 900)}\n\n{end}"
    body = {"intake-agent": render_intake_agent, "intake-check": render_intake_check,
            "classifier": lambda r, i, o: render_classifier(r, i, o, policy)}[box](results[box], item, others)
    return f"### {BOX_NAMES[box]}\n\n{body}\n\n{end}\n{data_block(results[box], 'intake', box, run, by.get(box))}"


def decide(item, results, whys, policy, people):
    """(outcome, role or None, the gate's words)."""
    types, roles = policy["types"], policy["roles"]
    rerun = ("Run Intake again for this item: Actions, \"line: intake\", Run workflow, "
             f"with the item's number, {item['number']}.")
    missing = [BOX_NAMES[b].lower() for b in BOXES if b not in results]
    if missing:
        return "stuck", None, ("**Stuck.** The gate has nothing to read from: the " + ", the ".join(missing) + ". "
                               "A missing result is a failed check, so the item is neither admitted nor returned.\n\n" + rerun)
    agent, check, classifier = (results[b] for b in BOXES)
    not_ready = []
    if not agent["one_idea"]:
        not_ready.append(f"It states {len(agent['ideas'])} ideas. File one item for each.")
    if agent["duplicates"]:
        not_ready.append("It asks for what " + ", ".join(f"#{d['item']}" for d in agent["duplicates"]) + " already asks for.")
    if agent["questions_for_requester"]:
        not_ready.append(f"The intake agent has {len(agent['questions_for_requester'])} question(s) for the requester, listed above.")
    if not_ready:
        return "returned", None, (f"**Returned to the requester** (@{item['requester']}). The item is not ready:"
                                  + bullets(not_ready) + "\n\nEdit the item to settle these. " + rerun)
    alone = policy["admitted-alone"]
    role = types[item["type"]]["admitted-by"]
    who = ", ".join("@" + p for p in people[role])
    if (item["type"] == alone["type"] and check["outcome"] == alone["proof"] and classifier["agrees"]
            and not agent["reversed_decisions"]):
        return "admitted", role, (f"**Admitted by the gate.** The item is in the class this gate admits alone: {alone['says']}.\n\n"
                                  f"By the policy its owner is {roles[role]} ({who}).\n\nNext: Understand.")
    facts = [f"Type: {item['type_name']}. " + ("The classifier agrees." if classifier["agrees"] else
             f"The classifier reads it as {types[classifier['type']]['name']}. To change the type, swap the item's `type:` label before you admit.")]
    n = len(agent["reversed_decisions"])
    facts.append("Standing decisions it would reverse: " + (f"{n}, listed by the intake agent above." if n else "none found."))
    n = len(agent["open_points"])
    facts.append("Open points: " + (f"{n}, listed above." if n else "none."))
    facts.append("Proof: " + check["outcome"] + ".")
    return "called", role, (f"**Called: {roles[role]}** ({who}).\n\n"
                            f"{types[item['type']]['name']}: outside the class this gate admits alone ({alone['says']}).\n\n"
                            "For the decision:" + bullets(facts) + "\n\n"
                            "To admit the item, add the label `admit`. Whoever admits it owns it from here: "
                            "they answer questions about it, and later gates call them.")


def main(argv):
    if len(argv) != 4:
        print(__doc__.split("\n\n")[1], file=sys.stderr)
        return 2
    item, folder, line, out = load(argv[0]), argv[1], argv[2], argv[3]
    policy, people = load(os.path.join(line, "policy.json")), load(os.path.join(line, "people.json"))
    run, url = os.environ.get("RUN_ID", "local"), os.environ.get("RUN_URL", "")
    others = len(load(os.path.join(os.path.dirname(argv[0]), "items.json"))) if os.path.exists(
        os.path.join(os.path.dirname(argv[0]), "items.json")) else 0
    results, whys, by = {}, {}, {}
    for box in BOXES:
        good, bad, ran = (os.path.join(folder, f"{box}.{ext}") for ext in ("json", "why", "ran.json"))
        if os.path.isfile(good):
            results[box] = load(good)
        else:
            whys[box] = text(bad).strip() if os.path.isfile(bad) else "The box's job left nothing: it did not run, or it failed before the check."
        if os.path.isfile(ran):
            by[box] = load(ran)
    outcome, role, words = decide(item, results, whys, policy, people)
    comments = [comment(b, results, whys, by, item, others, policy, run, url) for b in BOXES]
    decision = {"outcome": outcome, "role": role, "type": item["type"]}
    comments.append(f"### {BOX_NAMES['admission-gate']}\n\n{words}\n\n"
                    f"{foot('Intake', 'a policy, no model', run, url)}\n{data_block(decision, 'intake', 'admission-gate', run)}")
    effects = {"comments": comments, "add": [], "remove": ["stuck", "returned", "called:product-owner", "called:tech-lead"], "assign": []}
    if outcome == "admitted":
        effects.update(add=["admitted", "stage:understand"], remove=effects["remove"] + ["stage:intake"], assign=people[role][:1])
    elif outcome == "called":
        effects["add"] = [f"called:{role}"]
    else:
        effects["add"] = [outcome]
    effects["remove"] = [l for l in effects["remove"] if l not in effects["add"]]
    dump(out, effects)
    print(f"outcome={outcome}" + (f" role={role}" if role else ""))
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
            f.write(f"outcome={outcome}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
