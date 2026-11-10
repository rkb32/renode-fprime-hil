# fprime-cyclebench plan (update, 2026-11-07)

Model: Haiku 5.5. No hardware. One comment posted to nasa/fprime #5572 (2026-11-10: https://github.com/nasa/fprime/issues/5572#issuecomment-6760319745). Nothing else posted, pushed, opened, or sent.
Tags: [V] verified (how), [U] unverified. All instruction numbers are PROXY (Fw-only, Renode stm32f4), not hardware cycles.

## Verified
- [V] #5572: tlmWrite_<chan> 595 → 817 cycles (+37%) on VA416x0 (Cortex-M4), devel 1031e28b1d (Jun 11) → d739002 (Jul 29). Fix PR #5582 merged Aug 5. (gh, high)
- [V] `Time.cpp` and `Time.hpp` are byte-identical at 1031e28b1d and d739002. (gh diff, high)
- [V] `TlmBuffer` became `using TlmBuffer = LinearBufferTemplate<...>`, which zero-initializes its array. (gh patch, high)
- [V] PR #5582 diff vs its first parent (4f56327a42 → 4bc7685e6e) touches only `Time.cpp`, `Time.hpp`, and `LinearBufferTemplate.hpp`. (git diff --stat, high)
- [V] Renode 1.16.0 is installed. It exposes `cpu ExecutedInstructions`, has Cortex-M4 STM32F4 platforms, and has no VA416x0 platform. (local files, high)
- [V] Renode harness check: a 1000-iteration loop of 3 instructions reports 3003; a rerun reports 3003; a 2000-iteration loop reports 6003. Delta exact. (local run, high)
- [V] No `arm-none-eabi-gcc` on PATH earlier; ARM GNU 14.2 is installed system-wide (approved) at `C:\Program Files (x86)\Arm GNU Toolchain arm-none-eabi\14.2 rel1`. (PATH and install check, high)
- [V] No cycle or benchmark harness found in nasa/fprime or fprime-community. (search, medium)

## Proxy results (Fw-only, Renode stm32f4; PROXY, not cycles)
Harness: `TlmBuffer` serialize + `Time` copy, N iterations, same flags for every build. Startup now runs init arrays, copies .data, zeroes .bss, and enables the FPU. Fixed overhead is 3541 instructions in every build after that fix (was 6). Per-iteration counts are unchanged by the fix; the variant X run predates it, and its per-iteration figure still holds.

| Build | Per iteration | Notes |
|---|---|---|
| Before #5582 (4f56327a42) | 537 | zero-init on, old Time code |
| Variant X (after + zero-init restored) | 458 | isolates zero-init |
| After #5582 (4bc7685e6e) | 255 | zero-init off, new Time code |

- [V] Zero-init effect ≈ 458 − 255 = **203 instr/iter** (≈38% of 537). (proxy, high for this harness)
- [V] Remaining change (Time edits; assumes additivity with zero-init) ≈ 537 − 458 = **79 instr/iter**. Not isolated to the copy constructor alone. (proxy, medium)
- [U] Proxy instruction savings vs hardware cycles. The PR's own claim is ~250 cycles; the proxy shows 282 instructions. Not comparable without hardware.

## Unverified
- [U] Renode instruction counts vs VA416x0 cycles. Not tested. Renode isn't cycle-accurate (from memory).
- [U] Whether the Fw-only proxy matches a full deployment. Not tested.
- [U] Cause #2 (copy-ctor inlining) in source. `Time.cpp`/`Time.hpp` are unchanged between the commits, so the cause is elsewhere. Not resolved.

## Blockers
- **Hardware cycles (VA416x0):** needs a board. Blocked.
- **Full F4 deployment:** blocked. The F4 OSAL includes ST HAL and CMSIS; board glue (`main.h`, `tim2_clock.h`, `RawTimeSource`) isn't in the repos. d739002 `RawTimeInterface::getDelegate` has no `RawTimeSource` parameter, but fprime-stm32's F4 OSAL expects one (verified by compile error).
- `fprime-tools` 4.3.0a5 is now installed in `Desktop\fprime-venv` (pip list, verified). The proxy doesn't need it.

## Milestones
- **M0 (proxy):** done. Before/after per-iteration counts above.
- **M0b (full):** blocked (above).
- **M1:** done (pass 3). Telemetry write (605/write, real topology), event log (3,151/event, stand-in port), queue send+receive (201/pair, real F4 queue). Serialize is inside the telemetry case.
- **M2:** check instruction counts against on-target cycles. Needs a board.
- **M3:** CI job, later.

