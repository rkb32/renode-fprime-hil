import sys, estimate as e
variants = {
  'low':  {'branch_taken': 2, 'branch_not_taken': 1, 'load': 1, 'store': 1},
  'base': {},
  'high': {'branch_taken': 4, 'load': 2, 'store': 2, 'alu': 1},
}
a, b = 'trace_1000.txt', 'trace_d739_2000.txt'
c, d = 'trace_1031_1000.txt', 'trace_1031_2000.txt'
for name, over in variants.items():
    saved = dict(e.COST); e.COST.update(over)
    _, t1, _, _ = e.run(a); _, t2, _, _ = e.run(b)
    _, u1, _, _ = e.run(c); _, u2, _, _ = e.run(d)
    e.COST.clear(); e.COST.update(saved)
    d739 = (t2 - t1) / 1000; x1031 = (u2 - u1) / 1000
    print(f'{name:5s} d739 {d739:7.1f}  1031 {x1031:7.1f}  delta {d739 - x1031:6.1f}  ({(d739/x1031-1)*100:4.1f}%)')
