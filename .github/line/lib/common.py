"""What the line's scripts share: reading files, and making text safe to post.

Everything an agent or a requester wrote is data. Before it goes into a comment it is
cut to a length and stripped of what GitHub would act on: mentions, HTML, links.
"""
import json
import re

BOXES = ["intake-agent", "intake-check", "classifier"]
BOX_NAMES = {"intake-agent": "Intake agent", "intake-check": "Intake check", "classifier": "Classifier agent",
             "admission-gate": "Admission gate"}
MARK = "<!-- line:result stage={stage} box={box} run={run} -->"


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


def data_block(result, stage, box, run):
    """The result as data, for the boxes that read the item later, and the marker they look for."""
    body = json.dumps(result, indent=2, ensure_ascii=True)
    for ch in "<>`@":  # still valid JSON, and nothing GitHub acts on
        body = body.replace(ch, "\\u%04x" % ord(ch))
    return ("<details><summary>The result, as data</summary>\n\n```json\n" + body + "\n```\n\n</details>\n"
            + MARK.format(stage=stage, box=box, run=run))
