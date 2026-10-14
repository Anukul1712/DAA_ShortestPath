"""Download and verify the official 9th DIMACS New York road-network files."""

from __future__ import annotations

import argparse
import hashlib
import urllib.request
from pathlib import Path

BASE = "https://www.diag.uniroma1.it/challenge9/data/USA-road-d"
FILES = ("USA-road-d.NY.gr.gz", "USA-road-d.NY.co.gz")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/raw")
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        destination = output / name
        if not destination.exists() or destination.stat().st_size == 0:
            print(f"Downloading {name} ...")
            temporary = destination.with_suffix(destination.suffix + ".part")
            urllib.request.urlretrieve(f"{BASE}/{name}", temporary)
            temporary.replace(destination)
        digest = hashlib.sha256(destination.read_bytes()).hexdigest()
        print(f"{name}: {destination.stat().st_size:,} bytes, sha256={digest}")


if __name__ == "__main__":
    main()

