#!/usr/bin/env python3
"""
Download the DABstep context files and task lists from the Hugging Face dataset
`adyen/DABstep` (CC BY 4.0) into data/context and data/tasks.
"""

import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = "https://huggingface.co/datasets/adyen/DABstep/resolve/main/"
FILES = [
    "data/context/acquirer_countries.csv",
    "data/context/fees.json",
    "data/context/manual.md",
    "data/context/merchant_category_codes.csv",
    "data/context/merchant_data.json",
    "data/context/payments-readme.md",
    "data/context/payments.csv",
    "data/tasks/all.jsonl",
    "data/tasks/dev.jsonl",
]


def main() -> None:
    for rel in FILES:
        dst = ROOT / rel
        if dst.exists():
            print(f"exists   {rel}")
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(BASE + rel, headers={"User-Agent": "dabstep-fetch"})
        with urllib.request.urlopen(req) as r:
            dst.write_bytes(r.read())
        print(f"fetched  {rel} ({dst.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
