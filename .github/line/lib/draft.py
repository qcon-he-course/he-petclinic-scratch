#!/usr/bin/env python3
"""draft: write the spec-drafter's files into a checkout, and run the completeness check on them. No model, no key.

  draft.py write <spec-drafter.json> <clone> <item>
      Writes each file of the draft under openspec/changes/item-<item>/.
  draft.py check <clone> <item> <out dir>
      Runs lib/spec_check.py on the working tree and writes <out dir>/completeness.json,
      with the commit the draft was written onto. Prints passed=yes|no, also to $GITHUB_OUTPUT.
"""
import os
import re
import subprocess
import sys

import spec_check
from common import dump, load


def allowed(path, item):
    root = f"openspec/changes/item-{item}/"
    return path == root + "proposal.md" or bool(re.fullmatch(re.escape(root) + r"specs/[a-z0-9][a-z0-9/-]*/spec\.md", path))


def write(result, clone, item):
    for f in result["files"]:
        path = os.path.normpath(f["path"])
        if path != f["path"] or not allowed(path, item):
            raise SystemExit(f"draft: {f['path']!r} is not a file of the draft")
        full = os.path.join(clone, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as out:
            out.write(f["content"] if f["content"].endswith("\n") else f["content"] + "\n")


def main(argv):
    if len(argv) == 4 and argv[0] == "write" and argv[3].isdigit():
        write(load(argv[1]), argv[2], int(argv[3]))
        return 0
    if len(argv) == 4 and argv[0] == "check" and argv[2].isdigit():
        result = spec_check.check_files(argv[1], int(argv[2]))
        head = subprocess.run(["git", "-C", argv[1], "rev-parse", "HEAD"], capture_output=True, text=True)
        result["head"] = head.stdout.strip() or None
        os.makedirs(argv[3], exist_ok=True)
        dump(os.path.join(argv[3], "completeness.json"), result)
        said = "passed=" + ("yes" if result["passed"] else "no")
        print(said + "".join(f"\n  - {g}" for g in result["gaps"]))
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
                f.write(said + "\n")
        return 0
    print(__doc__.split("\n\n")[1], file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
