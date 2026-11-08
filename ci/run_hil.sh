#!/usr/bin/env bash
# CI test job: run the UNMODIFIED reference smoke tests against the ELF on Renode.
# Env (required): RENODE, ELF, DICT, REF_DIR (fetched reference), VENV (python venv with ci/requirements.txt)
# Env (optional): OUT (log dir, default ./hil-logs)
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RENODE="${RENODE:?set RENODE}"
ELF="${ELF:?set ELF}"
DICT="${DICT:?set DICT}"
REF_DIR="${REF_DIR:?set REF_DIR}"
VENV="${VENV:?set VENV}"
OUT="${OUT:-$ROOT/hil-logs}"
SMOKE="$REF_DIR/FprimeStm32BaremetalReference/Deployments/ReferenceDeployment/test/int/smoke_integration_tests.py"

if [ -z "$OUT" ] || [ "$OUT" = "/" ]; then echo "refusing to clear OUT=$OUT" >&2; exit 1; fi
rm -rf "$OUT"
mkdir -p "$OUT"
WORK="$(mktemp -d)"
ELF_ABS="$(readlink -f "$ELF")"
DICT_ABS="$(readlink -f "$DICT")"

# Fill in machine-specific paths in a private copy of the platform files
cp "$ROOT/platform/bmp280_spi5.py" "$WORK/"
sed "s|@@BMP280_SCRIPT@@|$WORK/bmp280_spi5.py|" "$ROOT/platform/my_stm32h743.repl" > "$WORK/my_stm32h743.repl"
sed -e "s|__REPL__|$WORK/my_stm32h743.repl|" -e "s|__ELF__|$ELF_ABS|" "$ROOT/platform/boot.resc.in" > "$WORK/boot.resc"

# Renode: emulated board; USART1 served on TCP 127.0.0.1:3456
"$RENODE" --disable-xwt --port 1234 "$WORK/boot.resc" > "$OUT/renode.log" 2>&1 &
READY=0
for i in $(seq 1 120); do
  if (exec 3<>/dev/tcp/127.0.0.1/3456) 2>/dev/null; then READY=1; break; fi
  sleep 1
done
echo "renode_socket_ready=$READY after ${i}s" | tee "$OUT/renode_ready.txt"
if [ "$READY" != 1 ]; then
  pkill -f "$WORK/boot.resc" 2>/dev/null
  exit 1
fi

# Bridge: strips Telnet from Renode, serves every TCP client on 127.0.0.1:50000
python3 "$ROOT/bridge/bridge_multi.py" 127.0.0.1 3456 50000 > "$OUT/bridge.log" 2>&1 &
BRIDGE_PID=$!
sleep 3

# GDS (comm) connects to the bridge as a TCP client, then the unmodified smoke tests run
cd "$REF_DIR" || exit 1
"$VENV/bin/fprime-gds" --dictionary "$DICT_ABS" --communication-selection ip \
  --ip-address 127.0.0.1 --ip-port 50000 --ip-client --no-app --gui none --log-to-stdout \
  --framing-selection space-packet-space-data-link \
  --output-unframed-data unframed.bin > "$OUT/gds.log" 2>&1 &
GDS_PID=$!
sleep 12
if ! kill -0 "$GDS_PID" 2>/dev/null; then
  echo "GDS exited before the tests started" | tee -a "$OUT/pytest.log" >&2
  tail -n 20 "$OUT/gds.log" >&2
  pkill -f "$WORK/boot.resc" 2>/dev/null
  kill "$BRIDGE_PID" 2>/dev/null
  exit 1
fi

"$VENV/bin/python" -m pytest -v "$SMOKE" --dictionary "$DICT_ABS" > "$OUT/pytest.log" 2>&1
RC=$?
echo "pytest_exit=$RC" | tee -a "$OUT/pytest.log"

kill -INT "$GDS_PID" 2>/dev/null
sleep 5
kill "$GDS_PID" "$BRIDGE_PID" 2>/dev/null
pkill -f fprime_gds.executables 2>/dev/null
pkill -f "$WORK/boot.resc" 2>/dev/null
# Archive the GDS logs: some file names contain colons, which upload-artifact rejects
tar -czf "$OUT/gds-logs.tar.gz" -C "$REF_DIR" logs 2>/dev/null || true
exit $RC
