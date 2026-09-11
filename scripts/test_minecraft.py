"""Launch the real-connectome service and an isolated Minecraft network test."""
import os
from pathlib import Path
import subprocess
import sys
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from flycraft.controller import Controller
from flycraft.server import make_server

server = make_server(Controller(ROOT/'fixtures/probe', ROOT/'fixtures/probe/mapping.json'), 0)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
try:
    result = subprocess.run(['node','bridge/integration.mjs'],cwd=ROOT,
        env={**os.environ,'NEURAL_URL':f'http://127.0.0.1:{server.server_port}'}, timeout=35)
    sys.exit(result.returncode)
finally:
    server.shutdown(); server.server_close(); thread.join()
