#!/bin/sh
# B3 final evaluation: every engine-dependent result regenerated on the current code, in one orchestrated run.
#   1. archive the engine-dependent results of the previous run (unprotected OFF runs are kept: they never touch
#      the engine, only the agent model)
#   2. fresh targets: 8787 garak (agent_eval), 8788 detect (content checkpoint), 8789 agent_eval, 8790 agent_headline
#   3. three queues in parallel:
#        detect: v3 attack suite on all 14 channels, held-out benign ho1, dev benign hb3, v3 user channel
#        e2e:    v2e protected, mt3 multi-turn protected, broad protected
#        head:   headline protected (per-run cost G7b), then garak scored run (protected)
#   4. benign task utility (protected) and isolated fast-path latency
# Then: python -m intentseal_eval.summary --attack v3 --dev hb3 --holdout ho1 --e2e headline v2e broad mt3
#       python -m intentseal_eval.readme
# Every output carries the target's engine fingerprint; the Tier 2 daily cap is lifted (recorded in the summary).
set -u
cd "$(dirname "$0")"
PY=../.venv/Scripts/python; [ -x "$PY" ] || PY=../.venv/bin/python
GPY="$(cd .. && pwd)/.venv-garak/Scripts/python"; [ -x "$GPY" ] || GPY="$(cd .. && pwd)/.venv-garak/bin/python"
export INTENTSEAL_BUDGET_TIER2_DAILY_TOKENS=none
STAMP=$(date +%Y-%m-%d-%H%M)
mkdir -p ../data/logs "promptfoo/output/archive/$STAMP" "garak/runs/archive/$STAMP"

for pat in "*.detect.v3." "*.detect.ho1." "*.detect.hb3." "*.on.v2e." "*.on.headline." "*.on.mt3." "*.on.broad."; do
  for f in promptfoo/output/${pat}results.json promptfoo/output/${pat}eval.log; do
    [ -f "$f" ] && mv "$f" "promptfoo/output/archive/$STAMP/"
  done
done
for f in garak/runs/scored.on.*; do [ -f "$f" ] && mv "$f" "garak/runs/archive/$STAMP/"; done
echo "archived previous engine-dependent results to promptfoo/output/archive/$STAMP"

INTENTSEAL_AGENT_ROLE=agent_eval "$PY" -m uvicorn targets.agent_target:app --port 8787 --log-level warning > ../data/logs/target.8787.log 2>&1 &
T0=$!
"$PY" -m uvicorn targets.agent_target:app --port 8788 --log-level warning > ../data/logs/target.8788.log 2>&1 &
T1=$!
INTENTSEAL_AGENT_ROLE=agent_eval "$PY" -m uvicorn targets.agent_target:app --port 8789 --log-level warning > ../data/logs/target.8789.log 2>&1 &
T2=$!
INTENTSEAL_AGENT_ROLE=agent_headline "$PY" -m uvicorn targets.agent_target:app --port 8790 --log-level warning > ../data/logs/target.8790.log 2>&1 &
T3=$!
trap 'kill $T0 $T1 $T2 $T3 2>/dev/null' EXIT
for port in 8787 8788 8789 8790; do
  for i in $(seq 1 60); do curl -s "127.0.0.1:$port/healthz" > /dev/null && break; sleep 3; done
  echo "target $port: $(curl -s 127.0.0.1:$port/healthz)"
done

( cd promptfoo && sh run_suite.sh v3 detect 2 db docx code pdf web html api email markdown ocr_text image pdf_hidden docx_hidden html_hidden \
  && sh run_suite.sh ho1 detect 2 && sh run_suite.sh hb3 detect 2 && sh run_suite.sh v3 detect 2 user ) > ../data/logs/q_detect.log 2>&1 &
Q1=$!
( cd promptfoo && sh run_suite.sh v2e on 2 && sh run_suite.sh mt3 on 2 user && sh run_suite.sh broad on 2 ) > ../data/logs/q_e2e.log 2>&1 &
Q2=$!
(
  cd promptfoo && sh run_suite.sh headline on 1 email pdf web user
  cd ../garak
  RUNS="$(cd runs && (pwd -W 2>/dev/null || pwd))"
  PROBES="encoding.InjectBase64,encoding.InjectROT13,encoding.InjectUnicodeTagChars,latentinjection.LatentInjectionReport,latentinjection.LatentInjectionResume,latentinjection.LatentWhois,promptinject.HijackKillHumans,dan.DanInTheWild"
  if [ -x "$GPY" ]; then
    sed 's/"protection": "off"/"protection": "on"/' rest_target.json > runs/target.on.json
    "$GPY" -m garak --model_type rest -G runs/target.on.json --probes "$PROBES" --config config.small.yaml \
      --generations 1 --report_prefix "$RUNS/scored.on" 2>&1 | grep -E "PASS|FAIL|ok on|report closed|Error" | tail -40
  else
    echo "garak environment (.venv-garak) not found: scored garak run skipped"
  fi
) > ../data/logs/q_head.log 2>&1 &
Q3=$!
wait $Q1 $Q2 $Q3
echo "promptfoo and garak queues finished"

"$PY" -m intentseal_eval.benign --protection on --role agent_eval > ../data/logs/q_benign.log 2>&1
"$PY" -m intentseal_eval.latency > ../data/logs/q_latency.log 2>&1
echo "all final-evaluation queues finished"
