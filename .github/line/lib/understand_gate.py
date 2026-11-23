#!/usr/bin/env python3
"""understand_gate: post what Understand's boxes left, then advance the item or return
it to the agent. No model, no key. No person is called at this stage.

  understand_gate.py <item.json> <results dir> <line dir> <out dir>

<results dir> holds pin-agent.json (or pin-agent.why), pin-agent.ran.json and
mutation-sensor.json, when the boxes left them. RUN_ID and RUN_URL name the run.

The policy, in order:
  return    something the agent can put right: it left no result, a pin did not
            compile or did not pass, or a pin cannot fail. The item goes back to the
            agent with the reasons, for the next round.
  stuck     the rounds policy.json allows are used up, or the evidence is missing
            for a reason the agent cannot put right: the sensor left no result, or
            the mutation run left no report.
  advance   every pin runs and passes, and no pin is one that cannot fail. The pins
            go to the item's branch, their names stay on the item, and the item moves
            to Shape. A pin that no mutant reached is "not judged": it is kept, and
            the item says so.

Writes <out dir>/effects.json for lib/apply.py and prints outcome=advance|return|stuck
and round=<next round>, also to $GITHUB_OUTPUT.
"""
import os
import sys

from common import BOX_NAMES, clean, code, data_block, dump, foot, load, ran_line, text


def problems(agent, why, sensor):
    """(what the agent can put right, what it cannot)."""
    if agent is None:
        return [f"The agent left no result: {why or 'its job left nothing'}"], []
    if sensor is None:
        return [], ["The mutation sensor left no result."]
    if not sensor["built"]:
        return [f"The pins did not build or run: {sensor['build_problem']}"], []
    fix = [f"{p['test']} {p['ran']}" + (f": {p['failure']}" if p["failure"] else "") + "."
           for p in sensor["pins"] if p["ran"] != "passed"]
    if fix:
        return fix, []
    if any(p["mutation"] == "not run" for p in sensor["pins"]):
        return [], ["The mutation run left no report, so no pin was checked."]
    return [f"{p['test']} cannot fail: {p['under']} mutant(s) ran under it and it failed for none. "
            + ("Assert the value the code produces." if p["kind"] == "written" else "Cite a test that asserts this behavior, or write one.")
            for p in sensor["pins"] if p["mutation"] == "cannot fail"], []


def bullets(lines, none="none."):
    return "\n" + "\n".join(f"- {l}" for l in lines) if lines else " " + none


def render_agent(r):
    rows = [f"| {clean(p['name'], 200)} | {code(p['test'])} | {p['kind']} | {code(p['where'])} |" for p in r["pins"]]
    out = ["**Pins: what the code does today.** Each is labelled observed: the code did this, and no owner has yet agreed that it should.",
           "| Pin | Test | | Where the behavior is |\n|---|---|---|---|\n" + "\n".join(rows)]
    out.append("**Behavior that looks wrong:**" + bullets(
        [f"{clean(s['behavior'])} {clean(s['why'])} ({code(s['where'])})" for s in r["suspects"]], "none found."))
    out.append("**Not pinned:**" + bullets([clean(g) for g in r["gaps"]], "nothing left out."))
    out.append(clean(r["summary"]))
    return "\n\n".join(out)


def render_sensor(s):
    if not s["built"]:
        return f"**The pins did not build or run.** {clean(s['build_problem'], 1200)}"
    words = {"can fail": "can fail", "cannot fail": "**cannot fail**", "not judged": "not judged", "not run": "not run"}
    rows = [f"| {code(p['test'])} | {p['ran'] if p['ran'] == 'passed' else '**' + p['ran'] + '**'} | {words[p['mutation']]} | "
            f"{p['killed']} of {p['under']} |" for p in s["pins"]]
    out = ["| Pin | On today's code | Under mutation | Mutants it failed for, of those that ran under it |\n|---|---|---|---|\n" + "\n".join(rows)]
    if s["mutants"] is not None:
        m = s["mutants"]
        out.append(f"{sum(m.values())} mutants in the production classes the pins name: " + ", ".join(
            f"{n} {k.lower().replace('_', ' ')}" for k, n in sorted(m.items())) + ".")
    if any(p["mutation"] == "not judged" for p in s["pins"]):
        out.append("Not judged: no mutant ran under the pin. Its behavior is outside the Java classes that were changed, "
                   "for example in a template or a message file.")
    return "\n\n".join(out)


def slim(agent):
    """The agent's result without the files' source: that is on the branch, and a comment has a size limit."""
    return {**agent, "files": [{"path": f["path"], "lines": f["content"].count("\n") + 1} for f in agent["files"]]}


