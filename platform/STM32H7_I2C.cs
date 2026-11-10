// STM32H7 I2C controller model for Renode (register-level, master mode). Not validated against silicon.
// Register offsets and bit positions: stm32h753xx.h (I2C_TypeDef, I2C_*_Pos) from the reference tree's CMSIS device header.
// Covers: 7-bit master transfers in AUTOEND and SOFTEND (CR2.STOP) modes; TXDR/RXDR; ISR flags TXE, TXIS, RXNE,
//         NACKF, STOPF, TC, BUSY; ICR clears; CR1.PE reset of the transfer engine; EventInterrupt/ErrorInterrupt lines.
// Not covered: slave mode, 10-bit addressing, RELOAD/TCR multi-segment transfers, DMA, bus errors, arbitration,
//              clock stretching, timeouts, filters. Unsupported use is logged as a warning.
// Load with: include @STM32H7_I2C.cs  (before the platform that instantiates I2C.STM32H7_I2C).
// Slaves attach as: <device> @ i2c1 <7-bit address>, e.g. Sensors.MPU6050 @ i2c1 0x68.

using System;
using System.Collections.Generic;
using Antmicro.Renode.Core;
using Antmicro.Renode.Core.Structure;
using Antmicro.Renode.Logging;
using Antmicro.Renode.Peripherals;
using Antmicro.Renode.Peripherals.Bus;

namespace Antmicro.Renode.Peripherals.I2C
{
    public class STM32H7_I2C : SimpleContainer<II2CPeripheral>, IDoubleWordPeripheral, IKnownSize
    {
        public STM32H7_I2C(Machine machine) : base(machine)
        {
            EventInterrupt = new GPIO();
            ErrorInterrupt = new GPIO();
            Reset();
        }

        public long Size { get { return 0x400; } }

        public GPIO EventInterrupt { get; private set; }
        public GPIO ErrorInterrupt { get; private set; }

        public override void Reset()
        {
            cr1 = 0;
            cr2 = 0;
            oar1 = 0;
            oar2 = 0;
            timingr = 0;
            timeoutr = 0;
            pecr = 0;
            rxdr = 0;
            txdr = 0;
            isr = ISR_TXE;
            rxQueue.Clear();
            txBuffer.Clear();
            txPreload.Clear();
            txPending = false;
            rxAutoEnd = false;
            txAutoEnd = false;
            activeSlave = null;
            UpdateInterrupts();
        }

        public uint ReadDoubleWord(long offset)
        {
            switch(offset)
            {
            case CR1:
                return cr1;
            case CR2:
                return cr2;
            case OAR1:
                return oar1;
            case OAR2:
                return oar2;
            case TIMINGR:
                return timingr;
            case TIMEOUTR:
                return timeoutr;
            case ISR:
                return isr;
            case ICR:
                return 0;
            case PECR:
                return pecr;
            case RXDR:
                return ReadRxdr();
            case TXDR:
                return txdr;
            default:
                this.Log(LogLevel.Warning, "Unhandled read from offset 0x{0:X}", offset);
                return 0;
            }
        }

        public void WriteDoubleWord(long offset, uint value)
        {
            switch(offset)
            {
            case CR1:
                cr1 = value;
                if((cr1 & CR1_PE) == 0)
                {
                    AbortTransfer();
                }
                UpdateInterrupts();
                break;
            case CR2:
                WriteCr2(value);
                break;
            case OAR1:
                oar1 = value;
                break;
            case OAR2:
                oar2 = value;
                break;
            case TIMINGR:
                timingr = value;
                break;
            case TIMEOUTR:
                timeoutr = value;
                break;
            case ICR:
                isr &= ~(value & ICR_MASK);
                UpdateInterrupts();
                break;
            case PECR:
                pecr = value;
                break;
            case TXDR:
                WriteTxdr(value);
                break;
            case ISR:
            case RXDR:
                this.Log(LogLevel.Warning, "Write to read-only register at offset 0x{0:X}", offset);
                break;
            default:
                this.Log(LogLevel.Warning, "Unhandled write to offset 0x{0:X} value 0x{1:X}", offset, value);
                break;
            }
        }

