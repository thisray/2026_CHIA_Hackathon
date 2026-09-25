"""Finite structural composition of no-fold parent 67c95564 with N01 or N02 phase map."""
from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path

from research.ecc_perf_bench.netlist_fanout import OUT_PINS
from research.ecc_perf_bench.polarity_kernel import parse_cells

PLAN_PATH = Path(__file__).with_name("no_fold_phase_composition_plans.json")
PARENT_SHA = "67c95564bf6e88ae5d732a40be478b0f1099b83cae78c77c06d79e9aefd560cc"
PLAN_SHA = "d4b92fc929c7da8e496809f5c12b0036cb0855e9ca2adfca42a378babf054fdc"
INTERNAL = re.compile(r"^_\d+_$")
ASSIGN = re.compile(r"\bassign\b([^;]*);", re.S)
XOR = "sky130_fd_sc_hd__xor2_1"
XNOR = "sky130_fd_sc_hd__xnor2_1"
OUT_PIN = {XOR: "X", XNOR: "Y"}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def cell_map_sha(cells: dict) -> str:
    return sha256(json.dumps(cells, sort_keys=True, separators=(",", ":")).encode())


def load_plans() -> dict:
    plan_bytes = PLAN_PATH.read_bytes()
    if sha256(plan_bytes) != PLAN_SHA:
        raise ValueError("fixed no-fold phase composition plan file changed")
    plans = json.loads(plan_bytes)
    if (plans.get("schema") != "nofold-phase-composition-v1"
        or plans.get("parent", {}).get("routed_netlist_sha256") != PARENT_SHA
        or set(plans.get("donors", {})) != {"donor_N01", "donor_N02"}
        or plans.get("functional_proof") != "NOT_RUN"
        or plans.get("route") != "NOT_RUN"
        or plans.get("measurement") != "NOT_RUN"):
        raise ValueError("fixed no-fold phase composition plan context changed")
    return plans


def derive(parent_text: str, donor: str) -> dict:
    if sha256(parent_text.encode()) != PARENT_SHA:
        raise ValueError("phase composition requires exact no-fold parent graph")
    plans = load_plans()
    if donor not in plans["donors"]:
        raise ValueError("only donor_N01 or donor_N02 is supported")
    plan = plans["donors"][donor]
    phases = plan["phase_one_nets"]
    if (not isinstance(phases, list) or not phases or len(phases) != len(set(phases))
        or any(not isinstance(net, str) or not INTERNAL.fullmatch(net) for net in phases)):
        raise ValueError("fixed phase map is malformed")
    phase = set(phases)
    cells = parse_cells(parent_text)
    drivers: dict[str, list[tuple[str, str]]] = {}
    sinks: dict[str, list[tuple[str, str]]] = {}
    gates = {}
    for name, row in cells.items():
        master, pins = row["cell"], row["pins"]
        if master in OUT_PIN:
            output_pin = OUT_PIN[master]
            if set(pins) != {"A", "B", output_pin}:
                raise ValueError(f"unsupported XOR2 pin map at {name}")
            gates[name] = {"b": int(master == XNOR), "output": pins[output_pin],
                           "inputs": (pins["A"], pins["B"])}
            drivers.setdefault(pins[output_pin], []).append((name, output_pin))
            sinks.setdefault(pins["A"], []).append((name, "A"))
            sinks.setdefault(pins["B"], []).append((name, "B"))
        else:
            for pin, net in pins.items():
                table = drivers if pin in OUT_PINS else sinks
                table.setdefault(net, []).append((name, pin))
    if len(gates) != 187 or sum(gate["b"] for gate in gates.values()) != 60:
        raise ValueError("no-fold XOR2 inventory differs from audited parent")
    if any(ASSIGN.search(parent_text) and any(re.search(rf"\b{re.escape(net)}\b", m.group(1)) for m in ASSIGN.finditer(parent_text)) for net in phase):
        raise ValueError("phase variable participates in continuous assignment")
    for net in phase:
        sources, consumers = drivers.get(net, []), sinks.get(net, [])
        if (len(sources) != 1 or sources[0][0] not in gates or not consumers
            or any(child not in gates or pin not in {"A", "B"} for child, pin in consumers)):
            raise ValueError(f"phase variable crosses supported private-net boundary: {net}")
    expected = copy.deepcopy(cells)
    targets = {}
    final_xnor = 0
    for name, gate in gates.items():
        new_b = gate["b"] ^ (sum(net in phase for net in (gate["output"], *gate["inputs"])) & 1)
        final_xnor += new_b
        if new_b == gate["b"]:
            continue
        old = cells[name]
        new_master = XNOR if new_b else XOR
        old_pin, new_pin = OUT_PIN[old["cell"]], OUT_PIN[new_master]
        new_pins = dict(old["pins"])
        output_net = new_pins.pop(old_pin)
        new_pins[new_pin] = output_net
        expected[name] = {"cell": new_master, "pins": new_pins}
        targets[name] = {"old_master": old["cell"], "new_master": new_master,
                         "old_output_pin": old_pin, "new_output_pin": new_pin}
    if (final_xnor != plan["expected_xnor2_count"]
        or len(targets) != plan["expected_changed_gate_count"]
        or cell_map_sha(expected) != plan["expected_cell_map_sha256"]):
        raise ValueError("phase map does not reproduce audited no-fold pure candidate")
    return {
        "kind": "phase_composition", "donor": donor,
        "parent_graph_sha256": PARENT_SHA,
        "parent_bbf_lineage_graph_sha256": plans["parent"]["lineage_bbf_graph_sha256"],
        "parent_artifact_manifest_sha256": plans["parent"]["artifact_manifest_sha256"],
        "parent_bbf_artifact_manifest_sha256": plans["parent"]["bbf_artifact_manifest_sha256"],
        "donor_graph_sha256": plan["donor_graph_sha256"],
        "donor_receipt_sha256": plan["donor_receipt_sha256"],
        "donor_artifact_manifest_sha256": plan["artifact_manifest_sha256"],
        "pure_proposal_summary_sha256": plans["source_summary_sha256"],
        "proposal_generator_sha256": plans["proposal_generator_sha256"],
        "phase_one_nets": sorted(phase), "targets": sorted(targets),
        "target_specs": targets, "expected_cells": expected,
        "expected_cell_map_sha256": plan["expected_cell_map_sha256"],
        "pure_candidate_sha256": plan["pure_candidate_sha256"],
        "baseline_xnor2_count": 60, "candidate_xnor2_count": final_xnor,
        "solver_optimality_proven": False, "functional_proof": "NOT_RUN",
        "route": "NOT_RUN", "measurement": "NOT_RUN",
    }


def validate_child(parent_text: str, child_text: str, manifest: dict) -> None:
    expected = derive(parent_text, manifest.get("donor"))
    if manifest != expected:
        raise ValueError("composition manifest differs from fixed donor derivation")
    after = parse_cells(child_text)
    if after != expected["expected_cells"]:
        raise ValueError("composition child full cell map differs from expected candidate")
