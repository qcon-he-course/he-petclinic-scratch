#!/usr/bin/env bash
# Set up the owner's attended session for Shape, part one, on this computer.
#
#   .github/line/shape/start-session.sh <item>
#
# Run it from a clone of this repository that is on the default branch and up to
# date: the default branch holds the line's scripts and skills. It makes a second
# working folder beside the clone, on the item's branch, and puts three things there
# that git does not track:
#   .line/item.md      what the line knows about the item: the idea, the pins, the notes
#   .line/stage        the stage, which tells the commit check what a commit may change
#   .claude/skills/    the refine-item skill, for the assistant
# It also installs the commit check as this clone's pre-commit hook. The hook acts on
# item branches only. A person can skip it (git commit --no-verify); the same check
# runs again in CI, where nobody can.
set -euo pipefail
[ $# = 1 ] || { sed -n '3p' "$0" >&2; exit 2; }
item="$1"
case "$item" in ''|*[!0-9]*) echo "the item is a number" >&2; exit 2 ;; esac
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
line="$(dirname "$here")"
clone="$(git -C "$here" rev-parse --show-toplevel)"
folder="$(dirname "$clone")/$(basename "$clone")-item-$item"
repo="$(git -C "$clone" remote get-url origin | sed -E 's#^(https://github.com/|git@github.com:)##; s#\.git$##')"

git -C "$clone" fetch --quiet origin "+refs/heads/item-$item:refs/remotes/origin/item-$item"
if [ -d "$folder" ]; then
  git -C "$folder" pull --quiet --ff-only origin "item-$item"
else
  git -C "$clone" worktree add --quiet --no-track -B "item-$item" "$folder" "origin/item-$item"
fi
# The branch pushes to and pulls from its namesake, also in a clone that tracks one branch.
git -C "$folder" config "branch.item-$item.remote" origin
git -C "$folder" config "branch.item-$item.merge" "refs/heads/item-$item"

mkdir -p "$folder/.line" "$folder/.claude/skills"
rm -rf "$folder/.claude/skills/refine-item"
cp -R "$here/refine-item" "$folder/.claude/skills/refine-item"
echo "shape-1" > "$folder/.line/stage"
echo "$line" > "$folder/.line/control"
python3 -B "$line/lib/brief.py" "$repo" "$item" "$folder/.line/item.md"

exclude="$(git -C "$clone" rev-parse --git-common-dir)/info/exclude"
case "$exclude" in /*) ;; *) exclude="$clone/$exclude" ;; esac
for path in .line/ .claude/; do
  grep -qxF "$path" "$exclude" 2> /dev/null || echo "$path" >> "$exclude"
done

hook="$(dirname "$exclude")/../hooks/pre-commit"
if [ -e "$hook" ] && ! grep -q "the line's commit check" "$hook"; then
  echo "A pre-commit hook exists and is not the line's: $hook. It is left alone, so the check will not run before a commit." >&2
else
  cat > "$hook" <<HOOK
#!/bin/sh
# the line's commit check: acts on item branches, at the stage .line/stage names
branch="\$(git symbolic-ref --short HEAD 2> /dev/null)"
top="\$(git rev-parse --show-toplevel)"
case "\$branch" in
  item-*)
    [ "\$(cat "\$top/.line/stage" 2> /dev/null)" = "shape-1" ] || exit 0
    exec python3 -B "$line/lib/shape_check.py" commit "\$top" "\${branch#item-}"
    ;;
esac
HOOK
  chmod +x "$hook"
fi

cat <<SAY

The session for item $item is ready in:
  $folder

Start Claude Code in that folder and say:
  Refine item $item with me. Use the refine-item skill.

When no question is open, the assistant commits and pushes the decisions. Then add
the label "answered" to the item. That starts the commit check in CI.
SAY
