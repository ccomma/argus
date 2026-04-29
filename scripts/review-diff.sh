#!/usr/bin/env bash
set -euo pipefail

git status --short
echo
git diff --stat
echo
git diff --check
echo
git diff
