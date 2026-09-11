import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
import numpy as np
from scipy import sparse
from flycraft.model import LIF
from flycraft.controller import Controller
from flycraft.import_shiu import write_bundle
from flycraft.server import make_server


class NeuralTests(unittest.TestCase):
    def test_quiescence_and_seed(self):
        a, b = Controller(), Controller()
        obs = dict(drive=1, obstacle_left=1, obstacle_right=0)
        self.assertEqual(a.step(obs), b.step(obs))
        quiet = LIF(sparse.csr_matrix((2,2)))
        self.assertFalse(quiet.advance([], []).any())

    def test_causal_connection_ablation(self):
        a = Controller()
        obs = dict(drive=1, obstacle_left=1, obstacle_right=0)
        for _ in range(20): result = a.step(obs)
        self.assertTrue(result['forward'])
        self.assertLess(result['yaw_rate'], 0)
        a.model.w.data.fill(0); a.reset()
        for _ in range(20): result = a.step(obs)
        self.assertFalse(result['forward'])
        self.assertEqual(result['yaw_rate'], 0)

    def test_no_input_no_output(self):
        c = Controller()
        result = c.step(dict(drive=0, obstacle_left=0, obstacle_right=0))
        self.assertFalse(result['forward'])
        self.assertEqual(result['yaw_rate'], 0)

    def test_invalid_observation(self):
        for value in [float('nan'), float('inf'), -1, 2, True, '1']:
            with self.assertRaises(ValueError):
                Controller().step(dict(drive=value, obstacle_left=0, obstacle_right=0))

    def test_import_preserves_ids_sign_orientation_duplicates(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/'bundle'
            ids = ['720575940000000001','720575940000000003']
            w = write_bundle(path, ids, [0,0,1], [1,1,0], [2,3,-4], {'dataset_version':'test'})
            self.assertAlmostEqual(float(w[1,0]), 5*.275, places=5)
            self.assertAlmostEqual(float(w[0,1]), -4*.275, places=5)
            self.assertEqual(json.loads((path/'ids.json').read_text()), ids)
            with self.assertRaises(ValueError):
                write_bundle(path, ids, [0], [1], [1], {})


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.server = make_server(Controller(), 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join()

    def post(self, path, body):
        req = urllib.request.Request(self.base+path, data=json.dumps(body).encode(),
                                     headers={'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(req) as r: return r.status, json.load(r)
        except urllib.error.HTTPError as e:
            return e.code, json.load(e)

    def test_sessions_sequence_and_malformed_inputs(self):
        _, data = self.post('/session', {'protocol':1})
        body = dict(protocol=1, session=data['session'], seq=1,
                    observation=dict(drive=1, obstacle_left=0, obstacle_right=0))
        status, result = self.post('/step', body)
        self.assertEqual(status,200)
        self.assertEqual(result['seq'],1)
        self.assertEqual(self.post('/step',body)[0],400)
        self.post('/session', {'protocol':1})
        self.assertEqual(self.post('/step',{**body,'seq':2})[0],409)
        self.assertEqual(self.post('/step',[])[0],400)


if __name__ == '__main__':
    unittest.main()
