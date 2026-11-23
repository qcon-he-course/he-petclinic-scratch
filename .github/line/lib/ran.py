#!/usr/bin/env python3
"""ran: record what ran a box, for the item and for whoever reads past runs. No model.

  ran.py <tool> <model> <seconds> <raw result.json> <out .ran.json>

From Claude Code's result message it takes the turns and the cost. Codex writes only
the result, so for Codex the record has the tool, the model and the seconds. On a
second try (AGENT_TRY=2) it adds to what the first try's record holds.
"""
import json
import os
import sys


def main(argv):
    if len(argv) != 5:
        print(__doc__.split("\n\n")[1], file=sys.stderr)
        return 2
    tool, model, seconds, raw, out = argv
    ran = {"tool": tool, "model": model, "seconds": int(seconds), "turns": None, "cost_usd": None,
           "tries": int(os.environ.get("AGENT_TRY", "1"))}
    before = None
    if ran["tries"] > 1 and os.path.isfile(out):  # a second try: add to what the first one used
        with open(out, encoding="utf-8") as f:
            before = json.load(f)
        ran["seconds"] += before.get("seconds") or 0
    try:
        with open(raw, encoding="utf-8") as f:
            result = json.load(f)
        if isinstance(result, dict) and "subtype" in result:
            if isinstance(result.get("num_turns"), int):
                ran["turns"] = result["num_turns"]
            if isinstance(result.get("total_cost_usd"), (int, float)):
                ran["cost_usd"] = round(float(result["total_cost_usd"]), 4)
    except (OSError, ValueError):
        pass
    if before:
        for key in ("turns", "cost_usd"):
            if ran[key] is not None or before.get(key) is not None:
                ran[key] = round((ran[key] or 0) + (before.get(key) or 0), 4)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(ran, f, indent=2)
        f.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
