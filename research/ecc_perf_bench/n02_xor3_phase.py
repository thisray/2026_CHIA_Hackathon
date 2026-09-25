"""Exact N02 two-cell XOR3/XNOR3 phase compensation; no physical claims."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path

from research.ecc_perf_bench.netlist_fanout import OUT_PINS
from research.ecc_perf_bench.polarity_execute import EcoError
from research.ecc_perf_bench.polarity_kernel import parse_cells

PARENT_ID = "N02-320970ab"
PARENT_SHA = "320970ab4870a46b7603f457414d938c47b7971d760c2b07c5fae1983e0ca44f"
ACTION = {"kind": "xor3_phase_replay", "plan": "n02_068"}
PLAN = "n02_068"
PHASE_NET = "_068_"
TARGETS = ("_326_", "_328_")
PURE_PROPOSAL_SHA = "eefeb2af735a2169fda65d2d8f5ced7507070ade895cfc9f5a261fd8e4c16cf3"
EXPECTED_CELL_MAP_SHA = "b364a3eb724826d5cd7ed60a7e22050cf71593e3e80fbfad53351c3f38d550bc"
SOURCE_MANIFEST_SHA = "ad8bd591a1f7772cd00a8800c8706570879a65a8246bb03b423fc05eff90e262"
SOURCE_GENERATOR_SHA = "3aed8f6ec2b2e3069956bb2f00e31e77951c7aebc25a64c32b098375668dacc4"
LIBERTY_SHA = "8e78e14442062dba34d414fca6490b2f6b96038d4510d1438ca44fee31487135"
LEF_SHA = "3a3ea4e9d0973402702764d897659e52fe3d413eb48c306cd811de40a75264fa"
SOURCE_FILES = {
    "proposal": ("n02_xor3_phase_source_proposal.json",
                 "bd7571a5ac6a350dca7ce4e10952c2111986366039c2529468e963ffa779ff2f"),
    "checker": ("n02_xor3_phase_source_checker.json",
                "362fe54880c2292c9233f5d74451711b974a4b66d4749ecda46f64986e332852"),
    "library": ("n02_xor3_phase_source_library.json",
                "20e3f42ec0dc3864e374204f86d64ad45ee1d9a5c327d52cf9512596826e2d8d"),
}
ASSIGN = re.compile(r"\bassign\b([^;]*);", re.S)
MASTER = {
    "sky130_fd_sc_hd__xor2_1": (0, "X", ("A", "B"), "sky130_fd_sc_hd__xnor2_1", "Y"),
    "sky130_fd_sc_hd__xnor2_1": (1, "Y", ("A", "B"), "sky130_fd_sc_hd__xor2_1", "X"),
    "sky130_fd_sc_hd__xor3_1": (0, "X", ("A", "B", "C"), "sky130_fd_sc_hd__xnor3_1", "X"),
    "sky130_fd_sc_hd__xnor3_1": (1, "X", ("A", "B", "C"), "sky130_fd_sc_hd__xor3_1", "X"),
    "sky130_fd_sc_hd__xor3_2": (0, "X", ("A", "B", "C"), "sky130_fd_sc_hd__xnor3_2", "X"),
    "sky130_fd_sc_hd__xnor3_2": (1, "X", ("A", "B", "C"), "sky130_fd_sc_hd__xor3_2", "X"),
}
PHYSICAL = {
    "sky130_fd_sc_hd__xor3_1": (23.7728, 8740, 2720),
    "sky130_fd_sc_hd__xnor3_1": (22.5216, 8280, 2720),
    "sky130_fd_sc_hd__xor3_2": (25.0240, 9200, 2720),
    "sky130_fd_sc_hd__xnor3_2": (23.7728, 8740, 2720),
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def cell_map_sha(cells: dict) -> str:
    return digest(json.dumps(cells, sort_keys=True, separators=(",", ":")).encode())


def source_evidence() -> dict:
    base = Path(__file__).resolve().parent
    evidence = {}
    for name, (filename, expected_sha) in SOURCE_FILES.items():
        path = base / filename
        if not path.is_file() or digest(path.read_bytes()) != expected_sha:
            raise EcoError(f"N02 XOR3 source {name} snapshot changed")
        evidence[name] = json.loads(path.read_text())
    proposal, checker, library = evidence["proposal"], evidence["checker"], evidence["library"]
    if (proposal.get("parent_graph_sha256") != PARENT_SHA
        or proposal.get("candidate_graph_sha256") != PURE_PROPOSAL_SHA
        or proposal.get("source_hashes", {}).get("Liberty") != LIBERTY_SHA
        or proposal.get("source_hashes", {}).get("LEF") != LEF_SHA
        or checker.get("status") != "PASS_PURE_CELLMAP_AND_FIVE_INPUT_TRUTH_ONLY"
        or checker.get("candidate_graph_sha256") != PURE_PROPOSAL_SHA
        or checker.get("full_cell_map_instances") != 553
        or len(checker.get("five_input_truth_rows", [])) != 32
        or set(library.get("cells", {})) != set(PHYSICAL)):
        raise EcoError("N02 XOR3 source evidence context changed")
    for name, (area, width, height) in PHYSICAL.items():
        row = library["cells"][name]
        if (abs(row.get("area_um2", -1) - area) > 1e-6
            or round(row.get("width_um", -1) * 1000) != width
            or round(row.get("height_um", -1) * 1000) != height
            or row.get("output_pin") != "X"
            or set(row.get("functional_pins", [])) != {"A", "B", "C", "X"}):
            raise EcoError(f"N02 XOR3 Liberty/LEF geometry or output differs: {name}")
    return evidence


def local_truth_table() -> list[dict]:
    rows = []
    for a in (0, 1):
        for b in (0, 1):
            for c in (0, 1):
                for d in (0, 1):
                    for e in (0, 1):
                        old_internal = a ^ b ^ c
                        new_internal = old_internal ^ 1
                        old_output = d ^ e ^ old_internal
                        new_output = d ^ e ^ new_internal ^ 1
                        rows.append({"A": a, "B": b, "C": c, "D": d, "E": e,
                                     "old_internal": old_internal, "new_internal": new_internal,
                                     "old_syndrome2": old_output, "new_syndrome2": new_output})
    return rows


def derive(parent_text: str) -> dict:
    if digest(parent_text.encode()) != PARENT_SHA:
        raise EcoError("N02 XOR3 action requires exact routed parent")
    evidence = source_evidence()
    cells = parse_cells(parent_text)
    required = {
        "_326_": {"cell": "sky130_fd_sc_hd__xor3_1",
                  "pins": {"A": "_047_", "B": "_053_", "C": "_067_", "X": "_068_"}},
        "_328_": {"cell": "sky130_fd_sc_hd__xor3_2",
                  "pins": {"A": "_006_", "B": "_069_", "C": "_068_", "X": "syndrome_o[2]"}},
    }
    if len(cells) != 287 or any(cells.get(name) != row for name, row in required.items()):
        raise EcoError("N02 exact XOR3 targets or complete instance count changed")
    drivers: dict[str, list[tuple[str, str, str]]] = {}
    sinks: dict[str, list[tuple[str, str, str]]] = {}
    for name, row in cells.items():
        for pin, net in row["pins"].items():
            table = drivers if pin in OUT_PINS else sinks
            table.setdefault(net, []).append((name, pin, row["cell"]))
    if (drivers.get(PHASE_NET) != [("_326_", "X", "sky130_fd_sc_hd__xor3_1")]
        or sinks.get(PHASE_NET) != [("_328_", "C", "sky130_fd_sc_hd__xor3_2")]
        or any(PHASE_NET in match.group(1) for match in ASSIGN.finditer(parent_text))):
        raise EcoError("N02 _068_ unique driver/complete fanout/alias guard failed")
    expected = copy.deepcopy(cells)
    changed = {}
    parity_gate_count = 0
    for name, row in cells.items():
        master = MASTER.get(row["cell"])
        if master is None:
            continue
        original_b, old_out, inputs, opposite, new_out = master
        parity_gate_count += 1
        if set(row["pins"]) != set(inputs) | {old_out}:
            raise EcoError(f"unsupported parity pin schema at {name}")
        phase_bit = (int(row["pins"][old_out] == PHASE_NET)
                     + sum(int(row["pins"][pin] == PHASE_NET) for pin in inputs)) & 1
        if not phase_bit:
            continue
        pins = dict(row["pins"])
        output_net = pins.pop(old_out)
        pins[new_out] = output_net
        expected[name] = {"cell": opposite, "pins": pins}
        changed[name] = {"old_master": row["cell"], "new_master": opposite,
                         "old_output_pin": old_out, "new_output_pin": new_out,
                         "output_net": output_net}
    rows = local_truth_table()
    if (parity_gate_count != 193 or set(changed) != set(TARGETS)
        or any(row["old_internal"] ^ row["new_internal"] != 1
               or row["old_syndrome2"] != row["new_syndrome2"] for row in rows)
        or rows != evidence["checker"]["five_input_truth_rows"]):
        raise EcoError("N02 XOR3 GF(2) or five-input truth guard failed")
    for name in TARGETS:
        source_spec = evidence["proposal"]["targets"].get(name)
        if (source_spec is None
            or source_spec["old_master"] != changed[name]["old_master"]
            or source_spec["new_master"] != changed[name]["new_master"]
            or source_spec["old_output_pin"] != changed[name]["old_output_pin"]
            or source_spec["new_output_pin"] != changed[name]["new_output_pin"]
            or source_spec["pins"] != cells[name]["pins"]):
            raise EcoError(f"N02 XOR3 source target pin/net map changed: {name}")
    if cell_map_sha(expected) != EXPECTED_CELL_MAP_SHA:
        raise EcoError("N02 XOR3 expected full cell map changed")
    area_delta = round(sum(PHYSICAL[changed[name]["new_master"]][0]
                           - PHYSICAL[changed[name]["old_master"]][0] for name in TARGETS), 4)
    db_area_delta = sum(
        PHYSICAL[changed[name]["new_master"]][1] * PHYSICAL[changed[name]["new_master"]][2]
        - PHYSICAL[changed[name]["old_master"]][1] * PHYSICAL[changed[name]["old_master"]][2]
        for name in TARGETS)
    if area_delta != -2.5024 or db_area_delta != -2502400:
        raise EcoError("N02 XOR3 pair area delta changed")
    return {
        "kind": ACTION["kind"], "plan": PLAN,
        "parent_id": PARENT_ID, "parent_graph_sha256": PARENT_SHA,
        "action": ACTION, "phase_one_nets": [PHASE_NET], "targets": list(TARGETS),
        "target_specs": changed, "expected_cells": expected,
        "expected_cell_map_sha256": EXPECTED_CELL_MAP_SHA,
        "pure_proposal_text_sha256": PURE_PROPOSAL_SHA,
        "source_artifact_manifest_sha256": SOURCE_MANIFEST_SHA,
        "source_generator_sha256": SOURCE_GENERATOR_SHA,
        "source_proposal_sha256": SOURCE_FILES["proposal"][1],
        "source_checker_sha256": SOURCE_FILES["checker"][1],
        "source_library_sha256": SOURCE_FILES["library"][1],
        "liberty_sha256": LIBERTY_SHA, "lef_sha256": LEF_SHA,
        "parity_gate_count": parity_gate_count, "gf2_mismatches": 0,
        "local_truth_rows": len(rows), "local_truth_mismatches": 0,
        "phase_net_driver": drivers[PHASE_NET], "phase_net_sinks": sinks[PHASE_NET],
        "downstream_output_net": "syndrome_o[2]",
        "liberty_area_delta_um2": area_delta, "db_area_delta_dbu2": db_area_delta,
        "per_cell_width_delta_um": {name: -0.460 for name in TARGETS},
        "per_cell_size_deltas_dbu": {name: {"width": -460, "height": 0} for name in TARGETS},
        "same_size_eco_legal": False,
        "functional_proof": "NOT_RUN", "route": "NOT_RUN", "measurement": "NOT_RUN",
    }


def validate_child(parent_text: str, child_text: str, manifest: dict) -> None:
    expected = derive(parent_text)
    if manifest != expected:
        raise EcoError("manifest differs from fixed N02 XOR3 action")
    if parse_cells(child_text) != expected["expected_cells"]:
        raise EcoError("N02 XOR3 child full cell map differs from exact proposal")


def derive_from_cells_guard(parent_cells: dict, manifest: dict) -> dict:
    fixed_specs = {
        "_326_": {"old_master": "sky130_fd_sc_hd__xor3_1",
                  "new_master": "sky130_fd_sc_hd__xnor3_1",
                  "old_output_pin": "X", "new_output_pin": "X", "output_net": "_068_"},
        "_328_": {"old_master": "sky130_fd_sc_hd__xor3_2",
                  "new_master": "sky130_fd_sc_hd__xnor3_2",
                  "old_output_pin": "X", "new_output_pin": "X", "output_net": "syndrome_o[2]"},
    }
    fixed_parent_cells = {
        "_326_": {"cell": "sky130_fd_sc_hd__xor3_1",
                  "pins": {"A": "_047_", "B": "_053_", "C": "_067_", "X": "_068_"}},
        "_328_": {"cell": "sky130_fd_sc_hd__xor3_2",
                  "pins": {"A": "_006_", "B": "_069_", "C": "_068_", "X": "syndrome_o[2]"}},
    }
    expected = manifest.get("expected_cells")
    if (manifest.get("kind") != ACTION["kind"] or manifest.get("plan") != PLAN
        or manifest.get("action") != ACTION or manifest.get("parent_graph_sha256") != PARENT_SHA
        or manifest.get("targets") != list(TARGETS) or manifest.get("target_specs") != fixed_specs
        or not isinstance(expected, dict) or set(parent_cells) != set(expected)
        or manifest.get("liberty_area_delta_um2") != -2.5024
        or manifest.get("db_area_delta_dbu2") != -2502400):
        raise EcoError("N02 XOR3 target TSV requires the exact two-cell manifest")
    for name, parent in parent_cells.items():
        if name not in fixed_specs:
            if expected[name] != parent:
                raise EcoError(f"N02 XOR3 proposal changed a non-target cell: {name}")
            continue
        spec = fixed_specs[name]
        if parent != fixed_parent_cells[name]:
            raise EcoError(f"N02 XOR3 target parent connectivity changed: {name}")
        if expected[name] != {"cell": spec["new_master"], "pins": parent["pins"]}:
            raise EcoError(f"N02 XOR3 target child connectivity changed: {name}")
    return manifest


def write_targets_tsv(path: Path, parent_cells: dict, manifest: dict) -> str:
    fixed = derive_from_cells_guard(parent_cells, manifest)
    rows = []
    for name in fixed["targets"]:
        spec = fixed["target_specs"][name]
        rows.append("\t".join((name, spec["old_master"], spec["new_master"],
                               spec["old_output_pin"], spec["new_output_pin"])))
    path.write_text("\n".join(rows) + "\n", encoding="ascii")
    return digest(path.read_bytes())


def n02_area_check(log: str) -> dict:
    match = re.search(r"(?m)^CHIA_N02_XOR3_AREA_CHECK\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*$", log)
    if match is None:
        raise EcoError("N02 XOR3 ECO omitted exact pair/design DB area marker")
    pair_before, pair_after, design_before, design_after = map(int, match.groups())
    if (pair_before != 48796800 or pair_after != 46294400
        or pair_after - pair_before != -2502400
        or design_after - design_before != -2502400):
        raise EcoError("N02 XOR3 target pair or whole DB area delta differs")
    return {"pair_before_dbu2": pair_before, "pair_after_dbu2": pair_after,
            "pair_delta_dbu2": pair_after - pair_before,
            "design_before_dbu2": design_before, "design_after_dbu2": design_after,
            "design_delta_dbu2": design_after - design_before}
