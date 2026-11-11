# renode-fprime-hil: M0/M1 blocker report

Date: 2026-11-07. Drafted by Claude Haiku 5.5 with Opus 5.5 decision checks. Nothing posted, pushed, or sent.

## Status
- **M0 (UART output from the firmware): met.** The firmware boots and sends telemetry.
- **M1 (GDS smoke tests): met.** The unmodified smoke tests (original 15 s and 5 s timeouts) pass 2 of 2 in 10.3 s (`m1_final.sh`, log `m1_final_logs/pytest.log`), using `bridge_multi.py`. The earlier failures came from the test bridge, not the GDS (see Corrections).
- **M3, IMU (blocked):** with the IMU restored (UART still POLLED), both smoke tests fail. The board sends about 1 KB, then stops. Renode has no STM32H7 I2C model (`STM32H7_I2C` not in the install; `i2c1` is `STM32F7_I2C`), so the firmware's I2C driver hangs during init. Verified by two program-counter samples: both land in the HAL's `I2C_WaitOnSTOPFlagUntilTimeout` / `I2C_IsErrorOccurred`, which poll for a STOP flag the F7 model never sets. Unverified: whether that wait ever times out. The MPU-6050 model (`platform/MPU6050.cs`) was never read by the firmware. The CI build stays IMU-free and M1 passes on it.
- **M3, SPI5 BMP280 (blocked):** Renode has no SPI5 controller model (only spi4 in the platform). The Python stand-in remains.

## Verified
- The ELF builds in WSL (`fprime-util`, Arm GNU 12.2) with the IMU removed and UART TX in polled mode.
- The rate group runs about 29 cycles/s, not the 100 Hz a 10 ms timer implies.
- Renode USART1 receive works. A test byte injected while paused set RXNE, and the firmware read it within 1 s.
- The firmware's polled receive reads every waiting byte on each poll (source: `Stm32UartDriverCommon.cpp`, POLLED branch).
- The command path is rate-limited, not blocked. GDS-to-board bytes rise at a steady 120 bytes per 5 s (about 23 B/s). In the 120 s run, 5.5 KB went to the board and 35 KB came back.
- The dictionary matches the build: no IMU in either, and both were written 7 s apart.
- The board sends 1024-byte CCSDS TM frames. In the last 11 KB capture, 10 of 10 frames pass the CRC-16 check. SCID is 68, VCID 1, and frame counters increment.
- The GDS default framing (`space-packet-space-data-link`) decodes those frames offline. The 1,003 discarded bytes are a partial frame at the capture start.
- **fprime-gds's own channel decoder (`ChDecoder`) with the dictionary decodes 20 of 20 APID-1 telemetry packets from the board.** Sample values: TickCount 2501, CPU 100.0, BytesRecv 4236, comQueueDepth [0, 1]. The descriptor is 2 bytes and the channel ID 4 bytes, matching the GDS types. Time base shows TB_NONE.
- The GDS log shows no decode errors, only connection resets at test end.
- Chunked input gives the same deframing result as one whole buffer (20 packets for any chunk size tested, 1 to 4096 bytes and random sizes). Live socket chunking is not the cause.
- In a 110 s live run, a ZMQ subscriber on the GDS output socket received 1 message: a handshake-type packet (descriptor 0xFE). No telemetry was published.
- The dictionary has no `FW_PACKET_TELEM` enum. The GDS uses its default descriptor map (`FW_PACKET_TELEM` = 1), which matches the board's descriptor.

## Unverified
- Resolved (see Corrections): why the live GDS got no bytes.
- Why the command path is slow: firmware poll rate or Renode serial timing.
- Whether the slow rate group (about 3.4x) matters at all, now that 120 s windows also fail.
- Probe hooks print to the monitor and may perturb timing. Hook counts are approximate.

## Corrections to earlier notes
- **ELF size gap (explained in part):** the loaded sections match between the local build and the CI build (`.text` and `.bss` identical). `.rodata` differs by 832 bytes (version string `-dirty` and build paths). The remaining ~7.8 KB of file size is in non-loaded debug sections, not checked.
- **Root cause of the "no telemetry" failure (verified):** `bridge_wsl.py` accepts one TCP client. In run 4, `ss` showed the bridge accepted a different client (127.0.0.1:45098), while comm's connection (127.0.0.1:52802, comm pid 12492) sat unaccepted in the listen backlog. comm read 0 bytes; the bridge's 60 KB went to the other client. The GDS was not at fault. Fix: `bridge_multi.py` serves every client. With it, the unmodified M1 tests pass.
- Run 1 of the comm hook was invalid (Renode not running). Runs 2–4 are logged in `m2_instr_logs/`.
- `m1_long.sh` does pass `--gui none`; an earlier note said it did not.
- The "bridge stall at about 840 bytes" was the rate limit above, not a deadlock.
- The earlier "framing mismatch" and "24 decoded packets" conclusions were wrong. They came from a parse offset error.
- `bridge_clean.bin` and `bridge_raw.bin` are appended across runs. Use only one run's bytes.

