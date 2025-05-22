#!/usr/bin/env bash
# Non-interactively rewrites a git commit message at some point in the past
#
# Source: https://peterevans.dev/posts/how-to-rewrite-git-commit-messages-non-interactively/

NEWLINE=$'\n'
commit_hash="$1"
new_commit_message="$2"

amend_message="amend! $commit_hash${NEWLINE}${NEWLINE}$new_commit_message"

git commit --allow-empty --only -m "$amend_message"
GIT_SEQUENCE_EDITOR=: git rebase -i --autosquash "$commit_hash^"
