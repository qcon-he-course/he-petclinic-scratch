#!/usr/bin/env python3
"""apply: carry out a box's effects on the item, through GitHub's API. No model, no key.

  apply.py <owner/repo> <item number> <effects.json> <line dir> [--dry]

<effects.json> holds comments (posted in order), labels to add, labels to remove and
accounts to assign. Every label the line uses is created first when the repository
lacks it, with the colour and description policy.json gives. --dry prints the calls
and makes none. The job's token is in GH_TOKEN; the calls go through the gh CLI.
"""
import json
import os
import subprocess
import sys
from urllib.parse import quote

from common import load


def call(method, path, body=None, dry=False, ok=()):
    """One API call. A status in <ok> is expected and not an error (a label that is already there)."""
    if dry:
        print(f"{method} {path}" + (f" {json.dumps(body, ensure_ascii=False)[:160]}" if body is not None else ""))
        return True
    cmd = ["gh", "api", "--method", method, path, "--silent"]
    if body is not None:
        cmd += ["--input", "-"]
    p = subprocess.run(cmd, input=json.dumps(body) if body is not None else None, capture_output=True, text=True)
    if p.returncode == 0 or any(f"HTTP {code}" in p.stderr for code in ok):
        return True
    print(f"apply: {method} {path} failed: {p.stderr.strip()[:300]}", file=sys.stderr)
    return False


def main(argv):
    dry = "--dry" in argv
    argv = [a for a in argv if a != "--dry"]
    if len(argv) != 4 or not argv[1].isdigit():
        print(__doc__.split("\n\n")[1], file=sys.stderr)
        return 2
    repo, number, effects, line = argv[0], argv[1], load(argv[2]), argv[3]
    labels = load(os.path.join(line, "policy.json"))["labels"]
    good = True
    for name, (colour, says) in labels.items():
        good &= call("POST", f"repos/{repo}/labels", {"name": name, "color": colour, "description": says}, dry, ok=(422,))
    unknown = [l for l in effects["add"] + effects["remove"] if l not in labels]
    if unknown:
        print(f"apply: not the line's labels: {unknown}", file=sys.stderr)
        return 1
    for name in effects["remove"]:
        good &= call("DELETE", f"repos/{repo}/issues/{number}/labels/{quote(name, safe='')}", None, dry, ok=(404,))
    if effects["add"]:
        good &= call("POST", f"repos/{repo}/issues/{number}/labels", {"labels": effects["add"]}, dry)
    for body in effects["comments"]:
        good &= call("POST", f"repos/{repo}/issues/{number}/comments", {"body": body}, dry)
    if effects["assign"]:
        good &= call("POST", f"repos/{repo}/issues/{number}/assignees", {"assignees": effects["assign"]}, dry)
    return 0 if good else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