## Open: `test_cmd_no_op` flake (M2, 2026-11-09)
- Morning batch (`m2_flake.sh`, `main` commit, ELF mtime 2026-11-07 17:27, not hash-checked against the morning run): 9 of 10 runs failed `test_cmd_no_op` with 0 matching events in the 5 s window. In 8 of the 9, GDS logged `OpCodeCompleted`. Whether the reply was late or the matcher missed it is not confirmed.
- Same day: 10 of 10 sequential runs of the unmodified test passed (call 0.11–2.71 s). A re-run of the morning batch (`flake2-*`) passed 10 of 10. Five runs with a 30 s wait passed (call up to 5.32 s).
- Cause: unexplained. The morning host state was not recorded. Environment suspected.
- The smoke test file is identical to upstream 89f1924. The runner now logs host state and leftover processes (`host_state.txt`) and per-test timing (`--durations=0`).
- Status: not reproduced today. The 5 s wait is unchanged.
- 2026-11-10, IMU-kept build (`--with-imu`, local): 3 of 4 runs passed. The failing run (`~/imu-rep-3`) had 0 events matched for `test_cmd_no_op`. Its GDS `event.log` records NoOpReceived and OpCodeCompleted, but with no wall-clock time (`TB_NONE: 0.000000s`). The earlier claim that they were logged "about 1 s after pytest started" is unsupported and is withdrawn. Cause not found.
- 2026-11-10, diagnostic (`diag_plugin` via `PYTEST_ADDOPTS`, test file unchanged, not in CI): 8 runs on the IMU-kept build, 4 failed. In all 4 failing runs the test API's event history had 0 entries when `test_cmd_no_op` gave up, while the GDS event log had both events. Recount from the run logs (`imu-rep-*`, `diag-*`, `diag2-*`, `diag3-*`, 23 runs in total): 12 failed, 11 passed. Every failure is `test_cmd_no_op` with `F(0)` and a sequence-search timeout. By set: plain `imu-rep` 1 of 3 failed; `diag` 4 of 8; `diag2` 3 of 6; `diag3` (`pytest -s`) 4 of 6. The earlier "5 of 12" was an undercount. In failing run `diag3-1`, the only event callback before FAIL was one `target=other` callback; the test API callback came after FAIL. Callback lines have no timestamps, so the delay is still unmeasured. Correction from the uncaptured run (`diag3`, `pytest -s`): in a failing run the test API's history got CMD_NO_OP and OpCodeCompleted after the test had already reported FAIL, so the events arrive late (after the 5 s window), not lost. A passing run gets them inside the window. Delay size not measured yet (no timestamps in the logging). The `APID 2 ... sequence count: 10 (expected: 0)` warning appears in every run, pass or fail, so it does not explain the failures. Cause in the GDS path not found.
- 2026-11-11, `diag4` (10 runs, `pytest -s`, `diag_plugin4` timestamps, test file unchanged, local only): 3 of 10 failed. In each failing run the first event decode in the pytest process came 5.39–5.70 s after the CMD_NO_OP send, and the events arrived in one burst within about 2 ms. Passing runs: first decode 1.00–4.50 s after the send. All 37 decodes across the 10 runs took under 0.5 ms (max 0.44 ms), so the delay is before the decoder. Host CPU was not captured (`run_hil.sh` clears `OUT`, which deleted the sampler log).
- 2026-11-11, `diag5` (10 runs, same plugin plus `TcpHandler` hooks): 0 of 10 failed; first decode 0.06–2.17 s. The TCP hooks logged nothing: the TCP client runs in the separate GDS process, not in pytest. GDS-side socket timing is not measured.
- 2026-11-11, `diag6`: the GDS hook did not run in the comm child process, so no socket data. Its 12 runs (1 failed) are not used.
- 2026-11-11, `diag7` (12 runs, `pytest -s`, timestamps on TCP recv in the GDS process and its comm child): 1 of 12 failed. In the failing run the GDS received no bytes in the first 5 s after the CMD_NO_OP send. The first bytes arrived 5.23 s after the send, and the pytest decode followed 83 ms later. In passing runs, the first GDS receive came 0.33–3.27 s after the send (run 1 received bytes 0.10 s before the send), and the decode followed the first receive by 16–54 ms. So the delay is before the GDS socket, not in the GDS-to-pytest hop. Sample size: one failing run. Bridge and Renode timing not yet measured.

## Models and build changes (Renode-only)
1. **PWR peripheral** (Python) in `my_stm32h743.repl`. Replaces Renode's plain tag. Returns ready bits.
2. **ICM-20948 stand-in** at I2C 0x68 (`mpu_stub`). Attaches Renode's existing model. Not an MPU-6050. The IMU driver is removed from the topology.
3. **BMP280 SPI5 stand-in** (`bmp280_spi5.py`). Register-level Python model. Not a real sensor model.
4. **Firmware build changes:** IMU subtopology removed from `topology.fpp`; UART TX set to `TransferMode::POLLED`. Originals saved as `.orig`.

## Next steps if resumed
1. Keep `bridge_multi.py` as the test bridge (`bridge_wsl.py` is superseded). M1 is met on the unmodified tests.
2. Renode timing (slow rate group, slow command path) is still unexplained and not needed for M1. Revisit only if it affects a later milestone.
3. M2 (CI on ubuntu-latest), M3, and M4 are not started. Nothing is committed or posted.
