"""啟動：python app.py --demo；Pi 實測：python app.py --host 0.0.0.0。"""
import argparse
from contextlib import contextmanager
import csv
import io
import logging
import sqlite3
import threading
import time
from pathlib import Path

from flask import Flask, jsonify, render_template, request, Response
from comfort import evaluate
from sensor import DemoSensor, DHT11Sensor, SCENARIOS

BASE = Path(__file__).resolve().parent
INTERVAL = 2.1  # DHT 程式庫的兩秒快取窗以外才再次讀取


class Monitor:
    def __init__(self, db_path, demo=False, pin=4):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.demo, self.pin = demo, pin
        self.sensor = DemoSensor() if demo else DHT11Sensor(pin)
        self.lock = threading.RLock()
        self.stop_event = threading.Event()
        self.thread = None
        self.latest = None
        self.error = None
        self.last_attempt = None
        self.humid_since = None
        self.last_success_mono = None
        self.humid_seconds = 0
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS readings (ts REAL PRIMARY KEY, temperature REAL NOT NULL, humidity REAL NOT NULL)')
            row = db.execute('SELECT ts, temperature, humidity FROM readings ORDER BY ts DESC LIMIT 1').fetchone()
            if row:
                self.latest = dict(row)
                self.error = '等待本次啟動後的第一筆有效讀值'

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.db_path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def sample(self, now=None, mono=None):
        now = time.time() if now is None else now
        mono = time.monotonic() if mono is None else mono
        with self.lock:
            self.last_attempt = now
            try:
                t, h = self.sensor.read()
                evaluate(t, h)
                with self.connect() as db:
                    db.execute('INSERT INTO readings VALUES (?, ?, ?)', (now, t, h))
                    db.execute('DELETE FROM readings WHERE ts < ?', (now - 7 * 86400,))
                # 無資料間隔不能算進持續潮濕時間。
                if self.last_success_mono is None or mono - self.last_success_mono > 10:
                    self.humid_since = None
                if h > 70:
                    if self.humid_since is None:
                        self.humid_since = mono
                else:
                    self.humid_since = None
                self.humid_seconds = 0 if self.humid_since is None else mono - self.humid_since
                self.last_success_mono = mono
                self.latest = {'ts': now, 'temperature': t, 'humidity': h}
                self.error = None
            except Exception as exc:
                self.error = str(exc) or type(exc).__name__
                self.humid_since = None
                self.humid_seconds = 0
                logging.warning('讀取或儲存失敗: %s', self.error)

    def snapshot(self):
        with self.lock:
            age = None if self.latest is None else max(0, time.time() - self.latest['ts'])
            stale = age is None or age > 10 or self.error is not None
            return {'mode': 'demo' if self.demo else 'live', 'pin': self.pin,
                    'reading': self.latest, 'stale': stale, 'error': self.error,
                    'last_attempt': self.last_attempt, 'age_seconds': age,
                    'scenario': getattr(self.sensor, 'scenario', None),
                    'comfort': None if self.latest is None else evaluate(self.latest['temperature'], self.latest['humidity'], self.humid_seconds)}

    def start(self):
        def collect():
            while not self.stop_event.is_set():
                self.sample()
                self.stop_event.wait(INTERVAL)
        self.thread = threading.Thread(target=collect, daemon=True, name='dht-collector')
        self.thread.start()

    def close(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=5)
        self.sensor.close()


def create_app(db_path=None, demo=False, pin=4, start=False):
    app = Flask(__name__)
    app.config['MAX_CONTENT_LENGTH'] = 2048
    monitor = Monitor(db_path or BASE / 'data' / ('demo.sqlite3' if demo else 'dht11.sqlite3'), demo, pin)
    app.extensions['monitor'] = monitor

    @app.after_request
    def headers(response):
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response

    @app.get('/')
    def index():
        return render_template('index.html')

    @app.get('/api/latest')
    def latest():
        return jsonify(monitor.snapshot())

    def hours_arg():
        value = request.args.get('hours', '24')
        if value not in ('1', '6', '24'):
            return None
        return int(value)

    @app.get('/api/history')
    def history():
        hours = hours_arg()
        if hours is None:
            return jsonify(error='hours 必須為 1、6 或 24'), 400
        end = time.time()
        start_ts = end - hours * 3600
        bucket = max(5, hours * 5)
        with monitor.connect() as db:
            rows = db.execute('SELECT AVG(ts) ts, AVG(temperature) temperature, AVG(humidity) humidity FROM readings WHERE ts >= ? AND ts <= ? GROUP BY CAST(ts / ? AS INTEGER) ORDER BY ts', (start_ts, end, bucket)).fetchall()
            stats = dict(db.execute('SELECT COUNT(*) count, MIN(temperature) min_t, MAX(temperature) max_t, AVG(temperature) avg_t, AVG(humidity) avg_h FROM readings WHERE ts >= ? AND ts <= ?', (start_ts, end)).fetchone())
        return jsonify(points=[dict(row) for row in rows], stats=stats, start=start_ts, end=end, bucket_seconds=bucket, mode='demo' if demo else 'live')

    @app.get('/api/export')
    def export():
        hours = hours_arg()
        if hours is None:
            return jsonify(error='hours 必須為 1、6 或 24'), 400
        stream = io.StringIO()
        writer = csv.writer(stream)
        writer.writerow(['timestamp_utc', 'temperature_c', 'humidity_percent', 'source'])
        from datetime import datetime, timezone
        with monitor.connect() as db:
            for row in db.execute('SELECT * FROM readings WHERE ts >= ? ORDER BY ts', (time.time() - hours * 3600,)):
                writer.writerow([datetime.fromtimestamp(row['ts'], timezone.utc).isoformat(), row['temperature'], row['humidity'], 'simulation' if demo else 'DHT11'])
        return Response('\ufeff' + stream.getvalue(), mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename="comfort-history.csv"'})

    @app.post('/api/demo/scenario')
    def scenario():
        if not demo:
            return jsonify(error='實測模式不可切換模擬情境'), 403
        if not request.is_json:
            return jsonify(error='請使用 JSON'), 415
        origin = request.headers.get('Origin')
        if origin and origin != request.host_url.rstrip('/'):
            return jsonify(error='來源不符'), 403
        data = request.get_json(silent=True)
        key = data.get('scenario') if isinstance(data, dict) else None
        if key not in (*SCENARIOS, 'offline'):
            return jsonify(error='未知情境'), 400
        with monitor.lock:
            monitor.sensor.scenario = key
            monitor.humid_since = None
            monitor.humid_seconds = 0
        return jsonify(ok=True)

    if start:
        monitor.start()
    return app


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='DHT11 智慧環境舒適度監測')
    parser.add_argument('--demo', action='store_true', help='使用明確標示的模擬資料')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=5000)
    parser.add_argument('--pin', type=int, default=4, help='BCM GPIO 編號，預設 4')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    app = create_app(demo=args.demo, pin=args.pin, start=True)
    print(f'開啟 http://127.0.0.1:{args.port}  |  {"模擬模式" if args.demo else "DHT11 實測模式"}', flush=True)
    try:
        from waitress import serve
        serve(app, host=args.host, port=args.port, threads=4)
    finally:
        app.extensions['monitor'].close()
