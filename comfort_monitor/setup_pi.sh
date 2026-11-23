#!/bin/sh
set -eu

cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
    echo "找不到 python3，請先安裝 Python 3。" >&2
    exit 1
fi

python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements-pi.txt

cat <<'EOF'

Python 套件安裝完成。

接線確認：
  DHT11 VCC  -> 3.3V (Pin 1)
  DHT11 GND  -> GND  (Pin 6)
  DHT11 DATA -> GPIO4 (Pin 7)

啟動實測：
  .venv/bin/python app.py --host 0.0.0.0 --port 5000 --pin 4

同一 Wi-Fi 下，以手機開啟 http://<樹莓派IP>:5000
EOF
