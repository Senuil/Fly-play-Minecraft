"""Loopback-only, single-controller HTTP server; bounded inputs and session IDs."""
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import time
import uuid
from .controller import Controller


def make_server(controller, port=8765):
    state = {"session": None, "seq": -1, "last": 0.}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def reply(self, status, payload):
            data = json.dumps(payload, allow_nan=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def do_GET(self):
            if self.path != "/health":
                return self.reply(404, {"error": "not found"})
            self.reply(200, {"mode": controller.mode, "neurons": controller.model.n,
                             "edges": controller.model.w.nnz, "protocol": 1})

        def do_POST(self):
            try:
                self.connection.settimeout(2)
                if self.headers.get("Content-Type") != "application/json":
                    raise ValueError("application/json required")
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 4096:
                    raise ValueError("body size must be 1..4096 bytes")
                payload = json.loads(self.rfile.read(size))
                if not isinstance(payload, dict) or payload.get("protocol") != 1:
                    raise ValueError("protocol must equal 1")
                if self.path == "/session":
                    controller.reset()
                    state.update(session=uuid.uuid4().hex, seq=-1, last=time.monotonic())
                    return self.reply(200, {"session": state["session"], "protocol": 1})
                if self.path != "/step":
                    return self.reply(404, {"error": "not found"})
                if state["session"] is None or payload.get("session") != state["session"]:
                    return self.reply(409, {"error": "start a new session"})
                seq = payload.get("seq")
                if type(seq) is not int or seq <= state["seq"]:
                    raise ValueError("seq must increase monotonically")
                if time.monotonic()-state["last"] > 2:
                    controller.reset()
                started = time.perf_counter()
                action = controller.step(payload["observation"])
                state.update(seq=seq, last=time.monotonic())
                self.reply(200, {**action, "protocol": 1, "session": state["session"], "seq": seq,
                                 "compute_ms": (time.perf_counter()-started)*1000})
            except (ValueError, KeyError, TypeError, TimeoutError) as exc:
                self.reply(400, {"error": str(exc)})

    return HTTPServer(("127.0.0.1", port), Handler)


def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--demo", action="store_true")
    mode.add_argument("--bundle")
    parser.add_argument("--mapping")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if args.bundle and not args.mapping:
        parser.error("--bundle requires --mapping")
    controller = Controller(args.bundle, args.mapping)
    server = make_server(controller, args.port)
    print(f"{controller.mode}: {controller.model.n} neurons; http://127.0.0.1:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
