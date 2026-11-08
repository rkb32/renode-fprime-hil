#!/usr/bin/env bash
# Install the pinned Renode portable build. The sha256 is GitHub's asset digest for this file (from the release API).
set -euo pipefail
VER="1.16.0"
URL="https://github.com/renode/renode/releases/download/v${VER}/renode-${VER}.linux-portable.tar.gz"
SHA256="99e43ad40d07be7a81835b5b95897619997d32da9998634730c0aec5486736f6"
DEST="${RENODE_DIR:-$HOME/renode}"

TAR="$(mktemp)"
curl -fsSL -o "$TAR" "$URL"
echo "$SHA256  $TAR" | sha256sum -c -
rm -rf "$DEST"
mkdir -p "$DEST"
tar -xzf "$TAR" -C "$DEST" --strip-components=1
rm -f "$TAR"
test -x "$DEST/renode"
echo "renode: $DEST/renode"
