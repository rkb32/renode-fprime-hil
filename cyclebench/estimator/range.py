"""Per-write cycle delta (d739 minus 1031) as a low / base / high range.

ESTIMATE, NOT A MEASUREMENT. The range covers only the two inputs that the
ARM DDI0439B table gives as ranges:
  P (branch and LDM/POP pipeline refill): 1..3
  div (SDIV/UDIV early termination): 2..12
Everything else stays at estimate.py defaults. Load/store cost (2, footnote b)
and flash wait states are NOT varied here.

usage: run from the folder that holds the trace files (trace_1000.txt, ...)
  python range.py
"""
import estimate as e

FILES = ('trace_1000.txt', 'trace_d739_2000.txt', 'trace_1031_1000.txt', 'trace_1031_2000.txt')
WRITES = 1000  # writes between the 1000 and 2000 traces

SCEN = {
    'low':  {'P': 1, 'div': 2},
    'base': {'P': 2, 'div': 6},
    'high': {'P': 3, 'div': 12},
}


def delta_for(scen):
    saved_p, saved_div = e.P, e.COST['div']
    e.P, e.COST['div'] = scen['P'], scen['div']
    try:
        core = {f: e.run(f)['core'] for f in FILES}
    finally:
        e.P, e.COST['div'] = saved_p, saved_div
    d739 = (core[FILES[1]] - core[FILES[0]]) / WRITES
    x1031 = (core[FILES[3]] - core[FILES[2]]) / WRITES
    return d739, x1031, d739 - x1031


def main():
    deltas = {}
    for name, scen in SCEN.items():
        d739, x1031, delta = delta_for(scen)
        deltas[name] = delta
        print(f'{name:5s} d739 {d739:8.1f}  1031 {x1031:8.1f}  delta {delta:+8.1f}', flush=True)
    lo, hi = min(deltas.values()), max(deltas.values())
    print(f'range (cycles per write, core only): {lo:+.1f} .. {hi:+.1f}, base {deltas["base"]:+.1f}')


if __name__ == '__main__':
    main()
