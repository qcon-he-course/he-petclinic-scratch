#!/usr/bin/env python3
"""check: accept a headless agent's output as a box's result, or fail closed. No model.

  check.py <box> <schema.json> <raw result.json> <clone> <inputs dir> <out dir>

<raw result.json> is what `claude -p --output-format json --json-schema ...` printed
(the result is in its "structured_output"), or the file `codex exec --output-schema
... -o` wrote (the result is the whole object).

Exit 0: <out dir>/<box>.json holds the result. Exit 1: <out dir>/<box>.why holds the
reason and there is no result; when the agent did return something and the check
refused it, <out dir>/<box>.rejected.json holds what it returned, for the agent's
next round and for nobody else. A run that ended in an error, hit its turn or budget
limit, returned no structured output, broke the schema or cited something that is
not there all exit 1. The gate reads a missing result as a failed check.

Beyond the schema, a result is held to what a script can check:
  - every "where" names a file of the clone, and lines that file has;
  - every "quote" is in the place its "where" names, character for character, and is
    at least eight characters long;
  - every duplicate names an item that is on the line;
  - the lists and the texts have a size a person can read;
  - the result does not contradict itself (one idea and two ideas; agrees and differs);
  - a pin names a test that exists or a test the result itself writes, in a new file
    under src/test/java, labelled observed;
  - a draft spec is a proposal and at least one delta spec, in the item's change folder;
  - a reviewer's finding has an id of its own and cites the draft.
"""
import os
import re
import sys

from common import dump, load

WHERE = re.compile(r"([^:\s]+)(?::(\d+)(?:-(\d+))?)?")
TEXT_LIMIT, LIST_LIMIT = 700, 12
LIMITS = {"content": 30000}  # a key whose text may be longer: the source of a test file
QUOTE_MIN = 8  # characters. A quote of code is often one word: th:text="${pet.type}"
TESTS = "src/test/java/"
PIN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*#[A-Za-z_][A-Za-z0-9_]*")


def schema_problems(value, schema, at="result"):
    """A small reading of JSON Schema: type, required, no other keys, enum, items."""
    kind = schema.get("type")
    if kind == "object":
        if not isinstance(value, dict):
            return [f"{at} is not an object"]
        out = [f"{at}: missing key {k}" for k in schema.get("required", []) if k not in value]
        out += [f"{at}: unknown key {k}" for k in value if k not in schema.get("properties", {})]
        for k, sub in schema.get("properties", {}).items():
            if k in value:
                out += schema_problems(value[k], sub, f"{at}.{k}")
        return out
    if kind == "array":
        if not isinstance(value, list):
            return [f"{at} is not a list"]
        if len(value) > LIST_LIMIT:
            return [f"{at} has {len(value)} entries; the limit is {LIST_LIMIT}"]
        return [p for i, v in enumerate(value) for p in schema_problems(v, schema.get("items", {}), f"{at}[{i + 1}]")]
    if kind == "string":
        if not isinstance(value, str):
            return [f"{at} is not text"]
        if not value.strip():
            return [f"{at} is empty"]
        limit = LIMITS.get(at.rsplit(".", 1)[-1], TEXT_LIMIT)
        if len(value) > limit:
            return [f"{at} has {len(value)} characters; the limit is {limit}"]
        if "enum" in schema and value not in schema["enum"]:
            return [f"{at}: {value!r} is not one of {schema['enum']}"]
        return []
    if kind == "boolean":
        return [] if isinstance(value, bool) else [f"{at} is not true or false"]
    if kind == "integer":
        return [] if isinstance(value, int) and not isinstance(value, bool) else [f"{at} is not a whole number"]
    return [f"{at}: the schema names no type this check reads"]


def where_problem(where, clone):
    """None when <where> names a file of the clone (and lines it has), else what is wrong."""
    m = WHERE.fullmatch(where.strip())
    if not m:
        return f"{where!r} is not written as path, path:line or path:line-line"
    path = os.path.normpath(m.group(1))
    if path.startswith(("..", "/")) or path == ".git" or path.startswith(".git/"):
        return f"{where!r} is outside the repository"
    full = os.path.join(clone, path)
    if os.path.isdir(full):
        return None if not m.group(2) else f"{where!r}: a folder has no lines"
    if not os.path.isfile(full):
        return f"{where!r}: no such file in the repository"
    if m.group(2):
        with open(full, encoding="utf-8", errors="replace") as f:
            lines = sum(1 for _ in f)
        last = int(m.group(3) or m.group(2))
        if int(m.group(2)) < 1 or last < int(m.group(2)) or last > lines:
            return f"{where!r}: the file has {lines} lines"
    return None


