#!/usr/bin/env python3
"""Make a test-only copy of platform/MPU6050.cs that logs every write and every read.

Usage: make_mpu_trace.py <src MPU6050.cs> <dst MPU6050_trace.cs>
"""
import sys

src, dst = sys.argv[1], sys.argv[2]
text = open(src).read()

# log every write transaction
a = "        public void Write(byte[] data)\n        {\n"
assert text.count(a) == 1
text = text.replace(a, a + "            Logger.Log(LogLevel.Info, \"MPU6050 write \" + BitConverter.ToString(data));\n")

# log every read, not only 0x75 / 0x6B
b = "            if (start == 0x75 || start == 0x6B)\n"
assert text.count(b) == 1
text = text.replace(b, "            if (true)\n")

open(dst, "w").write(text)
print("written", dst, len(text))
