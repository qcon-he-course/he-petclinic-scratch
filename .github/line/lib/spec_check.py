#!/usr/bin/env python3
"""spec_check: the completeness check of Shape. No model, no key.

It checks a draft spec against the template in the constitution, and every decision
of the owner against the draft. The same script checks the agent's draft in the
orchestrator and, later, the owner's refinement: in the session before a commit, and
again in CI.

  spec_check.py files <clone> <item>
      Checks the change folder openspec/changes/item-<item>/ as it stands in the
      working tree. Prints the result as JSON. Exit 0 when there is no gap.

The draft is complete when:
  - proposal.md has the template's sections (Why, What Changes, Capabilities, Impact),
    each with text of its own and none of the template's comments;
  - there is at least one delta spec, specs/<capability>/spec.md, that starts with
    "# Spec Delta" and has a section of ADDED, MODIFIED or REMOVED requirements;
  - every requirement says SHALL or MUST and has at least one scenario;
  - every scenario has a WHEN, a THEN, one CHECKED AT with a level the project
    knows, and one DECIDED BY that names decisions of the log; titles are not reused;
  - every decision of the log is named by a scenario's DECIDED BY, or is listed in
    the proposal under "## Decisions with no scenario", with the reason;
  - every pin a decision changes ("Changes pin: Test#method") is named in the
    proposal's Impact section.
"""
import glob
import json
import os
import re
import sys

import shape_check

LEVELS = ["unit", "form", "database", "mysql-postgres", "concurrency", "manual"]
SECTIONS = ["Why", "What Changes", "Capabilities", "Impact"]
DECISION = re.compile(r"\bD(\d+)\b")
CHANGES_PIN = re.compile(r"Changes pin: ([A-Za-z_][A-Za-z0-9_]*#[A-Za-z_][A-Za-z0-9_]*)")
NO_SCENARIO = "Decisions with no scenario"


def sections(text, mark):
    """{heading: body} for the headings at one level, such as "## "."""
    out, name, body = {}, None, []
    for line in text.split("\n"):
        if line.startswith(mark) and not line.startswith(mark + "#"):
            if name is not None:
                out[name] = "\n".join(body).strip()
            name, body = line[len(mark):].strip(), []
        elif name is not None:
            body.append(line)
    if name is not None:
        out[name] = "\n".join(body).strip()
    return out


def proposal_problems(text):
    out = []
    if "<!--" in text:
        out.append("proposal.md still holds a comment from the template")
    found = sections(text, "## ")
    for name in SECTIONS:
        if name not in found:
            out.append(f"proposal.md has no section \"## {name}\"")
        elif len(found[name].split()) < 3:
            out.append(f"proposal.md: the section \"{name}\" is empty")
    return out, found


def spec_problems(path, text):
    """(problems, [(scenario title, {decision numbers})])."""
    out, scenarios = [], []
    if "<!--" in text:
        out.append(f"{path} still holds a comment from the template")
    if not text.lstrip().startswith("# Spec Delta"):
        out.append(f"{path} does not start with \"# Spec Delta\"")
    kinds = [h for h in sections(text, "## ") if re.fullmatch(r"(ADDED|MODIFIED|REMOVED) Requirements", h)]
    if not kinds:
        out.append(f"{path} has no section of ADDED, MODIFIED or REMOVED requirements")
    requirements = sections(text, "### ")
    if not any(r.startswith("Requirement:") for r in requirements):
        out.append(f"{path} states no requirement")
    for name, body in requirements.items():
        if not name.startswith("Requirement:"):
            continue
        title = name[len("Requirement:"):].strip() or "(no name)"
        statement = body.split("#### ")[0]
        if not re.search(r"\b(SHALL|MUST)\b", statement):
            out.append(f"{path}: the requirement \"{title}\" does not say SHALL or MUST")
        found = sections(body, "#### ")
        if not any(s.startswith("Scenario:") for s in found):
            out.append(f"{path}: the requirement \"{title}\" has no scenario")
        for s_name, s_body in found.items():
            if not s_name.startswith("Scenario:"):
                continue
            s_title = s_name[len("Scenario:"):].strip() or "(no title)"
            bullets = [l.strip() for l in s_body.split("\n") if l.strip().startswith("- **")]
            has = lambda word: [b for b in bullets if b.startswith(f"- **{word}**")]
            for word in ("WHEN", "THEN"):
                if not has(word):
                    out.append(f"{path}: the scenario \"{s_title}\" has no {word}")
            checked = has("CHECKED AT")
            level = checked[0][len("- **CHECKED AT**"):].strip() if checked else None
            if len(checked) != 1 or level not in LEVELS:
                out.append(f"{path}: the scenario \"{s_title}\" needs one CHECKED AT with one of: {', '.join(LEVELS)}")
            decided = has("DECIDED BY")
            numbers = {int(n) for n in DECISION.findall(decided[0])} if decided else set()
            if len(decided) != 1 or not numbers:
                out.append(f"{path}: the scenario \"{s_title}\" needs one DECIDED BY that names decisions, such as D3, D8")
            scenarios.append((s_title, numbers))
    return out, scenarios


def check_files(clone, item):
    folder = os.path.join(clone, "openspec", "changes", f"item-{item}")
    read = lambda p: open(p, encoding="utf-8").read() if os.path.isfile(p) else None
    gaps = []
    log = read(os.path.join(folder, "decisions.md"))
    decided = {}
    if log is None:
        gaps.append("the change has no decisions log")
    else:
        _, decisions, _, _ = shape_check.read_log(log, item)
        decided = {n: said for n, said in decisions}
    proposal = read(os.path.join(folder, "proposal.md"))
    parts = {}
    if proposal is None:
        gaps.append("the draft has no proposal.md")
    else:
        problems, parts = proposal_problems(proposal)
        gaps += problems
    scenarios = []
    specs = sorted(glob.glob(os.path.join(folder, "specs", "**", "spec.md"), recursive=True))
    if not specs:
        gaps.append("the draft has no delta spec under specs/<capability>/spec.md")
    for path in specs:
        problems, found = spec_problems(os.path.relpath(path, folder), read(path))
        gaps += problems
        scenarios += found
    titles = [t for t, _ in scenarios]
    gaps += [f"the scenario title \"{t}\" is used more than once" for t in sorted({t for t in titles if titles.count(t) > 1})]
    named = {n for _, numbers in scenarios for n in numbers}
    gaps += [f"a scenario is decided by D{n}, and the log has no D{n}" for n in sorted(named - set(decided))]
    without = {int(n) for n in DECISION.findall(parts.get(NO_SCENARIO, ""))}
    gaps += [f"D{n} is in no scenario's DECIDED BY and is not listed under \"## {NO_SCENARIO}\" in the proposal"
             for n in sorted(set(decided) - named - without)]
    impact = parts.get("Impact", "")
    for n, said in sorted(decided.items()):
        gaps += [f"D{n} changes the pin {pin}, and the proposal's Impact section does not name it"
                 for pin in CHANGES_PIN.findall(said) if pin not in impact]
    return {"passed": not gaps, "gaps": gaps, "scenarios": len(scenarios), "specs": [os.path.relpath(p, clone) for p in specs],
            "decisions": len(decided), "decisions_with_no_scenario": sorted(f"D{n}" for n in without & set(decided))}


def main(argv):
    if len(argv) == 3 and argv[0] == "files" and argv[2].isdigit():
        result = check_files(argv[1], int(argv[2]))
        print(json.dumps(result, indent=2))
        return 0 if result["passed"] else 1
    print(__doc__.split("\n\n")[3], file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