## Adoption
Build as an external repo. Offer to nasa/fprime as a reproduction of #5572 once M1 works. Maintainers decide CI.

## Status updates (2026-11-07)
- [V] Pip lock: `scratchpad\req.lock` pins 37 packages with hashes. `pip download --require-hashes` fetched all 37 with exit 0. Not installed from the lock. (high)
- [V] ARM GNU 12.2 and 14.2 are both installed via winget; neither is on system PATH. Builds use full paths to 14.2. 12.2 left in place. (winget list, high)
- [V] Harness compile-only check (FW_DIRECT_PORT_CALLS=0) passes: 0 errors. Hardware build uses direct port calls, so this is not a hardware-build check. (high for the flag used)
- [U] Harness run and direct-call wiring: not done. (superseded by pass 2 below)

## Status updates (2026-11-07, pass 2: direct-call build and M1 cases)
Method: Renode `ExecutedInstructions`; per-unit cost = (N=2000 − N=1000) / 1000. All numbers are instructions, not cycles.
- [V] Direct-call build (`FW_DIRECT_PORT_CALLS=1`, the default in `default/config/FpConfig.h`) compiles and links. Stand-ins supply `Time_out`, `Tlm_out`, `Log_out`, and the `isConnected_*` checks; no topology exists here. (compile and link, high)
- [V] Telemetry write (`tlmWrite_Chan`): **705 instr/write**, from two builds (N=1000 total 709,510; N=2000 total 1,414,510; fixed ~4,510). A second build of the new component gave the same 705. (Renode, high for the method)
- [V] Event log (`log_ACTIVITY_HI_Ev`), constant argument: **3,151 instr/event** (N=1000 total 3,155,498; N=2000 total 6,306,498; fixed ~4,498). Text logging is on (`FW_ENABLE_TEXT_LOGGING=1`, the default in this FpConfig), so text formatting is included. (Renode, high for the method, medium for absolute: stand-in port)
- [V] Event with the loop index as argument gave non-linear totals (fixed would be negative): the text-format cost changes with the digit count of the argument. That is why the constant-argument build was used. (Renode, high)
- (Superseded in pass 3: port call and queue. See pass 3.)
- [U] Direct-call numbers are not comparable to the non-direct proxy numbers above (different harness: adds a Time output call and an event port).
- Files: `scratchpad\harness\run_direct.sh`, `run_m1.sh`, `run_evt_const.sh`; generated code in `scratchpad\harness\gen_m1`.
- Model: Haiku 5.5 for the work; Opus 5.5 for the decision (C, then B).

## Status updates (2026-11-07, pass 3: "do em all")
- [V] Cause #2 mechanism, -Os, disassembled proxy ELFs: before, `Fw::Time(const Time&)` is out-of-line in Time.cpp and calls `set()` (range assert, then `TimeValue::set`). After 4bc7685e6e, the copy ctor is inline in Time.hpp (`m_val(other.m_val)`), so the tlm path copies fields. The issue's "inlining" wording does not match the -Os binary; the cost is the `set()` path. Flight-build flags: [U]. (source + objdump, high at -Os)
- [V] Queue, real F4 OSAL (fprime-stm32 Os/Stm32F4): links with the CMSIS core (`core_cm4.h` from CMSIS_5). No HAL needed; `main.h` is a shim. Renode: N=1000 214,883; N=2000 415,883; delta **201 instr per send+receive**; fixed 13,883 (includes `create`). Allocator is a stand-in (create only, not in the loop). (high for method)
- [V] Port call, generated direct-call topology (`Top.fpp`: `harness.Tlm -> sink.TlmIn`): `Tlm_out` -> `TlmIn_handlerBase` -> sink handler (symbols present in ELF). Renode: N=1000 610,607; N=2000 1,215,607; delta **605 instr per tlmWrite**; fixed 5,607. Time port unconnected, so `Time_out` is skipped. Not comparable to the 705 stand-in build, which called a Time stub per write. (high for method, medium for comparison)
- [U] Hardware cycles: still blocked. No ST-Link, J-Link, or serial board in the Windows device list (PnP filter, checked 2026-11-07).
- All counts: Renode instructions, not cycles. Model: Haiku 5.5 (work); no new decisions needed.

