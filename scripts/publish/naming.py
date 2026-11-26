"""Single source of truth for model / dataset names (docs/naming.md is the readable view of this file).

Grammar
  model    <Base>-MobileAgent[-<Variant> | -Dev-<Recipe>][-<Format>]
  dataset  MobileAgent-<Kind>[-<Recipe>]

  Base     the upstream model name, unchanged (LFM3-VL-2B, Qwen3.5-2B, ...)
  none     the recommended model (the main model; its held-out comparison is the project's primary result)
  Variant  an evaluated alternative that is NOT a recommendation
  Dev      a development checkpoint, kept for reproducibility
  Recipe   CamelCase tag for what was ADDED to the training recipe of its parent (the parent is in `PARENT`)
  Format   GGUF | LiteRT (safetensors repos carry no format suffix)
  Kind     SFT | RL

The old labels (v1, v4.3-dpo2, v4.6-E, E-DPO, ...) exist only in the table below and in frozen records.
Run `python3 scripts/publish/naming.py --check` to validate the table; `--markdown` prints the docs table.
"""
import json
import re
import sys

ORG = "experimentalmachines"

# base repo name -> {old label: (new suffix after '-MobileAgent', tier, parent old label, what was added)}
LFM3 = "LFM3-VL-2B"
MODELS = {
    "v1": ("-Dev-AndroidControlOnly", "dev", None, "SFT on AndroidControl only (official train episodes)"),
    "v2": ("-Dev-MultiSource", "dev", "v1", "+ GUI-Odyssey, AMEX, ScreenQA (8,739 rows with a blank intent)"),
    "v3": ("-Dev-FilledIntents", "dev", "v2", "the blank intents filled (templates + a teacher model)"),
    "v4": ("", "main", "v3", "the FilledIntents data in the final prompt (answer-vs-complete rules, installed-app list) + navigate-then-answer episodes + shorter ScreenQA answers"),
    "v4-RL": ("-Dev-GRPO", "dev", "v4", "200 GRPO steps on static screenshots"),
    "v4.1": ("-Dev-WaitRelabel", "dev", "v4", "copied `wait` intents relabelled + recovery-history augmentation"),
    "v4.2": ("-Dev-OwnHistory", "dev", "v4.1", "+ the model's own replayed history on training episodes"),
    "v4.3-dpo": ("-Dev-DPOAllMistakes", "dev", "v4.2", "DPO on all 4,163 of its own mistakes"),
    "v4.3-dpo2": ("-Dev-DPOStopMistakes", "dev", "v4.2", "DPO on 851 balanced stop / copied-intent mistakes"),
    "v4.3-sft": ("-Dev-ContinuedSFT", "dev", "v4.2", "500 more SFT steps on the same mix"),
    "v4.4-A": ("-Dev-MemGUI", "dev", "v4", "+ MemGUI long, self-correcting trajectories"),
    "v4.4-B": ("-Dev-MemGUIChangeNotes", "dev", "v4.4-A", "+ \"[no visible change]\" notes in the history"),
    "v4.4-C": ("-Dev-MemGUIContinuedSFT", "dev", "v4", "500 more steps on 50% MemGUI / 50% main-model rows"),
    "v4.5-D": ("-Dev-FullMix", "dev", "v4", "one pass over all candidate sources, 24-step history, change notes"),
    "v4.6-E": ("-Counterfactual", "variant", "v4.5-D", "+ rows where history and screen disagree; judge-checked \"done\" labels"),
}
# weights each model was initialised from ('base' = the upstream model); `PARENT` in MODELS is the recipe it builds on
INIT = {"v1": "base", "v2": "base", "v3": "base", "v4": "base", "v4-RL": "v4", "v4.1": "base", "v4.2": "base",
        "v4.3-dpo": "v4.2", "v4.3-dpo2": "v4.2", "v4.3-sft": "v4.2", "v4.4-A": "base", "v4.4-B": "base", "v4.4-C": "v4",
        "v4.5-D": "base", "v4.6-E": "base"}
OTHER_BASES = {
    "Qwen3.5-2B": {"v1": "-Dev-AndroidControlOnly", "v2": "-Dev-MultiSource"},
    "Qwen3.5-0.8B": {"v1": "-Dev-AndroidControlOnly"},
    "LFM2.5-VL-450M": {"v1": "-Dev-AndroidControlOnly"},
}
# LFM3 repos that exist only as formats of a model above
FORMATS = {
    LFM3: {"GGUF": list(MODELS), "LiteRT": ["v4"]},   # every LFM3 model has a GGUF repo; only the main model has a LiteRT file
    "Qwen3.5-2B": {"GGUF": ["v1", "v2"]},
    "Qwen3.5-0.8B": {"GGUF": ["v1"]},
    "LFM2.5-VL-450M": {"GGUF": ["v1"]},
}
# intermediate training checkpoints, deleted after the final model's adapter was verified in its own repo
DELETE = ["LFM3-VL-2B-MobileAgent-v4.5-D-ckpt", "LFM3-VL-2B-MobileAgent-v4.6-E-ckpt"]

