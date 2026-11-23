#!/usr/bin/env python3
"""pins: write the agent's test files into a checkout, and read what the build and
the mutation run left. No model, no key.

  pins.py write <pin-agent.json> <clone>
      Writes each new test file. Prints, also to $GITHUB_OUTPUT:
        tests=    what surefire runs: Class#method+method,Class#method
        suites=   the pins' test classes, fully qualified, for PIT's targetTests
        classes=  the production classes to mutate, fully qualified, for PIT's targetClasses
  pins.py read <pin-agent.json> <clone> <surefire reports dir> <mutations.xml> <build log> <out dir>
      Writes <out dir>/mutation-sensor.json: for each pin, whether it ran and passed,
      and whether a mutant can fail it.

A pin "can fail" when it killed at least one mutant. It "cannot fail" when mutants
ran under it and it killed none: it protects nothing. It is "not judged" when no
mutant ran under it: its behavior is outside the classes PIT changed, for example in
a template or a message file. "not run" means PIT left no report.
"""
import glob
import os
import re
import sys
import xml.etree.ElementTree as ET

from common import dump, load

TESTS, MAIN = "src/test/java/", "src/main/java/"
METHOD = re.compile(r"\[class:([^\]]+)\]/\[method:([A-Za-z0-9_]+)\(")


def qualified(path, root):
    return path[len(root):-len(".java")].replace("/", ".")


def write(result, clone):
    for f in result["files"]:
        path = os.path.normpath(f["path"])
        full = os.path.join(clone, path)
        if not path.startswith(TESTS) or not path.endswith(".java") or os.path.exists(full):
            raise SystemExit(f"pins: {f['path']!r} is not a new Java file under {TESTS}")
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as out:
            out.write(f["content"] if f["content"].endswith("\n") else f["content"] + "\n")
    by_class = {}
    for pin in result["pins"]:
        cls, method = pin["test"].split("#")
        by_class.setdefault((cls, pin["file"]), []).append(method)
    return {"tests": ",".join(f"{cls}#{'+'.join(ms)}" for (cls, _), ms in by_class.items()),
            "suites": ",".join(sorted({qualified(path, TESTS) for (_, path) in by_class})),
            "classes": ",".join(qualified(c, MAIN) for c in result["target_classes"])}


def surefire(folder):
    """{(class simple name, method): (passed|failed, message)} from surefire's XML."""
    out = {}
    for path in glob.glob(os.path.join(folder, "TEST-*.xml")):
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError:
            continue
        for case in root.iter("testcase"):
            cls = case.get("classname", "").rsplit(".", 1)[-1]
            method = re.sub(r"\(.*$", "", case.get("name", ""))
            if case.find("skipped") is not None:
                continue
            bad = case.find("failure") if case.find("failure") is not None else case.find("error")
            if bad is None:
                out[(cls, method)] = ("passed", None)
            else:
                said = " ".join(((bad.get("message") or "") + " " + (bad.get("type") or "")).split())
                out[(cls, method)] = ("failed", said[:300] or "the test failed")
    return out


def mutations(path):
    """(killed by, ran under, totals): two {(class, method): count} and {status: count}; None when there is no report."""
    if not os.path.isfile(path):
        return None
    killed, under, totals = {}, {}, {}
    for m in ET.parse(path).getroot().iter("mutation"):
        totals[m.get("status")] = totals.get(m.get("status"), 0) + 1
        names = lambda tag: {(c.rsplit(".", 1)[-1], meth) for c, meth in METHOD.findall(m.findtext(tag) or "")}
        kills = names("killingTests")
        for t in kills:
            killed[t] = killed.get(t, 0) + 1
        for t in kills | names("succeedingTests") | names("coveringTests"):
            under[t] = under.get(t, 0) + 1
    return killed, under, totals


def build_problem(log):
    """The compiler's or the build's own words, when the tests never ran."""
    if not os.path.isfile(log):
        return "the build left no log"
    with open(log, encoding="utf-8", errors="replace") as f:
        lines = [l.rstrip() for l in f if l.startswith("[ERROR]")]
    return " ".join(" ".join(lines[:12]).split())[:1200] or "the build ended without a test report"


def read(result, reports, mutation_file, log):
    ran = surefire(reports)
    muts = mutations(mutation_file)
    pins = []
    for pin in result["pins"]:
        key = tuple(pin["test"].split("#"))
        state, said = ran.get(key, ("did not run", None))
        row = {"test": pin["test"], "name": pin["name"], "kind": pin["kind"], "ran": state, "failure": said,
               "mutation": "not run", "killed": 0, "under": 0}
        if muts is not None:
            row["killed"], row["under"] = muts[0].get(key, 0), muts[1].get(key, 0)
            row["mutation"] = "can fail" if row["killed"] else "cannot fail" if row["under"] else "not judged"
        pins.append(row)
    built = bool(ran)
    return {"built": built, "build_problem": None if built else build_problem(log), "pins": pins,
            "mutants": muts[2] if muts is not None else None}


def main(argv):
    if argv[:1] == ["write"] and len(argv) == 3:
        got = write(load(argv[1]), argv[2])
        lines = [f"{k}={v}" for k, v in got.items()]
        print("\n".join(lines))
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
        return 0
    if argv[:1] == ["read"] and len(argv) == 7:
        os.makedirs(argv[6], exist_ok=True)
        r = read(load(argv[1]), argv[3], argv[4], argv[5])
        dump(os.path.join(argv[6], "mutation-sensor.json"), r)
        print("pins: " + ", ".join(f"{p['test']} {p['ran']}, {p['mutation']}" for p in r["pins"]))
        return 0
    print(__doc__.split("\n\n")[1], file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
