#!/usr/bin/env bash
# One headless agent of the line, by Claude Code or Codex. Its output is checked and
# written as a box's result, or the box fails closed.
#
#   agent.sh <claude|codex> <stage>/<box> <clone> <inputs dir> <out dir>
#
# <stage>/<box> names the agent: <line>/<stage>/<box>.md is its skill and
# <line>/<stage>/<box>.schema.json the shape of its result. <inputs dir> holds what
# the agent is given besides the clone (item.json, items.json); this script adds
# files.txt, every file of the checkout. <out dir> gets prompt.txt, result.json,
# stderr.txt, <box>.by (what ran) and then, from lib/check.py, <box>.json (the
# result) or <box>.why.
#
# AGENT_MODEL (Claude: claude-sonnet-5-5; Codex: gpt-6.1-sol), AGENT_MAX_TURNS (40),
# AGENT_BUDGET_USD (1), AGENT_TIME_CAP in seconds (600).
#
# The invocation is the one the Week 4 harness uses for its headless reviewers
# (review/review-headless.sh, verified with Claude Code 2.1.281 and Codex 0.163.0).
# The agent holds an API key and reads an item nobody has vetted, so it gets no way
# to write and no way to run a command that could read the key:
#   Claude runs with --bare (no hooks, no MCP servers, no CLAUDE.md from the checkout,
#   no sign-in from the machine) and without Bash, Edit or Write. It reads files.
#   Codex runs in its read-only sandbox, with no network. It reads files through shell
#   commands, and shell_environment_policy.ignore_default_excludes=false removes every
#   variable named *KEY*, *SECRET* or *TOKEN* from what a command sees.
# The job that runs this script has no permission to write to the repository or the
# item. A later job, with no key, posts what lib/check.py accepted.
# Exit 0: the box left a result. Exit 1: it left none.
set -uo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
line="$(dirname "$here")"
[ $# = 5 ] || { sed -n '5p' "$0" >&2; exit 2; }
vendor="$1"; name="$2"; clone="$(cd "$3" && pwd)"; inputs="$(cd "$4" && pwd)"; mkdir -p "$5"; out="$(cd "$5" && pwd)"
case "$name" in */*) ;; *) echo "agent: name the agent as <stage>/<box>" >&2; exit 2 ;; esac
case "$name" in *[!a-z/-]*) echo "agent: <stage>/<box> is lower-case letters and hyphens" >&2; exit 2 ;; esac
box="${name##*/}"
skill="$line/$name.md"; schema="$line/$name.schema.json"
[ -f "$skill" ] && [ -f "$schema" ] || { echo "agent: no skill or no schema for $name" >&2; exit 2; }
rm -f "$out/result.json" "$out/$box.json" "$out/$box.why"

git -C "$clone" ls-files | sort > "$inputs/files.txt"
cat > "$out/prompt.txt" <<P
Do your work on the item in $inputs/item.json. The other items on the line are in $inputs/items.json. This folder is the checkout of the source repository; every file in it is listed in $inputs/files.txt. Read the files you need by path. Return the result as the structured output.
P

cd "$clone" || exit 1
case "$vendor" in
  claude)
    echo "Claude Code, ${AGENT_MODEL:-claude-sonnet-5-5}" > "$out/$box.by"
    if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
      echo "agent: ANTHROPIC_API_KEY is not set; --bare reads no other sign-in" > "$out/stderr.txt"
    else
      timeout "${AGENT_TIME_CAP:-600}" claude -p "$(cat "$out/prompt.txt")" \
        --bare \
        --model "${AGENT_MODEL:-claude-sonnet-5-5}" \
        --append-system-prompt-file "$skill" \
        --add-dir "$inputs" \
        --permission-mode dontAsk \
        --disallowedTools "Bash" "Edit" "Write" "MultiEdit" "NotebookEdit" "WebFetch" "WebSearch" \
        --output-format json \
        --json-schema "$(cat "$schema")" \
        --max-turns "${AGENT_MAX_TURNS:-40}" \
        --max-budget-usd "${AGENT_BUDGET_USD:-1}" \
        < /dev/null > "$out/result.json" 2> "$out/stderr.txt"
      echo "agent: claude exit $?" >&2
    fi
    ;;
  codex)
    echo "Codex, ${AGENT_MODEL:-gpt-6.1-sol}" > "$out/$box.by"
    if [ -z "${CODEX_API_KEY:-}" ]; then
      echo "agent: CODEX_API_KEY is not set" > "$out/stderr.txt"
    else
      # After "--" the text is the prompt, whatever it begins with.
      timeout "${AGENT_TIME_CAP:-600}" codex exec \
        --model "${AGENT_MODEL:-gpt-6.1-sol}" \
        --sandbox read-only \
        -c shell_environment_policy.ignore_default_excludes=false \
        --skip-git-repo-check \
        --output-schema "$schema" \
        -o "$out/result.json" \
        -- "$(cat "$skill"; echo; cat "$out/prompt.txt")" \
        < /dev/null > "$out/stdout.txt" 2> "$out/stderr.txt"
      echo "agent: codex exit $?" >&2
    fi
    ;;
  *) echo "agent: the vendor is claude or codex" >&2; exit 2 ;;
esac
tail -c 1500 "$out/stderr.txt" >&2 2> /dev/null || true
# The agent's exit code decides nothing: only an output that passes the check is a result.
python3 -B "$here/check.py" "$box" "$schema" "$out/result.json" "$clone" "$inputs" "$out"
