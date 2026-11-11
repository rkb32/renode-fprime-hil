#!/usr/bin/env python3
"""Estimate Cortex-M4 cycles from a Renode Disassembly execution trace.

ESTIMATE, NOT A MEASUREMENT. Core costs follow ARM DDI0439B Table 3-1 (text
extracted from the PDF; see trm.txt). Where the table gives a range or
symbol (P = pipeline refill, 1..3), a midpoint is used and tagged [U].
Bus stalls and load-use stalls are not modelled.

Flash wait states (optional; default 16 MHz gives 0 WS in every supply range):
  Extra cycles are charged for instruction fetches from flash and for
  PC-relative literal loads from flash. WS_BANDS is RM0368 Table 6 (Rev 4 and
  Rev 5 agree). Other data accesses are not modelled: the trace has no data
  addresses.

usage:
  estimate.py [--hclk-mhz F] [--vdd RANGE] [--flash-mode none|line|cache] <trace.txt> [...]
  estimate.py [same flags] --pair <t_low.txt> <t_high.txt> <n_low> <n_high>
                  # per-unit cost = delta cycles / delta n
  RANGE is one of 2.7-3.6 (default), 2.4-2.7, 2.1-2.4, 1.71-2.1 (Table 6 columns).
"""
import argparse
import re
import sys
from collections import Counter, OrderedDict

LINE = re.compile(r'^0x([0-9A-Fa-f]+):\s+([0-9A-Fa-f]+)\s+(\S+)\s*(.*?)\s*(\[.*\])?\s*$')
LIT_RE = re.compile(r'\[pc,\s*#(-?\d+)\]', re.IGNORECASE)
CONDS = {'eq', 'ne', 'cs', 'hs', 'cc', 'lo', 'mi', 'pl', 'vs', 'vc',
         'hi', 'ls', 'ge', 'lt', 'gt', 'le'}
IT_RE = re.compile(r'^it[te]*$')

P = 2  # pipeline refill, TRM gives 1..3; midpoint [U]
COST = {
    'alu': 1,              # TRM: moves, ALU, compares, extend, bit field: 1
    'mul': 1,              # TRM: MUL, MLA, SMULL/UMULL, SMLAL/UMLAL: 1
    'mls': 2,              # TRM: MLS: 2 (extraction ambiguous, see trm.txt) [U]
    'div': 6,              # TRM footnote a: SDIV/UDIV 2..12 early termination; midpoint [U]
    'load': 2,             # TRM: LDR/LDRH/LDRB/LDRSx: 2 (footnote b may pipeline: 2 is an upper bound)
    'store': 2,            # TRM: STR/STRH/STRB: 2 (same footnote b)
    'dbl': 3,              # TRM: LDRD/STRD: 1+N with N=2 registers
    'it': 1,               # TRM: IT: 1 (folding to 0 cycles not applied)
    'vfp': 1,              # not in Table 3-1; assumed 1 [U]
}

# Flash wait states vs HCLK, STM32F401 RM0368 Table 6 (section 3.4.1).
# Verified from the Rev 5 (2018) and Rev 4 (2015) PDF text, both saved locally.
# Each entry: (max HCLK in MHz for this WS, WS). Limits are inclusive.
WS_BANDS = {
    '2.7-3.6':  ((30, 0), (60, 1), (84, 2)),
    '2.4-2.7':  ((24, 0), (48, 1), (72, 2), (84, 3)),
    '2.1-2.4':  ((18, 0), (36, 1), (54, 2), (72, 3), (84, 4)),
    '1.71-2.1': ((16, 0), (32, 1), (48, 2), (64, 3), (80, 4), (84, 5)),
}
FLASH_LO, FLASH_HI = 0x08000000, 0x20000000   # flash alias region [U: F401 flash at 0x08000000]
LINE_BYTES = 16     # 128-bit line: RM0368 3.4.2 [V]
ART_LINES = 64      # I-Code cache: 64 lines of 128 bits, enabled by ICEN [V, RM0368 3.4.2]
DCODE_LINES = 8     # D-Code cache: 8 lines of 128 bits, literal pools [V, RM0368 3.4.2]


def ws_for(hclk_mhz, vdd):
    for limit, ws in WS_BANDS[vdd]:
        if hclk_mhz <= limit:
            return ws
    raise SystemExit(f'HCLK {hclk_mhz} MHz is above 84 MHz (RM0368 Table 6 top band)')