        // CR2: START begins a transfer; STOP ends one in SOFTEND mode. Both bits are self-clearing and are not stored.
        private void WriteCr2(uint value)
        {
            cr2 = value & ~(CR2_START | CR2_STOP);
            if((value & CR2_STOP) != 0 && (isr & ISR_BUSY) != 0)
            {
                isr |= ISR_STOPF;
                EndBus();
                UpdateInterrupts();
            }
            if((value & CR2_START) != 0)
            {
                if((cr1 & CR1_PE) == 0)
                {
                    this.Log(LogLevel.Warning, "START written while the peripheral is disabled (CR1.PE = 0); ignored");
                    return;
                }
                StartTransfer(value);
            }
        }

        private void StartTransfer(uint value)
        {
            if((value & CR2_RELOAD) != 0)
            {
                this.Log(LogLevel.Warning, "RELOAD (multi-segment transfer) is not modelled; treated as a single segment");
            }
            int address = (int)((value & CR2_SADD_MASK) >> 1) & 0x7F;
            int nbytes = (int)((value >> 16) & 0xFF);
            bool read = (value & CR2_RD_WRN) != 0;
            bool autoEnd = (value & CR2_AUTOEND) != 0;

            isr &= ~(ISR_TC | ISR_STOPF | ISR_NACKF);
            isr |= ISR_BUSY;
            activeSlave = null;

            II2CPeripheral slave;
            if(!TryGetByAddress(address, out slave))
            {
                this.Log(LogLevel.Debug, "No device answers at address 0x{0:X2}: NACK", address);
                isr |= ISR_NACKF;
                // The hardware ends the transfer with a STOP after the NACK; the HAL waits for STOPF.
                isr |= ISR_STOPF;
                isr &= ~ISR_BUSY;
                // Drop the byte preloaded before START, so a NACKed write's byte cannot be sent by the next write.
                txPreload.Clear();
                // Abort any write still in progress and any unread data, as EndBus does.
                txPending = false;
                txBuffer.Clear();
                rxQueue.Clear();
                UpdateInterrupts();
                return;
            }
            activeSlave = slave;

            if(read)
            {
                txPreload.Clear();
                rxAutoEnd = autoEnd;
                byte[] data = nbytes > 0 ? slave.Read(nbytes) : new byte[0];
                rxQueue.Clear();
                foreach(var b in data)
                {
                    rxQueue.Enqueue(b);
                }
                if(rxQueue.Count > 0)
                {
                    isr |= ISR_RXNE;
                }
                else
                {
                    CompleteRead();
                }
            }
            else
            {
                txAutoEnd = autoEnd;
                txBuffer.Clear();
                txBuffer.AddRange(txPreload);
                txPreload.Clear();
                expectedTxBytes = nbytes;
                if(nbytes > 0)
                {
                    txPending = true;
                    if(txBuffer.Count >= expectedTxBytes)
                    {
                        txPending = false;
                        CompleteWrite();
                    }
                    else
                    {
                        isr |= ISR_TXIS | ISR_TXE;
                    }
                }
                else
                {
                    CompleteWrite();
                }
            }
            UpdateInterrupts();
        }

        private void WriteTxdr(uint value)
        {
            txdr = value & 0xFF;
            if(!txPending)
            {
                // Byte written before START: the H7 HAL preloads the first byte of a write this way.
                if(txPreload.Count > 0)
                {
                    this.Log(LogLevel.Warning, "TXDR written twice before START; second byte dropped");
                    return;
                }
                txPreload.Add((byte)txdr);
                return;
            }
            txBuffer.Add((byte)txdr);
            isr &= ~ISR_TXIS;
            if(txBuffer.Count >= expectedTxBytes)
            {
                txPending = false;
                isr |= ISR_TXE;
                CompleteWrite();
            }
            else
            {
                isr |= ISR_TXIS | ISR_TXE;
            }
            UpdateInterrupts();
        }

        private uint ReadRxdr()
        {
            if(rxQueue.Count == 0)
            {
                return rxdr;
            }
            rxdr = rxQueue.Dequeue();
            if(rxQueue.Count == 0)
            {
                isr &= ~ISR_RXNE;
                CompleteRead();
            }
            UpdateInterrupts();
            return rxdr;
        }

        private void CompleteWrite()
        {
            if(activeSlave != null && txBuffer.Count > 0)
            {
                activeSlave.Write(txBuffer.ToArray());
            }
            isr &= ~ISR_TXIS;
            if(txAutoEnd)
            {
                isr |= ISR_STOPF;
                EndBus();
            }
            else
            {
                isr |= ISR_TC;
            }
            UpdateInterrupts();
        }

        private void CompleteRead()
        {
            if(rxAutoEnd)
            {
                isr |= ISR_STOPF;
                EndBus();
            }
            else
            {
                isr |= ISR_TC;
            }
            UpdateInterrupts();
        }

