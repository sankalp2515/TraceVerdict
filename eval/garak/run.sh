#!/bin/sh
# Run garak probe families against the local agent target (eval/targets/agent_target.py on :8787).
# garak's own detectors grade each attempt. Usage: sh run.sh <protection: off|on> [generations]
set -u
cd "$(dirname "$0")"
PROT=${1:-off}; GENS=${2:-1}
PY=../../.venv-garak/Scripts/python; [ -x "$PY" ] || PY=../../.venv-garak/bin/python
mkdir -p runs
sed "s/\"protection\": \"off\"/\"protection\": \"$PROT\"/" rest_target.json > "runs/target.$PROT.json"
# Probe families -> categories: eval/asg_eval/category_map.yaml (garak_probes)
PROBES="encoding.InjectBase64,encoding.InjectHex,encoding.InjectROT13,encoding.InjectBase32,encoding.InjectUnicodeTagChars,encoding.InjectZalgo,latentinjection.LatentInjectionReport,latentinjection.LatentInjectionResume,latentinjection.LatentInjectionFactSnippetEiffel,latentinjection.LatentInjectionFactSnippetLegal,latentinjection.LatentWhois,dan.DanInTheWild"
"$PY" -m garak --model_type rest -G "runs/target.$PROT.json" --probes "$PROBES" \
  --config config.yaml --generations "$GENS" --report_prefix "runs/$PROT" 2>&1 | tail -40
