#!/usr/bin/env bash
# CI build job: pinned reference + Renode patch -> ReferenceDeployment ELF and dictionary in $OUT.
# Usage: ci/build_elf.sh [--with-imu]   (default: IMU removed via renode-only.patch; --with-imu keeps the IMU)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${OUT:-$ROOT/out}"
WORK="${WORK:-$ROOT/build-ci}"
TC_NAME="arm-gnu-toolchain-12.2.mpacbti-rel1-x86_64-arm-none-eabi"
TC_URL="https://developer.arm.com/-/media/Files/downloads/gnu/12.2.mpacbti-rel1/binrel/${TC_NAME}.tar.xz"
# sha256 of the Arm 12.2 tarball. Matches Arm's published .sha256asc (developer.arm.com), checked 2026-11-08.
TC_SHA256="17455a06c816031cc2c66243c117cba48463cd6a3a3fdfac7275b4e9c40eb314"
TC_DIR="$HOME/$TC_NAME"

if [ ! -x "$TC_DIR/bin/arm-none-eabi-gcc" ]; then
  TAR="$(mktemp)"
  curl -fsSL -o "$TAR" "$TC_URL"
  echo "$TC_SHA256  $TAR" | sha256sum -c -
  tar -xJf "$TAR" -C "$HOME"
  rm -f "$TAR"
fi
export PATH="$TC_DIR/bin:$PATH"
# Cache hits skip the sha256 check, so also pin the compiler version (no download needed)
arm-none-eabi-gcc --version | head -n 1 | grep -q "12.2.1" || { echo "unexpected arm-none-eabi-gcc version"; arm-none-eabi-gcc --version | head -n 1; exit 1; }

"$ROOT/ci/fetch_reference.sh" "$WORK/reference" --submodules "$@"
python3 -m venv "$WORK/venv"
"$WORK/venv/bin/pip" install -q -r "$ROOT/ci/requirements.txt"
export PATH="$WORK/venv/bin:$PATH"

cd "$WORK/reference"
fprime-util generate stm32h7 -f
fprime-util build -j"$(nproc)"

mkdir -p "$OUT"
cp build-artifacts/stm32h7/ReferenceDeployment/bin/ReferenceDeployment "$OUT/ReferenceDeployment.elf"
cp build-artifacts/stm32h7/ReferenceDeployment/dict/ReferenceDeploymentTopologyDictionary.json "$OUT/"
echo "built: $OUT/ReferenceDeployment.elf"
