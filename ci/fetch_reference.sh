#!/usr/bin/env bash
# Clone the reference at the pinned commit and apply the Renode patch for the chosen build.
# Usage: ci/fetch_reference.sh <dest-dir> [--submodules] [--with-imu]
#   default:    renode-only.patch (UART polled, IMU removed)
#   --with-imu: uart-polled.patch only (IMU kept) + WHO_AM_I probe in fprime-sensors (implies --submodules)
set -euo pipefail
REF_URL="https://github.com/fprime-community/fprime-stm32-baremetal-reference.git"
REF_COMMIT="89f1924eae2aef30b095d6db9b9613274813ca5a"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${1:?usage: ci/fetch_reference.sh <dest-dir> [--submodules] [--with-imu]}"
SUBMODULES=0
WITH_IMU=0
for arg in "${@:2}"; do
  case "$arg" in
    --submodules) SUBMODULES=1 ;;
    --with-imu) WITH_IMU=1; SUBMODULES=1 ;;
    *) echo "unknown option: $arg" >&2; exit 2 ;;
  esac
done

rm -rf "$DEST"
git init -q "$DEST"
git -C "$DEST" remote add origin "$REF_URL"
git -C "$DEST" fetch -q --depth 1 origin "$REF_COMMIT"
git -C "$DEST" checkout -q FETCH_HEAD
if [ "$SUBMODULES" = 1 ]; then
  git -C "$DEST" submodule update --init --recursive --depth 1
fi
if [ "$WITH_IMU" = 1 ]; then
  git -C "$DEST" apply "$ROOT/patches/uart-polled.patch"
  git -C "$DEST/lib/fprime-sensors" apply --directory=fprime-sensors/MpuImu/Components/ImuManager \
    "$ROOT/projects/i2c-h7/imu-whoami-probe.patch"
  git -C "$DEST" apply -p1 "$ROOT/projects/i2c-h7/smoke-timeout.patch"
  echo "reference $(git -C "$DEST" rev-parse HEAD) + uart-polled patch + WHO_AM_I probe + 15 s smoke timeout (IMU kept)"
else
  git -C "$DEST" apply "$ROOT/patches/renode-only.patch"
  echo "reference $(git -C "$DEST" rev-parse HEAD) + renode-only patch"
fi
