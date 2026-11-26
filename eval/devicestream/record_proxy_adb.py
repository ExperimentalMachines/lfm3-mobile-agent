"""Recording proxy for a phone reached only through a REMOTE adb server (Qualcomm Device Cloud: `ssh -L <port>:<host>:5037`).

`adb forward` would open its listener on the remote adb server's host, not on this Mac, so each HTTP request is instead
carried through `adb shell` into curl on the phone (`curl http://127.0.0.1:8080...`, request body on stdin, response
on stdout). Same JSONL record as the (removed) direct-HTTP record_proxy.py (fsync per request): wall-clock latency (includes the tunnel), the
request summary and the full response JSON with llama.cpp's on-phone `timings` (the primary speed numbers).
Usage: python record_proxy_adb.py --listen 18301 --adb "adb -P 15037 -s SERIAL" --log out.jsonl --device D --model M
"""
import argparse
import json
import os
import re
import shlex
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import record_proxy_common as common

p = argparse.ArgumentParser()
p.add_argument("--listen", type=int, required=True)
p.add_argument("--adb", required=True)
p.add_argument("--phone_port", type=int, default=8080)
p.add_argument("--log", required=True)
p.add_argument("--device", required=True)
p.add_argument("--model", required=True)
a = p.parse_args()
ADB = shlex.split(a.adb)
LOCK = threading.Lock()


PATH_OK = re.compile(r"/(health|v1/[A-Za-z0-9/_.\-]+)")


def phone_http(method: str, path: str, body: bytes | None):
    """Run curl on the phone; returns (status, body bytes). The request path and method are interpolated into a
    phone-side shell command, so both are allowlisted and the URL is shell-quoted (security review)."""
    if method not in ("GET", "POST") or not PATH_OK.fullmatch(path):
        return 400, json.dumps({"proxy_error": "method/path not allowed"}).encode()
    url = shlex.quote(f"http://127.0.0.1:{int(a.phone_port)}{path}")
    cmd = f"curl -s -m 1800 -o - -w '\\n%{{http_code}}' -X {method} -H 'Content-Type: application/json' "
    cmd += ("--data-binary @- " if body else "") + url
    r = subprocess.run(ADB + ["shell", "-T", cmd], input=body or b"", capture_output=True, timeout=2000)
    out = r.stdout
    head, _, code = out.rpartition(b"\n")
    try:
        return int(code.strip() or b"0"), head
    except ValueError:
        return 502, out


class H(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _handle(self, method):
        n = int(self.headers.get("Content-Length") or 0)
        data = self.rfile.read(n) if n else None
        t0 = time.time()
        try:
            status, out = phone_http(method, self.path, data)
        except Exception as e:
            status, out = 502, json.dumps({"proxy_error": repr(e)}).encode()
        t1 = time.time()
        if self.path.startswith("/v1/chat/completions"):
            try:
                body = json.loads(data or b"{}")
            except Exception:
                body = {}
            try:
                resp = json.loads(out or b"{}")
            except Exception:
                resp = {"raw": out[:2000].decode(errors="replace")}
            common.write(a.log, LOCK, {"t_start": t0, "t_end": t1, "latency_s": round(t1 - t0, 3), "device": a.device,
                                       "model": a.model, "status": status, "transport": "adb-shell-curl",
                                       "request": common.summarize(body), "response": resp})
        self.send_response(status or 502)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def do_POST(self):
        self._handle("POST")

    def do_GET(self):
        self._handle("GET")


ThreadingHTTPServer(("127.0.0.1", a.listen), H).serve_forever()
