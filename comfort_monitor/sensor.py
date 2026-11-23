"""DHT11 實測與明確標示的模擬來源，不會自動切換成假資料。"""
import math
import time

SCENARIOS = {'normal': (24, 53), 'hot': (32, 65), 'humid': (25, 78), 'cold': (13, 55), 'dry': (24, 32)}


class DemoSensor:
    def __init__(self):
        self.scenario = 'normal'

    def read(self):
        if self.scenario == 'offline':
            raise RuntimeError('模擬感測器讀取失敗')
        t, h = SCENARIOS[self.scenario]
        return round(t + .6 * math.sin(time.monotonic() / 30), 1), round(h + 1.5 * math.sin(time.monotonic() / 37), 1)

    def close(self):
        pass


class DHT11Sensor:
    def __init__(self, pin=4):
        self.pin = pin
        self.device = None

    def read(self):
        if self.device is None:
            import board
            import adafruit_dht
            self.device = adafruit_dht.DHT11(getattr(board, 'D' + str(self.pin)), use_pulseio=False)
        t, h = self.device.temperature, self.device.humidity
        if t is None or h is None or not math.isfinite(t) or not math.isfinite(h) or not 0 <= h <= 100:
            raise RuntimeError('DHT11 回傳無效數值')
        return float(t), float(h)

    def close(self):
        if self.device is not None:
            self.device.exit()
