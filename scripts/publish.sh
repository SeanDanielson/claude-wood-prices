#!/usr/bin/env bash
# publish.sh — push the current wood-shop/ folder to GitHub.
#
# Required files in the workspace root (siblings of this script's parent):
#   .gh-token   — GitHub Personal Access Token with `Contents: Read & Write`
#                 on the target repo (single line, no trailing newline)
#   .repo-url   — Repo path, e.g.  github.com/seandanielson/wood-shop
#                 (no protocol, no .git suffix)
#
# Usage:
#   bash scripts/publish.sh                   # auto commit message
#   bash scripts/publish.sh "your message"    # custom commit message
#
# Exit codes:
#   0  pushed (or no changes)
#   1  missing token / repo-url file (publish skipped)
#   2  git/network error during push
set -euo pipefail

WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOKEN_FILE="$WORKSPACE_DIR/.gh-token"
URL_FILE="$WORKSPACE_DIR/.repo-url"

if [[ ! -f "$TOKEN_FILE" || ! -f "$URL_FILE" ]]; then
  echo "[publish] Missing $TOKEN_FILE or $URL_FILE — skipping publish."
  exit 1
fi

TOKEN=$(tr -d '\n\r ' < "$TOKEN_FILE")
RAW_URL=$(tr -d '\n\r ' < "$URL_FILE")
# Strip any protocol the user pasted; we want host/path only.
REPO_PATH="${RAW_URL#https://}"
REPO_PATH="${REPO_PATH#http://}"
REPO_PATH="${REPO_PATH%.git}"

CLONE_DIR=$(mktemp -d -t wood-shop-publish-XXXXXX)
trap 'rm -rf "$CLONE_DIR"' EXIT

REMOTE_URL="https://x-access-token:${TOKEN}@${REPO_PATH}.git"
COMMIT_MSG="${1:-Refresh $(date -I)}"

echo "[publish] Cloning $REPO_PATH into $CLONE_DIR…"
if ! git clone --quiet --depth 1 "$REMOTE_URL" "$CLONE_DIR" 2>/dev/null; then
  echo "[publish] Clone failed (auth issue, network, or repo doesn't exist). Aborting." >&2
  exit 2
fi

cd "$CLONE_DIR"
git config user.email "sdanielson719@gmail.com"
git config user.name "Wood Shop Bot"

# A fresh empty GitHub repo has no commits and a local-default branch
# (typically 'master' or whatever 'init.defaultBranch' is set to). Force
# everything onto 'main' so push targets the right ref.
if [[ -z "$(git rev-list -n 1 --all 2>/dev/null)" ]]; then
  echo "[publish] Empty remote — initializing main branch."
  git checkout -B main --quiet
fi

echo "[publish] Mirroring workspace files into clone…"
rsync -a --delete \
  --filter='P /.git/' \
  --exclude=.git \
  --exclude='.gh-token*' \
  --exclude='.repo-url*' \
  --exclude=data/inputs \
  --exclude=data/processed \
  --exclude='__pycache__' \
  --exclude='zzz-*' \
  --exclude='*.lock' \
  --exclude='*.swp' \
  --exclude='*.swo' \
  --exclude='*~' \
  --exclude='.DS_Store' \
  "$WORKSPACE_DIR/" "$CLONE_DIR/"

# Sweep out any clone files that match the ignore list but were committed
# in earlier runs (e.g. sandbox artifacts before the ignore patterns existed).
shopt -s nullglob
for f in "$CLONE_DIR"/zzz-* "$CLONE_DIR"/*.lock; do
  [[ -e "$f" ]] && rm -f "$f"
done
shopt -u nullglob

git add -A
if git diff --cached --quiet 2>/dev/null && [[ $(git rev-list --count HEAD 2>/dev/null || echo 0) -gt 0 ]]; then
  echo "[publish] No changes to publish."
  exit 0
fi

echo "[publish] Committing: $COMMIT_MSG"
git commit --quiet -m "$COMMIT_MSG"

echo "[publish] Pushing…"
if ! git push --quiet origin main 2>&1; then
  echo "[publish] Push failed." >&2
  exit 2
fi

echo "[publish] Done."
