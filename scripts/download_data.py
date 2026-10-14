"""Download and verify the official 9th DIMACS New York road-network files."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import shutil
import urllib.request
from pathlib import Path

BASE = "https://www.diag.uniroma1.it/challenge9/data/USA-road-d"
FILES = ("USA-road-d.NY.gr.gz", "USA-road-d.NY.co.gz")


def extract_gzip(archive: Path) -> Path:
    """Extract one gzip archive atomically and return the output path."""

    destination = archive.with_suffix("")
    needs_extraction = (
        not destination.exists()
        or destination.stat().st_size == 0
        or destination.stat().st_mtime < archive.stat().st_mtime
    )
    if needs_extraction:
        print(f"Extracting {archive.name} -> {destination.name} ...")
        temporary = destination.with_suffix(destination.suffix + ".part")
        with gzip.open(archive, "rb") as source, temporary.open("wb") as target:
            shutil.copyfileobj(source, target, length=1024 * 1024)
        temporary.replace(destination)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/raw")
    parser.add_argument("--no-extract", action="store_true", help="keep only the .gz archives")
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
        if not args.no_extract:
            extracted = extract_gzip(destination)
            print(f"{extracted.name}: {extracted.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()

