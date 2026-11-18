"""Shared pieces of the recording proxies: request summary (no image bytes; sha256 + size of each image) and fsync'ed
JSONL append."""
import base64
import hashlib
import io
import json
import os


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


def write(path: str, lock, rec: dict):
    line = json.dumps(rec) + "\n"
    with lock:
        with open(path, "a") as f:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())
