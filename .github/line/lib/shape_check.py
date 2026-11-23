#!/usr/bin/env python3
"""shape_check: the commit check of Shape, part one. No model, no key.

In an attended session the item's owner decides, and the assistant writes the
decisions down. This script says whether that change is safe to commit to the source
repository. The session runs it before a commit, where a person can skip it. The
orchestrator runs it again on the pushed branch, where nobody can.

  shape_check.py commit <worktree> <item>
      Before a commit: checks what is staged. Exit 0 when it is safe, 1 with the reasons.
  shape_check.py branch <clone> <item> <line ref>
      On the item's branch: checks every commit since Understand's pins, and that no
      question is left open. Prints the result as JSON. Exit 0 when it passed.

A change of this stage touches only:
  openspec/changes/item-<item>/decisions.md   the decisions log
  GLOSSARY.md                                 the team's words
  docs/adr/NNNN-slug.md                       a decision record, for a hard-to-reverse trade-off
and each file is well formed. On the branch, the first commit may be Understand's
pins: new files under src/test/java/ and nothing else.
"""
import json
import re
import subprocess
import sys

ADR = re.compile(r"docs/adr/\d{4}-[a-z0-9-]+\.md")
ENTRY = re.compile(r"^- \*\*([DFO])(\d+)\*\*\s*(.*)$")
ANSWERED = re.compile(r"Asked as Q\d+[a-z]?, answered \d{4}-\d{2}-\d{2}")
TERM = re.compile(r"^\*\*([^*]+)\*\*:\s*(.*)$")


def git(repo, *args):
    p = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {p.stderr.strip()[:200]}")
    return p.stdout


def log_path(item):
    return f"openspec/changes/item-{item}/decisions.md"


def allowed(path, item):
    return path in (log_path(item), "GLOSSARY.md") or bool(ADR.fullmatch(path))


def read_log(text, item):
    """(problems, decisions, facts, open questions) of a decisions log."""
    lines = text.split("\n")
    out = []
    if not lines or lines[0].strip() != f"# Decisions: item-{item}":
        out.append(f"the log's first line is not \"# Decisions: item-{item}\"")
    if not any(re.match(rf"^Item: #{item}\b", l) for l in lines[:6]):
        out.append(f"the log does not name its item in a line \"Item: #{item} <title>\"")
    heads = [l.strip() for l in lines if l.startswith("## ")]
    want = ["## Decided", "## Facts the decisions rest on", "## Open"]
    if heads != want:
        out.append("the log's sections are not, in order: " + ", ".join(h[3:] for h in want))
    found, section = {"D": [], "F": [], "O": []}, None
    belongs = {"## Decided": "D", "## Facts the decisions rest on": "F", "## Open": "O"}
    for l in lines:
        if l.startswith("## "):
            section = belongs.get(l.strip())
            continue
        m = ENTRY.match(l)
        if not m:
            continue
        kind, number, said = m.group(1), int(m.group(2)), m.group(3).strip()
        if kind != section:
            out.append(f"{kind}{number} is in the wrong section")
        if number in [n for n, _ in found[kind]]:
            out.append(f"{kind}{number} is used twice")
        if not said:
            out.append(f"{kind}{number} is empty")
        if kind == "D" and not ANSWERED.search(said):
            out.append(f"D{number} does not say \"Asked as Q<n>, answered <yyyy-mm-dd>\"")
        if kind == "F" and "Source:" not in said:
            out.append(f"F{number} names no source")
        found[kind].append((number, said))
    if not found["D"]:
        out.append("the log records no decision")
    return out, found["D"], found["F"], found["O"]


def glossary_problems(text):
    lines = text.split("\n")
    out = []
    if not lines or not lines[0].startswith("# "):
        out.append("GLOSSARY.md does not start with the context's name as a heading")
    if "## Language" not in [l.strip() for l in lines]:
        out.append("GLOSSARY.md has no section \"## Language\"")
    terms = []
    for i, l in enumerate(lines):
        m = TERM.match(l)
        if not m:
            continue
        terms.append(m.group(1).strip())
        if not (m.group(2).strip() or (i + 1 < len(lines) and lines[i + 1].strip())):
            out.append(f"the term {m.group(1).strip()!r} has no definition")
    if not terms:
        out.append("GLOSSARY.md defines no term")
    return out, terms


