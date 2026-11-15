Independent check, Renode on an STM32F401 full image (Cortex-M4, -O3, direct port calls). These are instruction counts, not cycles.

- d739002 vs 1031e28b1d: +192 instructions per tlmWrite (1154.4 vs 962.3). "Per tlmWrite" is per harness loop iteration, which includes the time read and the sink handler.
- Execution trace: at d739002, `tlmWrite_Chan` calls `memset` once per write, clearing 506 bytes: 199 instructions, all STRD. At 1031e28b1d, `memset` is never called. That `memset` alone is about the whole +192 instruction delta; everything else nets to about -7.
- Source matches: `LinearBufferTemplate` declares `m_bufferData[MaxSize] = {}` at d739002; the 1031e28b1d `TlmBuffer` has no initializer.
- Estimated cycles from the Arm Cortex-M4 timing table, not measured: about +383 per write. That is larger than the +129 and +222 reported in this issue, and this build is -O3 where the report used -Os. The F401 is a different chip from the VA416x0, so these are not the reported numbers.
