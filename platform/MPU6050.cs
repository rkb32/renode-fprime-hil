// MPU-6050 register-level I2C model for Renode (M3 spike). Not validated against silicon.
// Covers: WHO_AM_I (0x75), PWR_MGMT_1 (0x6B), accel/temp/gyro output registers (0x3B..0x48).
// Load with: include @MPU6050.cs  (before the platform that instantiates Sensors.MPU6050).

using System;
using Antmicro.Renode.Logging;
using Antmicro.Renode.Peripherals.I2C;

namespace Antmicro.Renode.Peripherals.Sensors
{
    public class MPU6050 : II2CPeripheral
    {
        private const byte WhoAmIValue = 0x68;
        private readonly byte[] regs = new byte[256];
        private int pointer;      // register address for the next access
        private bool addressSet;  // a write's first byte is the register pointer

        public MPU6050()
        {
            Reset();
        }

        public void Reset()
        {
            Array.Clear(regs, 0, regs.Length);
            regs[0x75] = WhoAmIValue; // WHO_AM_I
            regs[0x6B] = 0x40;        // PWR_MGMT_1: SLEEP set at power-up (datasheet default)
            regs[0x3F] = 0x40;        // ACCEL_ZOUT_H: +1 g at the default +/-2 g range (16384)
            regs[0x40] = 0x00;        // ACCEL_ZOUT_L
            pointer = 0;
            addressSet = false;
        }

        public void Write(byte[] data)
        {
            if (data == null || data.Length == 0)
            {
                return;
            }
            int i = 0;
            if (!addressSet)
            {
                pointer = data[0];
                addressSet = true;
                i = 1;
            }
            for (; i < data.Length; i++)
            {
                regs[pointer & 0xFF] = data[i];
                pointer = (pointer + 1) & 0xFF;
            }
        }

        public byte[] Read(int count)
        {
            var result = new byte[count];
            int start = pointer & 0xFF;
            for (int i = 0; i < count; i++)
            {
                result[i] = regs[pointer & 0xFF];
                pointer = (pointer + 1) & 0xFF;
            }
            // Evidence for the M3 check: log every WHO_AM_I and PWR_MGMT_1 access
            if (start == 0x75 || start == 0x6B)
            {
                Logger.Log(LogLevel.Info, "MPU6050 read reg 0x" + start.ToString("X2") + " count " + count + " -> 0x" + result[0].ToString("X2"));
            }
            return result;
        }

        public void FinishTransmission()
        {
            addressSet = false;
        }
    }
}
