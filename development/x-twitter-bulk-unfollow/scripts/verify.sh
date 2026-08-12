#!/bin/bash
# 只读验证: 检查 handles 是否已取关（uf:false = 实际已完成）
# 用法: SESSION_NAME=xxx TAB_ID=xxx INPUT_FILE=handles.json bash verify.sh
# 坑: SESSION 必须匹配 TAB 所属的 session（obu open-tab 时的名字），跨 session 全 EVAL_FAIL
cd "${WORKDIR:-$HOME/x-following-audit}"
SESSION="${SESSION_NAME:-x-verify}"
TAB="${TAB_ID:-0}"
LOG="${LOG_FILE:-verify_pending.txt}"
INPUT="${INPUT_FILE:-handles.json}"
: > "$LOG"

handles=$(python -c "import json; print(' '.join(json.load(open('$INPUT', encoding='utf-8'))))")

eval_js() {
  echo "$2" > p.json
  obu cdp --tab-id $TAB --session-id "$SESSION" --method Runtime.evaluate --params "$(cat p.json)" > e_out.json 2>&1
  python -c "
import json
try:
    j = json.load(open('e_out.json', encoding='utf-8'))
    print(j['result']['result']['value'])
except Exception:
    print('EVAL_FAIL')
"
}

done_cnt=0; pending_cnt=0
for h in $handles; do
  obu navigate --tab-id $TAB --session-id "$SESSION" --url "https://x.com/$h" > /dev/null 2>&1
  st=""
  for i in $(seq 1 12); do
    st=$(eval_js "" '{"expression":"JSON.stringify({p: location.pathname, r: document.readyState, uf: !!document.querySelector(\"[data-testid$=-unfollow]\")})","returnByValue":true}')
    if [[ "$st" == *"$h"* && "$st" == *'"r":"complete"'* ]]; then break; fi
    sleep 0.8
  done
  if [[ "$st" == *'"uf":false'* ]]; then
    echo "[$h] ALREADY_UNFOLLOWED" | tee -a "$LOG"
    done_cnt=$((done_cnt+1))
  elif [[ "$st" == *'"uf":true'* ]]; then
    echo "[$h] STILL_FOLLOWING" | tee -a "$LOG"
    pending_cnt=$((pending_cnt+1))
  else
    echo "[$h] UNKNOWN $st" | tee -a "$LOG"
  fi
done
echo "=== DONE done=$done_cnt pending=$pending_cnt ===" | tee -a "$LOG"