class FlashModel:
    """Extra cycles for flash reads.

    Instruction fetch, by --flash-mode:
    none  - every fetch from flash waits WS (no accelerator; upper bound) [U]
    line  - a fetch waits WS only when it enters a new 16-byte line (prefetch line only) [U]
    cache - as 'line', plus a 64-line LRU for the I-Code cache; hits wait 0 [U timing]
    Literal loads (PC-relative): 'cache' uses an 8-line LRU for the D-Code cache;
    other modes charge WS on every literal load [U].
    """

    def __init__(self, ws, mode):
        self.ws = ws
        self.mode = mode
        self.last = None
        self.lru = OrderedDict()
        self.dlru = OrderedDict()
        self.extra = 0
        self.lit_extra = 0
        self.misses = 0

    def literal(self, addr):
        if not self.ws or not (FLASH_LO <= addr < FLASH_HI):
            return
        line = addr // LINE_BYTES
        if self.mode == 'cache':
            if line in self.dlru:
                self.dlru.move_to_end(line)
                return
            self.dlru[line] = None
            if len(self.dlru) > DCODE_LINES:
                self.dlru.popitem(last=False)
        self.lit_extra += self.ws

    def fetch(self, pc):
        if not self.ws or not (FLASH_LO <= pc < FLASH_HI):
            return
        line = pc // LINE_BYTES
        if self.mode == 'none':
            miss = True
        elif self.mode == 'line':
            miss = (line != self.last)
        else:  # cache
            miss = line not in self.lru
            if miss:
                self.lru[line] = None
                if len(self.lru) > ART_LINES:
                    self.lru.popitem(last=False)
            else:
                self.lru.move_to_end(line)
        self.last = line
        if miss:
            self.extra += self.ws
            self.misses += 1


def norm(mn):
    for suf in ('.w', '.n'):
        if mn.endswith(suf):
            mn = mn[:-len(suf)]
    return mn


def reg_num(name):
    name = name.strip().lower()
    special = {'sp': 13, 'lr': 14, 'pc': 15}
    if name in special:
        return special[name]
    return int(name[1:])


def reg_list(ops):
    """Return (count, includes_pc) for a {..} register list in operands."""
    m = re.search(r'\{([^}]*)\}', ops)
    if not m:
        return 0, False
    n, has_pc = 0, False
    for part in m.group(1).split(','):
        part = part.strip().lower()
        if not part:
            continue
        if '-' in part:
            a, b = part.split('-', 1)
            n += reg_num(b) - reg_num(a) + 1
            if reg_num(b) == 15:
                has_pc = True
        else:
            n += 1
            if reg_num(part) == 15:
                has_pc = True
    return n, has_pc


def classify(mn):
    if mn in ('ldr', 'ldrb', 'ldrh', 'ldrsb', 'ldrsh', 'ldrt', 'ldrbt', 'ldrht', 'ldrsht', 'ldrsbt'):
        return 'load'
    if mn in ('str', 'strb', 'strh', 'strsb', 'strsh', 'strt', 'strbt', 'strht', 'strsht', 'strsbt'):
        return 'store'
    if mn in ('ldrd', 'strd'):
        return 'dbl'
    if mn in ('ldm', 'ldmia', 'ldmdb', 'ldmfd', 'pop'):
        return 'ldm'
    if mn in ('stm', 'stmia', 'stmdb', 'stmfd', 'push'):
        return 'stm'
    if mn in ('udiv', 'sdiv'):
        return 'div'
    if mn in ('mls',):
        return 'mls'
    if mn in ('mul', 'muls', 'mla', 'mlas', 'smull', 'umull', 'smlal', 'umlal'):
        return 'mul'
    if mn in ('b', 'bl', 'bx', 'blx'):
        return 'branch_uncond'
    if mn.startswith('b') and mn[1:] in CONDS:
        return 'branch_cond'
    if mn in ('cbz', 'cbnz'):
        return 'branch_cond'
    if IT_RE.match(mn):
        return 'it'
    if mn.startswith('v'):
        return 'vfp'
    return 'alu'


def instr_cycles(cls, mn, ops, taken):
    if cls == 'branch_uncond':
        return 1 + P                       # TRM: B, BL, BX, BLX = 1+P
    if cls == 'branch_cond':
        if taken:
            return COST.get('branch_taken', 1 + P)     # TRM: B<cc>, CBZ, CBNZ: 1 or 1+P
        return COST.get('branch_not_taken', 1)
    if cls in ('ldm', 'stm'):
        n, has_pc = reg_list(ops)
        extra = P if (cls == 'ldm' and has_pc) else 0   # TRM: LDM/POP with PC = 1+N+P
        return 1 + n + extra
    return COST[cls]


