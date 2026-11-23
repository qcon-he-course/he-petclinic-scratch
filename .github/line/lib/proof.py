#!/usr/bin/env python3
"""proof: the intake check. It runs a failing test the item brings, and writes none. No model.

  proof.py plan <item.json>
      Prints ref=<branch> and test=<TestClass#method> (both empty when the item brings
      no proof), also to $GITHUB_OUTPUT.
  proof.py none <out dir>
      Writes the result for an item with no proof: nothing to run.
  proof.py read <item.json> <surefire reports dir> <out dir>
      Reads what the test run left and writes the result.

The result, <out dir>/intake-check.json, has one of four outcomes:
  nothing to run     the item brings no test
  fails as claimed   the named test ran and failed
  passes             the named test ran and passed: the claim is not confirmed
  could not run      no report of the named test: it did not compile, or does not exist
"""
import glob
import os
import sys
import xml.etree.ElementTree as ET

from common import dump, load


def result(outcome, proof, detail):
    return {"ran": outcome in ("fails as claimed", "passes"), "proof": proof, "outcome": outcome, "detail": detail}


def read_reports(folder, test):
    """(tests run, tests failed) for the named class or class#method, from surefire's XML."""
    cls, _, method = test.partition("#")
    ran = failed = 0
    for path in glob.glob(os.path.join(folder, "TEST-*.xml")):
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError:
            continue
        for case in root.iter("testcase"):
            if case.get("classname", "").rsplit(".", 1)[-1] != cls or (method and case.get("name") != method):
                continue
            if case.find("skipped") is not None:
                continue
            ran += 1
            if case.find("failure") is not None or case.find("error") is not None:
                failed += 1
    return ran, failed


def main(argv):
    if argv[:1] == ["plan"] and len(argv) == 2:
        proof = load(argv[1]).get("proof") or {"ref": "", "test": ""}
        lines = [f"ref={proof['ref']}", f"test={proof['test']}"]
        print("\n".join(lines))
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
        return 0
    if argv[:1] == ["none"] and len(argv) == 2:
        os.makedirs(argv[1], exist_ok=True)
        dump(os.path.join(argv[1], "intake-check.json"),
             result("nothing to run", None, "The item brings no failing test."))
        return 0
    if argv[:1] == ["read"] and len(argv) == 4:
        proof = load(argv[1])["proof"]
        name = f"{proof['ref']}:{proof['test']}"
        ran, failed = read_reports(argv[2], proof["test"])
        if ran == 0:
            r = result("could not run", name, "The build left no report of the named test.")
        elif failed:
            r = result("fails as claimed", name, f"{failed} of {ran} test(s) failed.")
        else:
            r = result("passes", name, f"{ran} test(s) ran and passed.")
        os.makedirs(argv[3], exist_ok=True)
        dump(os.path.join(argv[3], "intake-check.json"), r)
        print(f"proof: {r['outcome']}")
        return 0
    print(__doc__.split("\n\n")[1], file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
