# DHT11 智慧環境舒適度監測

本專題使用 Vue 3、Flask、SQLite，提供溫濕度、舒適度燈號、提醒和歷史趨勢。
前端 Vue 已放在 static/vendor，可在無外網的區域網路使用。

## 這台 Mac 直接開啟

雙擊「啟動模擬.command」，或在終端機切換到本資料夾執行：

```sh
.venv/bin/python app.py --demo --port 5050
```

瀏覽器開啟 http://127.0.0.1:5050 。首次開啟若尚未啟動完成，重新整理即可。
關閉服務：在該終端機按 Control+C。

模擬模式清楚標示非實測資料，可切換舒適、高溫、潮濕、低溫、乾燥與斷線情境。
不會預先產生歷史數據，圖表從啟動後開始累積。模擬與實測各自使用獨立資料庫。

## 在 Raspberry Pi 上安裝

將整個 comfort_monitor 資料夾複製到 Pi，但不要複製 Mac 的 .venv 或 data 資料夾。
若從 GitHub clone 整個「嵌入式」專案，先進入監控程式資料夾：

```sh
cd comfort_monitor
```

接著執行安裝腳本（Python 3.9 以上）：

```sh
chmod +x setup_pi.sh
./setup_pi.sh
```

腳本只會建立專案內的 `.venv` 並安裝 Python 套件，不會設定 systemd 或修改 GPIO 權限。
也可以手動執行：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-pi.txt
.venv/bin/python app.py --host 0.0.0.0 --port 5000 --pin 4
```

感測器 DATA 預設 BCM GPIO4（實體 Pin 7）；3.3V 為 Pin 1，GND 為 Pin 6。
依實際模組確認供電、腳位與上拉電阻。若接其他腳位，用 --pin 修改 BCM 編號。
依 Pi OS 版本安裝所需的 libgpiod 系統套件，使用者須具備 GPIO 權限。
DHT11 在 Pi 5 的時序相容性必須實機驗證；失敗會顯示錯誤，絕不自動換成模擬資料。
同一 Wi-Fi 下手機開啟 http://<Pi的IP>:5000 。可用 hostname -I 查看 Pi 的 IP。
服務限受信任區域網路使用，沒有帳號登入功能；不要設定公網連接埠轉送。
這是 Flask 網站，請透過上述網址開啟，不要用 Live Server 或直接雙擊 templates/index.html。

## 行為與資料

- 採樣間隔 2.1 秒，避開 DHT 函式庫兩秒內的快取；網頁每 2 秒取最新狀態。
- /api/latest 回傳最近有效讀值、來源、感測器錯誤與舒適度。
- /api/history?hours=24 支援 1、6、24 小時；圖表採時間區間平均，最多約 720 點。
- /api/export?hours=24 匯出原始 CSV，時間為 UTC，包含資料來源欄位。
- SQLite 保留最近 7 天；歷史統計根據原始有效讀值，不以平均後圖表計算。
- 讀取失敗不插入舊資料，頁面標示上次有效值；超過 10 秒未更新視為過期。
- 濕度 >70% 連續達 30 分鐘觸發防霉提醒；讀取失敗或程序重啟會重新計時。
- 小數溫度以連續區間判斷：<15、15至<20、20至26、>26至30、>30。
- 濕度以 <40、40至60、>60至70、>70 判斷。
- 此系統只監測與提醒，不會控制電器。

## 開機自動執行

以專案內 comfort-monitor.service 為範本，修改 User、WorkingDirectory 和 ExecStart，
使其對應 Pi 上的使用者與專案絕對路徑。確認手動執行實測成功後：

```sh
sudo cp comfort-monitor.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now comfort-monitor
journalctl -u comfort-monitor -f
```

僅執行一個採樣服務，避免同時操作 GPIO。app.py 已用 Waitress 的單程序多執行緒服務。

## 推送 GitHub 前

專案的 `.gitignore` 已排除 `.venv/`、`data/`、`__pycache__/` 與 `*.pyc`。
請提交程式、網頁、requirements、README、測試與 service 範本；不要提交虛擬環境或 SQLite 實測資料。

## 驗證

```sh
.venv/bin/python -m unittest discover -s tests -v
```

## 參考文件

- Vue：https://vuejs.org/guide/quick-start.html
- Flask / Waitress：https://flask.palletsprojects.com/en/stable/deploying/waitress/
- DHT 驅動：https://docs.circuitpython.org/projects/dht/en/latest/