## Status updates (2026-11-07, pass 4: follow-ups; supersedes pass 2/3 where they differ)
- [V] Flight flags, from the fprime-stm32 repo: toolchain sets `-mcpu=cortex-m4 -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard -ffunction-sections -fdata-sections -fno-exceptions -fno-rtti -fno-threadsafe-statics -g3`. No `-O` flag and no `CMAKE_BUILD_TYPE` in the repos, so flight optimization is set by the user's build type: [U]. Template `FpConfig.h` for F4: `FW_ENABLE_TEXT_LOGGING=0`, `FW_DIRECT_PORT_CALLS=1`. Our runs used `-Os` (assumed).
- [V] Cause #2, disassembled Time.o per commit: at -O2 the before copy ctor is out-of-line and has `set()`'s range assert, `TimeBase::isValid`, and `TimeValue::set` inlined into it. At -Os, `set()` is a separate call. Either way the before copy goes through `set()`; the after copy (inline in Time.hpp) copies fields. The issue's "inlining" wording matches -O2. (objdump, high)
- [V] Event log, text logging **off** (flight config): **449 instr/event** (N=1000 453,498; N=2000 902,498; N=3000 1,351,498; exact linear). Text logging on was 3,151 (two points only).
- [V] Topology with Time provider connected (`harness.Time -> timer.TimeGet`): **940 instr/write** (N=1000 946,750; N=2000 1,886,750; N=3000 2,826,751). Without the time provider: 605 (N=3000 residual 1). The 705 stand-in is not directly comparable: it had Time and Tlm stubs, no sink, no time provider.
- [V] Linearity, third point N=3000: topology no-time residual 1; queue residual 0 (616,883); event text-off residual 0.
- [V] F4 OSAL (queue, mutex, task, raw time) compiles from fprime-stm32 with the CMSIS core. Remaining external symbols are libc, libgcc, and C++ runtime (provided by the arm-none-eabi link) and Fw objects already in the link set. `Stm32_GetSystemMicroseconds` is stubbed (board TIM2 unavailable). Full deployment (board init, HAL, UART/GDS, Main) is NOT built: [U].
- Cleanup: removed worktrees `wt_before` (4f56327a42) and `wt_after` (4bc7685e6e); both recreatable from those SHAs. Removed `temurin17-jre.zip`; the extracted JRE (`jre17`) is kept because `fpp-to-cpp` needs it. Kept fprime-src, cmsis5-src, fprime-stm32-src, fprime-baremetal-src, and the harness/proxy/topo/queue dirs.
- [V] Uninstalled ARM GNU 12.2 (its own uninstaller, exit 0) and LLVM 23.1.5 (MSI, elevated, exit 0). Verified: winget no longer lists them; `Program Files\LLVM` is gone; `arm-none-eabi-g++` 14.2.1 still runs. (high)
- Name clash: no change. `Desktop\PLAN.md` belongs to renode-fprime-hil.
- Model: Haiku 5.5 (work). No new decisions, so no Opus check this pass.

## Decisions (pass 5, Opus 5.5 check)
- D1 Name clash: keep both files. Our plan stays `PLAN-cyclebench.md` in this folder; `Desktop\PLAN.md` is renode-fprime-hil's and is not touched. Opus: optimal, high confidence.
- D2 Optimization level: measure both `-Os` and `-O2`. Opus: optimal, medium confidence. Opus also suggested that with no build type set, CMake adds no `-O` flag, so the build would be `-O0`. [V] (pass 6): CMake 4.4.3 configure with no build type gives no `-O` flag in build.ninja; `__OPTIMIZE__` is undefined for arm-none-eabi-g++ 14.2.1 and host g++, so the build is unoptimized. fprime's cmake sets no build type. Which build type flight uses: [U].
- D3 Full F4 deployment: deferred. Not needed for per-call cost tracking. Stub-based numbers would look real without being real. Opus: probably optimal, medium confidence. Reopen if startup, topology wiring, or rate-group dispatch regressions matter, since only a full image shows those.

## -O2 results (pass 5; same cases, all objects rebuilt at -O2; Renode instructions)
- [V] Topology with time provider: **903 instr/write** (N=1000 909,036; N=2000 1,812,036; fixed 6,036). -Os was 940.
- [V] Event, text logging off: **467 instr/event** (N=1000 471,121; N=2000 938,121; fixed 4,121). -Os was 449.
- [V] Queue send+receive, real F4 queue: **198 instr/pair** (N=1000 211,822; N=2000 409,822; fixed 13,822). -Os was 201.
- [V] Third point, N=3000 (pass 6; hex converted and checked): topology 2,715,037 (residual 1); event text-off 1,405,121 (residual 0); queue 607,822 (residual 0). Linear at -O2 as well as -Os. Per-unit numbers above stand.
- Read: the optimization level moves these counts by a few percent, and in both directions. The #5572 mechanism holds at both levels (cause #2 section).

