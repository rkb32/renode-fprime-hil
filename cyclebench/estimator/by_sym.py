import re, sys
from collections import Counter
import estimate as e
LINE = e.LINE
def sym_of(line):
    m = re.search(r'\[([^\]]*)\]\s*$', line)
    return (m.group(1).split(' (')[0].split('+')[0]) if m else '?'
def run(path):
    cyc = Counter(); prev = None
    with open(path, errors='replace') as f:
        for line in f:
            m = LINE.match(line)
            if not m: continue
            pc = int(m.group(1), 16); size = 4 if len(m.group(2)) == 8 else 2
            mn = e.norm(m.group(3).lower()); ops = m.group(4) or ''
            if prev is not None:
                ppc, psize, pmn, pops, pcls, psym = prev
                c = e.instr_cycles(pcls, pmn, pops, pc != ppc + psize)
                cyc[psym] += c
            prev = (pc, size, mn, ops, e.classify(mn), sym_of(line))
    return cyc
a = run('trace_1000.txt'); b = run('trace_d739_2000.txt')
c = run('trace_1031_1000.txt'); d = run('trace_1031_2000.txt')
keys = set(a) | set(b) | set(c) | set(d)
rows = []
for k in keys:
    dd = ((b[k] - a[k]) - (d[k] - c[k])) / 1000  # not used; per-run deltas below
rows = []
for k in keys:
    d739 = (b[k] - a[k]) / 1000
    x1031 = (d[k] - c[k]) / 1000
    rows.append((d739 - x1031, k, d739, x1031))
rows.sort(reverse=True)
for diff, k, d739, x1031 in rows[:8]:
    print(f'{diff:8.1f}  d739 {d739:8.1f}  1031 {x1031:8.1f}  {k}')
print('total delta', round(sum(r[0] for r in rows), 1))
