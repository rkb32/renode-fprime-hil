# Project: STM32H7 SPI5 controller model for Renode

## Goal
Model the STM32H7 SPI5 controller so the F´ reference firmware can talk to a BMP280 at 0x40015000. Done when the firmware reads the BMP280 chip ID (0xD0 = 0x58) through a C# BMP280 model, and the smoke tests still pass.

## Why
- Renode's installed build has no SPI5 controller. Our platform has `spi4: SPI.STM32H7_SPI` at 0x40013400 and nothing for SPI5 (verified by listing SPI instances in `platform/my_stm32h743.repl`).
- We use a Python register-level stand-in for SPI5 (`platform/bmp280_spi5.py`). It answers the firmware's register writes but is not a real controller or sensor.
- The C# device interface `ISPIPeripheral` exists in Renode (`Transmit(byte)`, `FinishTransmission()`, verified by reflection), but a BMP280 model would need a SPI5 controller to attach to.

## Approach (not yet checked)
- Write an STM32H7 SPI controller as a C# peripheral on sysbus at 0x40015000, or reuse `spi4`'s model with a different base address if the register layouts match (check first).
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
