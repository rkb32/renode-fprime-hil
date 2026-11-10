# i2c-h7: STM32H7 I2C model and MPU-6050 WHO_AM_I probe

Renode model of the STM32H7 I2C master (`platform/STM32H7_I2C.cs`), the MPU-6050 DEVICE_RESET fix (`platform/MPU6050.cs`), and two patches for the reference tree. Status and open items: [PROJECT.md](PROJECT.md).

## Apply the patches to the reference tree

The patches are for the reference checkout (see `ci/fetch_reference.sh`), not for this repo. Run each from the directory shown; both were checked with `git apply -p1 --reverse --check` on the reference tree.

```bash
cd <reference>/lib/fprime-sensors/fprime-sensors/MpuImu/Components/ImuManager
git apply -p1 <repo>/projects/i2c-h7/imu-whoami-probe.patch

cd <reference>/lib
git apply -p1 <repo>/projects/i2c-h7/fprime-stm32-gpio-depends.patch
```

`imu-whoami-probe.patch` adds the WHO_AM_I value check to `ImuManager::configure_device()` and its unit tests. `fprime-stm32-gpio-depends.patch` fixes the CMake dependency needed to build the native unit tests.

## NACK trace (Renode)

`test/nack_trace/` builds test-only copies of the I2C and MPU-6050 models and runs Renode with a forced NACK on one START. It needs Renode, `bash`, `python3` and an IMU-restored `ReferenceDeployment.elf`.

```bash
ELF=/path/to/ReferenceDeployment.elf RENODE=/path/to/renode NACK_AT=7 \
  ./projects/i2c-h7/test/nack_trace/run_nack_trace.sh
```

- `NACK_AT=5` forces a NACK on the WHO_AM_I probe write. The stale-byte path is not reached there, because the probe's read clears the queue first.
- `NACK_AT=7` forces a NACK on the accelerometer config write. With the fix, the reset write after it is `6B-80`.
- To see the pre-fix behaviour, delete the `txPreload.Clear();` line in the no-slave NACK branch of `platform/STM32H7_I2C.cs` (do not commit that), then run with `NACK_AT=7`. The reset write goes out as `1C-80` and the log shows `TXDR written twice before START; second byte dropped`.

The sim is slow under load: use `SLEEP_SECONDS=420` (the default). A 130 s run stopped before the NACK.

## Smoke tests

`ci/run_hil.sh` with the IMU-restored ELF: first run 1 of 2 (`test_cmd_no_op` timed out; cause not found), rerun 2 of 2. CI builds with `renode-only.patch`, which removes the IMU, so the IMU path is not exercised in CI.

## Not validated

- Not validated against silicon.
- Not modelled: interrupt and DMA modes, slave mode, RELOAD, bus errors, clock stretching.
- TC is not cleared on STOP. The polled HAL doesn't use TC, so this is not exercised.
