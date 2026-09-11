from pathlib import Path
import unittest
from flycraft.controller import Controller

PROBE = Path(__file__).resolve().parents[1]/'fixtures/probe'


class RealProbeTests(unittest.TestCase):
    def test_real_edges_drive_bidirectional_actions_and_ablation(self):
        c = Controller(PROBE, PROBE/'mapping.json')
        self.assertEqual(c.model.n,6)
        self.assertEqual(c.model.w.nnz,6)
        for left,right,sign in [(1,0,-1),(0,1,1)]:
            c.reset()
            for _ in range(20):
                result = c.step(dict(drive=1,obstacle_left=left,obstacle_right=right))
            self.assertTrue(result['forward'])
            self.assertGreater(sign*result['yaw_rate'], 0)
        c.model.w.data.fill(0); c.reset()
        for _ in range(20):
            result = c.step(dict(drive=1,obstacle_left=1,obstacle_right=0))
        self.assertFalse(result['forward'])
        self.assertEqual(result['yaw_rate'],0)
