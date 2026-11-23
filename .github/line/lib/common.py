"""What the line's scripts share: reading files, and making text safe to post.

Everything an agent or a requester wrote is data. Before it goes into a comment it is
cut to a length and stripped of what GitHub would act on: mentions, HTML, links.
"""
import json
import re

BOXES = ["intake-agent", "intake-check", "classifier"]
BOX_NAMES = {"intake-agent": "Intake agent", "intake-check": "Intake check", "classifier": "Classifier agent",
             "admission-gate": "Admission gate", "pin-agent": "Pin-requirements agent", "mutation-sensor": "Mutation sensor",
             "understand-gate": "Understand gate"}
MARK = "<!-- line:result stage={stage} box={box} run={run} -->"
MARK_RE = re.compile(r"<!-- line:result stage=([a-z-]+) box=([a-z-]+) run=(\w+) -->\s*$")
BOT = "github-actions[bot]"


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def text(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def dump(path, value):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(value, f, indent=2, ensure_ascii=False)
        f.write("\n")


def clean(text, limit=600):
    """One line of text that GitHub renders as text and nothing else."""
    s = " ".join(str(text).split())
    if len(s) > limit:
        s = s[: limit - 1].rstrip() + "…"
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    s = s.replace("@", "@​")           # no mention, no notification
    s = re.sub(r"([\[\]`|*_!#])", r"\\\1", s)  # no link, image, code span, table cell or heading
    return s


def code(text, limit=200):
    """A path or a name, shown as code."""
    s = " ".join(str(text).split())[:limit].replace("`", "'")
    return f"`{s}`" if s else ""


def data_block(result, stage, box, run, ran=None):
    """The result as data, for the boxes that read the item later, and the marker they look for.
    <ran> says what produced it: the tool, the model, the turns, the cost, the seconds."""
    body = json.dumps({"ran": ran or {}, "result": result}, indent=2, ensure_ascii=True)
    for ch in "<>`@":  # still valid JSON, and nothing GitHub acts on
        body = body.replace(ch, "\\u%04x" % ord(ch))
    return ("<details><summary>The result, as data</summary>\n\n```json\n" + body + "\n```\n\n</details>\n"
            + MARK.format(stage=stage, box=box, run=run))


def foot(stage, by, run, url=""):
    ran = f"[run {run}]({url})" if url else f"run {run}"
    return f"<sub>{stage} · {by} · {ran}</sub>"


def ran_line(ran):
    """What ran a box, in one line, from the facts lib/ran.py recorded."""
    if not ran:
        return "a job, no model"
    parts = [f"{ran['tool']}, {ran['model']}"]
    if ran.get("turns") is not None:
        parts.append(f"{ran['turns']} turns")
    if ran.get("cost_usd") is not None:
        parts.append(f"${ran['cost_usd']:.2f}")
    if ran.get("seconds") is not None:
        parts.append(f"{ran['seconds']} s")
    return ", ".join(parts)


def read_results(comments):
    """The results posted on an item, newest last: a list of (stage, box, run, ran, result).

    Only a comment by the workflow's own account counts. Anyone may comment on an issue,
    and a comment that looks like a result is not one."""
    out = []
    for c in comments:
        if c.get("user", {}).get("login") != BOT:
            continue
        m = MARK_RE.search(c.get("body") or "")
        if not m:
            continue
        try:
            data = json.loads(c["body"].split("```json\n", 1)[1].rsplit("\n```", 1)[0])
        except (IndexError, ValueError):
            continue
        if isinstance(data, dict) and set(data) == {"ran", "result"}:
            out.append((m.group(1), m.group(2), m.group(3), data["ran"] or {}, data["result"]))
        elif isinstance(data, dict):  # the first run's comments carry the bare result
            out.append((m.group(1), m.group(2), m.group(3), {}, data))
    return out


def latest(results, stage, box):
    """The newest result a box left at a stage, or None."""
    found = [r for r in results if r[0] == stage and r[1] == box]
    return found[-1][4] if found else None
