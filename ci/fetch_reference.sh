#!/usr/bin/env bash
# Clone the reference at the pinned commit and apply the Renode-only patch.
# Usage: ci/fetch_reference.sh <dest-dir> [--submodules]
set -euo pipefail
REF_URL="https://github.com/fprime-community/fprime-stm32-baremetal-reference.git"
REF_COMMIT="89f1924eae2aef30b095d6db9b9613274813ca5a"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${1:?usage: ci/fetch_reference.sh <dest-dir> [--submodules]}"
SUBMODULES="${2:-}"

rm -rf "$DEST"
git init -q "$DEST"
git -C "$DEST" remote add origin "$REF_URL"
git -C "$DEST" fetch -q --depth 1 origin "$REF_COMMIT"
git -C "$DEST" checkout -q FETCH_HEAD
if [ "$SUBMODULES" = "--submodules" ]; then
  git -C "$DEST" submodule update --init --recursive --depth 1
fi
git -C "$DEST" apply "$ROOT/patches/renode-only.patch"
echo "reference $(git -C "$DEST" rev-parse HEAD) + renode-only patch"
