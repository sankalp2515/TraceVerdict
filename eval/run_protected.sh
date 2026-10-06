#!/bin/sh
# One clean protected evaluation: three targets on the current code, three run queues in parallel.
#   8788 detect (content checkpoint): attack suite, held-out benign, dev benign, user channel
#   8789 end-to-end protected subset (agent_eval role)
#   8790 headline protected suite (agent_headline role, single model)
# Every output carries the target's engine fingerprint; asg_eval.summary reports them per suite.
# The Tier 2 daily cap is lifted for evaluation (recorded in the summary): a production cap is not an eval limit.
set -u
cd "$(dirname "$0")"
PY=../.venv/Scripts/python; [ -x "$PY" ] || PY=../.venv/bin/python
export ASG_BUDGET_TIER2_DAILY_TOKENS=none
mkdir -p ../data/logs
"$PY" -m uvicorn targets.agent_target:app --port 8788 --log-level warning > ../data/logs/target.8788.log 2>&1 &
T1=$!
ASG_AGENT_ROLE=agent_eval "$PY" -m uvicorn targets.agent_target:app --port 8789 --log-level warning > ../data/logs/target.8789.log 2>&1 &
T2=$!
ASG_AGENT_ROLE=agent_headline "$PY" -m uvicorn targets.agent_target:app --port 8790 --log-level warning > ../data/logs/target.8790.log 2>&1 &
T3=$!
trap 'kill $T1 $T2 $T3 2>/dev/null' EXIT
for port in 8788 8789 8790; do
  for i in $(seq 1 60); do curl -s "127.0.0.1:$port/healthz" > /dev/null && break; sleep 3; done
  echo "target $port: $(curl -s 127.0.0.1:$port/healthz)"
done
cd promptfoo
( sh run_suite.sh v3 detect 2 db docx code pdf web html api email markdown ocr_text image pdf_hidden docx_hidden html_hidden \
  && sh run_suite.sh ho1 detect 2 && sh run_suite.sh hb3 detect 2 && sh run_suite.sh v3 detect 2 user ) > ../../data/logs/q_detect.log 2>&1 &
Q1=$!
sh run_suite.sh v2e on 2 > ../../data/logs/q_e2e.log 2>&1 &
Q2=$!
sh run_suite.sh headline on 1 email pdf web user > ../../data/logs/q_headline.log 2>&1 &
Q3=$!
wait $Q1 $Q2 $Q3
echo "all queues finished"
