"""Launch the real-connectome service and an isolated Minecraft network test."""
import os
from pathlib import Path
import subprocess
import sys
import threading
import argparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from flycraft.controller import Controller
from flycraft.server import make_server

parser=argparse.ArgumentParser()
parser.add_argument('--scenario',choices=['wall','step','drop','follow'],default='wall')
args=parser.parse_args()
server = make_server(Controller(ROOT/'fixtures/probe', ROOT/'fixtures/probe/mapping.json'), 0)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
try:
    result = subprocess.run(['node','bridge/integration.mjs'],cwd=ROOT,
        env={**os.environ,'NEURAL_URL':f'http://127.0.0.1:{server.server_port}','SCENARIO':args.scenario},
        capture_output=True,text=True,timeout=35)
    print(result.stdout, end='')
    print(result.stderr, end='', file=sys.stderr)
    # Flying Squid can exit(0) on an internal error. Require actual assertions too.
    passed = '"test":"minecraft-network-integration"' in result.stdout
    sys.exit(result.returncode if result.returncode else (0 if passed else 1))
finally:
    server.shutdown(); server.server_close(); thread.join()
