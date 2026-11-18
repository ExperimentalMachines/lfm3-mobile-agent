"""Run ON the MobileWorld VM: exit 0 only if the llama-server behind localhost:<port> (Colab reverse tunnel) serves
MAI-UI-2B Q8_0 from llama.cpp cd959bae9 with a 20,480-token context. Usage: python3 check_maiui_server.py 18093"""
import json
import sys
import urllib.request

d = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{sys.argv[1]}/props", timeout=10).read())
ok = (str(d.get("model_path", "")).endswith("MAI-UI-2B-Q8_0.gguf") and str(d.get("build_info", "")).endswith("cd959bae9")
      and d.get("default_generation_settings", {}).get("n_ctx") == 20480)
print(sys.argv[1], d.get("model_path"), d.get("build_info"), d.get("default_generation_settings", {}).get("n_ctx"), "OK" if ok else "WRONG")
sys.exit(0 if ok else 1)
