"""Pure fixed GF(2) recipe for the balanced P02 critical XOR3/XNOR3 width exchange."""
from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path

from research.ecc_perf_bench.netlist_fanout import OUT_PINS
from research.ecc_perf_bench.polarity_execute import EcoError
from research.ecc_perf_bench.polarity_kernel import parse_cells

PARENT_ID = "d6b1d9c2"
PARENT_SHA = "d6b1d9c234f4de9d44f5fc1c29b728fb033c93c0ee5e1bfb5718f9c717c970e9"
ACTION = {"kind": "balanced_phase_replay", "plan": "critical_068"}
PLAN = "critical_068"
PHASE_NET = "_068_"
TARGETS = ("_326_", "_328_")
ASSIGN = re.compile(r"\bassign\b([^;]*);", re.S)
MASTER = {
    "sky130_fd_sc_hd__xor2_1": {"b": 0, "out": "X", "inputs": ("A", "B"),
                                  "opposite": "sky130_fd_sc_hd__xnor2_1", "opposite_out": "Y"},
    "sky130_fd_sc_hd__xnor2_1": {"b": 1, "out": "Y", "inputs": ("A", "B"),
                                   "opposite": "sky130_fd_sc_hd__xor2_1", "opposite_out": "X"},
    "sky130_fd_sc_hd__xor3_1": {"b": 0, "out": "X", "inputs": ("A", "B", "C"),
                                  "opposite": "sky130_fd_sc_hd__xnor3_1", "opposite_out": "X"},
    "sky130_fd_sc_hd__xnor3_1": {"b": 1, "out": "X", "inputs": ("A", "B", "C"),
                                   "opposite": "sky130_fd_sc_hd__xor3_1", "opposite_out": "X"},
}
PHYSICAL = {
    "sky130_fd_sc_hd__xor3_1": {"area_um2": 23.7728, "width_um": 8.740, "height_um": 2.720,
                                  "width_dbu": 8740, "height_dbu": 2720},
    "sky130_fd_sc_hd__xnor3_1": {"area_um2": 22.5216, "width_um": 8.280, "height_um": 2.720,
                                   "width_dbu": 8280, "height_dbu": 2720},
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def cell_map_sha(cells: dict) -> str:
    return digest(json.dumps(cells, sort_keys=True, separators=(",", ":")).encode())


def local_truth_table() -> list[dict]:
    rows = []
    for a in (0, 1):
        for b in (0, 1):
            for c in (0, 1):
                for d in (0, 1):
                    for e in (0, 1):
                        producer = a ^ b ^ c
                        original = int(not (d ^ e ^ producer))
                        flipped_producer = int(not producer)
                        transformed = d ^ e ^ flipped_producer
                        rows.append({"producer_inputs": [a, b, c], "consumer_other_inputs": [d, e],
                                     "original": original, "transformed": transformed})
    return rows


def derive(parent_text: str) -> dict:
    if digest(parent_text.encode()) != PARENT_SHA:
        raise EcoError("balanced phase replay requires exact P02 routed graph")
    cells = parse_cells(parent_text)
    required = {
        "_326_": {"cell": "sky130_fd_sc_hd__xor3_1",
                  "pins": {"A": "_047_", "B": "_053_", "C": "_067_", "X": "_068_"}},
        "_328_": {"cell": "sky130_fd_sc_hd__xnor3_1",
                  "pins": {"A": "_006_", "B": "_069_", "C": "_068_", "X": "_070_"}},
    }
    if any(cells.get(name) != spec for name, spec in required.items()):
        raise EcoError("P02 critical balanced-phase target map changed")
    drivers: dict[str, list[tuple[str, str, str]]] = {}
    sinks: dict[str, list[tuple[str, str, str]]] = {}
    for name, row in cells.items():
        for pin, net in row["pins"].items():
            target = drivers if pin in OUT_PINS else sinks
            target.setdefault(net, []).append((name, pin, row["cell"]))
    if (drivers.get(PHASE_NET) != [("_326_", "X", "sky130_fd_sc_hd__xor3_1")]
        or sinks.get(PHASE_NET) != [("_328_", "C", "sky130_fd_sc_hd__xnor3_1")]):
        raise EcoError("critical phase net is not a single-driver/single-sink boundary")
    if any(PHASE_NET in match.group(1) for match in ASSIGN.finditer(parent_text)):
        raise EcoError("critical phase net participates in assign alias/export")
    phase = {PHASE_NET}
    expected = copy.deepcopy(cells)
    changed = {}
    parity_gates = 0
    for name, row in cells.items():
        spec = MASTER.get(row["cell"])
        if spec is None:
            continue
        parity_gates += 1
        if set(row["pins"]) != set(spec["inputs"]) | {spec["out"]}:
            raise EcoError(f"unsupported parity pin schema at {name}")
        flip = (int(row["pins"][spec["out"]] in phase)
                + sum(int(row["pins"][pin] in phase) for pin in spec["inputs"])) & 1
        if not flip:
            continue
        new_pins = dict(row["pins"])
        output_net = new_pins.pop(spec["out"])
        new_pins[spec["opposite_out"]] = output_net
        expected[name] = {"cell": spec["opposite"], "pins": new_pins}
        changed[name] = {"old_master": row["cell"], "new_master": spec["opposite"],
                         "old_output_pin": spec["out"], "new_output_pin": spec["opposite_out"],
                         "output_net": output_net}
    truth_rows = local_truth_table()
    truth_mismatches = sum(row["original"] != row["transformed"] for row in truth_rows)
    if parity_gates != 193 or set(changed) != set(TARGETS) or truth_mismatches:
        raise EcoError("fixed GF(2) or 32-row local truth check failed")
    area_delta = sum(PHYSICAL[changed[name]["new_master"]]["area_um2"]
                     - PHYSICAL[changed[name]["old_master"]]["area_um2"] for name in TARGETS)
    if area_delta != 0.0:
        raise EcoError("fixed pair is no longer total-area balanced")
    downstream = sorted((name, pin) for name, pin, _master in sinks.get("_070_", []))
    return {
        "kind": ACTION["kind"], "plan": PLAN,
        "parent_id": PARENT_ID, "parent_graph_sha256": PARENT_SHA,
        "action": ACTION, "phase_one_nets": [PHASE_NET], "targets": list(TARGETS),
        "target_specs": changed, "expected_cells": expected,
        "expected_cell_map_sha256": cell_map_sha(expected),
        "parity_gate_count": parity_gates, "gf2_mismatches": 0,
        "local_truth_rows": 32, "local_truth_mismatches": truth_mismatches,
        "phase_net_driver": drivers[PHASE_NET], "phase_net_sinks": sinks[PHASE_NET],
        "downstream_output_net": "_070_", "downstream_output_fanout": downstream,
        "liberty_area_delta_um2": area_delta,
        "per_cell_width_delta_um": {
            name: PHYSICAL[changed[name]["new_master"]]["width_um"]
                 - PHYSICAL[changed[name]["old_master"]]["width_um"] for name in TARGETS
        },
        "per_cell_size_deltas_dbu": {
            name: {"width": PHYSICAL[changed[name]["new_master"]]["width_dbu"]
                           - PHYSICAL[changed[name]["old_master"]]["width_dbu"],
                   "height": PHYSICAL[changed[name]["new_master"]]["height_dbu"]
                            - PHYSICAL[changed[name]["old_master"]]["height_dbu"]} for name in TARGETS
        },
        "same_size_eco_legal": False,
        "functional_proof": "NOT_RUN", "route": "NOT_RUN", "measurement": "NOT_RUN",
    }


def validate_child(parent_text: str, child_text: str, manifest: dict) -> None:
    expected = derive(parent_text)
    serialized_manifest = json.loads(json.dumps(manifest, sort_keys=True))
    serialized_expected = json.loads(json.dumps(expected, sort_keys=True))
    if serialized_manifest != serialized_expected:
        raise EcoError("manifest differs from fixed critical_068 action")
    if parse_cells(child_text) != expected["expected_cells"]:
        raise EcoError("child full cell map differs from balanced phase proposal")


def write_targets_tsv(path, parent_cells: dict, manifest: dict) -> str:
    expected = derive_from_cells_guard(parent_cells, manifest)
    rows = []
    for name in expected["targets"]:
        spec = expected["target_specs"][name]
        rows.append("\t".join((name, spec["old_master"], spec["new_master"],
                              spec["old_output_pin"], spec["new_output_pin"])))
    path.write_text("\n".join(rows) + "\n", encoding="ascii")
    return digest(path.read_bytes())


def derive_from_cells_guard(parent_cells: dict, manifest: dict) -> dict:
    fixed_specs = {
        "_326_": {"old_master": "sky130_fd_sc_hd__xor3_1", "new_master": "sky130_fd_sc_hd__xnor3_1",
                  "old_output_pin": "X", "new_output_pin": "X", "output_net": "_068_"},
        "_328_": {"old_master": "sky130_fd_sc_hd__xnor3_1", "new_master": "sky130_fd_sc_hd__xor3_1",
                  "old_output_pin": "X", "new_output_pin": "X", "output_net": "_070_"},
    }
    expected = manifest.get("expected_cells")
    if (manifest.get("kind") != ACTION["kind"] or manifest.get("plan") != PLAN
        or manifest.get("action") != ACTION or manifest.get("parent_graph_sha256") != PARENT_SHA
        or manifest.get("targets") != list(TARGETS) or set(manifest.get("target_specs", {})) != set(TARGETS)
        or manifest["target_specs"] != fixed_specs or not isinstance(expected, dict)
        or set(parent_cells) != set(expected) or manifest.get("liberty_area_delta_um2") != 0.0):
        raise EcoError("balanced target TSV requires the exact critical_068 manifest")
    for name, parent in parent_cells.items():
        if name not in fixed_specs:
            if expected[name] != parent:
                raise EcoError(f"balanced proposal changed a non-target cell: {name}")
            continue
        spec = fixed_specs[name]
        if (parent["cell"] != spec["old_master"]
            or parent["pins"].get(spec["old_output_pin"]) != spec["output_net"]):
            raise EcoError(f"balanced target parent connectivity changed: {name}")
        new_pins = dict(parent["pins"])
        new_pins.pop(spec["old_output_pin"])
        new_pins[spec["new_output_pin"]] = spec["output_net"]
        if expected[name] != {"cell": spec["new_master"], "pins": new_pins}:
            raise EcoError(f"balanced target child connectivity changed: {name}")
    return manifest
