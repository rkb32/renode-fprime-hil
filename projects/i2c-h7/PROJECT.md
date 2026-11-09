# Project: STM32H7 I2C controller model for Renode

## Goal
Model the STM32H7 I2C controller so the F´ reference firmware can drive I2C1 and read the MPU-6050 at 0x68. Done when the IMU-restored ELF passes the unmodified smoke tests and the firmware reads WHO_AM_I (0x75) from the MPU-6050 model.

## Why
- Renode ships no STM32H7 I2C model (`STM32H7_I2C` is absent from the install). Our platform maps i2c1 to `I2C.STM32F7_I2C` (`platform/my_stm32h743.repl`, i2c1 at 0x40005400).
- With the IMU restored, the firmware spins in the HAL's STOP-flag wait: `I2C_WaitOnSTOPFlagUntilTimeout` and `I2C_IsErrorOccurred` (verified by two PC samples; the H7 HAL source is in the fprime-stm32 tree).
- The MPU-6050 model (`platform/MPU6050.cs`) is written and loads, but has no controller to drive it.

## Facts we verified
- Interfaces (Renode Infrastructure.dll, by reflection): `II2CPeripheral` has `Write(byte[])`, `Read(int)`, `FinishTransmission()`, and inherits `IPeripheral`.
- Renode loads C# at runtime with `include @file.cs` (MPU6050.cs loaded without error).

## Approach (not yet checked)
- Write an STM32H7 I2C controller as a C# peripheral on sysbus at 0x40005400. Register offsets for the H7 I2C (CR1, CR2, TIMINGR, ISR, ICR, RXDR, TXDR) need checking against the H7 reference manual or the HAL headers. Unverified from memory: the F7 and H7 layouts match for these registers.
- Set the flags the HAL polls: TXIS when TXDR is ready, RXNE when data is in RXDR, TC/STOPF after a transfer, NACKF on a missing device.
- Forward transfers to the attached `II2CPeripheral` at address 0x68.

## Test
1. Unit: a small firmware test or Renode script that writes WHO_AM_I and reads it back.
2. Integration: restore the IMU (`patches/uart-polled.patch` on the reference), boot in Renode, run `ci/run_hil.sh`. Expect 2 of 2 smoke tests to pass and the Renode log to show `MPU6050 read reg 0x75`.

## Risks
- The HAL may poll other flags than STOPF (for example BUSY, TC, or timeouts). Each must be set correctly or the HAL times out.
- The IMU driver may use DMA or interrupts. Renode's model would need to support that too.
- Scope could grow; keep the first milestone to polled WHO_AM_I.

## Status (2026-11-08, Haiku 5.5; Opus 5.5 checked the open decisions)

Changed (branch `i2c-h7-controller`, committed locally, not pushed):
- `platform/STM32H7_I2C.cs` (new): H7 I2C master model on `i2c1`, `SimpleContainer<II2CPeripheral>` for slaves.
- `platform/my_stm32h743.repl`: `i2c1` is `I2C.STM32H7_I2C`; `mpu: Sensors.MPU6050 @ i2c1 0x68` replaces the ICM20948 stub.
- `platform/MPU6050.cs`: DEVICE_RESET (PWR_MGMT_1 bit 7) restores defaults and clears itself. Without this the driver's reset poll never finishes.
- `platform/boot.resc.in`: includes both C# models via `__MODELS__`.
- `ci/run_hil.sh`: one extra `sed` for `__MODELS__`. This is a CI-path change; the IMU-free run below still passes.

Verified (run on the final code):
- H7 register offsets and bit positions: read from `stm32h753xx.h` in the reference tree, not from memory. High confidence.
- Polling flow: read from `stm32h7xx_hal_i2c.c` and `Stm32I2cDriver.cpp`. The HAL preloads the first TXDR byte before START, and a NACK sets NACKF and STOPF. High confidence.
- IMU-restored ELF on the new model: reset, wake, config writes and repeated 14-byte reads from 0x3B all ACK. Renode log. High confidence.
- `ci/run_hil.sh` with the IMU-restored ELF: 2/2 smoke tests pass (`pytest_exit=0`).
- `ci/run_hil.sh` with the IMU-free ELF (`~/ci-full/out`): 2/2 pass. Regression check.
- WHO_AM_I through the controller registers (Renode monitor, firmware paused): the sequence returns 0x68. Log line: `MPU6050 read reg 0x75 count 1 -> 0x68`. High confidence for the model; this is not a firmware read.

Firmware WHO_AM_I (Opus 5.5 picked the firmware probe; the value check was added after a target test, see below):
- Probe: one `bus_write` of 0x75 with a 1-byte read in `ImuManager::configure_device()`, before the accel and gyro writes. A value other than 0x68 returns an error, which sends the state machine to RESET. Patch: `projects/i2c-h7/imu-whoami-probe.patch`, applied in `~/ci-full/reference/lib/fprime-sensors` (outside this repo; `.orig` backups sit next to the files).
- Verified on target, probe working: smoke tests pass 2/2 (`pytest_exit=0`); firmware log `MPU6050 read reg 0x75 count 1 -> 0x68`. High confidence. Done criterion 1 is met.
- Verified on target, probe NACKed (a test-only model copy forces the 5th START to NACK; test copies live in WSL home, not the repo): the HAL did not report the NACK on the one-byte pointer write. Configure carried on and read a stale register (0x6C = 0x00). Without a value check the bad read passed silently. With the check: configure fails, the firmware goes to RESET, and the next cycle reads 0x68. High confidence.
- Opus's earlier advice was to log a mismatch, not fail. The value check overrides that because the NACK was otherwise silent. Opus 5.5 endorsed the override on 2026-11-08.
- Unit tests (`test/ut`): 5/5 pass (`fprime-util check`, 2026-11-08), including `WhoAmIProbeFailureReturnsToReset` (bus error) and `WhoAmIMismatchReturnsToReset` (device returns 0x00, bus OK). Running them needed a fix to `STM32GpioDriver/CMakeLists.txt` in `lib/fprime-stm32` (`projects/i2c-h7/fprime-stm32-gpio-depends.patch`).
- IMU-free build: `ImuManager` is not in that ELF (0 hits), so the earlier IMU-free pass still stands. Not re-run after the probe change.

Not modelled or not exercised (unverified):
- Interrupt mode, DMA, slave mode, 10-bit addressing, RELOAD/TCR, bus errors, arbitration, timeouts, clock stretching.
- NACK on a multi-byte transfer (reset) is run on target with no MPU on the bus: the firmware retries with no crash or hang (2 NACKs in 40 s). A NACK on a one-byte write is not reported by the HAL; see the probe notes above.
- Behaviour is not validated against silicon.

## Out of scope
- BMP280 (SPI5): see `projects/spi5-h7/PROJECT.md`.
