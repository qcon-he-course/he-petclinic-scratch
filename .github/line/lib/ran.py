#!/usr/bin/env python3
"""ran: record what ran a box, for the item and for whoever reads past runs. No model.

  ran.py <tool> <model> <seconds> <raw result.json> <out .ran.json>

From Claude Code's result message it takes the turns and the cost. Codex writes only
the result, so for Codex the record has the tool, the model and the seconds.
"""
import json
import sys


def main(argv):
    if len(argv) != 5:
        print(__doc__.split("\n\n")[1], file=sys.stderr)
        return 2
    tool, model, seconds, raw, out = argv
    ran = {"tool": tool, "model": model, "seconds": int(seconds), "turns": None, "cost_usd": None}
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
    with open(out, "w", encoding="utf-8") as f:
        json.dump(ran, f, indent=2)
        f.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
