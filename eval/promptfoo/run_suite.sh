#!/bin/sh
# Run a built suite (build_suites.py) against the local agent target, one promptfoo eval per channel.
# Usage: sh run_suite.sh <suite> <protection: off|on|detect> [concurrency] [channels...]
set -u
cd "$(dirname "$0")"
SUITE=$1; PROT=$2; J=${3:-2}; shift 3 2>/dev/null || shift $#
export PROMPTFOO_DISABLE_TELEMETRY=1 PROMPTFOO_DISABLE_UPDATE=1
CHANNELS=${*:-$(ls output/*."$PROT"."$SUITE".plain.yaml 2>/dev/null | sed "s#output/##; s#\.$PROT\.$SUITE\.plain\.yaml##")}
for ch in $CHANNELS; do
  base="output/$ch.$PROT.$SUITE"
  if [ -f "$base.results.json" ]; then echo "$ch: results exist, skipped"; continue; fi
  npx promptfoo eval -c "$base.plain.yaml" -o "$base.results.json" --no-cache -j "$J" < /dev/null > "$base.eval.log" 2>&1
  echo "$ch done: $(grep -E 'Results:|Pass Rate' "$base.eval.log" | tail -1)"
done