def quote_problem(where, quote, clone):
    """None when <quote> stands in the place <where> names, character for character; spacing is not compared."""
    m = WHERE.fullmatch(where.strip())
    full = os.path.join(clone, os.path.normpath(m.group(1)))
    if os.path.isdir(full):
        return f"{where!r} is a folder: a quote needs a file"
    with open(full, encoding="utf-8", errors="replace") as f:
        lines = f.read().split("\n")
    if m.group(2):
        first, last = int(m.group(2)), int(m.group(3) or m.group(2))
        lines = lines[first - 1:last]
    squeeze = lambda t: " ".join(t.split())
    words = squeeze(quote)
    if len(words) < QUOTE_MIN:
        return (f"the quote {words!r} for {where!r} is too short to show anything: copy at least {QUOTE_MIN} characters "
                "from those lines, code or text")
    if words not in squeeze(" ".join(lines)):
        return (f"the quote {words[:60]!r} is not at {where!r}: copy it exactly from those lines, "
                "or cite the lines where it stands")
    return None


def pin_problems(r, clone):
    out = []
    written = {f["path"]: f["content"] for f in r["files"]}
    if len(written) != len(r["files"]):
        out.append("a file is written twice")
    for path, content in written.items():
        norm = os.path.normpath(path)
        if norm != path or not path.startswith(TESTS) or not path.endswith(".java"):
            out.append(f"{path!r} is not a Java file under {TESTS}")
        elif os.path.exists(os.path.join(clone, path)):
            out.append(f"{path!r} exists: a pin is written in a new file, and no existing file changes")
        elif '@Tag("observed")' not in content:
            out.append(f"{path!r} has no test labelled @Tag(\"observed\")")
    if not r["pins"]:
        out.append("no pins: the stage records at least one behavior")
    seen = set()
    for pin in r["pins"]:
        if not PIN.fullmatch(pin["test"]):
            out.append(f"pin {pin['test']!r} is not written as TestClass#method")
            continue
        if pin["test"] in seen:
            out.append(f"pin {pin['test']} is named twice")
        seen.add(pin["test"])
        cls, method = pin["test"].split("#")
        if os.path.basename(pin["file"]) != f"{cls}.java":
            out.append(f"pin {pin['test']}: the file {pin['file']!r} is not {cls}.java")
            continue
        if pin["kind"] == "written":
            source = written.get(pin["file"])
            if source is None:
                out.append(f"pin {pin['test']} is written, and the result writes no file {pin['file']!r}")
                continue
        else:
            full = os.path.join(clone, os.path.normpath(pin["file"]))
            if not pin["file"].startswith(TESTS) or not os.path.isfile(full):
                out.append(f"pin {pin['test']} cites {pin['file']!r}, which is not a test file of the repository")
                continue
            with open(full, encoding="utf-8", errors="replace") as f:
                source = f.read()
        if not re.search(r"\bvoid\s+" + re.escape(method) + r"\s*\(", source):
            out.append(f"pin {pin['test']}: {pin['file']} has no test method {method}")
    for path in written:
        if not any(p["kind"] == "written" and p["file"] == path for p in r["pins"]):
            out.append(f"{path!r} is written and no pin names it")
    for cls in r["target_classes"]:
        if not cls.startswith("src/main/java/") or not cls.endswith(".java") or not os.path.isfile(os.path.join(clone, os.path.normpath(cls))):
            out.append(f"{cls!r} is not a production class of the repository")
    return out


