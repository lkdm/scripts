#!/usr/bin/env -S uv --quiet run --script
# /// script
# requires-python = ">=3.14"
# dependencies = [
#   "pygit2",
# ]
# ///

import argparse
from pathlib import Path

import pygit2


def list_repos(root_dir: Path) -> list[Path]:
    """Find repositories by locating .git directories."""
    return sorted(p.parent for p in root_dir.rglob(".git") if p.is_dir())


def repo_state(repo_path: Path) -> str:
	"""Check the status of the worktree"""
    repo = pygit2.Repository(repo_path / ".git")
    return "dirty" if repo.status() else "clean"


def app() -> None:
	"""Cli application"""
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, help="Path to root directory")
    args = parser.parse_args()

    root = args.root.expanduser().resolve()

    if not root.exists():
        parser.error(f"path does not exist: {root}")
    if not root.is_dir():
        parser.error(f"path is not a directory: {root}")

    repos = list_repos(root)

    if not repos:
        print("No git repositories found.")
        return

    for repo_path in repos:
        try:
            state = repo_state(repo_path)
            print(f"{state:5}  {repo_path}")
        except Exception as e:
            print(f"error  {repo_path} ({e})")


if __name__ == "__main__":
    app()
