#!/bin/zsh
cd -- "${0:A:h}"
if [[ ! -x .venv/bin/python ]]; then
  echo '請先依 README.md 建立 .venv 並安裝 requirements.txt。'
  exit 1
fi
.venv/bin/python app.py --demo --port 5050 &
monitor_pid=$!
trap 'kill "$monitor_pid" 2>/dev/null' EXIT INT TERM
for attempt in {1..30}; do
  if ! kill -0 "$monitor_pid" 2>/dev/null; then
    echo '服務啟動失敗，請查看上方訊息。'
    exit 1
  fi
  if curl -fsS http://127.0.0.1:5050/api/latest >/dev/null 2>&1; then
    open 'http://127.0.0.1:5050'
    break
  fi
  sleep 0.3
done
wait "$monitor_pid"
