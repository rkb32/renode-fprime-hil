// BMP280 SPI register-level model for Renode (M3 spike). Not validated against silicon.
// Covers: chip ID (0xD0 = 0x58), soft reset (0xE0 = 0xB6), status (0xF3), ctrl_meas (0xF4), config (0xF5),
// calibration (0x88..0xA1) and measurement data (0xF7..0xFC). Values match the former Python stand-in.
// Protocol, as used by the reference firmware's BmpManager: the first byte of each transfer is the register address.
// Reads send address | 0x80, writes send address & 0x7F. Later bytes are data, with the address auto-incrementing.
// Load with: include @BMP280.cs  (before the platform that instantiates Sensors.BMP280).

using System;
using Antmicro.Renode.Logging;
using Antmicro.Renode.Peripherals.SPI;

namespace Antmicro.Renode.Peripherals.Sensors
{
    public class BMP280 : ISPIPeripheral
    {
        private const byte ChipIdRegister = 0xD0;
        private const byte ChipIdValue = 0x58;
        private const byte ResetRegister = 0xE0;
        private const byte ResetValue = 0xB6;
        private readonly byte[] regs = new byte[256];  // indexed by register address (0x80..0xFF used)
        private int pointer;      // register address for the next data byte
        private bool addressSet;  // the first byte of a transfer is the register address
        private bool reading;     // the address byte had the read flag (bit 7) set

        public BMP280()
        {
            Reset();
        }

        public void Reset()
        {
            Array.Clear(regs, 0, regs.Length);
            regs[ChipIdRegister] = ChipIdValue;
            regs[0xF3] = 0x00;  // status: no measurement in progress
            regs[0xF4] = 0x00;  // ctrl_meas: sleep mode
            regs[0xF5] = 0x00;  // config
            // calibration 0x88..0x9F (BMP280 datasheet example values, little endian), then 0xA1
            byte[] calib = {
                0x70, 0x6B, 0x43, 0x67, 0x18, 0xFC, 0x7D, 0x8E, 0xC3, 0xD6, 0xD0, 0x0B,
                0x27, 0x0B, 0x8C, 0x00, 0xF9, 0xFF, 0x8C, 0x3C, 0xF8, 0xC7, 0x70, 0x17 };
            Array.Copy(calib, 0, regs, 0x88, calib.Length);
            regs[0xA1] = 0x4B;
            // raw pressure 0xF7..0xF9 and temperature 0xFA..0xFC (fixed values)
            regs[0xF7] = 0x50; regs[0xF8] = 0x00; regs[0xF9] = 0x00;
            regs[0xFA] = 0x80; regs[0xFB] = 0x00; regs[0xFC] = 0x00;
            pointer = 0x80;
            addressSet = false;
            reading = false;
        }

        // SPI carries 7 address bits; every BMP280 register used here is at 0x80..0xFF.
        private static int MapAddress(byte b)
        {
            return (b & 0x7F) | 0x80;
        }

        public byte Transmit(byte data)
        {
            if (!addressSet)
            {
                pointer = MapAddress(data);
                reading = (data & 0x80) != 0;
                addressSet = true;
                return 0x00;
            }

            if (reading)
            {
                byte value = regs[pointer];
                if (pointer == ChipIdRegister)
                {
                    Logger.Log(LogLevel.Info, "BMP280 read reg 0xD0 (chip ID) -> 0x" + value.ToString("X2"));
                }
                pointer = 0x80 | ((pointer + 1) & 0x7F);
                return value;
            }

            // Write: a soft reset is a write of 0xB6 to 0xE0; the chip ID register is read-only.
            if (pointer == ResetRegister)
            {
                if (data == ResetValue)
                {
                    Reset();
                }
                return 0x00;
            }
            if (pointer != ChipIdRegister)
            {
                regs[pointer] = data;
            }
            pointer = 0x80 | ((pointer + 1) & 0x7F);
            return 0x00;
        }

        public void FinishTransmission()
        {
            addressSet = false;
            reading = false;
        }
    }
}