def content_problems(item, names, read):
    """What is wrong inside the changed files. <read> returns a file's text, or None when it is gone."""
    out, facts = [], {"decisions": [], "facts": 0, "open": [], "glossary_terms": [], "adrs": []}
    log = read(log_path(item))
    if log is None:
        out.append(f"there is no decisions log at {log_path(item)}")
    else:
        problems, decided, rest_on, still_open = read_log(log, item)
        out += problems
        facts.update(decisions=[{"id": f"D{n}", "text": said} for n, said in decided], facts=len(rest_on),
                     open=[{"id": f"O{n}", "text": said} for n, said in still_open])
    if "GLOSSARY.md" in names:
        text = read("GLOSSARY.md")
        if text is None:
            out.append("GLOSSARY.md was deleted")
        else:
            problems, terms = glossary_problems(text)
            out += problems
            facts["glossary_terms"] = terms
    for name in sorted(n for n in names if ADR.fullmatch(n)):
        text = read(name)
        if text is None or not text.startswith("# ") or len(text.split()) < 20:
            out.append(f"{name} is not a decision record: a heading, then the context, the decision and why")
        else:
            facts["adrs"].append(name)
    return out, facts


def check_commit(repo, item):
    names = [n for n in git(repo, "diff", "--cached", "--name-only").split("\n") if n]
    out = [f"{n} is not a file this stage changes" for n in names if not allowed(n, item)]

    def staged(path):
        p = subprocess.run(["git", "-C", repo, "show", f":{path}"], capture_output=True, text=True)
        return p.stdout if p.returncode == 0 else None
    problems, _ = content_problems(item, names, staged)
    return out + problems


def check_branch(repo, item, line):
    base = git(repo, "merge-base", line, "HEAD").strip()
    commits = [c for c in git(repo, "rev-list", "--reverse", f"{base}..HEAD").split("\n") if c]
    out, session, pins = [], set(), None
    for i, c in enumerate(commits):
        changes = [l.split("\t") for l in git(repo, "diff-tree", "--no-commit-id", "--name-status", "-r", "--root", c).split("\n") if l]
        names = [ch[-1] for ch in changes]
        if i == 0 and changes and all(ch[0] == "A" and ch[-1].startswith("src/test/java/") for ch in changes):
            pins = c
            continue
        bad = [n for n in names if not allowed(n, item)]
        out += [f"commit {c[:7]} changes {n}, which is not a file this stage changes" for n in bad]
        session.update(names)
    if not session:
        out.append("the branch has no commit of this stage: nothing was decided")

    def at_head(path):
        p = subprocess.run(["git", "-C", repo, "show", f"HEAD:{path}"], capture_output=True, text=True)
        return p.stdout if p.returncode == 0 else None
    problems, facts = content_problems(item, session, at_head)
    out += problems
    out += [f"{o['id']} is still open: an item is answered when no question is open" for o in facts["open"]]
    return {"passed": not out, "problems": out, **facts, "commits": len(commits) - (1 if pins else 0),
            "pins_commit": pins, "head": git(repo, "rev-parse", "HEAD").strip()}


def main(argv):
    try:
        if len(argv) == 3 and argv[0] == "commit" and argv[2].isdigit():
            problems = check_commit(argv[1], int(argv[2]))
            if problems:
                print("The commit check refuses this commit:", file=sys.stderr)
                for p in problems:
                    print(f"  - {p}", file=sys.stderr)
                return 1
            print("commit check: passed")
            return 0
        if len(argv) == 4 and argv[0] == "branch" and argv[2].isdigit():
            result = check_branch(argv[1], int(argv[2]), argv[3])
            print(json.dumps(result, indent=2))
            return 0 if result["passed"] else 1
    except RuntimeError as e:
        print(f"shape_check: {e}", file=sys.stderr)
        return 2
    print(__doc__.split("\n\n")[3], file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
