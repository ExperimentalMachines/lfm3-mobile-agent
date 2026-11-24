"""Probe parquet files -> datasets save_to_disk folders for generate.py, in two prompt formats:
  d/<probe>   D's format (24-step history + notes), plus C3n = C3 with " [no visible change]" on its last history line
  v4/<probe>  v4's format: the same rows with the last 8 history lines and no notes (= agent_format.history_text(…, 8))
Usage: python probes_to_disk.py <probe parquet dir> <out dir>"""
import glob, os, re, sys
from datasets import Dataset, Image, Sequence, load_dataset
src, out = sys.argv[1], sys.argv[2]
HB = re.compile(r"(\nPrevious steps:\n)(.*?)(\nWhat is the next action\?)$", re.S)
NOTE = " [no visible change]"


def edit(ds, fn):
    return ds.map(lambda r: {"messages": [dict(r["messages"][0]), {**r["messages"][1], "content": fn(r["messages"][1]["content"])}]
                             + [dict(x) for x in r["messages"][2:]]})


def block(u, f):
    m = HB.search(u)
    return u[:m.start(2)] + f(m.group(2)) + u[m.end(2):]


def note_last(b):
    lines = b.split("\n")
    if not lines[-1].endswith(NOTE):
        lines[-1] += NOTE
    return "\n".join(lines)


def v4fmt(b):
    lines = [l.removesuffix(NOTE) for l in b.split("\n")]
    return "\n".join(lines[-8:]) if lines != ["None"] else "None"


for f in sorted(glob.glob(os.path.join(src, "*.parquet"))):
    name = os.path.basename(f)[:-8]
    ds = load_dataset("parquet", data_files={"x": [f]}, split="x")
    ds = ds.cast_column("images", Sequence(Image()))  # pyarrow-written probes lose the Image type (processor needs PIL)
    ds.save_to_disk(os.path.join(out, "d", name))
    edit(ds, lambda u: block(u, v4fmt)).save_to_disk(os.path.join(out, "v4", name))
    if name == "C3_stale":
        edit(ds, lambda u: block(u, note_last)).save_to_disk(os.path.join(out, "d", "C3n_stale_note"))
print("ok", sorted(os.listdir(os.path.join(out, "d"))), sorted(os.listdir(os.path.join(out, "v4"))))