## Reconciliation with #5572 (pass 6; Opus pick C: reconcile first, full F4 image not built)
- [V] Issue #5572 table (their Vorago Cortex-M4 build, `tlmWrite_OverheadTotalCycles`): d739002 out-of-line copy ctor 612 cycles; d739002 memberwise copy 453; 1031e28b1d 483. (gh issue, high)
- [V] Our no-time topology, d739002: 605 instr/write at -Os (earlier pass). At -O2: **600** (N=1000 605,103; N=2000 1,205,103; fixed 5,103). Close to the issue's 612. (Renode, high)
- [V] -O2, time port connected, provider leaves the caller's time unchanged: **734** instr/write (N=1000 740,036; N=2000 1,474,036). The port call adds about 134 over no-time. (Renode, high)
- [V] -O2, same with our stub's `Fw::Time(TB_NONE,0,0)` construction: 903 (see -O2 results). The stub construction adds about 169. So 903 is inflated by our stub, not by the framework. (Renode, high)
- [U] The issue's 817 is a different app and time source; not reproduced. 734 (time port, no stub construction) is below 817, consistent with cycles ≥ instructions on a single-issue Cortex-M4 (architecture reasoning, Opus 5.5 at about 85%). Not measured on hardware.
- For comparisons with the issue, use 600 (no time) and 734 (time port), not 903 or 940, which include our stub's Fw::Time construction.
- Model: Haiku 5.5 (work); Opus 5.5 (decision check).

## Reproduction of the #5572 rise (pass 6; Opus pick D: run the harness on both commits at both levels; CI wiring not started)
Harness: no-time topology (`scratchpad\topo`), Fw objects from each commit, same flags. Per write = (N2000 − N1000) / 1000.
- [V] 1031e28b1d (before): **408** instr/write at -O2, **413** at -Os. (Renode, high)
- [V] d739002 (regressed): **600** at -O2, **605** at -Os. (Renode, high)
- [V] Rise: **+192** at -O2 (+47%) and **+192** at -Os (+46%). Issue table, -Os cycles: 483 → 612 (+129, +27%). First report: 595 → 817 (+222, +37%). Our +192 falls inside that range. Direction and rough size reproduced. (high for instruction counts; medium for the cycle comparison)
- [U] Caveats: instructions, not cycles. Flash wait states and bus stalls are not modelled. Both commits' Fw code is built against the same generated harness code (from d739002 FPP), which may bias the 1031e28b1d number.
- [V] Build note: 1031e28b1d needs `Fw/Tlm/TlmBuffer.cpp` in the object list (it is out-of-line there; the first build failed to link without it).
- CI wiring and repo push: not started (needs your OK).

