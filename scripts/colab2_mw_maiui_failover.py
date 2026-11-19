"""Run IN the second Colab session (colab exec -s mwgpu2 < this file): failover model servers for the MobileWorld
MAI-UI run (docs/PREREG_v4.md 2026-11-19 10:20). Reassembles the uploaded 50 MB parts (/content/q8p/p_*, /content/mmp/p_*),
checks both SHA-256s against the Mac's files, starts two MAI-UI-2B Q8_0 servers on :8093 and :8094 with exactly the
flags of the first session (scripts/colab_mw_maiui_q8.py; llama.cpp cd959bae9 built with the same CMake flags), and
starts a reverse-tunnel loop to the env VM for 18093/18094. While the first session is alive its tunnel holds those VM
ports, so this loop's ssh fails (ExitOnForwardFailure) and retries every 10 s; it binds as soon as the first session's
tunnel is gone (the VM's sshd drops a dead client after 120 s x 3). The MAI-UI watcher launches a half only when
check_maiui_server.py confirms model file, build and n_ctx through the tunnel. Idempotent: safe to re-run.
"""
import glob
import hashlib
import json
import os
import subprocess
import time
import urllib.request

VM_IP = "136.70.38.46"
FILES = {  # destination: (parts glob, sha256)
    "/content/models/MAI-UI-2B-Q8_0.gguf": ("/content/q8p/p_*", "5bc5ca6886c4b9ef1c76e9a911f1ac0b1ce807d12c1127c8c106c01fae363eaa"),
    "/content/models/mmproj-MAI-UI-2B-Q8_0.gguf": ("/content/mmp/p_*", "abeaacca571eeaf59ff193d3485025d0e532cd9c04501ef6779a685182fe561e"),
}
os.chdir("/content")
os.makedirs("models", exist_ok=True)
assert open("/content/build_rc.txt").read().strip() == "BUILD_RC=0", "llama.cpp build not finished/failed"
for dst, (pat, sha) in FILES.items():
    if not os.path.exists(dst):
        parts = sorted(glob.glob(pat))
        with open(dst + ".tmp", "wb") as out:
            for p in parts:
                out.write(open(p, "rb").read())
        os.rename(dst + ".tmp", dst)
    h = hashlib.sha256()
    with open(dst, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""):
            h.update(b)
    assert h.hexdigest() == sha, ("SHA-256 mismatch", dst, h.hexdigest())
    print("OK", dst, os.path.getsize(dst))

FLAGS = ["-m", "models/MAI-UI-2B-Q8_0.gguf", "--mmproj", "models/mmproj-MAI-UI-2B-Q8_0.gguf", "-c", "20480", "-np", "1",
         "-ngl", "99", "--image-max-tokens", "2600", "--jinja", "--cache-ram", "0", "--host", "127.0.0.1"]
running = subprocess.run("pgrep -fa '[l]lama-server'", shell=True, capture_output=True, text=True).stdout
for port in (8093, 8094):
    if f"--port {port}" not in running:
        subprocess.Popen(["llama.cpp/build/bin/llama-server", *FLAGS, "--port", str(port)],
                         stdout=open(f"/content/maiui_q8_{port}.log", "w"), stderr=subprocess.STDOUT, start_new_session=True)
for port in (8093, 8094):
    for _ in range(120):
        try:
            props = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/props", timeout=5).read())
            if props.get("model_path", "").endswith("MAI-UI-2B-Q8_0.gguf") and props.get("build_info", "").endswith("cd959bae9"):
                print(port, "up:", props["model_path"], props["build_info"], props.get("default_generation_settings", {}).get("n_ctx"))
                break
        except Exception:
            pass
        time.sleep(3)
    else:
        print(port, "NOT up"); print(open(f"/content/maiui_q8_{port}.log").read()[-1500:])

if not subprocess.run("pgrep -f '[t]unnel2_loop'", shell=True).returncode == 0:
    loop = ("cd /content; chmod 600 tunnel_key; while true; do : tunnel2_loop; ssh -o StrictHostKeyChecking=accept-new "
            "-o IdentitiesOnly=yes -o BatchMode=yes -o ControlPath=none -o ServerAliveInterval=15 -o ServerAliveCountMax=4 "
            f"-o ExitOnForwardFailure=yes -i tunnel_key -N -R 18093:127.0.0.1:8093 -R 18094:127.0.0.1:8094 ubuntu@{VM_IP}; "
            "echo \"[$(date +%T)] tunnel ended (rc $?); retrying\"; sleep 10; done")
    subprocess.Popen(["nohup", "bash", "-c", loop], stdout=open("/content/tunnel2.log", "a"), stderr=subprocess.STDOUT,
                     start_new_session=True)
    print("tunnel loop started (binds 18093/18094 once the first session's tunnel is gone)")
time.sleep(12)
print(subprocess.run("tail -3 /content/tunnel2.log; nvidia-smi --query-gpu=memory.used,memory.total --format=csv",
                     shell=True, capture_output=True, text=True).stdout)
