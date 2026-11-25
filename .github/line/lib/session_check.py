#!/usr/bin/env python3
"""session_check: the commit check of an attended session, whatever its stage. No model, no key.

  session_check.py commit <worktree> <item>

Reads the stage from <worktree>/.line/stage, which start-session.sh wrote, and runs
that stage's check on what is staged: shape-1 (the owner decides) or shape-3 (the
owner refines the draft). The pre-commit hook calls this, and so does the skill.
"""
import os
import sys

import ready_check
import shape_check

CHECKS = {"shape-1": shape_check.check_commit, "shape-3": ready_check.check_commit}


def main(argv):
    if len(argv) != 3 or argv[0] != "commit" or not argv[2].isdigit():
        print(__doc__.split("\n\n")[1], file=sys.stderr)
        return 2
    try:
        with open(os.path.join(argv[1], ".line", "stage"), encoding="utf-8") as f:
            stage = f.read().strip()
    except OSError:
        print("session_check: no .line/stage here. Run start-session.sh for the item first.", file=sys.stderr)
        return 2
    if stage not in CHECKS:
        print(f"session_check: no check is written for the stage {stage!r}", file=sys.stderr)
        return 2
    try:
        problems = CHECKS[stage](argv[1], int(argv[2]))
    except RuntimeError as e:
        print(f"session_check: {e}", file=sys.stderr)
        return 2
    if problems:
        print("The commit check refuses this commit:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1
    print(f"commit check ({stage}): passed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
