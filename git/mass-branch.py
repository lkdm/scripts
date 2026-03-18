#!/usr/bin/env -S uv --quiet run --script
# /// script
# requires-python = ">=3.14"
# dependencies = [
# "typer",
# ]
# ///
import os
import typer
from pathlib import Path
import subprocess
from dataclasses import dataclass


app = typer.Typer()


@dataclass
class Step:
    name: str
    cmd: list[str]
    parallel: bool = False

def get_root_dir() -> Path:
    root_dir = Path(os.environ["MANYREPO_ROOT"]).expanduser()
    if not root_dir.is_dir():
        raise typer.BadParameter(f"Invalid MANYREPO_ROOT: {root_dir}")
    return root_dir

def list_repos(root_dir: Path) -> list[Path]:
    """Find repositories by locating .git directories."""
    return sorted(p.parent for p in root_dir.rglob(".git") if p.is_dir())


def run_step(step: Step, repos: list[Path]) -> None:
    typer.echo(f"\n### {step.name}")

    if step.parallel:
        procs = [
            (
                repo,
                subprocess.Popen(
                    step.cmd,
                    cwd=repo,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                ),
            )
            for repo in repos
        ]

        results = [
            (repo, *proc.communicate(), proc.returncode)
            for repo, proc in procs
        ]
    else:
        results = []
        for repo in repos:
            r = subprocess.run(step.cmd, cwd=repo, capture_output=True, text=True)
            results.append((repo, r.stdout, r.stderr, r.returncode))

    failures = []

    for repo, stdout, stderr, code in results:
        out = [line for line in stdout.splitlines() if line.strip()]

        if code != 0:
            failures.append((repo, stderr.strip() or stdout.strip() or "unknown error"))
            continue

        if out:
            typer.echo(f"\n==> {repo}")
            typer.echo("\n".join(out))

    if failures:
        for repo, msg in failures:
            typer.echo(f"{repo}: {msg}", err=True)
        raise typer.Exit(code=1)


def run_steps(steps: list[Step]) -> None:
    repos = list_repos(get_root_dir())
    if not repos:
        typer.echo("No repos found")
        raise typer.Exit(code=1)

    for step in steps:
        run_step(step, repos)


@app.command()
def fetch() -> None:
    run_steps([
        Step("fetch", ["git", "fetch", "origin", "main"]),
    ])


@app.command()
def status() -> None:
    run_steps([
        Step("status", ["git", "status", "--porcelain"], parallel=True),
    ])


@app.command()
def add() -> None:
    run_steps([
        Step("add", ["git", "add", "."]),
    ])

if __name__ == "__main__":
	app()
