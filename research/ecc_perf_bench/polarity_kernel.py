"""Structural XOR/XNOR phase relocation candidates and exact child validation."""

from __future__ import annotations

import copy
import re

from research.ecc_perf_bench.netlist_fanout import CELL_RE, CONN_RE


PHYSICAL_CELLS = {
    "sky130_fd_sc_hd__tapvpwrvgnd_1",
    "sky130_fd_sc_hd__decap_3",
}
XOR = "sky130_fd_sc_hd__xor2_1"
XNOR = "sky130_fd_sc_hd__xnor2_1"
SUPPORTED = {XOR, XNOR}
INTERNAL_NET = re.compile(r"^_\d+_$")
ASSIGN_RE = re.compile(r"\bassign\b([^;]*);", re.S)


def parse_cells(text: str) -> dict[str, dict]:
    """Parse mapped cells, rejecting ambiguous instances and internal aliases."""
    for match in ASSIGN_RE.finditer(text):
        if any(INTERNAL_NET.fullmatch(token) for token in re.findall(r"\b_\d+_\b", match.group(1))):
            raise ValueError("assign involving an internal net is unsupported")

    result: dict[str, dict] = {}
    seen: set[str] = set()
    for match in CELL_RE.finditer(text):
        master, name = match.group(1), match.group(2)
        if name in seen:
            raise ValueError(f"duplicate cell instance {name}")
        seen.add(name)
        if master in PHYSICAL_CELLS:
            continue
        pins: dict[str, str] = {}
        for pin, net in CONN_RE.findall(match.group("conns")):
            if pin in pins:
                raise ValueError(f"duplicate pin {name}.{pin}")
            pins[pin] = net.strip()
        result[name] = {"cell": master, "pins": pins}
    return result


def _output(master: str) -> str | None:
    if master == XOR:
        return "X"
    if master == XNOR:
        return "Y"
    return None


def _graph(cells: dict[str, dict]) -> tuple[dict[str, tuple[str, str]], dict[str, list[tuple[str, str]]]]:
    drivers: dict[str, tuple[str, str]] = {}
    loads: dict[str, list[tuple[str, str]]] = {}
    for name, record in cells.items():
        master = record["cell"]
        outpin = _output(master)
        if outpin and outpin in record["pins"]:
            net = record["pins"][outpin]
            if INTERNAL_NET.fullmatch(net):
                if net in drivers:
                    raise ValueError(f"multiple supported producers for {net}")
                drivers[net] = (name, outpin)
        for pin, net in record["pins"].items():
            if pin in {"X", "Y", "Q", "Q_N", "SUM", "COUT", "COUT_N", "HI", "LO"}:
                continue
            loads.setdefault(net, []).append((name, pin))
    return drivers, loads


def catalog(cells: dict) -> dict:
    """Return complete, supported one-sink pairs and 2..4 fanout stars."""
    drivers, loads = _graph(cells)
    pairs = []
    stars = []
    for net, (root, _) in drivers.items():
        sinks = loads.get(net, [])
        if not sinks or any(
            name not in cells or cells[name]["cell"] not in SUPPORTED or pin not in {"A", "B"}
            for name, pin in sinks
        ):
            continue
        consumers = sorted({name for name, _ in sinks})
        if len(consumers) == 1 and len(sinks) == 1:
            pairs.append({"lower": root, "upper": consumers[0]})
        elif 2 <= len(consumers) <= 4 and len(sinks) == len(consumers):
            stars.append({"root": root, "consumers": consumers})
    pairs.sort(key=lambda item: (item["lower"], item["upper"]))
    stars.sort(key=lambda item: (item["root"], item["consumers"]))
    return {"pairs": pairs, "stars": stars}


