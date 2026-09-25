#!/usr/bin/env bash
# git-tree.sh — regenerate GIT_TREE.md (the living map). Run after EVERY merge and
# every new iteration commit. Doctrine §3.3: GIT_TREE.md must never be more than
# one iteration stale.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

OUT=GIT_TREE.md
LAST_MAIN=$(git log -1 --format='%h %s' main)
NOW=$(date -u '+%Y-%m-%d %H:%M UTC')

{
echo "# GIT_TREE.md — living map (auto-generated: scripts/git-tree.sh)"
echo
echo "> Regenerated: **$NOW** · repo HEAD: \`$LAST_MAIN\`"
echo "> Doctrine: this file is refreshed at EVERY merge/iteration commit. If it's stale, run the script."
echo
echo "## Tree (source zones; evidence/cold zones summarized)"
echo '```'
find engine retell services docs plans scripts -maxdepth 3 -type d \
  -not -path "*/.venv*" -not -path "*__pycache__*" -not -path "*/.pytest_cache*" \
  -not -path "*/node_modules*" -not -path "*/json_logs*" \
  | sort | awk -F/ '{
      indent=""; for(i=2;i<NF;i++) indent=indent"  ";
      printf "%s%s/\n", indent, $NF
    }'
echo '```'
echo
echo "## Engine iteration branches (the real history)"
echo '```'
git for-each-ref --sort=-committerdate --format='%(refname:short)|%(objectname:short)|%(committerdate:short)|%(subject)' 'refs/heads/engine/*' \
  | awk -F'|' '{printf "  %-42s %s  %s  %s\n", $1, $2, $3, substr($4,1,80)}'
echo '```'
echo
echo "## History-preserving refs (nested-repo archaeology)"
echo '```'
git for-each-ref --format='%(refname:short)' 'refs/heads/history/*' | sed 's/^/  /'
echo '```'
echo
echo "## Root repo — recent main"
echo '```'
git log --oneline -8 main | sed 's/^/  /'
echo '```'
echo
echo "## Cold archive (tarballs, gitignored — NOT in git)"
echo '```'
ls -lh _cold_archive/*.tar 2>/dev/null | awk '{printf "  %-8s %s %s %s\n", $5, $9, $6, $7}'
echo '```'
} > "$OUT"

echo "regenerated $OUT ($(wc -l < "$OUT") lines)"
