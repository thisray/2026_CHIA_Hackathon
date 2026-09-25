#!/usr/bin/env python3
"""Fanout / load structure of a mapped sky130 netlist, plus arrival profile.

Two complementary feedback channels for a successor rewrite:

1. ``fanout`` -- parses ``mapped.v`` and reports, per net, how many cell input
   pins it drives and which cell drives it. High-fanout nets driven by x1
   cells are the ones the area-oriented ``abc -liberty`` mapping leaves
   unbuffered, and they are what dominated the Round-1 critical path.

2. ``arrival`` -- parses the wide ``probe_sta.log`` and reports the worst
   arrival for every endpoint, so a successor can see whether the bottleneck
   sits in the syndrome tree (late ``syndrome_o[*]``) or in the correction
   decoder (``data_o[*]`` much later than the syndrome bits it consumes).
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

CELL_RE = re.compile(
    r"^\s*(sky130_fd_sc_hd__\w+)\s+(\S+)\s*\((?P<conns>[^;]*)\)\s*;", re.M | re.S
)
CONN_RE = re.compile(r"\.(\w+)\(([^)]*)\)")
# sky130 high-density cell output pin names.
OUT_PINS = {"X", "Y", "Q", "Q_N", "SUM", "COUT", "COUT_N", "HI", "LO"}


def parse_netlist(path: Path) -> dict:
    text = path.read_text(errors="replace")
    drivers: dict[str, tuple[str, str]] = {}
    loads: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    cell_count: Counter = Counter()

    for m in CELL_RE.finditer(text):
        cell, inst = m.group(1), m.group(2)
        cell_count[cell] += 1
        for pin, net in CONN_RE.findall(m.group("conns")):
            net = net.strip()
            if not net or net in ("1'b0", "1'b1"):
                continue
            if pin in OUT_PINS:
                drivers[net] = (cell, inst)
            else:
                loads[net].append((cell, inst, pin))

    records = []
    for net, ls in loads.items():
        drv = drivers.get(net)
        records.append(
            {
                "net": net,
                "fanout": len(ls),
                "driver_cell": drv[0] if drv else "PRIMARY_INPUT",
                "driver_inst": drv[1] if drv else None,
                "load_cells": dict(Counter(c for c, _, _ in ls)),
            }
        )
    records.sort(key=lambda r: -r["fanout"])
    return {
        "num_cells": sum(cell_count.values()),
        "cell_histogram": dict(cell_count.most_common(15)),
        "fanout_histogram": dict(
            sorted(Counter(r["fanout"] for r in records).items())
        ),
        "top_fanout_nets": records[:25],
        "max_fanout": records[0]["fanout"] if records else 0,
        # x1 drives on wide nets are the structural symptom the mapper will not
        # fix, because the frozen recipe gives abc no delay target.
        "weak_driven_wide_nets": [
            r for r in records
            if r["fanout"] >= 8 and r["driver_cell"].endswith(("_1", "_0"))
        ][:20],
    }


def parse_arrivals(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    endpoint = None
    for line in path.read_text(errors="replace").splitlines():
        m = re.match(r"^Endpoint:\s*(\S+)", line)
        if m:
            endpoint = m.group(1)
            continue
        m = re.match(r"^\s*([\d.]+)\s+data arrival time", line)
        if m and endpoint:
            out.append({"endpoint": endpoint, "arrival_ns": float(m.group(1))})
            endpoint = None
    out.sort(key=lambda r: -r["arrival_ns"])
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("case_dirs", nargs="+")
    ap.add_argument("--out", default=None)
    ap.add_argument("--top", type=int, default=10)
    args = ap.parse_args()

    allrec = {}
    for d in args.case_dirs:
        case = Path(d)
        rec: dict = {}
        mapped = case / "mapped.v"
        if mapped.exists():
            rec["netlist"] = parse_netlist(mapped)
        arrivals = parse_arrivals(case / "probe_sta.log")
        if arrivals:
            syn = [a for a in arrivals if a["endpoint"].startswith("syndrome_o")]
            dat = [a for a in arrivals if a["endpoint"].startswith("data_o")]
            flg = [a for a in arrivals
                   if a["endpoint"].endswith("error_o")]
            rec["arrival"] = {
                "worst_overall": arrivals[:args.top],
                "syndrome_latest": syn[:3],
                "syndrome_earliest": syn[-3:],
                "syndrome_spread_ns": (
                    round(syn[0]["arrival_ns"] - syn[-1]["arrival_ns"], 6) if syn else None
                ),
                "data_worst": dat[:3],
                "flag_worst": flg[:3],
                # How much time the correction decoder adds on top of the last
                # syndrome bit. This is the decoder's own cost, isolated.
                "decoder_cost_ns": (
                    round(dat[0]["arrival_ns"] - syn[0]["arrival_ns"], 6)
                    if syn and dat else None
                ),
            }
        allrec[case.name] = rec

        print(f"### {case.name}")
        if "netlist" in rec:
            n = rec["netlist"]
            print(f"  cells={n['num_cells']} max_fanout={n['max_fanout']}")
            for r in n["top_fanout_nets"][:6]:
                print(f"    fo={r['fanout']:3d}  {r['driver_cell']:32s} {r['net']}")
        if "arrival" in rec:
            a = rec["arrival"]
            print(f"  syndrome spread={a['syndrome_spread_ns']} ns  "
                  f"decoder cost={a['decoder_cost_ns']} ns")
            for s in a["syndrome_latest"]:
                print(f"    LATE  {s['endpoint']:18s} {s['arrival_ns']:.6f}")
            for s in a["syndrome_earliest"]:
                print(f"    EARLY {s['endpoint']:18s} {s['arrival_ns']:.6f}")
        print()

    if args.out:
        Path(args.out).write_text(json.dumps(allrec, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
