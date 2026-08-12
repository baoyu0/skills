#!/bin/bash
# X batch unfollow FAST v2: 每用户最多2次尝试，FAIL 记入 retry 文件最后统一重试
# 用法: SESSION_NAME=xxx TAB_ID=xxx INPUT_FILE=handles.json LOG_FILE=out.txt bash batch_fast.sh
cd "${WORKDIR:-$HOME/x-following-audit}"
SESSION="${SESSION_NAME:-x-unfollow}"
TAB="${TAB_ID:-0}"
LOG="${LOG_FILE:-unfollow_fast.txt}"
INPUT="${INPUT_FILE:-handles.json}"
: > "$LOG"
: > "retry_${LOG}"

handles=$(python -c "import json; print(' '.join(json.load(open('$INPUT', encoding='utf-8'))))")

click_at() {
  obu cdp --tab-id $TAB --session-id "$SESSION" --method Input.dispatchMouseEvent --params "{\"type\":\"mouseMoved\",\"x\":$1,\"y\":$2}" > /dev/null 2>&1
  sleep 0.2
  obu cdp --tab-id $TAB --session-id "$SESSION" --method Input.dispatchMouseEvent --params "{\"type\":\"mousePressed\",\"x\":$1,\"y\":$2,\"button\":\"left\",\"clickCount\":1}" > /dev/null 2>&1
  obu cdp --tab-id $TAB --session-id "$SESSION" --method Input.dispatchMouseEvent --params "{\"type\":\"mouseReleased\",\"x\":$1,\"y\":$2,\"button\":\"left\",\"clickCount\":1}" > /dev/null 2>&1
}

eval_js() {
  if [ -n "$2" ]; then echo "$2" > p.json; else
    python -c "import json; print(json.dumps({'expression': open('$1', encoding='utf-8').read(), 'returnByValue': True, 'awaitPromise': True}))" > p.json
  fi
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

ok=0; fail=0
for h in $handles; do
  obu navigate --tab-id $TAB --session-id "$SESSION" --url "https://x.com/$h" > /dev/null 2>&1
  ready=""
  for i in $(seq 1 10); do  # 等待上限 10s
    st=$(eval_js "" '{"expression":"JSON.stringify({p: location.pathname, r: document.readyState, uf: !!document.querySelector(\"[data-testid$=-unfollow]\")})","returnByValue":true}')
    if [[ "$st" == *"$h"* && "$st" == *'"uf":true'* && "$st" == *'"r":"complete"'* ]]; then ready="YES"; break; fi
    sleep 0.8
  done
  if [[ "$ready" != "YES" ]]; then
    echo "[$h] FAIL_TIMEOUT" >> "retry_${LOG}"
    fail=$((fail+1))
    continue
  fi
  bpos=$(eval_js btnpos.js)
  if [[ "$bpos" != \{* ]]; then
    echo "[$h] FAIL_NOBTN" >> "retry_${LOG}"
    fail=$((fail+1))
    continue
  fi
  bx=$(echo "$bpos" | python -c "import sys,json; print(json.load(sys.stdin)['x'])")
  by=$(echo "$bpos" | python -c "import sys,json; print(json.load(sys.stdin)['y'])")
  done_flag=""
  for attempt in 1 2; do  # 最多 2 次点击尝试
    click_at $bx $by
    coord=""
    for i in 1 2 3; do  # 确认菜单轮询 3s
      coord=$(eval_js coords.js)
      [[ "$coord" == \{* ]] && break
      sleep 1
    done
    if [[ "$coord" == \{* ]]; then
      cx=$(echo "$coord" | python -c "import sys,json; print(json.load(sys.stdin)['x'])")
      cy=$(echo "$coord" | python -c "import sys,json; print(json.load(sys.stdin)['y'])")
      click_at $cx $cy
      sleep 1.5
      done_flag="YES"
      break
    fi
  done
  vres=$(eval_js "" '{"expression":"JSON.stringify({uf: !!document.querySelector(\"[data-testid$=-unfollow]\")})","returnByValue":true}')
  if [[ "$vres" == *'"uf":false'* ]]; then
    echo "[$h] OK" >> "$LOG"
    ok=$((ok+1))
  else
    echo "[$h] FAIL $vres" >> "retry_${LOG}"
    fail=$((fail+1))
  fi
done
echo "=== DONE ok=$ok fail=$fail ===" | tee -a "$LOG"
echo "RETRY_LIST:" && cat "retry_${LOG}"