def parse(path):
    """Yield (pc, size, mn, ops, lit) per executed instruction, in order.

    lit is the flash/SRAM address of a PC-relative literal load, else None.
    """
    with open(path, 'r', errors='replace') as f:
        for line in f:
            m = LINE.match(line)
            if not m:
                continue
            pc = int(m.group(1), 16)
            size = 4 if len(m.group(2)) == 8 else 2
            mn = norm(m.group(3).lower())
            ops = m.group(4) or ''
            lit = None
            if mn.startswith('ldr'):
                lm = LIT_RE.search(line)
                if lm:
                    lit = ((pc + 4) & ~3) + int(lm.group(1))   # Thumb PC = addr+4, word-aligned
            yield pc, size, mn, ops, lit


def run(path, ws=0, mode='none'):
    total = 0
    count = 0
    by_cls_cycles = Counter()
    by_cls_count = Counter()
    fm = FlashModel(ws, mode)
    prev = None
    for pc, size, mn, ops, lit in parse(path):
        fm.fetch(pc)
        if lit is not None:
            fm.literal(lit)
        if prev is not None:
            ppc, psize, pmn, pops, pcls = prev
            taken = (pc != ppc + psize)
            c = instr_cycles(pcls, pmn, pops, taken)
            total += c
            by_cls_cycles[pcls] += c
            by_cls_count[pcls] += 1
            count += 1
        prev = (pc, size, mn, ops, classify(mn))
    if prev is not None:  # last instruction: treat as not taken
        ppc, psize, pmn, pops, pcls = prev
        c = instr_cycles(pcls, pmn, pops, False)
        total += c
        by_cls_cycles[pcls] += c
        by_cls_count[pcls] += 1
        count += 1
    return {'count': count, 'core': total, 'flash': fm.extra, 'lit': fm.lit_extra,
            'misses': fm.misses, 'total': total + fm.extra + fm.lit_extra,
            'k': by_cls_count, 'y': by_cls_cycles}


def main(argv=None):
    ap = argparse.ArgumentParser(description='Estimate Cortex-M4 cycles from a Renode execution trace (estimate, not measured).')
    ap.add_argument('traces', nargs='*')
    ap.add_argument('--pair', nargs=4, metavar=('LOW', 'HIGH', 'NLOW', 'NHIGH'),
                    help='per-unit cost = (HIGH - LOW) / (NHIGH - NLOW)')
    ap.add_argument('--hclk-mhz', type=float, default=16.0,
                    help='CPU clock in MHz. Default 16 = HSI, as the full-image glue runs (0 WS).')
    ap.add_argument('--vdd', choices=tuple(WS_BANDS), default='2.7-3.6',
                    help='supply range in V, selects the RM0368 Table 6 column (default 2.7-3.6)')
    ap.add_argument('--flash-mode', choices=('none', 'line', 'cache'), default='none',
                    help='flash read model for wait states (see FlashModel)')
    a = ap.parse_args(argv[1:] if argv else None)
    ws = ws_for(a.hclk_mhz, a.vdd)
    print(f'# HCLK {a.hclk_mhz:g} MHz, VDD {a.vdd} V -> {ws} flash WS (RM0368 Table 6); flash mode {a.flash_mode}')

    if a.pair:
        lo, hi = a.pair[0], a.pair[1]
        nlo, nhi = int(a.pair[2]), int(a.pair[3])
        r1 = run(lo, ws, a.flash_mode)
        r2 = run(hi, ws, a.flash_mode)
        dn = nhi - nlo
        for label, r in ((lo, r1), (hi, r2)):
            print(f'{label}: instr {r["count"]}, core {r["core"]}, flash {r["flash"]}, '
                  f'literal {r["lit"]}, est cycles {r["total"]}')
        print(f'per unit (n {nlo}->{nhi}): instr {(r2["count"] - r1["count"]) / dn:.1f}, '
              f'est cycles {(r2["total"] - r1["total"]) / dn:.1f} '
              f'(core {(r2["core"] - r1["core"]) / dn:.1f}, '
              f'flash {(r2["flash"] - r1["flash"]) / dn:.1f}, '
              f'literal {(r2["lit"] - r1["lit"]) / dn:.1f})')
        for cls in sorted(set(r1['y']) | set(r2['y'])):
            print(f'  {cls:16s} est cycles/unit {(r2["y"][cls] - r1["y"][cls]) / dn:9.1f}  '
                  f'instr/unit {(r2["k"][cls] - r1["k"][cls]) / dn:7.1f}')
        return 0

    for path in a.traces:
        r = run(path, ws, a.flash_mode)
        print(f'{path}: instr {r["count"]}, est cycles {r["total"]} '
              f'(core {r["core"]}, flash {r["flash"]}, literal {r["lit"]}, '
              f'flash misses {r["misses"]}), est CPI {r["total"] / r["count"]:.3f}')
        for cls in sorted(r['y']):
            print(f'  {cls:16s} cycles {r["y"][cls]:10d}  instr {r["k"][cls]:9d}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
