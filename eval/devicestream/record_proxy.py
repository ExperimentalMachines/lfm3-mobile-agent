"""Recording HTTP proxy for the device-streaming speed benchmark.

Sits between an agent (OpenAI-compatible client) and a llama-server running ON a phone (reached through
`adb forward`). Every request is forwarded unchanged; for each one a JSON line is appended and fsync'ed to --log
before the response is returned, so nothing is lost if the phone session ends:
  t_start/t_end (Mac wall clock), device, model, request summary (message roles, text lengths, sha256 + size of every
  image, sampling params), HTTP status, and the full response JSON (content, usage, llama.cpp `timings`:
  prompt_n/prompt_ms/predicted_n/predicted_ms/cache_n).
Usage: python record_proxy.py --listen 18301 --upstream http://127.0.0.1:18201 --log out.jsonl --device D --model M
"""
import argparse
import base64
import hashlib
import io
import json
import os
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

p = argparse.ArgumentParser()
p.add_argument("--listen", type=int, required=True)
p.add_argument("--upstream", required=True)
p.add_argument("--log", required=True)
p.add_argument("--device", required=True)
p.add_argument("--model", required=True)
a = p.parse_args()
LOCK = threading.Lock()


def summarize(body: dict) -> dict:
    msgs = []
    for m in body.get("messages", []):
        parts = m["content"] if isinstance(m.get("content"), list) else [{"type": "text", "text": m.get("content") or ""}]
        for c in parts:
            if c.get("type") == "image_url":
                url = c["image_url"]["url"]
                raw = base64.b64decode(url.split(",", 1)[1]) if url.startswith("data:") else url.encode()
                try:
                    from PIL import Image
                    w, h = Image.open(io.BytesIO(raw)).size
                except Exception:
                    w = h = None
                msgs.append({"role": m["role"], "image_sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw), "w": w, "h": h})
            else:
                t = c.get("text") or ""
                msgs.append({"role": m["role"], "text_len": len(t), "text_sha256": hashlib.sha256(t.encode()).hexdigest()[:16]})
    return {"messages": msgs, **{k: v for k, v in body.items() if k != "messages"}}


def write(rec: dict):
    line = json.dumps(rec) + "\n"
    with LOCK:
        with open(a.log, "a") as f:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())


class H(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _forward(self, method):
        n = int(self.headers.get("Content-Length") or 0)
        data = self.rfile.read(n) if n else None
        t0 = time.time()
        req = urllib.request.Request(a.upstream + self.path, data=data, method=method,
                                     headers={"Content-Type": self.headers.get("Content-Type", "application/json")})
        status, out = 502, b""
        try:
            with urllib.request.urlopen(req, timeout=1800) as r:
                status, out = r.status, r.read()
        except urllib.error.HTTPError as e:
            status, out = e.code, e.read()
        except Exception as e:
            out = json.dumps({"proxy_error": repr(e)}).encode()
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
            write({"t_start": t0, "t_end": t1, "latency_s": round(t1 - t0, 3), "device": a.device, "model": a.model,
                   "status": status, "request": summarize(body), "response": resp})
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def do_POST(self):
        self._forward("POST")

    def do_GET(self):
        self._forward("GET")


ThreadingHTTPServer(("127.0.0.1", a.listen), H).serve_forever()