def box_problems(box, r, clone, inputs):
    out = []
    quoted = []
    if box == "pin-agent":
        quoted = [(e["where"], e["quote"]) for k in ("pins", "suspects") for e in r[k]]
        out += pin_problems(r, clone)
    elif box == "spec-drafter":
        number = load(os.path.join(inputs, "item.json"))["number"]
        paths = [f["path"] for f in r["files"]]
        root = f"openspec/changes/item-{number}/"
        spec = re.compile(re.escape(root) + r"specs/[a-z0-9][a-z0-9/-]*/spec\.md")
        out += [f"{p!r} is not a file of the draft: proposal.md or specs/<capability>/spec.md under {root}"
                for p in paths if p != root + "proposal.md" and not spec.fullmatch(p)]
        if len(set(paths)) != len(paths):
            out.append("a file is written twice")
        if root + "proposal.md" not in paths or not any(spec.fullmatch(p) for p in paths):
            out.append("the draft is a proposal.md and at least one delta spec, each returned whole")
    elif box == "spec-reviewer":
        number = load(os.path.join(inputs, "item.json"))["number"]
        quoted = [(f["where"], f["quote"]) for f in r["findings"]]
        ids = [f["id"] for f in r["findings"]]
        out += [f"finding id {i!r} is not S<number>" for i in ids if not re.fullmatch(r"S[0-9]+", i)]
        out += [f"finding id {i} is used twice" for i in sorted({i for i in ids if ids.count(i) > 1})]
        out += [f"{f['id']} cites {f['where']!r}, which is not in the draft" for f in r["findings"]
                if not f["where"].startswith(f"openspec/changes/item-{number}/")]
    elif box == "intake-agent":
        quoted = [(e["where"], e["quote"]) for k in ("terms", "related", "reversed_decisions") for e in r[k]]
        if r["one_idea"] and len(r["ideas"]) != 1:
            out.append("one_idea is true, so ideas holds the one idea, restated")
        if not r["one_idea"] and len(r["ideas"]) < 2:
            out.append("one_idea is false, so ideas holds each idea, at least two")
        on_line = {i["number"] for i in load(os.path.join(inputs, "items.json"))}
        out += [f"duplicate #{d['item']} is not an item on the line" for d in r["duplicates"] if d["item"] not in on_line]
    elif box == "classifier":
        quoted = [(f["where"], f["quote"]) for f in r["facts"]]
        item = load(os.path.join(inputs, "item.json"))
        if not r["facts"]:
            out.append("no facts: a view of the type comes with the facts behind it")
        if r["agrees"] != (r["type"] == item["type"]):
            out.append(f"agrees is {r['agrees']}, the requester picked {item['type']} and the result says {r['type']}")
    else:
        out.append(f"no check is written for the box {box!r}")
    for where, quote in quoted:
        problem = where_problem(where, clone) or quote_problem(where, quote, clone)
        if problem:
            out.append(problem)
    return out


def extract(result):
    """(result, reason it cannot be used). Claude Code wraps the result; Codex writes it bare."""
    if not isinstance(result, dict):
        return None, "the output is not a JSON object"
    if "type" in result and "subtype" in result:  # Claude Code's result message
        if result.get("is_error") or result.get("subtype") != "success":
            said = " ".join(str(result.get("result") or "").split())[:300]
            return None, (f"the run did not succeed: subtype {result.get('subtype')!r}, is_error {result.get('is_error')!r}"
                          + (f"; it said: {said}" if said else ""))
        if result.get("structured_output") is None:
            return None, "the run returned no structured output"
        return result["structured_output"], None
    return result, None


def main(argv):
    if len(argv) != 6:
        print(__doc__.split("\n\n")[1], file=sys.stderr)
        return 2
    box, schema, raw, clone, inputs, out = argv
    os.makedirs(out, exist_ok=True)
    good, bad = os.path.join(out, f"{box}.json"), os.path.join(out, f"{box}.why")
    rejected = os.path.join(out, f"{box}.rejected.json")
    for stale in (good, bad, rejected):
        if os.path.exists(stale):
            os.remove(stale)

    def refuse(why):
        with open(bad, "w", encoding="utf-8") as f:
            f.write(why + "\n")
        print(f"check: no result from {box}: {why}", file=sys.stderr)
        return 1

    try:
        result, why = extract(load(raw))
    except (OSError, ValueError) as e:
        return refuse(f"the output could not be read ({type(e).__name__})")
    if why:
        return refuse(why)
    problems = schema_problems(result, load(schema))
    if not problems:
        problems = box_problems(box, result, clone, inputs)
    if problems:
        if isinstance(result, dict):
            dump(rejected, result)
        return refuse("; ".join(problems[:6]) + (f"; and {len(problems) - 6} more" if len(problems) > 6 else ""))
    dump(good, result)
    print(f"check: {box} left a result")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