# old dataset name -> new dataset name
DATASETS = {
    "MobileAgent-SFT-v1": "MobileAgent-SFT-AndroidControl",
    "MobileAgent-SFT-v2": "MobileAgent-SFT-MultiSource",
    "MobileAgent-SFT-v3": "MobileAgent-SFT-FilledIntents",
    "MobileAgent-SFT-v4": "MobileAgent-SFT",
    "MobileAgent-RL-v4": "MobileAgent-RL",
    "MobileAgent-SFT-v4.4": "MobileAgent-SFT-MemGUI",
    "MobileAgent-SFT-v4.5": "MobileAgent-SFT-FullMix",
    "MobileAgent-SFT-v4.6": "MobileAgent-SFT-Counterfactual",
    "MobileAgent-SFT-v4.7": "MobileAgent-SFT-Counterfactual-WaitFix",
}

# Candidates that were never published (docs only): old label -> new display name
UNPUBLISHED = {
    "E-DPO": "Counterfactual+StopDPO",
    "E-T": "Counterfactual+Endings",
    "E-V": "Counterfactual+DoneCheck",
    "E-S": "Counterfactual+OwnHistoryRL (stopped)",
    "E-S2": "Counterfactual+OwnHistoryRL",
    "E-D": "Counterfactual+OwnHistorySFT",
    "F": "Counterfactual-WaitFix (never trained)",
}


def _old_model_name(base, label):
    # how the repo was named before this migration
    return f"{base}-MobileAgent-{label}"


def model_map():
    """old repo name -> new repo name for every model repo."""
    m = {}
    for label, (suffix, *_rest) in MODELS.items():
        m[_old_model_name(LFM3, label)] = f"{LFM3}-MobileAgent{suffix}"
    for base, d in OTHER_BASES.items():
        for label, suffix in d.items():
            m[_old_model_name(base, label)] = f"{base}-MobileAgent{suffix}"
    for base, fm in FORMATS.items():
        for fmt, labels in fm.items():
            for label in labels:
                old = _old_model_name(base, label) + f"-{fmt}"
                new_base = m[_old_model_name(base, label)]
                m[old] = f"{new_base}-{fmt}"
    return m


def file_renames(old_repo, new_repo, files):
    """in-repo file renames implied by a repo rename: {old path: new path}"""
    out = {}
    o_stem = old_repo.replace("-GGUF", "").replace("-LiteRT", "")
    n_stem = new_repo.replace("-GGUF", "").replace("-LiteRT", "")
    for f in files:
        if "/" in f:
            continue
        if f.startswith(o_stem + "-Q4_K_M") and f.endswith(".gguf"):
            out[f] = n_stem + f[len(o_stem):]
        elif f.startswith("mmproj-" + o_stem):
            out[f] = "mmproj-" + n_stem + f[len("mmproj-" + o_stem):]
        elif f.startswith(o_stem + "_") and f.endswith(".litertlm"):
            out[f] = n_stem + f[len(o_stem):]
    return out


def all_repo_renames():
    r = {f"{ORG}/{k}": f"{ORG}/{v}" for k, v in model_map().items()}
    return r


def check():
    mm = model_map()
    new = list(mm.values()) + list(DATASETS.values())
    assert len(new) == len(set(new)), "new names collide"
    for n in new:
        assert re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]*", n), n
    for label, (suffix, tier, parent, _) in MODELS.items():
        assert tier in ("main", "variant", "dev")
        assert (tier == "dev") == suffix.startswith("-Dev-"), label
        assert INIT[label] == "base" or INIT[label] in MODELS, label
        if parent:
            assert parent in MODELS, (label, parent)
    assert sum(1 for v in MODELS.values() if v[1] == "main") == 1
    assert not (set(mm) & set(DELETE)), "a deleted repo must not be mapped"
    print(f"ok: {len(mm)} model repos, {len(DATASETS)} datasets, {len(DELETE)} deleted")


def markdown():
    print("| Model | Old label | Tier | Initialised from | Recipe builds on | What was added |\n|---|---|---|---|---|---|")
    for label, (suffix, tier, parent, what) in MODELS.items():
        init = "base model" if INIT[label] == "base" else f"`{LFM3}-MobileAgent{MODELS[INIT[label]][0]}`"
        par = f"`{LFM3}-MobileAgent{MODELS[parent][0]}`" if parent else "-"
        print(f"| `{LFM3}-MobileAgent{suffix}` | {label} | {tier} | {init} | {par} | {what} |")


if __name__ == "__main__":
    if "--check" in sys.argv:
        check()
    elif "--markdown" in sys.argv:
        markdown()
    elif "--json" in sys.argv:
        print(json.dumps({"models": model_map(), "datasets": DATASETS, "unpublished": UNPUBLISHED, "deleted": DELETE}, indent=1))
    else:
        print(__doc__)
