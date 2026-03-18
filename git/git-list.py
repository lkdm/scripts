#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///

import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", default=".")
    args = parser.parse_args()

    root = Path(args.path).expanduser().resolve()

    if not root.exists():
    	raise SystemExit(f"path does not exist: {root}")

    paths = sorted({p.parent for p in root.rglob(".git")})
    print("\n".join(str(p) for p in paths))


if __name__ == "__main__":
    main()
