#!/usr/bin/env python3
"""Make a test-only copy of platform/STM32H7_I2C.cs that can force a NACK on the Nth START.

Usage: make_nack_model.py <src STM32H7_I2C.cs> <dst STM32H7_I2C_nack.cs>

The copy adds NackAt/TxCount properties and a TEST START log line. Never ship the copy.
"""
import sys

src, dst = sys.argv[1], sys.argv[2]
text = open(src).read()

# 1) fields for the test-only fault injection
a = "        private uint cr1;\n"
assert text.count(a) == 1
text = text.replace(a, "        public int NackAt { get; set; }\n        public int TxCount { get { return txCount; } }\n        private int txCount;\n" + a)

# 2) initialise slave so the out-parameter is definitely assigned on every path
b = "            II2CPeripheral slave;\n"
assert text.count(b) == 1
text = text.replace(b, "            II2CPeripheral slave = null;\n")

# 3) force a NACK on the Nth START (counted only when NackAt > 0)
c = "            if(!TryGetByAddress(address, out slave))\n"
assert text.count(c) == 1
text = text.replace(c,
    "            bool forceNack = (NackAt > 0 && ++txCount == NackAt);\n"
    "            this.Log(LogLevel.Info, \"TEST START #\" + txCount + \" addr=0x\" + address.ToString(\"X2\") + \" n=\" + nbytes + \" rd=\" + read + \" force=\" + forceNack);\n"
    "            if(forceNack || !TryGetByAddress(address, out slave))\n")

open(dst, "w").write(text)
print("written", dst, len(text))
