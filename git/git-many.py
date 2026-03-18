#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///

import argparse
import datetime
import subprocess
import sys


SAFE_EXACT = {
    ("status",),
    ("fetch",),
    ("fetch", "origin"),
    ("branch",),
    ("log",),
    ("diff",),
    ("show",),
    ("rev-parse",),
    ("remote",),
}

SAFE_PREFIX = {
    "log",
    "diff",
    "show",
    "rev-parse",
}


def run(repo, args):
    return subprocess.run(
        ["git", "-C", repo, *args],
        text=True,
        capture_output=True,
    )


def is_repo(path):
    r = run(path, ["rev-parse", "--is-inside-work-tree"])
    return r.returncode == 0 and r.stdout.strip() == "true"


def is_safe(cmd):
    t = tuple(cmd)
    return t in SAFE_EXACT or (cmd and cmd[0] in SAFE_PREFIX)

def is_clean(repo):
    r = run(repo, ["status", "--porcelain"])
    return r.returncode == 0 and not r.stdout.strip()

def main():
    p = argparse.ArgumentParser()
    p.add_argument("-t", "--transaction", action="store_true")
    p.add_argument("git_args", nargs=argparse.REMAINDER)
    ns = p.parse_args()

    git_args = ns.git_args[1:] if ns.git_args[:1] == ["--"] else ns.git_args
    if not git_args:
        p.error("usage: git-many [--transaction] -- <git args>")

    repos = [line.strip() for line in sys.stdin if line.strip()]
    if not repos:
        sys.exit("no repos on stdin")

    if ns.transaction:
        dirty = [r for r in repos if not is_clean(r)]
        if dirty:
            sys.exit(f"transaction requires clean repos: {', '.join(dirty)}")

    for repo in repos:
        if not is_repo(repo):
            sys.exit(f"not a git repo: {repo}")

    if not is_safe(git_args) and not ns.transaction:
        sys.exit("unsafe command requires --transaction")

    tag = f"git-many/{datetime.datetime.now(datetime.UTC).strftime('%Y%m%dT%H%M%SZ')}" if ns.transaction else None

    if tag:
        for repo in repos:
            r = run(repo, ["tag", tag])
            if r.returncode:
                sys.exit(f"failed to tag {repo}: {r.stderr.strip()}")

    done = []
    for repo in repos:
        print(f"==> {repo}", file=sys.stderr)
        r = run(repo, git_args)
        if r.stdout:
            print(r.stdout, end="")
        if r.stderr:
            print(r.stderr, end="", file=sys.stderr)
        if r.returncode:
            if tag:
                for rr in done + [repo]:
                    run(rr, ["reset", "--hard", tag])
                for rr in repos:
                    run(rr, ["tag", "-d", tag])
            sys.exit(r.returncode)
        done.append(repo)

    if tag:
        for repo in repos:
            run(repo, ["tag", "-d", tag])


if __name__ == "__main__":
    main()
