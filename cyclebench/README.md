# fprime-cyclebench

Software-only cost study of F´ telemetry writes, tied to nasa/fprime #5572. Renode instruction counts plus an estimated Cortex-M4 cycle figure. No hardware measurements.

## Layout

- `PLAN-cyclebench.md`: results log, with [V] verified and [U] unverified tags.
- `estimator/`: Python estimator. Turns a Renode execution trace into instruction counts and estimated cycles, using ARM DDI0439B Table 3-1 costs.
- `results/`: sweep and per-function outputs, Renode `.resc` scripts, and trace logs.
- `posted/comment_5572.md`: exact text posted to https://github.com/nasa/fprime/issues/5572#issuecomment-6760319745
- `artifacts/`: full-image ELFs (commits d739002 and 1031e28b1d, -O3). Not in git.

## Rebuild

- Traces (about 600 MB in total) are not kept. Regenerate them into `traces/` (git-ignored) from the repo root:
  `Renode.exe --disable-xwt --console -e 'include @results/trace1000.resc'` (same form for the other `results/*.resc`).
- The `.resc` files use `$ORIGIN/../artifacts/...` and `$ORIGIN/../traces/...`. Relative paths without `$ORIGIN` fail to create trace files in Renode 1.16.0.
- Tested: all four `.resc` files rerun with no errors. Each regenerated trace is byte-identical to the original (md5 match).
- Estimator: `python estimator/estimate.py --pair <low.txt> <high.txt> <n_low> <n_high>`. Flags: `--hclk-mhz` (default 16, which is 0 WS in every supply range), `--vdd` (default 2.7-3.6), `--flash-mode none|line|cache`. Wait-state bands are RM0368 Table 6 (verified); cache timing is unverified.
- Paths with spaces in the repo path are untested.

## Status

- Cycle figures are estimates. No hardware board was used.
- Open items are in the plan file.