## Full F401 image, -O2 (pass 6; Opus picks D, then B; time path is shim-based)
Build: STM32CubeF4 submodules fetched (approved). Our glue: HSI 16 MHz (no PLL), TIM2 at 1 MHz from fprime-stm32 `tim2_clock.cpp`, F401 linker script, CMSIS startup. fprime-stm32 F4 RawTime delegate patched to d739002's `getDelegate` signature (Opus B). d739002 Fw objects. Topology: harness plus a time provider reading `Os::RawTime`. Not included: rate-group driver, UART/GDS, PLL clock, real board.
- [V] Per write: N=1000 1,161,456; N=2000 2,315,872; N=3000 3,470,289. Deltas 1,154,416 and 1,154,417, so linear within ±1. **1154.4 instr/write.** (Renode, high)
- [V] Fixed (startup, HAL init, TIM2 init, topology static init): **7,040 instr**. (Renode, high)
- [U] Time path is shim-based: our RawTime adapter, and HSI with no PLL. Real TIM2 code is used, but counts could differ on a real PLL clock.
- [U] Compared with the stub series (-O2): time port with no stub construction 734; stub `Fw::Time` construction 903. The full-image 1154 sits about 250 above the stub, plausibly from the real RawTime path (now, interval, `Fw::Time`). Attribution not measured.
- No cycles. Files: `scratchpad\full\` (glue, fprime-f4 shim, topo_full, obj).
- Model: Haiku 5.5 (work); Opus 5.5 (picks D, B).

## Full F401 image with rate group, -O2 (pass 6)
Added to the full image: `Svc.RateGroupDriver` (one divider, every cycle), `Svc.PassiveRateGroup` (one member), both from d739002 source; FPP generated from d739002 (`fpp-to-cpp`, JRE on PATH); harness now drives cycles through the rate group, so each cycle = dispatch + one telemetry write + rate-group telemetry + time reads. Time path still shim-based.
- [V] Per cycle: N=1000 4,429,098; N=2000 8,846,690; N=3000 13,264,282. Deltas 4,417,592 and 4,417,592 (exact). **4417.6 instr/cycle.** (Renode, high)
- [V] Fixed: **11,506 instr**. (Renode, high)
- [U] Not attributed: the rate group adds about 3,260 instr per cycle on top of the 1154 per write measured without it. Breakdown (dispatch vs rate-group telemetry vs time reads) not measured.
- [V] Two configuration asserts had to be satisfied: `RateGroupDriver::configure` and `PassiveRateGroup::configure` (called in main). Without them the image halts in `Fw::SwAssert`.
- Files: `scratchpad\full\rg_stage` (generated), `topo_rg`, `main_rg.cpp`, `obj_rg`.

## Commit diff on the full F401 image, -O2 (pass 6; Opus pick C: rebuild both commits and diff)
Each commit regenerated its own FPP (`fpp-to-cpp`, 3.3.0a13) and used its own Fw, Svc, and Os RawTime sources. HAL, glue, shim time path, and harness code are identical. Renode instructions.
- [V] No rate group, per write. 1031e28b1d: N=1000 969,392; N=2000 1,931,736; N=3000 2,894,081 → **962.3**, fixed 7,048. d739002: **1154.4**, fixed 7,040 (earlier run). **d739002 − 1031e28b1d = +192.1 per write.** (Renode, high; linear ±1)
- [V] With rate group, per cycle. 1031e28b1d: N=1000 3,665,254; N=2000 7,319,574; N=3000 10,973,886 → **3654.3**, fixed 10,934. d739002: **4417.6**, fixed 11,506. **d739002 − 1031e28b1d = +763.3 per cycle** (about +21%). (Renode, high; linear ±8)
- [V] The rate group amplifies the commit delta: about 4× the standalone +192. Read: the regression grows when the rate group runs.
- [V] Breakdown, drive-only variant (dividers all zero, so the rate group never calls its member): **143.05 per cycle at both commits** (delta 0). Fixed 9,396 (d739002) and 9,208 (1031e28b1d). (Renode, high)
- [E] Estimated split of the per-cycle delta (member write taken from the no-rate-group image, rate-group own cost as the residual):
  - drive path: Δ 0
  - member write (`tlmWrite` with `Fw::Time()`): Δ +192
  - rate group own (dispatch, time reads, rate-group telemetry): Δ ≈ +571 (residual)
  - total Δ +763
- [V] Telemetry variant T1 (rate group's `Tlm` port unconnected; member still called). Per cycle: d739002 **2320.8** (fixed 9,418); 1031e28b1d **1941.7** (fixed 9,230). Telemetry emission costs d739002 **2096.8** and 1031e28b1d **1712.6** per cycle. (Renode, high)
- [V] T2 (also `Time` unconnected) gives identical counts to T1. The generated telemetry path returns before fetching time when the port is unconnected, so time reads inside telemetry cannot be split from emission with port connections alone. Telemetry includes its time fetch.
- [E] Split of the +763 per cycle (d739002 − 1031e28b1d). Member write and drive from the earlier breakdown; core is T1 minus drive minus write (write estimated from no-rate-group image):
  - drive: Δ 0
  - member write: Δ +192
  - rate-group core (dispatch, RawTime reads, bookkeeping): Δ ≈ +187
  - rate-group telemetry (emission, time fetch, formatting, sink): Δ ≈ +384
  - total Δ +763 (sum checks out to 763.2)
- [E] Absolute per cycle, d739002 / 1031e28b1d: drive 143 / 143; write 1154 / 962; core ≈ 1023 / 836; telemetry 2097 / 1713.
- [U] Caveats: instruction counts, not cycles; wait states and cache effects not modelled. Time path is our shim for both commits. -O2 only.
- Files: `scratchpad\full\pw1031_stage`, `obj_1031pw`, `rg1031_stage`, `obj_1031rg`.
- Model: Haiku 5.5 (work); Opus 5.5 (pick C).

## Remaining checks at -O3 (pass 6; Opus order: 1 NDEBUG, 2 per-write mismatch, 3 split)
- [V] **-DNDEBUG has no effect.** No `NDEBUG` reference in fprime `Fw`, `Os`, `Svc` or `default`. No-time topology at -O3 with and without it is identical (d739 590; 1031 398). (grep + Renode, high)
- [V] **Asserts are controlled by `FW_ASSERT_LEVEL`, not NDEBUG.** Default is `FW_FILENAME_ASSERT` (asserts on) in `default/config/FpConfig.h`. Built with `FW_NO_ASSERT`, -O3 no-time: d739 **550** per write, 1031 **358**; delta still +192. Asserts cost about 40 instructions per write at -O3. Flight may differ: **question for you**.
- [V] Clean rebuild (all Fw compiled at each level, asserts on) gives the same per-write counts: d739 1154.4 at both levels; 1031 962.3 at both (Renode, high). Fixed overhead differs by 4 instructions (d739 7,040 vs 7,036; 1031 7,048 vs 7,044). Root cause not found. Image text size differs (1031: -O2 52,328 B, -O3 58,008 B), so code is larger at -O3 while the counted path length is the same (unverified why).
- [V] Disassembly (1031, per-write): at -O2 `tlmWrite` is a separate function (88 B) called from `tlmWrite_Chan`; at -O3 it is inlined into `tlmWrite_Chan` (61 instr vs 37 static). Other hot-path functions are the same size at both levels (Tlm_out, TlmIn_handlerBase, SinkComp::TlmIn_handler, TimeGet_handler, Fw::Time copy, TlmBuffer ctor). The one-fewer-call at -O3 is probably balanced by extra checks; not proven without a dynamic trace (unverified).
- [V] **Split at -O3 (Release, no-NDEBUG, asserts on)**, per cycle:
  - drive: d739 138.0; 1031 138.0 (Δ 0)
  - member write (from the no-rate-group -O3 image): d739 1154.4; 1031 962.3 (Δ +192.1)
  - rate-group core (dispatch, RawTime reads, bookkeeping), estimate = telemetry-off minus drive minus write: d739 1046.4; 1031 845.4 (Δ +201.0)
  - rate-group telemetry (full minus telemetry-off): d739 2096.8; 1031 1712.6 (Δ +384.1)
  - total Δ +777.2 (matches +777.3)
- [U] Caveat for both controlled -O2 and -O3 runs: `pcb.o`, `objbase.o` and `assert_stub.o` have no source in the tree and were copied from the -O3 asserts-on build. Their effect on the -O2/-O3 match is not checked.
- Model: Haiku 5.5 (work); Opus 5.5 (order check).

## -O3 full image, flight headline (pass 6; user confirmed flight = Release, -O3)
Full F401 image rebuilt at -O3 for both commits, all objects at -O3 (Fw from each commit's -O3 build; HAL and glue at -O3). Renode instructions. Note: the Release preset also defines `-DNDEBUG`, which these builds do not; not yet measured.
- [V] No rate group, per write: d739002 **1154.4**; 1031e28b1d **962.3**. **Delta +192.1.** (Renode, high; linear ±1)
- [V] With rate group, per cycle: d739002 **4435.6**; 1031e28b1d **3658.3**. **Delta +777.3.** (Renode, high; linear ±8)
- [V] Fixed: d739002 7,036 / 10,323 (write / cycle); 1031e28b1d 7,044 / 10,017.
- [V] The per-write numbers match the -O2 run (1154.4 and 962.3); confirmed on a clean rebuild (see the -O2/-O3 line above). Not root-caused.
- [V] Per-cycle delta at -O3 is +777 (vs +763 at -O2). Split not yet redone at -O3.
- Files: `scratchpad\full\o3build.sh`, `o3_d739_rg`, `o3_d739_pw`, `o3_1031_rg`, `o3_1031_pw`.

## -O0 unoptimized reference build (pass 6; Opus pick C)
Flight build type unconfirmed. The only cross-built STM32 cache here (renode-fprime-hil reference, stm32h7) has empty `CMAKE_BUILD_TYPE` and no `-O` flag, so it is unoptimized. Headline stays -O2 until the user confirms; -O0 is a reference only.
- [V] No-time topology, per write (Renode, high):
  - d739002: N=1000 1,541,089; N=2000 3,076,089 → **1535**, fixed 6,089.
  - 1031e28b1d: N=1000 1,336,089; N=2000 2,666,089 → **1330**, fixed 6,089.
  - **Delta d739002 − 1031e28b1d = +205** (vs +192 at -O2).
- [U] At -O0 nothing is inlined, so call-overhead costs are inflated. Here the delta is close to -O2's, but the -O0 vs -O2 gap (1535 vs 600 at d739002) is not a cycle figure.
- Model: Haiku 5.5 (work); Opus 5.5 (pick C).
- Model: Haiku 5.5 (work).

## -O3 check (pass 6; flight candidate: Release preset in Desktop\fprime\CMakePresets.json; stock CMake Release = -O3)
No-time topology, same method. Per write = (N2000 − N1000) / 1000.
- [V] d739002 (regressed): N=1000 595,103; N=2000 1,185,103 → **590 instr/write**; fixed 5,103. (Renode, high)
- [V] 1031e28b1d (before): N=1000 403,103; N=2000 801,103 → **398 instr/write**; fixed 5,103. (Renode, high)
- [V] Rise at -O3: **+192** (+48%), same as -O2 and -Os.
- Full table (no-time, per write): -O2 600 / 408; -Os 605 / 413; -O3 590 / 398. The +192 holds at all three levels.
- [U] Whether the flight build is -O3 is unconfirmed. The preset is a native host build, not the Cortex-M target.
- [V] Portable script (`scratchpad\cyclebench-repo\cyclebench.sh`) reproduces the d739002 -O2 no-time result exactly: 600 per write, fixed 5,103. (Renode, high)
- [U] CI workflow draft (`.github\workflows\cyclebench.yml`): not run, not pushed. Renode URL and toolchain package unverified. Repo not created.
- [V] PLL clock would not change instruction counts (reasoning only, not measured here). Rate-group driver is not in the full image yet.
- Model: Haiku 5.5 (work).
- Model: Haiku 5.5 (work); Opus 5.5 (decision check).

## Full image, asserts off (-O3; -DFW_ASSERT_LEVEL=1 = FW_NO_ASSERT, same value as ci profile "no-assert")
Flight assert setting is not in the repo: fprime default is asserts on (`default/config/FpConfig.h`); `reference\build-fprime-automatic-stm32h7` sets no FW_ASSERT_LEVEL. User answered 2026-11-09: flight keeps asserts on (the user's word; the repo has no flight profile). Headline: asserts on. Renode, two points (N=1000, N=2000); per unit = (N2000 − N1000) / 1000.
- [V] Per write, no rate group: d739002 **1041.4** (fixed 6,628); 1031e28b1d **849.3** (fixed 6,636). **Delta +192.1** (same as asserts on). Asserts cost 113.0 per write at each commit. (Renode, high)
- [V] Per cycle, full rate-group image: d739002 **3936.4** (fixed 10,483); 1031e28b1d **3171.1** (fixed 9,231). **Delta +765.3** (asserts on: +777.3, difference 12). Asserts cost 499.2 (d739002) and 487.2 (1031e28b1d) per cycle. (Renode, high)
- [U] pcb.o, objbase.o and assert_stub.o have no source in the tree; reused from the asserts-on -O3 build. Effect not checked.
- [V] d739002 per-write build: DpRequestPortAc.cpp fails a static_assert (PlatformSizeType vs PlatformSignedSizeType), same as the asserts-on build. Link succeeds, so no unresolved reference to it.
- [V] Relative per-write rise: +22.6% asserts off (192.1 / 849.3) vs +20.0% asserts on (192.1 / 962.3). The percentage is higher with asserts off, so state both.
- [U] Two N points only; the asserts-on runs used three. Linearity not re-checked.

## Cycle estimator (pass 7; Renode execution trace + per-instruction cost table)
- [V] Renode `CreateExecutionTracing ... Disassembly` writes one line per executed instruction. Line count matches ExecutedInstructions within 4. Script: `scratchpad\cyc_est\estimate.py`.
- [V] Cost table from ARM DDI0439B Table 3-1 (PDF text, `scratchpad\cyc_est\trm.txt`): ALU/MUL/MLA 1; LDR/STR 2b; LDRD/STRD 1+N; LDM/STM/PUSH/POP 1+N (+P if PC); B/BL/BX 1+P; B<cc> and CBZ/CBNZ 1+P taken, 1 not taken; IT 1; SDIV/UDIV 2–12 (midpoint 6 used). P is 1–3 in the TRM; midpoint 2 used [U]. MLS value is ambiguous in the text extraction (2 used) [U].
- [E] Estimated cycles per write with the TRM table: d739002 2415.9; 1031e28b1d 2032.7; delta +383.2 (+18.9%). Instruction delta +192.1. (Earlier memory-table run: +321.2. Its low/high variants are superseded.)
- [E] Delta breakdown (cycles/write): LDRD/STRD +186 (d739 81 per write vs 19); conditional branches +106 (100 vs 60 per write); ALU +89; stores +8; LDM/LDR/STM about −5 combined. Cause of the LDRD/STRD count difference not checked [U].
- [E] Pipeline refill sweep (P = 1 / 2 / 3), delta cycles per write: +351.1 (19.5%) / +383.2 (18.9%) / +415.2 (18.3%). Instruction delta +192.1 in all cases.
- [V] Opus 5.5 review of the cycle analysis and the draft #5572 comment (not posted). Checked: memset is called once per write from tlmWrite_Chan, 199 instructions per write, all STRD (62), no LDRD, clearing 506 bytes (`mov.w r2, #506`); 1031e28b1d never calls memset. The other code nets about -7 instructions per write. The issue's build flags use -Os; this run is -O3. The +383 estimate is larger than the issue's +129/+222, so the comment must say so.
- [V] Posted to nasa/fprime #5572 (closed issue) as a comment, text in `scratchpad\cyc_est\comment_5572.md`: https://github.com/nasa/fprime/issues/5572#issuecomment-6760319745
- [E] Per-function split (P=2, per write): `memset` +403 cycles in d739002, 0 in 1031e28b1d (62 LDRD/STRD per write in d739002). Other functions net −20 (`tlmWrite_Chan` +14, the Sink and Tlm_out handlers +80 combined, offset by unlisted negatives). Link from memset to TlmBuffer zero-init is now checked: trace shows all 1000 memset calls come from `tlmWrite_Chan` (generated `Fw::TlmBuffer _tlmBuff;`). d739002 `LinearBufferTemplate` declares `m_bufferData[MaxSize] = {}` (zero-init); 1031e28b1d `TlmBuffer` declares `m_bufferData[...]` with no initializer (`fprime-src` and `cyc\fprime-1031` source, high).
- [U] Not modelled: flash wait states, bus stalls, load-use stalls. Estimate only, not a measurement.
- Model: Haiku 5.5 (work).