def _normalized(cells: dict, action: dict) -> tuple[dict, list[str], list[str]]:
    if not isinstance(action, dict):
        raise ValueError("action must be a mapping")
    available = catalog(cells)
    kind = action.get("kind")
    if kind == "pair_batch":
        raw = action.get("pairs")
        if not isinstance(raw, list) or not 1 <= len(raw) <= 4:
            raise ValueError("pair_batch requires 1..4 pairs")
        allowed = {(p["lower"], p["upper"]) for p in available["pairs"]}
        chosen = []
        used: set[str] = set()
        for item in raw:
            if not isinstance(item, dict) or set(item) != {"lower", "upper"}:
                raise ValueError("invalid pair specification")
            pair = (item["lower"], item["upper"])
            if pair not in allowed:
                raise ValueError(f"pair is not in catalog: {pair}")
            if used.intersection(pair):
                raise ValueError("pair targets overlap")
            used.update(pair)
            chosen.append({"lower": pair[0], "upper": pair[1]})
        chosen.sort(key=lambda p: (p["lower"], p["upper"]))
        names = sorted(used)
        nets = sorted({cells[pair["lower"]]["pins"][_output(cells[pair["lower"]]["cell"])] for pair in chosen})
        return {"kind": kind, "pairs": chosen}, names, nets
    if kind == "star":
        if set(action) != {"kind", "root"}:
            raise ValueError("invalid star action keys")
        root = action.get("root")
        match = next((s for s in available["stars"] if s["root"] == root), None)
        if match is None:
            raise ValueError(f"star is not in catalog: {root}")
        nets = [cells[root]["pins"][_output(cells[root]["cell"])] ]
        return {"kind": kind, "root": root}, sorted([root, *match["consumers"]]), nets
    if kind == "star_batch":
        if set(action) != {"kind", "roots"}:
            raise ValueError("invalid star_batch action keys")
        roots = action.get("roots")
        if not isinstance(roots, list) or not 2 <= len(roots) <= 4:
            raise ValueError("star_batch requires 2..4 roots")
        if any(not isinstance(root, str) for root in roots):
            raise ValueError("star_batch roots must be instance names")
        if len(set(roots)) != len(roots):
            raise ValueError("star_batch roots must be unique")
        normalized_roots = sorted(roots)
        stars = {star["root"]: star for star in available["stars"]}
        targets: set[str] = set()
        nets: set[str] = set()
        for root in normalized_roots:
            star = stars.get(root)
            if star is None:
                raise ValueError(f"star root is not in catalog: {root}")
            star_targets = {root, *star["consumers"]}
            overlap = targets.intersection(star_targets)
            if overlap:
                raise ValueError(f"star_batch target sets overlap: {sorted(overlap)}")
            targets.update(star_targets)
            outpin = _output(cells[root]["cell"])
            nets.add(cells[root]["pins"][outpin])
        return {"kind": kind, "roots": normalized_roots}, sorted(targets), sorted(nets)
    raise ValueError("unsupported action kind")


def derive(cells: dict, action: dict) -> dict:
    """Build a fully compensated expected cell map without mutating input."""
    normalized, targets, producer_nets = _normalized(cells, action)
    transformed = copy.deepcopy(cells)
    target_specs = {}
    for name in targets:
        old = cells[name]
        old_out = _output(old["cell"])
        new_master = XNOR if old["cell"] == XOR else XOR
        new_out = _output(new_master)
        pins = transformed[name]["pins"]
        old_net = pins.pop(old_out)
        pins[new_out] = old_net
        transformed[name]["cell"] = new_master
        target_specs[name] = {
            "old_master": old["cell"],
            "new_master": new_master,
            "old_output_pin": old_out,
            "new_output_pin": new_out,
        }
    return {
        "action": normalized,
        "targets": targets,
        "target_specs": target_specs,
        "expected_cells": transformed,
        "producer_nets": producer_nets,
        "functional_proof": "NOT_RUN",
    }


def validate_child(before: dict, after: dict, manifest: dict) -> None:
    """Require an exact structural match to a freshly derived manifest action."""
    if not isinstance(manifest, dict) or "action" not in manifest:
        raise ValueError("manifest action is missing")
    expected = derive(before, manifest["action"])["expected_cells"]
    if after != expected:
        raise ValueError("child cell map does not exactly match derived transformation")
