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

## Out of scope
- BMP280 (SPI5): see `projects/spi5-h7/PROJECT.md`.
