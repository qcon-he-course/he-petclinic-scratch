#!/usr/bin/env python3
"""item: read a filed issue as an item of the line. No model, no key.

  item.py <issue.json> <others.json> <line dir> <out dir>

<issue.json> is the issue as GitHub's API returns it. <others.json> is the list of
issues that carry the label "line". Writes, into <out dir>:

  item.json     the idea in the requester's words, the type they picked, the proof
  items.json    the other items on the line: number, title, state
  effects.json  what to do on the issue: labels, and a comment when it is returned

Prints go=yes or go=no, also to $GITHUB_OUTPUT. The agents run only on go=yes.

An issue is an item when a named requester filed it through the form. Anyone may
file an issue in a public repository, and each item starts two agents that hold an
API key, so an issue from anyone else starts nothing and gets no reply.
"""
import os
import re
import sys

from common import clean, dump, load

IDEA_LIMIT = 4000
PROOF = re.compile(r"([A-Za-z0-9._/-]+):([A-Za-z0-9_]+(?:#[A-Za-z0-9_]+)?)")


def fields(body):
    """The form's three answers. The form writes its headings in order, so the last
    "### Proof" and the last "### Type" before it are the form's own, whatever the
    requester typed into the idea."""
    text = "\n" + (body or "").replace("\r\n", "\n").strip() + "\n"
    head = text.find("\n### Idea\n")
    proof = text.rfind("\n### Proof\n")
    kind = text.rfind("\n### Type\n", 0, proof if proof >= 0 else len(text))
    if head != 0 or kind < 0 or proof < kind:
        return None
    blank = lambda s: "" if s.strip() == "_No response_" else s.strip()
    return {"idea": blank(text[len("\n### Idea\n"):kind]),
            "type": blank(text[kind + len("\n### Type\n"):proof]),
            "proof": blank(text[proof + len("\n### Proof\n"):])}


def read(issue, people, policy):
    """(item, None) or (None, reason). A reason that starts with "quiet:" is not posted."""
    if "pull_request" in issue:
        return None, "quiet: a pull request is a change, and the line's items are issues"
    who = issue["user"]["login"]
    if who not in people["requesters"]:
        return None, f"quiet: {who} is not a named requester"
    got = fields(issue.get("body"))
    if got is None:
        return None, "The item was not filed through the form \"An idea for the line\", so the line cannot read it."
    if not got["idea"]:
        return None, "The item states no idea. One line is the minimum."
    by_name = {t["name"].lower(): key for key, t in policy["types"].items()}
    kind = by_name.get(got["type"].lower())
    if kind is None:
        return None, "The item's type is not one of: " + ", ".join(t["name"] for t in policy["types"].values()) + "."
    proof = None
    if got["proof"]:
        m = PROOF.fullmatch(got["proof"])
        if not m or ".." in m.group(1) or m.group(1).startswith(("-", "/")):
            return None, "The proof is not written as branch:TestClass#method."
        proof = {"ref": m.group(1), "test": m.group(2)}
    return {"number": issue["number"], "title": " ".join(issue["title"].split())[:200],
            "idea": got["idea"][:IDEA_LIMIT], "idea_cut": len(got["idea"]) > IDEA_LIMIT,
            "type": kind, "type_name": policy["types"][kind]["name"], "proof": proof,
            "requester": who}, None


def main(argv):
    if len(argv) != 4:
        print(__doc__.split("\n\n")[1], file=sys.stderr)
        return 2
    issue, others, line, out = load(argv[0]), load(argv[1]), argv[2], argv[3]
    people, policy = load(os.path.join(line, "people.json")), load(os.path.join(line, "policy.json"))
    os.makedirs(out, exist_ok=True)
    item, why = read(issue, people, policy)
    effects = {"comments": [], "add": [], "remove": [], "assign": []}
    if item:
        dump(os.path.join(out, "item.json"), item)
        dump(os.path.join(out, "items.json"),
             [{"number": o["number"], "title": " ".join(o["title"].split())[:200], "state": o["state"]}
              for o in others if "pull_request" not in o and o["number"] != issue["number"]])
        stale = [l for l in ("returned", "stuck", "called:product-owner", "called:tech-lead", "admit", "admitted",
                             "stage:understand") + tuple(f"type:{t}" for t in policy["types"] if t != item["type"])]
        effects.update(add=["line", "stage:intake", f"type:{item['type']}"], remove=stale)
    elif not why.startswith("quiet:"):
        effects.update(add=["line", "returned"],
                       comments=["### Intake\n\n**Returned to the requester.** " + clean(why)
                                 + "\n\nFile the idea again through the form."])
    dump(os.path.join(out, "effects.json"), effects)
    go = "yes" if item else "no"
    print(f"go={go}" + ("" if item else f" ({why})"))
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
            f.write(f"go={go}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
