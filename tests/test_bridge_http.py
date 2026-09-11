import os
from pathlib import Path
import subprocess
import threading
import unittest
from flycraft.controller import Controller
from flycraft.server import make_server


class BridgeHTTPTest(unittest.TestCase):
    def test_node_python_closed_loop(self):
        server = make_server(Controller(), 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            result = subprocess.run(['node', 'bridge/smoke.mjs'], cwd=Path(__file__).resolve().parents[1],
                env={**os.environ, 'NEURAL_URL':f'http://127.0.0.1:{server.server_port}'},
                capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            print(result.stdout.strip())
        finally:
            server.shutdown(); server.server_close(); thread.join()