## Pass 8 (2026-11-10): flash wait states, path fix, rerun test
Note: `scratchpad\...` paths in earlier passes are historical. Current inputs: `artifacts/` (ELFs) and `traces/` (git-ignored traces). See README.
- [V] Estimator flash model (`estimator/estimate.py`: `--hclk-mhz`, `--flash-mode none|line|cache`). At 16 MHz (0 WS) it reproduces the baseline: d739002 2415.9, 1031e28b1d 2032.7 cycles/write. (Estimator run, high)
- [V] Wait-state bands: RM0368 Table 6 (section 3.4.1, p.46). Rev 5 (2018) and Rev 4 (2015) text agree (saved PDFs, `pdftotext`, high). 2.7–3.6 V: 0 WS for 0 < HCLK ≤ 30, 1 WS for 30 < HCLK ≤ 60, 2 WS for 60 < HCLK ≤ 84. The 2.4–2.7, 2.1–2.4 and 1.71–2.1 V columns are in the estimator (`--vdd`).
- [V] Caches (RM0368 Rev 5, section 3.4.2): I-Code cache 64 lines of 128 bits, enabled by ICEN, LRU replacement; D-Code cache 8 lines of 128 bits, used for literal pools. Hit timing is "no delay" per the manual. The prefetch-buffer details are [U].
- Sweep, cycles per write, d739002 vs 1031e28b1d (core delta at 16 MHz: +383.2):
  - 60 MHz, no accelerator: 3639.4 vs 3065.2 (+574)
  - 84 MHz, no accelerator (upper bound): 4862.9 vs 4097.6 (+765)
  - 84 MHz, line buffer: 3348.5 vs 2875.2 (+473)
  - 84 MHz, 64-line I-cache + 8-line D-cache (cache mode): 2848.3 vs 2433.1 (+415). Before the D-cache: 2922.4 vs 2505.2 (+417).
  - Flash rows [U] (cache timing). Literal-pool loads: WS each in the none and line modes (138.2 per write at 84 MHz); the 8-line D-cache in cache mode lowers this to 64.1 per write [U].
  - Verified after the D-cache change: 16 MHz baseline (d739002 2415.9); WS table unit checks pass. Only the cache rows were re-run; none and line rows follow from the same code path and were not re-run.
- [V] `.resc` paths: relative `@` paths fail to create trace files (Renode 1.16.0), from both cwd = repo root and cwd = `results/`. `$ORIGIN/../...` works. Opus 5.5 subagent proposed `$ORIGIN` (probe-tested by the subagent); I confirmed it by rerun. (Renode, high)
- [V] Rerun of `results/trace1000.resc`: no errors; ExecutedInstructions 0x11B8EC = 1,161,452; `traces/trace_1000.txt` md5 identical to the original (ea4c88ec…). (Renode + md5, high)
- [V] ELFs in `artifacts/` match the originals by md5 (d739 and 1031, img_1000 and img_2000). (md5, high)
- [V] The other three `.resc` files reran with no errors (Renode exit 0). Each regenerated trace is md5-identical to its original (`trace_1031_1000`, `trace_1031_2000`, `trace_d739_2000`; `trace_1000` above). (Renode + md5, high)
- [U] Paths with spaces and Linux/macOS are untested.
- Not done: no commit or push; no CI; no hardware. Flight HCLK is unknown: the answer changes which flash row applies.
- Model: Haiku 5.5 (work); Opus 5.5 (path-form decision).
