#!/bin/sh
# Generate (promptfoo), convert to deterministic-only evals, and run against the local agent target.
# Usage: sh run_all.sh <protection: off|on> <tests-per-plugin> [channels...]
set -u
cd "$(dirname "$0")"
PROT=${1:-off}; N=${2:-3}; shift 2 || true
CHANNELS=${*:-"user web html api email pdf docx markdown code ocr_text image db"}
PY=../../.venv/Scripts/python; [ -x "$PY" ] || PY=../../.venv/bin/python
export PROMPTFOO_DISABLE_TELEMETRY=1 PROMPTFOO_DISABLE_UPDATE=1
mkdir -p output
$PY make_configs.py --n "$N" --protection "$PROT" >/dev/null
for ch in $CHANNELS; do
  base="output/$ch.$PROT"
  if [ ! -f "$base.tests.yaml" ]; then
    npx promptfoo redteam generate -c "configs/$ch.$PROT.yaml" -o "$base.tests.yaml" < /dev/null > "$base.gen.log" 2>&1 || echo "generate failed: $ch"
  fi
  $PY to_plain_eval.py "$base.tests.yaml" >/dev/null
  npx promptfoo eval -c "$base.plain.yaml" -o "$base.results.json" --no-cache -j 2 < /dev/null > "$base.eval.log" 2>&1
  echo "$ch done: $(grep -E 'Results:' "$base.eval.log" | tail -1)"
done
