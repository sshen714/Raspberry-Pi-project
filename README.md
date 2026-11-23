# 智慧環境舒適度監測系統

本專題使用 Raspberry Pi 5、DHT11、Flask、Vue 3 與 SQLite，提供即時溫濕度、舒適度判斷、生活提醒及歷史趨勢。

程式位於 `comfort_monitor/`。clone 後請先閱讀 [`comfort_monitor/README.md`](comfort_monitor/README.md)。

在 Raspberry Pi 上快速開始：

```sh
cd comfort_monitor
chmod +x setup_pi.sh
./setup_pi.sh
.venv/bin/python app.py --host 0.0.0.0 --port 5000 --pin 4
```

請勿將 `.venv/`、`data/` 或 SQLite 感測資料提交到 GitHub。
