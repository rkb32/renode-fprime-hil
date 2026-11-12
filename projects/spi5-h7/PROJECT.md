# Project: STM32H7 SPI5 controller model for Renode

## Goal
Model the STM32H7 SPI5 controller so the F´ reference firmware can talk to a BMP280 at 0x40015000. Done when the firmware reads the BMP280 chip ID (0xD0 = 0x58) through a C# BMP280 model, and the smoke tests still pass.

## Why
- Renode's installed `platforms/cpus/stm32h743.repl` has a plain Tag for SPI5, not a controller. But `SPI.STM32H7_SPI` instantiates at 0x40015000 (verified 2026-11-11 by loading the platform and running the smoke tests).
- The Python stand-in (`platform/bmp280_spi5.py`) has been removed. `platform/BMP280.cs` now answers the firmware's SPI transactions.
- The C# device interface `ISPIPeripheral` exists in Renode (`Transmit(byte)`, `FinishTransmission()`, verified by reflection). The BMP280 model attaches to `spi5` (`Sensors.BMP280 @ spi5`).

## Approach (done)
- Reuse `spi4`'s model at 0x40015000: `spi5: SPI.STM32H7_SPI @ sysbus 0x40015000` in `platform/my_stm32h743.repl`. Done; the firmware's BMP280 driver polls (TransferMode POLLED, the default in `open`) and reads chip ID 0x58.
- Forward transfers to an `ISPIPeripheral` BMP280 model: first byte bit 7 = read, low bits = register; then auto-increment; `FinishTransmission` resets.
- BMP280 map: chip ID 0xD0 = 0x58, reset 0xE0, ctrl_meas 0xF4, config 0xF5, status 0xF3, calibration 0x88–0xA1, data 0xF7–0xFC. From memory, unverified.

## Test
1. Unit: a Renode script that sends a chip-ID read and checks 0x58.
2. Integration: boot the ELF in Renode with the BMP280 model, run `ci/run_hil.sh`, and check the firmware reads the chip ID (Renode log line from the model) while the smoke tests still pass.

## Risks
- Renode's SPI controller models may not match the H7 HAL's polling flags (same risk as the I2C controller).
- The BMP280 sensor data path also depends on the firmware's I2C/SPI driver setup; check which bus the firmware actually uses for BMP280 before building the model.

## Dependencies
- Shares the controller-model approach with `projects/i2c-h7/PROJECT.md`. Do the I2C one first if the approach works there.
