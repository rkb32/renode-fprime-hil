# renode-fprime-hil

Runs the F´ reference deployment for STM32H7 (`fprime-community/fprime-stm32-baremetal-reference`, pinned at `89f1924`) on an emulated board in Renode, with no hardware. The unmodified smoke tests run against the emulated board.

## Status

- **Smoke job (no hardware):** passes locally, 2 of 2 unmodified tests.
- **IMU (MPU-6050):** in the IMU-kept CI build (`build-elf-imu`, `renode-smoke-imu`); the IMU-removed build is still the default. The STM32H7 I2C model and MPU-6050 model are merged to `main`; see [projects/i2c-h7/README.md](projects/i2c-h7/README.md). Not validated against silicon.
- **BMP280 on SPI5:** Python stand-in only. Renode has no SPI5 controller model.

See `BLOCKER.md` for the details and what is unverified.

## Layout

- `ci/` build and test scripts. `build_elf.sh` builds the ELF; `run_hil.sh` runs the tests.
- `patches/renode-only.patch` changes the reference: IMU removed, UART TX polled.
- `platform/` Renode platform, boot script template, and the BMP280 and MPU-6050 models.
- `bridge/bridge_multi.py` exposes the emulated UART to fprime-gds over TCP.
- `.github/workflows/hil-smoke.yml` builds the ELF and runs the smoke tests on ubuntu-latest.

## Run locally

Needs WSL or Linux with Python 3.12, the Arm GNU toolchain 12.2.MPACBTI-Rel1, and Renode 1.16.0. The toolchain is installed in `$HOME/arm-gnu-toolchain-12.2.mpacbti-rel1-x86_64-arm-none-eabi`; `ci/build_elf.sh` downloads it there if it's missing.

```bash
bash ci/build_elf.sh          # writes out/ReferenceDeployment.elf
bash ci/install_renode.sh     # installs Renode to $HOME/renode
RENODE="$HOME/renode/renode" ELF=out/ReferenceDeployment.elf \
  DICT=out/ReferenceDeploymentTopologyDictionary.json \
  REF_DIR=build-ci/reference VENV=build-ci/venv bash ci/run_hil.sh
```