def main(argv):
    if len(argv) != 4:
        print(__doc__.split("\n\n")[1], file=sys.stderr)
        return 2
    item, folder, line, out = load(argv[0]), argv[1], argv[2], argv[3]
    policy = load(os.path.join(line, "policy.json"))
    run, url = os.environ.get("RUN_ID", "local"), os.environ.get("RUN_URL", "")
    path = lambda name: os.path.join(folder, name)
    agent = load(path("pin-agent.json")) if os.path.isfile(path("pin-agent.json")) else None
    why = text(path("pin-agent.why")).strip() if os.path.isfile(path("pin-agent.why")) else None
    ran = load(path("pin-agent.ran.json")) if os.path.isfile(path("pin-agent.ran.json")) else None
    sensor = load(path("mutation-sensor.json")) if os.path.isfile(path("mutation-sensor.json")) else None
    round_, limit = item["round"], policy["understand"]["max-rounds"]
    stage = f"Understand, round {round_}"
    fix, cannot = problems(agent, why, sensor)

    comments = []
    if agent is None:
        comments.append(f"### {BOX_NAMES['pin-agent']}\n\n**No result.** {clean(why or 'Its job left nothing.', 900)}\n\n"
                        + foot(stage, ran_line(ran), run, url))
    else:
        comments.append(f"### {BOX_NAMES['pin-agent']}\n\n{render_agent(agent)}\n\n{foot(stage, ran_line(ran), run, url)}\n"
                        + data_block(slim(agent), "understand", "pin-agent", run, ran))
        if sensor is not None:
            comments.append(f"### {BOX_NAMES['mutation-sensor']}\n\n{render_sensor(sensor)}\n\n"
                            f"{foot(stage, 'a job, no model', run, url)}\n" + data_block(sensor, "understand", "mutation-sensor", run))

    branch = f"item-{item['number']}"
    effects = {"comments": comments, "add": [], "remove": ["stuck"], "assign": [], "file": []}
    again = f"Run Understand again for this item: Actions, \"line: understand\", Run workflow, with the item's number, {item['number']}."
    if cannot:
        outcome, words = "stuck", "**Stuck.** " + " ".join(cannot) + " The agent cannot put this right, so the item does not go back to it.\n\n" + again
    elif fix and round_ < limit:
        outcome = "return"
        words = (f"**Returned to the agent.** Round {round_ + 1} of {limit} starts now, with these reasons:" + bullets([clean(f, 700) for f in fix]))
    elif fix:
        outcome = "stuck"
        words = (f"**Stuck.** Round {round_} was the last the policy allows, and the pins still do not hold:"
                 + bullets([clean(f, 700) for f in fix]) + "\n\n" + again)
    else:
        outcome = "advance"
        written = sum(1 for p in agent["pins"] if p["kind"] == "written")
        unjudged = sum(1 for p in sensor["pins"] if p["mutation"] == "not judged")
        words = (f"**Pinned.** {len(agent['pins'])} pins run and pass on today's code: {written} written, {len(agent['pins']) - written} cited. "
                 + (f"The written ones are on the branch `{branch}`. " if written else f"The branch `{branch}` starts here. ")
                 + (f"{unjudged} could not be judged by mutation. " if unjudged else "")
                 + (f"{len(agent['suspects'])} suspect behavior(s) filed as new items. " if agent["suspects"] else "")
                 + "\n\nNext: Shape. The item's owner reads the pins' names there.")
        effects["add"], effects["remove"] = ["stage:shape"], ["stuck", "stage:understand"]
        for s in agent["suspects"][:3]:
            effects["file"].append({
                "title": "Suspect: " + " ".join(s["behavior"].split())[:120],
                "body": ("### Idea\n\n" + " ".join(s["behavior"].split()) + " " + " ".join(s["why"].split())
                         + f"\n\nSeen at `{s['where']}` while pinning item #{item['number']}. Filed by the line. "
                           "Intake does not start by itself for an item the line files: a requester runs it.\n\n"
                           "### Type\n\nDefect\n\n### Proof\n\n_No response_"),
                "labels": ["line", "suspect"]})
    if outcome == "stuck":
        effects["add"] = ["stuck"]
        effects["remove"] = []
    decision = {"outcome": outcome, "round": round_, "branch": branch if outcome == "advance" else None,
                "reasons": fix + cannot}
    comments.append(f"### {BOX_NAMES['understand-gate']}\n\n{words}\n\n{foot(stage, 'a policy, no model', run, url)}\n"
                    + data_block(decision, "understand", "understand-gate", run))
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
