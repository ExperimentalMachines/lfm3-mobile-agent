"""Upload the model / dataset cards in scripts/publish/cards/ as README.md of the matching Hugging Face repos.

  python scripts/publish/publish_cards.py            # dry run: list what would be uploaded
  python scripts/publish/publish_cards.py --apply    # upload (needs HF_TOKEN or a logged-in `hf auth`)
  python scripts/publish/publish_cards.py --check    # compare every card with the live README (exit 1 on a difference)

Card file names are the repo names (see docs/naming.md). Only README.md is touched: the LICENSE.md files that some dataset
repos carry are left as they are.
"""
import argparse
import os
import sys

from huggingface_hub import HfApi, hf_hub_download

ORG = "experimentalmachines"
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cards")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def cards():
    for kind, sub in (("model", "models"), ("dataset", "datasets")):
        d = os.path.join(HERE, sub)
        for f in sorted(os.listdir(d)):
            if f.endswith(".md"):
                yield kind, f[:-3], os.path.join(d, f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    api = HfApi()
    diff = 0
    for kind, name, path in cards():
        rid = f"{ORG}/{name}"
        text = open(path).read()
        if a.check:
            live = open(hf_hub_download(rid, "README.md", repo_type=kind)).read()
            if live != text:
                diff += 1
                print("DIFFERS", rid)
        elif a.apply:
            api.upload_file(path_or_fileobj=text.encode(), path_in_repo="README.md", repo_id=rid, repo_type=kind,
                            commit_message="Update card (scripts/publish/cards)")
            print("uploaded", rid)
        else:
            print("would upload", rid)
    sys.exit(1 if diff else 0)


if __name__ == "__main__":
    main()
