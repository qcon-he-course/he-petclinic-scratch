#!/usr/bin/env python3
"""ready_check: the check of Shape, part three, where the owner refines the reviewed draft. No model, no key.

The session runs it before a commit, where a person can skip it. The orchestrator
runs it again on the pushed branch when the owner marks the item ready.

  ready_check.py commit <worktree> <item>
      Before a commit: checks what is staged, and the draft as it stands in the folder.
      Exit 0 when it is safe, 1 with the reasons.
  ready_check.py branch <clone> <item> <line ref>
      On the item's branch: checks every commit since Understand's pins, the log and
      the draft at its head. Prints the result as JSON. Exit 0 when it passed.

A change of this stage touches only the draft (proposal.md and the delta specs in
the item's change folder) and what a session of part one may touch (the decisions
log, GLOSSARY.md, a decision record). The log is well formed and leaves no question
open. The draft passes the completeness check, lib/spec_check.py: the template's
form, every decision in the draft, every changed pin named.
"""
import json
import subprocess
import sys

import draft
import shape_check
import spec_check


def allowed(path, item):
    return shape_check.allowed(path, item) or draft.allowed(path, item)


def content(repo, item, names, read):
    problems, facts = shape_check.content_problems(item, names, read)
    problems += [f"{o['id']} is still open: a spec is ready when no question is open" for o in facts["open"]]
    complete = spec_check.check_files(repo, item)
    return problems + complete["gaps"], facts, complete


def check_commit(repo, item):
    names = [n for n in shape_check.git(repo, "diff", "--cached", "--name-only").split("\n") if n]
    out = [f"{n} is not a file this stage changes" for n in names if not allowed(n, item)]

    def staged(path):
        p = subprocess.run(["git", "-C", repo, "show", f":{path}"], capture_output=True, text=True)
        return p.stdout if p.returncode == 0 else None
    problems, _, _ = content(repo, item, names, staged)
    return out + problems


def draft_commit(repo, item, commits):
    """The last commit that the line's draft gate made: by its message. It is a hint for
    what the owner changed, and nothing rests on it."""
    found = None
    for c in commits:
        if shape_check.git(repo, "log", "-1", "--format=%s", c).strip() == f"Shape: draft spec for item {item}":
            found = c
    return found


def check_branch(repo, item, line):
    base = shape_check.git(repo, "merge-base", line, "HEAD").strip()
    commits = [c for c in shape_check.git(repo, "rev-list", "--reverse", f"{base}..HEAD").split("\n") if c]
    out, touched = [], set()
    for i, c in enumerate(commits):
        changes = [l.split("\t") for l in shape_check.git(repo, "diff-tree", "--no-commit-id", "--name-status", "-r", "--root", c).split("\n") if l]
        if i == 0 and changes and all(ch[0] == "A" and ch[-1].startswith("src/test/java/") for ch in changes):
            continue  # Understand's pins
        names = [ch[-1] for ch in changes]
        out += [f"commit {c[:7]} changes {n}, which is not a file this stage changes" for n in names if not allowed(n, item)]
        touched.update(names)

    def at_head(path):
        p = subprocess.run(["git", "-C", repo, "show", f"HEAD:{path}"], capture_output=True, text=True)
        return p.stdout if p.returncode == 0 else None
    problems, facts, complete = content(repo, item, touched, at_head)
    reviewed = draft_commit(repo, item, commits)
    changed = [n for n in shape_check.git(repo, "diff", "--name-only", f"{reviewed}..HEAD").split("\n") if n] if reviewed else []
    return {"passed": not (out + problems), "problems": out + problems, "decisions": len(facts["decisions"]),
            "scenarios": complete["scenarios"], "specs": complete["specs"], "glossary_terms": facts["glossary_terms"],
            "draft_commit": reviewed, "changed_since_the_reviewed_draft": changed,
            "head": shape_check.git(repo, "rev-parse", "HEAD").strip()}


def main(argv):
    try:
        if len(argv) == 3 and argv[0] == "commit" and argv[2].isdigit():
            problems = check_commit(argv[1], int(argv[2]))
            if problems:
                print("The check refuses this commit:", file=sys.stderr)
                for p in problems:
                    print(f"  - {p}", file=sys.stderr)
                return 1
            print("ready check: passed")
            return 0
        if len(argv) == 4 and argv[0] == "branch" and argv[2].isdigit():
            result = check_branch(argv[1], int(argv[2]), argv[3])
            print(json.dumps(result, indent=2))
            return 0 if result["passed"] else 1
    except RuntimeError as e:
        print(f"ready_check: {e}", file=sys.stderr)
        return 2
    print(__doc__.split("\n\n")[2], file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
