#!/usr/bin/env -S uv --quiet run --script
# /// script
# requires-python = ">=3.14"
# dependencies = [
# "typer",
# ]
# ///
import typer
from pathlib import Path
import subprocess

app = typer.Typer()


def run(*, cmd: list[str]) -> list[str]:
	"list files in a directory"
	result = subprocess.run(
		cmd,
		capture_output=True,
		text=True
	)
	
	if result.returncode == 0:
	    return [line for line in result.stdout.splitlines() if line.strip()]
	
	if result.returncode == 1:
		return []
		raise RuntimeError(
        f"command failed: {result.stderr.strip() or 'unknown error'}"
    )

# @app.command()
def list_repos(*, dir: str):
	"""
	Help for this command goes here
	"""
	repos = [r.parent for r in root_dir.rglob("*.git")]
	return repos

if __name__ == "__main__":
	root_dir = Path.home() / "Repos/bitbucket.org/invastglobal/"
	repos = list_repos(dir=root_dir)
	out = [run(
		cmd=["echo", repo]
	) for repo in repos]
	print(out)
