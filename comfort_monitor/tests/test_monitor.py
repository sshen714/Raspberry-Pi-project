import sys
import tempfile
import time
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app
from comfort import evaluate


class Rules(unittest.TestCase):
    def test_boundaries(self):
        for t, label in [(14.9,'寒冷'),(15,'偏涼'),(19.5,'偏涼'),(20,'舒適'),(26,'舒適'),(26.1,'偏熱'),(30,'偏熱'),(30.1,'炎熱')]:
            self.assertEqual(evaluate(t,50)['temperature_label'],label)
        for h, label in [(39.9,'乾燥'),(40,'舒適'),(60,'舒適'),(60.1,'偏濕'),(70,'偏濕'),(70.1,'潮濕')]:
            self.assertEqual(evaluate(24,h)['humidity_label'],label)
        self.assertEqual(evaluate(24,50)['level'],'green')
        self.assertEqual(evaluate(27,50)['level'],'yellow')
        self.assertEqual(evaluate(27,35)['level'],'red')

    def test_mold_threshold(self):
        def mold(h,s):return any('防霉' in a['title'] for a in evaluate(24,h,s)['alerts'])
        self.assertFalse(mold(71,1799))
        self.assertTrue(mold(71,1800))
        self.assertFalse(mold(70,2000))


class Integration(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/'test.sqlite3'
        self.app=create_app(self.path,demo=True)
        self.client=self.app.test_client()
        self.m=self.app.extensions['monitor']

    def tearDown(self):
        self.m.close()
        self.tmp.cleanup()

    def test_empty_and_assets(self):
        self.assertEqual(self.client.get('/').status_code,200)
        self.assertTrue(self.client.get('/api/latest').json['stale'])
        self.assertEqual(self.client.get('/api/history').json['stats']['count'],0)
        self.assertEqual(self.client.get('/api/history?hours=invalid').status_code,400)
        self.assertEqual(self.client.get('/api/export?hours=999').status_code,400)
        for asset in ['app.js','style.css','vendor/vue.global.prod.js']:
            response=self.client.get('/static/'+asset)
            self.assertEqual(response.status_code,200)
            response.close()

    def test_failures_do_not_duplicate_and_restart_resets(self):
        self.m.sample()
        first=self.client.get('/api/latest').json
        self.assertFalse(first['stale'])
        self.m.sensor.scenario='offline'
        self.m.sample()
        failed=self.client.get('/api/latest').json
        self.assertTrue(failed['stale'])
        self.assertEqual(failed['reading'],first['reading'])
        self.assertEqual(self.client.get('/api/history').json['stats']['count'],1)
        app2=create_app(self.path,demo=True)
        self.assertTrue(app2.test_client().get('/api/latest').json['stale'])
        app2.extensions['monitor'].close()
        self.m.sensor.scenario='normal'
        self.m.sample()
        self.assertFalse(self.client.get('/api/latest').json['stale'])
        self.assertIn(b'simulation',self.client.get('/api/export').data)

    def test_continuity(self):
        self.m.sensor.scenario='humid'
        base=time.time()-1900
        for n in range(0,1801,2):self.m.sample(base+n,n)
        self.assertEqual(self.m.humid_seconds,1800)
        self.m.sensor.scenario='offline'
        self.m.sample(base+1802,1802)
        self.assertEqual(self.m.humid_seconds,0)
        self.m.sensor.scenario='humid'
        self.m.sample(base+1804,1804)
        self.assertEqual(self.m.humid_seconds,0)
        self.m.sample(base+1900,1900)
        self.assertEqual(self.m.humid_seconds,0)

    def test_scenario_validation_and_live_protection(self):
        self.assertEqual(self.client.post('/api/demo/scenario',json={'scenario':'hot'}).status_code,200)
        self.m.sample()
        self.assertEqual(self.client.get('/api/latest').json['comfort']['level'],'red')
        self.assertEqual(self.client.post('/api/demo/scenario',json={'scenario':'wrong'}).status_code,400)
        self.assertEqual(self.client.post('/api/demo/scenario',json=['hot']).status_code,400)
        self.assertEqual(self.client.post('/api/demo/scenario',json={'scenario':'hot'},headers={'Origin':'http://elsewhere'}).status_code,403)
        live=create_app(Path(self.tmp.name)/'live.sqlite3')
        self.assertEqual(live.test_client().post('/api/demo/scenario',json={'scenario':'hot'}).status_code,403)
        live.extensions['monitor'].close()


if __name__=='__main__':unittest.main()
