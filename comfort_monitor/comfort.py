"""報告中的舒適度規則。小數區間連續，避免 19.5°C 等數值無法分類。"""
import math


def evaluate(temperature, humidity, humid_seconds=0):
    if not all(math.isfinite(x) for x in (temperature, humidity)) or not 0 <= humidity <= 100:
        raise ValueError('感測值無效')
    t = temperature
    h = humidity
    temp_label = '寒冷' if t < 15 else '偏涼' if t < 20 else '舒適' if t <= 26 else '偏熱' if t <= 30 else '炎熱'
    humidity_label = '乾燥' if h < 40 else '舒適' if h <= 60 else '偏濕' if h <= 70 else '潮濕'
    level = 'red' if t < 15 or t > 30 or h < 40 or h > 70 else 'green' if 20 <= t <= 26 and 40 <= h <= 60 else 'yellow'
    clothing = '厚外套，注意保暖' if t < 15 else '長袖加薄外套' if t < 20 else '短袖或薄長袖' if t <= 26 else '輕薄、透氣的衣物'
    alerts = []
    if t > 30:
        alerts.append({'title': '高溫提醒', 'message': '補充水分，可開啟風扇或冷氣。', 'level': 'red'})
    if t < 15:
        alerts.append({'title': '低溫提醒', 'message': '注意保暖，長輩與小孩特別留意。', 'level': 'red'})
    if h > 60:
        alerts.append({'title': '除濕建議', 'message': '可開啟除濕機或冷氣的除濕模式。', 'level': 'yellow'})
    if h < 40:
        alerts.append({'title': '環境偏乾', 'message': '適時補充水分，注意皮膚保濕。', 'level': 'red'})
    if h > 70 and humid_seconds >= 1800:
        alerts.append({'title': '持續潮濕・防霉提醒', 'message': '濕度高於 70% 已持續 30 分鐘，注意衣櫃、牆角並保持通風。', 'level': 'red'})
    return {'level': level, 'label': {'green': '環境舒適', 'yellow': '留意環境', 'red': '需要調整'}[level],
            'temperature_label': temp_label, 'humidity_label': humidity_label, 'clothing': clothing,
            'alerts': alerts, 'humid_minutes': round(humid_seconds / 60, 1)}
