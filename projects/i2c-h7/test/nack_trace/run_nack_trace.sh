#!/bin/bash
# Renode NACK trace for the STM32H7 I2C model.
#
# Forces a NACK on START number NACK_AT (default 5 = the WHO_AM_I probe write) and logs every
# MPU-6050 transaction and every model START. Uses test-only copies generated into WORK; the
# repo's platform files are not changed.
#
# Required: ELF=/path/to/IMU-restored ReferenceDeployment.elf
# Optional: RENODE (default: renode on PATH), NACK_AT (default 5), SLEEP_SECONDS (default 420;
#           the sim is slow under load, a 130 s run stopped before the NACK), WORK (default: new temp dir)
# Output:   $WORK/nack_trace_clean.log (the matching lines are printed)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
HERE="$(cd "$(dirname "$0")" && pwd)"
RENODE="${RENODE:-renode}"
: "${ELF:?set ELF to the IMU-restored ReferenceDeployment.elf}"
NACK_AT="${NACK_AT:-5}"
SLEEP_SECONDS="${SLEEP_SECONDS:-420}"
WORK="${WORK:-$(mktemp -d)}"
mkdir -p "$WORK"
ELF_ABS="$(readlink -f "$ELF")"

# Private copy of the platform file, as ci/run_hil.sh makes it
cp "$ROOT/platform/my_stm32h743.repl" "$WORK/my_stm32h743.repl"

# Test-only models: the NACK-injecting I2C copy and the traced MPU-6050 copy
python3 "$HERE/make_nack_model.py" "$ROOT/platform/STM32H7_I2C.cs" "$WORK/STM32H7_I2C_nack.cs"
python3 "$HERE/make_mpu_trace.py" "$ROOT/platform/MPU6050.cs" "$WORK/MPU6050_trace.cs"

cat > "$WORK/nack_trace.resc" <<EOF
include @$WORK/STM32H7_I2C_nack.cs
include @$WORK/MPU6050_trace.cs
include @$ROOT/platform/BMP280.cs
mach create "stm32h753"
machine LoadPlatformDescription @$WORK/my_stm32h743.repl
# No UART terminal socket: the I2C trace does not need one (a fixed port clashed with another Renode run).
sysbus LoadELF @$ELF_ABS
sysbus.i2c1 NackAt $NACK_AT
start
sleep $SLEEP_SECONDS
pause
sysbus.i2c1 TxCount
quit
EOF

cd "$WORK"
(tail -f /dev/null | timeout $((SLEEP_SECONDS + 60)) "$RENODE" --disable-xwt --console "$WORK/nack_trace.resc" > "$WORK/nack_trace.log" 2>&1) || true
sed -E 's/\x1b\[[0-9;]*m//g' "$WORK/nack_trace.log" > "$WORK/nack_trace_clean.log"
grep -E "TEST START|MPU6050|error CS|Error E" "$WORK/nack_trace_clean.log" | cut -c1-160 | head -n 80
echo "log: $WORK/nack_trace_clean.log"
