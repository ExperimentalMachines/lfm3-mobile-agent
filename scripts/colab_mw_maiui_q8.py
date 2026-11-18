"""Run IN the Colab MobileWorld model session (colab exec -s mwgpu < this file). Prepares MAI-UI-2B Q8_0 for its
MobileWorld run: reassembles the uploaded 50 MB parts (/content/q8p/p_*), checks SHA-256 against the Mac's file, stops
the two servers that are no longer needed (MAI-UI Q4_K_M on :8093 and v4 on :8094, matched by their exact model file;
GUI-Owl on :8092 is left alone), and starts two identical MAI-UI Q8_0 servers on :8093 and :8094 with the flags of
MAI-UI's AndroidWorld arm (scripts/local_maiui_aw.sh) plus --cache-ram 0 as on the GUI-Owl MobileWorld server.
The existing reverse tunnel (tunnel_loop.sh) already forwards 18093 -> :8093 and 18094 -> :8094 on the env host.
Set DRY = True to only print what would be stopped.
"""
import glob
import hashlib
import json
import os
import signal
import subprocess
import time
import urllib.request

DRY = False
SHA = "5bc5ca6886c4b9ef1c76e9a911f1ac0b1ce807d12c1127c8c106c01fae363eaa"
DST = "/content/models/MAI-UI-2B-Q8_0.gguf"
os.chdir("/content")
if not os.path.exists(DST):
    parts = sorted(glob.glob("/content/q8p/p_*"))
    print(len(parts), "parts")
    with open(DST + ".tmp", "wb") as out:
        for p in parts:
            out.write(open(p, "rb").read())
    os.rename(DST + ".tmp", DST)
h = hashlib.sha256()
with open(DST, "rb") as f:
    for b in iter(lambda: f.read(1 << 24), b""):
        h.update(b)
assert h.hexdigest() == SHA, ("SHA-256 mismatch", h.hexdigest())
MMPROJ, MMSHA = "/content/models/mmproj-MAI-UI-2B-Q8_0.gguf", "abeaacca571eeaf59ff193d3485025d0e532cd9c04501ef6779a685182fe561e"
assert hashlib.sha256(open(MMPROJ, "rb").read()).hexdigest() == MMSHA, "projector SHA-256 mismatch"
print("Q8_0 file and projector OK", os.path.getsize(DST))

STOP = ("models/MAI-UI-2B-Q4_K_M.gguf", "models/LFM3-VL-2B-AndroidAgent-v4-Q4_K_M.gguf")
victims = []
for p in glob.glob("/proc/[0-9]*/cmdline"):
    try:
        cmd = open(p, "rb").read().replace(b"\0", b" ").decode()
    except OSError:
        continue
    argv = cmd.split()
    model = next((argv[i + 1] for i, a in enumerate(argv[:-1]) if a in ("-m", "--model")), "")
    if argv and argv[0].endswith("llama-server") and any(os.path.normpath(os.path.join("/content", model)).endswith(m) for m in STOP):
        victims.append((int(p.split("/")[2]), cmd[:160]))
print("stop:", victims)
if DRY:
    raise SystemExit
for pid, _ in victims:
    os.kill(pid, signal.SIGTERM)
time.sleep(8)
FLAGS = ["-m", "models/MAI-UI-2B-Q8_0.gguf", "--mmproj", "models/mmproj-MAI-UI-2B-Q8_0.gguf", "-c", "20480", "-np", "1",
         "-ngl", "99", "--image-max-tokens", "2600", "--jinja", "--cache-ram", "0", "--host", "127.0.0.1"]
procs = {}
for port in (8093, 8094):
    procs[port] = subprocess.Popen(["llama.cpp/build/bin/llama-server", *FLAGS, "--port", str(port)],
                     stdout=open(f"/content/maiui_q8_{port}.log", "w"), stderr=subprocess.STDOUT, start_new_session=True)
for port in (8093, 8094):
    for _ in range(120):
        try:
            assert procs[port].poll() is None, f"server for {port} exited"
            props = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/props", timeout=5).read())
            if props.get("model_path", "").endswith("MAI-UI-2B-Q8_0.gguf") and props.get("build_info", "").endswith("cd959bae9"):
                print(port, "up: MAI-UI Q8_0", props["build_info"]); break
        except Exception:
            time.sleep(3)
    else:
        print(port, "NOT up"); print(open(f"/content/maiui_q8_{port}.log").read()[-1500:])
print(subprocess.run("nvidia-smi --query-gpu=memory.used,memory.total --format=csv", shell=True, capture_output=True, text=True).stdout)
