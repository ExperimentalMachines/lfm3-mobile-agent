"""Additional regressions, prior CPU controls, and artifact-upload boundary checks."""
from common import *
import datetime
import gzip
import logging
import math
import pickle
import re
from jinja2 import Environment, nodes
from jinja2.ext import Extension

OUT = fresh("regressions")
RESULT = {"artifact_dir": str(OUT), "scope": "CPU local stubs and existing pinned-source references; no network"}

# Reuse the prior audit's exact Jinja/LoRA/resize and AW teardown reproductions.
# Only selected definitions are compiled; the old script's top-level writes/main never run.
ns = dict(globals(), HERE=ROOT / "results/codex/pass2")
sys.path.insert(0, str(ROOT / "results/codex"))
from reference_trl_multimodal import prepare_multimodal_messages
ns["prepare_multimodal_messages"] = prepare_multimodal_messages
execute_nodes("results/codex/pass2/reproduce.py", ns,
              names={"extract", "CaptureGeneration", "render", "template_checks", "lora_resize_schema", "parsers_aw"})
ns["template_checks"](); ns["lora_resize_schema"](); ns["parsers_aw"]()
assert RESULT["lora"]["jobs"]["qwen35_2b_l4"]["matched"] == 186
assert RESULT["lora"]["jobs"]["qwen35_08b_l4"]["matched"] == 186
assert RESULT["patched_teardown"]["is_successful"] == 1.0
assert RESULT["cleanup_error_status_empty_stdout"]["returned_normally"]

# The old reproduction includes a manually composed reasoning-fallback expression;
# it is NOT the current AW agent behavior. Remove it to prevent misleading evidence.
RESULT.pop("thinking_only_action_accepted", None)

# Check the legacy Qwen job's inherited EXTRA against the actual generator CLI.
g = dict(globals())
execute_nodes("results/codex/pass3/verify_generation.py", g, names={"generate"})
env = json.loads((ROOT / "scripts/jobs/qwen35_train_l4.json").read_text())[0]["env"]
import shlex
legacy = g["generate"](OUT / "legacy_extra", extra=tuple(shlex.split(env["EXTRA"])))
assert legacy["exit"] == 2 and "unrecognized arguments" in legacy["stdout"]
RESULT["legacy_qwen_generate_cli"] = legacy

# Execute the production upload loop with virtual file sizes, without allocating 500 MB.
shell = (ROOT / "scripts/vm_model_pipeline.sh").read_text()
body = shell.split("python - <<PY\n", 1)[1].split("\nPY", 1)[0]
body = body.replace("$FINAL_REPO", "synthetic/final").replace("$OUT", str(OUT / "training"))
files = {"/content/eval/current.metrics.json": 100, "/content/eval/current.jsonl": 500_000_000,
         "/content/eval/unrelated.jsonl": 499_999_999}
uploads = []
class Api:
    def create_repo(self, *a, **kw): pass
    def upload_file(self, **kw): uploads.append(kw)
    def upload_folder(self, **kw): uploads.append(kw)
import glob
with mock.patch.dict(sys.modules, {"huggingface_hub": module(HfApi=Api)}), \
     mock.patch.object(glob, "glob", lambda _: list(files)), \
     mock.patch.object(os.path, "isfile", lambda p: p in files), \
     mock.patch.object(os.path, "getsize", lambda p: files[p]), \
     mock.patch.object(os.path, "isdir", lambda _: False):
    exec(compile(body, "production push_evals heredoc", "exec"), {})
assert len(uploads) == 2 and not any(u["path_in_repo"] == "eval/current.jsonl" for u in uploads)
RESULT["upload_size_boundary"] = {"file_sizes": files, "uploads": uploads}

write_json(OUT / "results.json", RESULT)
print("RESULTS", OUT / "results.json")
