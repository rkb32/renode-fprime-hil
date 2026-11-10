import estimate as e

def delta(p):
    e.P = p
    _, a1, _, _ = e.run('trace_1000.txt')
    _, a2, _, _ = e.run('trace_d739_2000.txt')
    _, b1, _, _ = e.run('trace_1031_1000.txt')
    _, b2, _, _ = e.run('trace_1031_2000.txt')
    d739 = (a2 - a1) / 1000
    x1031 = (b2 - b1) / 1000
    print(f'P={p}  d739 {d739:8.1f}  1031 {x1031:8.1f}  delta {d739 - x1031:7.1f}  ({(d739 / x1031 - 1) * 100:4.1f}%)', flush=True)

for p in (1, 3):
    delta(p)
