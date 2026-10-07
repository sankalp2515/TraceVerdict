#!/bin/sh
# Run garak probe families against the local agent target (eval/targets/agent_target.py on :8787).
# garak's own detectors grade each attempt. Usage: sh run.sh <protection: off|on> [generations]
set -u
cd "$(dirname "$0")"
PROT=${1:-off}; GENS=${2:-1}
PY=../../.venv-garak/Scripts/python; [ -x "$PY" ] || PY=../../.venv-garak/bin/python
mkdir -p runs
sed "s/\"protection\": \"off\"/\"protection\": \"$PROT\"/" rest_target.json > "runs/target.$PROT.json"
# Probe families -> categories: eval/intentseal_eval/category_map.yaml (garak_probes)
PROBES="encoding.InjectBase64,encoding.InjectHex,encoding.InjectROT13,encoding.InjectBase32,encoding.InjectUnicodeTagChars,encoding.InjectZalgo,latentinjection.LatentInjectionReport,latentinjection.LatentInjectionResume,latentinjection.LatentInjectionFactSnippetEiffel,latentinjection.LatentInjectionFactSnippetLegal,latentinjection.LatentWhois,dan.DanInTheWild"
# garak resolves a relative --report_prefix against its own run directory: pass an absolute path.
RUNS="$(cd runs && (pwd -W 2>/dev/null || pwd))"
"$PY" -m garak --model_type rest -G "runs/target.$PROT.json" --probes "$PROBES" \
  --config config.yaml --generations "$GENS" --report_prefix "$RUNS/$PROT" 2>&1 | tail -40
# Harvest only (no target calls; the attempts feed eval/promptfoo/build_suites.py):
#   "$PY" -m garak --model_type test.Blank --probes "$PROBES" --config config.yaml --report_prefix "$RUNS/harvest"
