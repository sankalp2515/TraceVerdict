#!/bin/sh
# Backlog C runs (7 Oct): multi-turn suite (C2), headline protected run with per-run usage (C1), scored garak run (C6).
# Same pattern as run_protected.sh: fresh targets on the current code, every output stamped with the engine fingerprint.
set -u
cd "$(dirname "$0")"
PY=../.venv/Scripts/python; [ -x "$PY" ] || PY=../.venv/bin/python
GPY="$(cd .. && pwd)/.venv-garak/Scripts/python"; [ -x "$GPY" ] || GPY="$(cd .. && pwd)/.venv-garak/bin/python"
export ASG_BUDGET_TIER2_DAILY_TOKENS=none
mkdir -p ../data/logs garak/runs
ASG_AGENT_ROLE=agent_eval "$PY" -m uvicorn targets.agent_target:app --port 8787 --log-level warning > ../data/logs/target.8787.log 2>&1 &
T0=$!
ASG_AGENT_ROLE=agent_eval "$PY" -m uvicorn targets.agent_target:app --port 8789 --log-level warning > ../data/logs/target.8789.log 2>&1 &
T1=$!
ASG_AGENT_ROLE=agent_headline "$PY" -m uvicorn targets.agent_target:app --port 8790 --log-level warning > ../data/logs/target.8790.log 2>&1 &
T2=$!
trap 'kill $T0 $T1 $T2 2>/dev/null' EXIT
for port in 8787 8789 8790; do
  for i in $(seq 1 60); do curl -s "127.0.0.1:$port/healthz" > /dev/null && break; sleep 3; done
  echo "target $port: $(curl -s 127.0.0.1:$port/healthz)"
done
( cd promptfoo && sh run_suite.sh mt3 off 2 user && sh run_suite.sh mt3 on 2 user ) > ../data/logs/q_mt3.log 2>&1 &
Q1=$!
( cd promptfoo && sh run_suite.sh headline on 1 email pdf web user ) > ../data/logs/q_headline.log 2>&1 &
Q2=$!
(
  cd garak
  RUNS="$(cd runs && (pwd -W 2>/dev/null || pwd))"
  PROBES="encoding.InjectBase64,encoding.InjectROT13,encoding.InjectUnicodeTagChars,latentinjection.LatentInjectionReport,latentinjection.LatentInjectionResume,latentinjection.LatentWhois,promptinject.HijackKillHumans,dan.DanInTheWild"
  for PROT in off on; do
    sed "s/\"protection\": \"off\"/\"protection\": \"$PROT\"/" rest_target.json > "runs/target.$PROT.json"
    "$GPY" -m garak --model_type rest -G "runs/target.$PROT.json" --probes "$PROBES" --config config.small.yaml \
      --generations 1 --report_prefix "$RUNS/scored.$PROT" 2>&1 | grep -E "PASS|FAIL|ok on|report closed|Error" | tail -40
  done
) > ../data/logs/q_garak.log 2>&1 &
Q3=$!
wait $Q1 $Q2 $Q3
echo "all backlog C queues finished"