        // End of a bus transaction (STOP): release the bus and tell the slave its transaction is over.
        private void EndBus()
        {
            isr &= ~ISR_BUSY;
            txPending = false;
            txPreload.Clear();
            rxQueue.Clear();
            if(activeSlave != null)
            {
                activeSlave.FinishTransmission();
                activeSlave = null;
            }
        }

        private void AbortTransfer()
        {
            if(activeSlave != null)
            {
                activeSlave.FinishTransmission();
            }
            activeSlave = null;
            txPending = false;
            txPreload.Clear();
            rxQueue.Clear();
            txBuffer.Clear();
            isr = ISR_TXE;
        }

        private void UpdateInterrupts()
        {
            bool eventIrq = ((cr1 & CR1_TXIE) != 0 && (isr & ISR_TXIS) != 0)
                         || ((cr1 & CR1_RXIE) != 0 && (isr & ISR_RXNE) != 0)
                         || ((cr1 & CR1_ADDRIE) != 0 && (isr & ISR_ADDR) != 0)
                         || ((cr1 & CR1_STOPIE) != 0 && (isr & ISR_STOPF) != 0)
                         || ((cr1 & CR1_TCIE) != 0 && (isr & ISR_TC) != 0);
            bool errorIrq = ((cr1 & CR1_NACKIE) != 0 && (isr & ISR_NACKF) != 0)
                         || ((cr1 & CR1_ERRIE) != 0 && (isr & (ISR_BERR | ISR_ARLO | ISR_OVR)) != 0);
            EventInterrupt.Set(eventIrq);
            ErrorInterrupt.Set(errorIrq);
        }

        // CR1
        private const long CR1 = 0x00;
        private const long CR2 = 0x04;
        private const long OAR1 = 0x08;
        private const long OAR2 = 0x0C;
        private const long TIMINGR = 0x10;
        private const long TIMEOUTR = 0x14;
        private const long ISR = 0x18;
        private const long ICR = 0x1C;
        private const long PECR = 0x20;
        private const long RXDR = 0x24;
        private const long TXDR = 0x28;

        private const uint CR1_PE = 1u << 0;
        private const uint CR1_TXIE = 1u << 1;
        private const uint CR1_RXIE = 1u << 2;
        private const uint CR1_ADDRIE = 1u << 3;
        private const uint CR1_NACKIE = 1u << 4;
        private const uint CR1_STOPIE = 1u << 5;
        private const uint CR1_TCIE = 1u << 6;
        private const uint CR1_ERRIE = 1u << 7;

        private const uint CR2_SADD_MASK = 0x3FFu;
        private const uint CR2_RD_WRN = 1u << 10;
        private const uint CR2_START = 1u << 13;
        private const uint CR2_STOP = 1u << 14;
        private const uint CR2_RELOAD = 1u << 24;
        private const uint CR2_AUTOEND = 1u << 25;

        private const uint ISR_TXE = 1u << 0;
        private const uint ISR_TXIS = 1u << 1;
        private const uint ISR_RXNE = 1u << 2;
        private const uint ISR_ADDR = 1u << 3;
        private const uint ISR_NACKF = 1u << 4;
        private const uint ISR_STOPF = 1u << 5;
        private const uint ISR_TC = 1u << 6;
        private const uint ISR_BERR = 1u << 8;
        private const uint ISR_ARLO = 1u << 9;
        private const uint ISR_OVR = 1u << 10;
        private const uint ISR_BUSY = 1u << 15;

        // ICR clears ADDRCF(3), NACKCF(4), STOPCF(5), BERRCF(8), ARLOCF(9), OVRCF(10): same bit positions as ISR.
        private const uint ICR_MASK = ISR_ADDR | ISR_NACKF | ISR_STOPF | ISR_BERR | ISR_ARLO | ISR_OVR;

        private uint cr1;
        private uint cr2;
        private uint oar1;
        private uint oar2;
        private uint timingr;
        private uint timeoutr;
        private uint isr;
        private uint pecr;
        private uint rxdr;
        private uint txdr;

        private readonly Queue<byte> rxQueue = new Queue<byte>();
        private readonly List<byte> txBuffer = new List<byte>();
        private readonly List<byte> txPreload = new List<byte>();
        private int expectedTxBytes;
        private bool txPending;
        private bool txAutoEnd;
        private bool rxAutoEnd;
        private II2CPeripheral activeSlave;
    }
}
