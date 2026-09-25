"""Execute the exact six-star replay on b00 without the syndrome2 fold."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from research.ecc_perf_bench.bench_ecc_f1 import parse_routed_area_from_log
from research.ecc_perf_bench.polarity_kernel import XNOR, catalog, derive, parse_cells
from research.ecc_perf_bench.polarity_execute import (
    DENOMINATORS, GOAL, EcoError, file_hash, head, proof_valid, read_json,
    reuse_proof, validate_goal_workloads, validate_parent, write_artifact_manifest,
)
from research.ecc_perf_bench.postroute_star_phase import (
    IMAGE, PROOF_SHA, placement_map, proof, run_openroad, write_json,
)
from research.ecc_perf_bench.no_fold_phase_composition import (
    PARENT_SHA as NOFOLD_PARENT_SHA, derive as derive_phase_composition,
    validate_child as validate_phase_composition_child,
)
from research.ecc_perf_bench.balanced_phase_replay import (
    ACTION as BALANCED_ACTION, PARENT_ID as BALANCED_PARENT_ID,
    PARENT_SHA as BALANCED_PARENT_SHA, derive as derive_balanced_phase,
    validate_child as validate_balanced_phase_child,
    write_targets_tsv as write_balanced_targets_tsv,
)
from research.ecc_perf_bench.n02_xor3_phase import (
    ACTION as N02_XOR3_ACTION, PARENT_ID as N02_XOR3_PARENT_ID,
    PARENT_SHA as N02_XOR3_PARENT_SHA, PURE_PROPOSAL_SHA as N02_XOR3_PROPOSAL_SHA,
    derive as derive_n02_xor3_phase, validate_child as validate_n02_xor3_child,
    write_targets_tsv as write_n02_xor3_targets_tsv, n02_area_check,
)

NOFOLD_PARENT_ID = "67c95564"
NOFOLD_ACTIONS = {"donor_N01", "donor_N02"}
STOP_ACTION = {"kind": "STOP"}

PARENT_SHA = "b00ff2fad85f6648f4e6fc32d15a7c80589e44b6741ba0c543eb5f562d23512f"
PARENT_ID = "b00ff2fa"
ACTION = {"kind": "replay_no_fold"}
PLAN = (
    ("_258_", "_266_", "_271_", "_274_"),
    ("_311_", "_330_"),
)
EXPECTED_CELL_MAP_SHA = "21c828ac318e90b6308d5844d9fd6b7ef23f5465843573744593ea69f6ff2ec7"
PURE_PROPOSAL_SHA = "67c95564bf6e88ae5d732a40be478b0f1099b83cae78c77c06d79e9aefd560cc"
LIBERTY_SHA = "8e78e14442062dba34d414fca6490b2f6b96038d4510d1438ca44fee31487135"
COMPOSITION_MASTER_OUTPUT = {
    "sky130_fd_sc_hd__xor2_1": "X",
    "sky130_fd_sc_hd__xnor2_1": "Y",
}


def cell_map_sha(cells: dict) -> str:
    return hashlib.sha256(json.dumps(cells, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def replay_recipe_paths(repo: Path, is_composition: bool, is_balanced: bool = False,
                        is_n02_xor3: bool = False) -> dict[str, Path]:
    if is_n02_xor3:
        return {
            "eco.tcl": repo / "eda/ecc_n02_xor3_phase/eco.tcl",
            "reroute.tcl": repo / "eda/ecc_phase_assignment/reroute.tcl",
        }
    if is_balanced:
        return {
            "eco.tcl": repo / "eda/ecc_phase_replay_balanced/eco.tcl",
            "reroute.tcl": repo / "eda/ecc_phase_assignment/reroute.tcl",
        }
    directory = "eda/ecc_phase_assignment" if is_composition else "eda/ecc_phase_replay"
    return {name: repo / directory / name for name in ("eco.tcl", "reroute.tcl")}


def write_composition_targets_tsv(path: Path, parent_cells: dict, manifest: dict) -> str:
    targets = manifest.get("targets")
    specs = manifest.get("target_specs")
    if (manifest.get("kind") != "phase_composition" or not isinstance(targets, list)
        or targets != sorted(set(targets)) or not isinstance(specs, dict)
        or set(targets) != set(specs)):
        raise EcoError("composition target specification set is malformed")
    rows = []
    for name in targets:
        spec = specs[name]
        if (not re.fullmatch(r"_\d+_", name) or name not in parent_cells
            or parent_cells[name]["cell"] != spec.get("old_master")
            or spec.get("old_master") not in COMPOSITION_MASTER_OUTPUT
            or spec.get("new_master") not in COMPOSITION_MASTER_OUTPUT
            or spec.get("new_master") == spec.get("old_master")
            or spec.get("old_output_pin") != COMPOSITION_MASTER_OUTPUT[spec["old_master"]]
            or spec.get("new_output_pin") != COMPOSITION_MASTER_OUTPUT[spec["new_master"]]
            or spec["old_output_pin"] not in parent_cells[name]["pins"]):
            raise EcoError(f"invalid bidirectional composition target specification: {name}")
        rows.append("\t".join((name, spec["old_master"], spec["new_master"],
                              spec["old_output_pin"], spec["new_output_pin"])))
    path.write_text("\n".join(rows) + "\n", encoding="ascii")
    return file_hash(path)


def port_signature(text: str) -> tuple:
    module = re.search(r"\bmodule\s+([A-Za-z_]\w*)\s*\((?P<ports>.*?)\)\s*;", text, re.S)
    if module is None:
        raise EcoError("module port header missing")
    ports = tuple(sorted(part.strip() for part in module.group("ports").split(",") if part.strip()))
    declared = {}
    for match in re.finditer(r"(?m)^\s*(input|output|inout)\b([^;]*);", text):
        direction, body = match.groups()
        widths = re.findall(r"\[\s*\d+\s*:\s*\d+\s*\]", body)
        width = re.sub(r"\s+", "", widths[0]) if widths else ""
        body = re.sub(r"\[[^\]]+\]", " ", body)
        body = re.sub(r"\b(wire|reg|logic|signed|unsigned)\b", " ", body)
        for item in body.split(","):
            names = re.findall(r"[A-Za-z_]\w*", item)
            if names:
                name = names[-1]
                value = (direction, width)
                if name in declared and declared[name] != value:
                    raise EcoError("conflicting port declaration")
                declared[name] = value
    if set(ports) != set(declared):
        raise EcoError("module header and port declarations disagree")
    return module.group(1), ports, tuple(sorted(declared.items()))


def fixed_plan(parent_cells: dict) -> dict:
    available = {s["root"]: s for s in catalog(parent_cells)["stars"]}
    selected = [root for batch in PLAN for root in batch]
    if len(selected) != 6 or len(set(selected)) != 6:
        raise EcoError("fixed replay root set changed")
    target_sets = []
    for root in selected:
        star = available.get(root)
        if (star is None or len(star["consumers"]) != 2
            or any(parent_cells[name]["cell"] != XNOR for name in (root, *star["consumers"]))):
            raise EcoError(f"fixed replay star invalid on b00: {root}")
        target_sets.append(set([root, *star["consumers"]]))
    if len(set.union(*target_sets)) != 18 or sum(map(len, target_sets)) != 18:
        raise EcoError("fixed replay stars overlap")
    current = parent_cells
    steps = []
    for roots in PLAN:
        manifest = derive(current, {"kind": "star_batch", "roots": list(roots)})
        steps.append({"action": manifest["action"], "targets": manifest["targets"],
                      "target_specs": manifest["target_specs"],
                      "producer_nets": manifest["producer_nets"]})
        current = manifest["expected_cells"]
    targets = sorted(set(name for step in steps for name in step["targets"]))
    if len(targets) != 18 or cell_map_sha(current) != EXPECTED_CELL_MAP_SHA:
        raise EcoError("fixed replay graph differs from saved pure proposal")
    return {"action": ACTION, "sequential_steps": steps, "targets": targets,
            "target_specs": {name: spec for step in steps for name, spec in step["target_specs"].items()},
            "expected_cells": current, "expected_cell_map_sha256": EXPECTED_CELL_MAP_SHA,
            "pure_proposal_text_sha256": PURE_PROPOSAL_SHA, "functional_proof": "NOT_RUN"}


def validate_child_graph(parent_text: str, child_text: str, manifest: dict) -> None:
    if port_signature(parent_text) != port_signature(child_text):
        raise EcoError("replay changed public module ports")
    before = parse_cells(parent_text)
    if manifest.get("kind") == "phase_composition":
        validate_phase_composition_child(parent_text, child_text, manifest)
        return
    if manifest.get("kind") == "balanced_phase_replay":
        validate_balanced_phase_child(parent_text, child_text, manifest)
        return
    if manifest.get("kind") == "xor3_phase_replay":
        validate_n02_xor3_child(parent_text, child_text, manifest)
        return
    expected = fixed_plan(before)
    if manifest != expected:
        raise EcoError("replay manifest differs from exact parent-derived plan")
    after = parse_cells(child_text)
    if after != manifest["expected_cells"]:
        raise EcoError("replay child full cell map differs from fixed plan")


def validate_native_decision(decision: dict, parent_id: str, action: dict = ACTION) -> None:
    parsed = decision.get("parsed_object")
    if decision.get("http_status") != 200 or not isinstance(parsed, dict):
        raise EcoError("native decision metadata is incomplete")
    if action == ACTION:
        expected_parent = PARENT_ID
    elif action == BALANCED_ACTION:
        expected_parent = BALANCED_PARENT_ID
    elif action == N02_XOR3_ACTION:
        expected_parent = N02_XOR3_PARENT_ID
    elif (isinstance(action, dict) and set(action) == {"kind", "donor"}
          and action.get("kind") == "phase_composition" and action.get("donor") in NOFOLD_ACTIONS):
        expected_parent = NOFOLD_PARENT_ID
    elif action == STOP_ACTION and parent_id in {NOFOLD_PARENT_ID, BALANCED_PARENT_ID,
                                                  N02_XOR3_PARENT_ID}:
        expected_parent = parent_id
    else:
        raise EcoError("native model action is outside the fixed replay and allowed composition actions")
    if parent_id != expected_parent:
        raise EcoError("native model selected a parent outside the fixed replay action binding")
    if action == STOP_ACTION:
        if parsed.get("decision") != "STOP" or parsed.get("parent_id") != parent_id:
            raise EcoError("native model did not STOP on the selected parent")
        return
    if (parsed.get("decision") != "RUN" or parsed.get("parent_id") != parent_id
        or parsed.get("action") != action or not isinstance(parsed.get("reason"), str)):
        raise EcoError("native model did not RUN the fixed replay or allowed fixed action")


R01_REUSE_DIR = "/home/vegapunk/projects/260908_CHIA_Hackathon_artifacts/chia-top1-20260923/R-xor3-critical-phase/run-01/case"
R01_REUSE_MANIFEST = "af54861638e25eaedf52da7f4b0688c174e9647f00b048c40ff2ad3467be9554"
R01_REUSE_RECEIPT = "e9b1f3a82140a7d49df412cfa16bcbc3e00b5ec509880bab634fa3dfbd356086"
R01_SOURCE = "ee8d3fedb504708a8fbcfc299f92a990b81376ad"
R01_PARENT_DIR = "/home/vegapunk/projects/260908_CHIA_Hackathon_artifacts/chia-top1-20260923/P-nofold-phase-complement/run-02/case"
R01_PARENT_HASHES = {
    "routed.v": BALANCED_PARENT_SHA,
    "routed.odb": "e336d882efd607a14d02779419a116d3978a852956164e7c4dd5dedee26be304",
    "routed.spef": "df67bd3697f8d6edbd840db8ec9070e7da3d4cb3ae78dae306536b89fea0f053",
}


def verify_r01_reuse(request: dict, parent: Path, manifest: dict) -> dict:
    ref = request.get("balanced_eco_reuse")
    if ref != {"artifact_dir": R01_REUSE_DIR, "artifact_manifest_sha256": R01_REUSE_MANIFEST,
               "receipt_sha256": R01_REUSE_RECEIPT}:
        raise EcoError("reuse is not bound to the exact R01 attempt")
    if str(parent) != R01_PARENT_DIR or request.get("action") != BALANCED_ACTION:
        raise EcoError("R01 reuse parent or action differs from the original attempt")
    root = Path(R01_REUSE_DIR)
    if root.is_symlink() or not root.is_dir():
        raise EcoError("R01 artifact directory missing or unsafe")

    def checked(name: str) -> Path:
        path = root / name
        if (Path(name).is_absolute() or ".." in Path(name).parts
            or path.is_symlink() or not path.is_file()
            or path.resolve().parent != root.resolve()):
            raise EcoError("R01 evidence file missing or unsafe: " + name)
        return path

    if file_hash(checked("artifact_manifest.json")) != R01_REUSE_MANIFEST:
        raise EcoError("R01 artifact manifest hash mismatch")
    files = read_json(checked("artifact_manifest.json")).get("files")
    if not isinstance(files, list) or len(files) != 21:
        raise EcoError("R01 artifact manifest has an unexpected file set")
    names = [item.get("path") for item in files if isinstance(item, dict)]
    if len(names) != len(files) or len(set(names)) != len(names):
        raise EcoError("R01 artifact manifest has duplicate or malformed paths")
    for item in files:
        if file_hash(checked(item["path"])) != item.get("sha256"):
            raise EcoError("R01 artifact manifest file mismatch: " + item["path"])
    receipt, oldreq = read_json(checked("receipt.json")), read_json(checked("request.json"))
    if (file_hash(checked("receipt.json")) != R01_REUSE_RECEIPT
        or oldreq.get("source_commit") != R01_SOURCE
        or oldreq.get("parent_id") != BALANCED_PARENT_ID
        or oldreq.get("parent_root") != R01_PARENT_DIR
        or oldreq.get("action") != BALANCED_ACTION
        or oldreq.get("expected_parent_sha256") != BALANCED_PARENT_SHA
        or oldreq.get("goal_id") != GOAL or oldreq.get("keep_vcd") is not True
        or oldreq.get("model_decision_path") != request.get("model_decision_path")
        or receipt.get("source_commit") != R01_SOURCE
        or receipt.get("parent_graph_sha256") != BALANCED_PARENT_SHA
        or receipt.get("parent_id") != BALANCED_PARENT_ID
        or receipt.get("parent_root") != R01_PARENT_DIR
        or receipt.get("action") != BALANCED_ACTION
        or receipt.get("goal_id") != GOAL
        or receipt.get("status") != "ERROR_OR_UNKNOWN" or receipt.get("stage") != "eco"
        or receipt.get("actual_chia_identity", {}).get("hostname") != "chia-arm64-eda-02"
        or receipt.get("actual_chia_identity", {}).get("in_ray_worker") is not True
        or receipt.get("eco", {}).get("returncode") != 0
        or receipt.get("eco", {}).get("timed_out") is not False
        or receipt.get("pre_route_proof") is not None
        or receipt.get("final_proof") is not None
        or receipt.get("reroute") is not None
        or receipt.get("measurement") is not None):
        raise EcoError("R01 is not the expected ECO-only result")
    if (file_hash(checked("model_decision.json")) != receipt.get("model_decision_sha256")
        or file_hash(Path(request["model_decision_path"])) != receipt.get("model_decision_sha256")
        or file_hash(checked("parent_receipt.json")) != receipt.get("parent_receipt_sha256")
        or file_hash(parent / "receipt.json") != receipt.get("parent_receipt_sha256")
        or file_hash(checked("parent_binding.json")) != receipt.get("parent_binding_sha256")
        or file_hash(parent / "parent_binding.json") != receipt.get("parent_binding_sha256")
        or file_hash(checked("eco.log")) != receipt.get("eco", {}).get("log_sha256")):
        raise EcoError("R01 model, parent, or ECO log is not bound to the original receipt")
    persisted = read_json(checked("manifest.json"))
    if json.loads(json.dumps(persisted, sort_keys=True)) != json.loads(json.dumps(manifest, sort_keys=True)):
        raise EcoError("R01 action manifest differs from current derivation")
    repo = Path(request["repo_root"]).resolve()
    for recipe in ("eco.tcl", "reroute.tcl"):
        expected = receipt.get("recipe_hashes", {}).get(recipe)
        current = replay_recipe_paths(repo, False, True)[recipe]
        if file_hash(checked(recipe)) != expected or file_hash(current) != expected:
            raise EcoError("R01 original or continuation recipe changed: " + recipe)
    for name, digest in R01_PARENT_HASHES.items():
        original_name = "original_" + name if name != "routed.v" else "original_routed.v"
        if file_hash(parent / name) != digest or file_hash(checked(original_name)) != digest:
            raise EcoError("R01 original or current parent identity mismatch: " + name)
    log = checked("eco.log").read_text(errors="replace")
    if ("CHIA_BALANCED_WIDTH_COMPLETE" not in log
        or "CHIA_BALANCED_WIDTH_DPL_LEGALIZATION_COMPLETE" not in log):
        raise EcoError("R01 ECO/DPL completion marker missing")
    area = balanced_area_check(log)
    validate_child_graph(checked("original_routed.v").read_text(),
                         checked("eco_pre_route.v").read_text(), manifest)
    moved = validate_balanced_placement(checked("original_placement.def"),
                                        checked("eco_placement.def"),
                                        manifest["target_specs"], allow_dpl_movement=True)
    return {"root": root, "area": area, "moved": moved, "receipt": receipt}


S01_REUSE_DIR = "/home/vegapunk/projects/260908_CHIA_Hackathon_artifacts/chia-top1-20260923/S-folded-xor3-phase-20260924/run-01/case"
S01_REUSE_MANIFEST = "8cec1d04c06b9f0a4c2e5b71904dc15475366ba037a6720873c18993d52beede"
S01_REUSE_RECEIPT = "8ef05da527de9e70ab2e48874c3f980eee1ec7a65820dd32f13f6459f480d5a4"
S01_SOURCE = "68fafe35c3c553c9d1adadaad29f3b3551b5cfb4"
S01_PARENT_DIR = "/home/vegapunk/projects/260908_CHIA_Hackathon_artifacts/chia-top1-20260923/N-weighted-phase-assignment/feedback-02/d48cc962484f4e77832c5f2107e3c7db/step-01/artifacts"
S01_PARENT_HASHES = {
    "routed.v": N02_XOR3_PARENT_SHA,
    "routed.odb": "31ac626cd5e0ec76ae39b69ae9b49eb0e4293bda419429a9ca9a07c920452bff",
    "routed.spef": "d62064f949382aa95a4fcd149f24806f6aed3922bd754b025b36c066b8505e0b",
}


def verify_s01_reuse(request: dict, parent: Path, manifest: dict) -> dict:
    if request.get("n02_eco_reuse") != {
        "artifact_dir": S01_REUSE_DIR, "artifact_manifest_sha256": S01_REUSE_MANIFEST,
        "receipt_sha256": S01_REUSE_RECEIPT,
    }:
        raise EcoError("N02 reuse is not bound to the exact S01 attempt")
    if str(parent) != S01_PARENT_DIR or request.get("action") != N02_XOR3_ACTION:
        raise EcoError("S01 reuse parent or action differs from the original attempt")
    root = Path(S01_REUSE_DIR)
    if root.is_symlink() or not root.is_dir():
        raise EcoError("S01 ECO evidence directory missing or unsafe")

    def checked(name: str) -> Path:
        path = root / name
        if (Path(name).is_absolute() or ".." in Path(name).parts
            or path.is_symlink() or not path.is_file()
            or path.resolve().parent != root.resolve()):
            raise EcoError("S01 ECO evidence file missing or unsafe: " + name)
        return path

    if file_hash(checked("artifact_manifest.json")) != S01_REUSE_MANIFEST:
        raise EcoError("S01 ECO artifact manifest changed")
    files = read_json(checked("artifact_manifest.json")).get("files")
    if not isinstance(files, list) or len(files) != 23:
        raise EcoError("S01 ECO artifact file set changed")
    names = [item.get("path") for item in files if isinstance(item, dict)]
    if len(names) != 23 or len(set(names)) != 23:
        raise EcoError("S01 ECO artifact paths are malformed")
    for item in files:
        if file_hash(checked(item["path"])) != item.get("sha256"):
            raise EcoError("S01 ECO artifact file changed: " + item["path"])

    receipt, oldreq = read_json(checked("receipt.json")), read_json(checked("request.json"))
    if (file_hash(checked("receipt.json")) != S01_REUSE_RECEIPT
        or oldreq.get("source_commit") != S01_SOURCE
        or oldreq.get("parent_id") != N02_XOR3_PARENT_ID
        or oldreq.get("parent_root") != S01_PARENT_DIR
        or oldreq.get("expected_parent_sha256") != N02_XOR3_PARENT_SHA
        or oldreq.get("action") != N02_XOR3_ACTION
        or oldreq.get("goal_id") != GOAL or oldreq.get("keep_vcd") is not True
        or oldreq.get("model_decision_path") != request.get("model_decision_path")
        or receipt.get("source_commit") != S01_SOURCE
        or receipt.get("parent_id") != N02_XOR3_PARENT_ID
        or receipt.get("parent_root") != S01_PARENT_DIR
        or receipt.get("parent_graph_sha256") != N02_XOR3_PARENT_SHA
        or receipt.get("action") != N02_XOR3_ACTION or receipt.get("goal_id") != GOAL
        or receipt.get("status") != "ERROR_OR_UNKNOWN" or receipt.get("stage") != "eco"
        or receipt.get("error") != "EcoError: N02 XOR3 DPL placement check report missing"
        or receipt.get("actual_chia_identity", {}).get("hostname") != "chia-arm64-eda-03"
        or receipt.get("actual_chia_identity", {}).get("in_ray_worker") is not True
        or receipt.get("eco", {}).get("returncode") != 0
        or receipt.get("eco", {}).get("timed_out") is not False
        or receipt.get("pre_route_proof") is not None
        or receipt.get("final_proof") is not None
        or receipt.get("reroute") is not None
        or receipt.get("measurement") is not None
        or receipt.get("proof_image") != IMAGE
        or receipt.get("proof_recipe_sha256") != PROOF_SHA
        or receipt.get("liberty_sha256") != LIBERTY_SHA):
        raise EcoError("S01 is not the exact ECO-only result")
    repo = Path(request["repo_root"]).resolve()
    if (file_hash(checked("model_decision.json")) != receipt.get("model_decision_sha256")
        or file_hash(Path(request["model_decision_path"])) != receipt.get("model_decision_sha256")
        or file_hash(checked("parent_receipt.json")) != receipt.get("parent_receipt_sha256")
        or file_hash(parent / "receipt.json") != receipt.get("parent_receipt_sha256")
        or file_hash(checked("eco.log")) != receipt.get("eco", {}).get("log_sha256")
        or file_hash(checked("n02_xor3_phase.py")) != receipt.get("n02_xor3_kernel_sha256")
        or file_hash(repo / "research/ecc_perf_bench/n02_xor3_phase.py") != receipt.get("n02_xor3_kernel_sha256")
        or file_hash(repo / "research/ecc_perf_bench/bench_ecc_routed_three_profile.py")
             != receipt.get("measurement_runner_sha256")):
        raise EcoError("S01 model, parent, source, or ECO log identity changed")
    persisted = read_json(checked("manifest.json"))
    if json.loads(json.dumps(persisted, sort_keys=True)) != json.loads(json.dumps(manifest, sort_keys=True)):
        raise EcoError("S01 action manifest differs from exact current derivation")
    for recipe in ("eco.tcl", "reroute.tcl"):
        expected = receipt.get("recipe_hashes", {}).get(recipe)
        if (file_hash(checked(recipe)) != expected
            or file_hash(replay_recipe_paths(repo, False, False, True)[recipe]) != expected):
            raise EcoError("S01 original or continuation recipe changed: " + recipe)
    for name, digest in S01_PARENT_HASHES.items():
        if file_hash(parent / name) != digest or file_hash(checked("original_" + name)) != digest:
            raise EcoError("S01 original or current parent changed: " + name)
    log = checked("eco.log").read_text(errors="replace")
    if ("CHIA_N02_XOR3_COMPLETE" not in log
        or "CHIA_N02_XOR3_DPL_LEGALIZATION_COMPLETE" not in log):
        raise EcoError("S01 ECO or DPL completion marker missing")
    area = n02_area_check(log)
    if area != receipt.get("n02_area_check"):
        raise EcoError("S01 ECO area receipt differs from OpenROAD log")
    if file_hash(checked("eco_pre_route.v")) != N02_XOR3_PROPOSAL_SHA:
        raise EcoError("S01 ECO candidate differs from pure N02 plan")
    validate_child_graph(checked("original_routed.v").read_text(),
                         checked("eco_pre_route.v").read_text(), manifest)
    moved = validate_n02_xor3_placement(checked("original_placement.def"),
                                        checked("eco_placement.def"),
                                        manifest["target_specs"], allow_dpl_movement=True)
    if not checked("eco_pre_route.odb").is_file():
        raise EcoError("S01 ECO pre-route ODB missing")
    return {"root": root, "area": area, "moved": moved, "receipt": receipt}

def validate_request(request: dict) -> tuple[dict, dict | None]:
    required = {"repo_root", "python", "source_commit", "parent_id", "parent_root",
                "expected_parent_sha256", "action", "model_decision_path", "artifact_dir", "goal_id"}
    if not isinstance(request, dict) or not required.issubset(request):
        raise EcoError("phase replay request fields missing")
    action = request["action"]
    is_legacy = (request["parent_id"] == PARENT_ID and request["expected_parent_sha256"] == PARENT_SHA
                 and action == ACTION)
    is_composition = (
        request["parent_id"] == NOFOLD_PARENT_ID
        and request["expected_parent_sha256"] == NOFOLD_PARENT_SHA
        and isinstance(action, dict) and set(action) == {"kind", "donor"}
        and action.get("kind") == "phase_composition" and action.get("donor") in NOFOLD_ACTIONS
        and request.get("keep_vcd") is True
    )
    is_balanced = (
        request["parent_id"] == BALANCED_PARENT_ID
        and request["expected_parent_sha256"] == BALANCED_PARENT_SHA
        and action == BALANCED_ACTION and request.get("keep_vcd") is True
    )
    is_n02_xor3 = (
        request["parent_id"] == N02_XOR3_PARENT_ID
        and request["expected_parent_sha256"] == N02_XOR3_PARENT_SHA
        and action == N02_XOR3_ACTION and request.get("keep_vcd") is True
    )
    is_stop = (
        action == STOP_ACTION and (
            (request["parent_id"] == NOFOLD_PARENT_ID and request["expected_parent_sha256"] == NOFOLD_PARENT_SHA)
            or (request["parent_id"] == BALANCED_PARENT_ID and request["expected_parent_sha256"] == BALANCED_PARENT_SHA)
            or (request["parent_id"] == N02_XOR3_PARENT_ID and request["expected_parent_sha256"] == N02_XOR3_PARENT_SHA)
        )
    )
    if request["goal_id"] != GOAL or not (is_legacy or is_composition or is_balanced or is_n02_xor3 or is_stop):
        raise EcoError("phase replay goal, parent, or finite action mismatch")
    if (Path(request["python"]).resolve() != Path(sys.executable).resolve()
        or not (Path(sys.prefix) / "conda-meta").is_dir()):
        raise EcoError("request must use active conda Python")
    repo = Path(request["repo_root"]).resolve()
    if head(repo) != request["source_commit"]:
        raise EcoError("source commit differs from repository HEAD")
    parent = Path(request["parent_root"]).resolve()
    if file_hash(parent / "routed.v") != request["expected_parent_sha256"]:
        raise EcoError("parent routed graph SHA mismatch")
    validated = validate_parent(request, repo)
    if request["parent_id"] != N02_XOR3_PARENT_ID:
        binding = read_json(parent / "parent_binding.json")
        if binding.get("liberty_sha256") != LIBERTY_SHA:
            raise EcoError("parent Liberty binding changed")
    if is_legacy:
        manifest = fixed_plan(parse_cells((parent / "routed.v").read_text()))
    elif is_stop:
        manifest = None
    elif is_balanced:
        manifest = derive_balanced_phase((parent / "routed.v").read_text())
    elif is_n02_xor3:
        manifest = derive_n02_xor3_phase((parent / "routed.v").read_text())
        if manifest["liberty_sha256"] != LIBERTY_SHA:
            raise EcoError("N02 XOR3 pinned Liberty evidence changed")
    else:
        manifest = derive_phase_composition((parent / "routed.v").read_text(), action["donor"])
    if is_balanced and "balanced_eco_reuse" in request:
        validated["r01_reuse"] = verify_r01_reuse(request, parent, manifest)
    if is_n02_xor3 and "n02_eco_reuse" in request:
        validated["s01_reuse"] = verify_s01_reuse(request, parent, manifest)
    validate_native_decision(read_json(Path(request["model_decision_path"])), request["parent_id"], action)
    return validated, manifest


def validate_placement(original: Path, after: Path, specs: dict) -> None:
    before_map, after_map = placement_map(original), placement_map(after)
    if before_map.keys() != after_map.keys():
        raise EcoError("replay placement instance set changed")
    for name, old in before_map.items():
        new = after_map[name]
        expected = specs[name]["new_master"] if name in specs else old[0]
        if new[0] != expected or new[1:] != old[1:]:
            raise EcoError(f"replay placement changed unexpectedly: {name}")
        if name in specs and old[0] != specs[name]["old_master"]:
            raise EcoError(f"replay old placement master mismatch: {name}")


def validate_balanced_placement(before_path: Path, after_path: Path, specs: dict,
                                *, allow_dpl_movement: bool, before_is_parent: bool = True) -> list[dict]:
    before, after = placement_map(before_path), placement_map(after_path)
    if before.keys() != after.keys():
        raise EcoError("balanced DPL changed the instance set")
    if set(specs) != {"_326_", "_328_"}:
        raise EcoError("balanced placement received an unexpected target set")
    moved = []
    for name, old in before.items():
        new = after[name]
        spec = specs.get(name)
        expected_master = spec["new_master"] if spec else old[0]
        if new[0] != expected_master:
            raise EcoError(f"balanced placement master mismatch at {name}")
        if spec:
            expected_before = spec["old_master"] if before_is_parent else spec["new_master"]
            if old[0] != expected_before:
                raise EcoError(f"balanced placement before master mismatch at {name}")
        if old[1:] != new[1:]:
            if not allow_dpl_movement:
                raise EcoError(f"post-route placement changed after legalization at {name}")
            moved.append({"instance": name, "target": bool(spec),
                          "old_master": old[0], "new_master": new[0],
                          "old_x_dbu": int(old[1]), "old_y_dbu": int(old[2]),
                          "new_x_dbu": int(new[1]), "new_y_dbu": int(new[2]),
                          "old_orient": old[3], "new_orient": new[3]})
    return moved


def validate_n02_xor3_placement(before_path: Path, after_path: Path, specs: dict,
                                *, allow_dpl_movement: bool,
                                before_is_parent: bool = True) -> list[dict]:
    before, after = placement_map(before_path), placement_map(after_path)
    if before.keys() != after.keys():
        raise EcoError("N02 XOR3 DPL changed the complete instance set")
    exact = {
        "_326_": ("sky130_fd_sc_hd__xor3_1", "sky130_fd_sc_hd__xnor3_1"),
        "_328_": ("sky130_fd_sc_hd__xor3_2", "sky130_fd_sc_hd__xnor3_2"),
    }
    if set(specs) != set(exact):
        raise EcoError("N02 XOR3 placement received an unexpected target set")
    moved = []
    for name, old in before.items():
        new = after[name]
        spec = specs.get(name)
        expected_master = spec["new_master"] if spec else old[0]
        if new[0] != expected_master:
            raise EcoError(f"N02 XOR3 placement master mismatch at {name}")
        if spec:
            if (spec["old_master"], spec["new_master"]) != exact[name]:
                raise EcoError(f"N02 XOR3 target master pair changed at {name}")
            old_expected = spec["old_master"] if before_is_parent else spec["new_master"]
            if old[0] != old_expected:
                raise EcoError(f"N02 XOR3 before master mismatch at {name}")
        if old[1:] != new[1:]:
            if not allow_dpl_movement:
                raise EcoError(f"N02 XOR3 placement changed after legalization at {name}")
            moved.append({"instance": name, "target": bool(spec),
                          "old_master": old[0], "new_master": new[0],
                          "old_x_dbu": int(old[1]), "old_y_dbu": int(old[2]),
                          "new_x_dbu": int(new[1]), "new_y_dbu": int(new[2]),
                          "old_orient": old[3], "new_orient": new[3]})
    return moved


def balanced_area_check(log: str) -> dict:
    match = re.search(r"(?m)^CHIA_BALANCED_WIDTH_AREA_CHECK\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*$", log)
    if not match:
        raise EcoError("balanced ECO omitted its pair/design DB area-balance marker")
    pair_before, pair_after, design_before, design_after = map(int, match.groups())
    if pair_before != pair_after or design_before != design_after:
        raise EcoError("balanced target pair or total design area changed")
    return {"pair_before_dbu2": pair_before, "pair_after_dbu2": pair_after,
            "pair_delta_dbu2": pair_after - pair_before,
            "design_before_dbu2": design_before, "design_after_dbu2": design_after,
            "design_delta_dbu2": design_after - design_before}


def execute(request: dict, identity: dict) -> dict:
    validated, manifest = validate_request(request)
    repo = Path(request["repo_root"]).resolve()
    parent = Path(request["parent_root"]).resolve()
    output = Path(request["artifact_dir"]).resolve()
    if output.exists():
        raise EcoError("unique replay artifact directory already exists")
    is_composition = manifest.get("kind") == "phase_composition"
    is_balanced = manifest.get("kind") == "balanced_phase_replay"
    is_n02_xor3 = manifest.get("kind") == "xor3_phase_replay"
    reuse_balanced_eco = is_balanced and "r01_reuse" in validated
    reuse_n02_eco = is_n02_xor3 and "s01_reuse" in validated
    retain_vcd = is_composition or is_balanced or is_n02_xor3
    recipes = replay_recipe_paths(repo, is_composition, is_balanced, is_n02_xor3)
    parent_sha = request["expected_parent_sha256"]
    record: dict[str, Any] = {
        "kind": "xor3_phase_replay" if is_n02_xor3 else (
            "balanced_phase_replay" if is_balanced else "phase_replay_no_fold"),
        "status": "STARTED", "stage": "intent",
        "source_commit": request["source_commit"], "parent_id": request["parent_id"],
        "parent_root": str(parent), "goal_id": GOAL, "action": request["action"],
        "actual_chia_identity": identity, "parent_graph_sha256": parent_sha,
        "vcd_retention": {"keep_vcd": bool(request.get("keep_vcd", False)),
                          "delete_vcd": not bool(request.get("keep_vcd", False))},
        "parent_receipt_sha256": file_hash(parent / "receipt.json"),
        "parent_binding_sha256": (None if is_n02_xor3 else file_hash(parent / "parent_binding.json")),
        "parent_odb_sha256": validated["hashes"]["eco_routed_odb"],
        "parent_spef_sha256": validated["hashes"]["eco_routed_spef"],
        "parent_proof_log_sha256": validated["receipt"]["final_proof"]["log_sha256"],
        "parent_measurement_meta_sha256": file_hash(parent / "three_profile/measurement_meta.json"),
        "model_decision_sha256": file_hash(Path(request["model_decision_path"])),
        "recipe_hashes": {name: file_hash(path) for name, path in recipes.items()},
        "proof_recipe_sha256": PROOF_SHA, "proof_image": IMAGE, "liberty_sha256": LIBERTY_SHA,
        "measurement_runner_sha256": file_hash(repo / "research/ecc_perf_bench/bench_ecc_routed_three_profile.py"),
        "route_submission_counted": 1, "mapped_submission_counted": 0,
        "expected_cell_map_sha256": manifest.get("expected_cell_map_sha256"),
        "pure_proposal_text_sha256": (
            manifest.get("pure_candidate_sha256") if is_composition
            else (N02_XOR3_PROPOSAL_SHA if is_n02_xor3
                  else (None if is_balanced else PURE_PROPOSAL_SHA))),
    }
    if is_composition:
        record.update(donor=manifest["donor"], phase_one_net_count=len(manifest["phase_one_nets"]),
                      target_count=len(manifest["targets"]),
                      donor_graph_sha256=manifest["donor_graph_sha256"],
                      donor_receipt_sha256=manifest["donor_receipt_sha256"],
                      composition_plan_sha256=file_hash(repo / "research/ecc_perf_bench/no_fold_phase_composition_plans.json"))
    if reuse_balanced_eco:
        reuse = validated["r01_reuse"]
        record.update(eco_reuse_origin_dir=R01_REUSE_DIR,
                      eco_reuse_origin_source_commit="ee8d3fedb504708a8fbcfc299f92a990b81376ad",
                      eco_reuse_origin_manifest_sha256=R01_REUSE_MANIFEST,
                      eco_reuse_origin_receipt_sha256=R01_REUSE_RECEIPT,
                      eco_reuse_moved_instances=reuse["moved"],
                      eco_reuse_origin_chia_identity=reuse["receipt"]["actual_chia_identity"],
                      eco_reuse_origin_eco=reuse["receipt"]["eco"],
                      eco_reuse_status="VERIFIED_COMPLETED_ECO_ONLY")
    if is_balanced:
        record.update(plan=manifest["plan"], target_count=len(manifest["targets"]),
                      balanced_kernel_sha256=file_hash(repo / "research/ecc_perf_bench/balanced_phase_replay.py"),
                      dpl_policy="detailed_placement max_displacement 25um x 10um",
                      target_pair_liberty_area_delta_um2=manifest["liberty_area_delta_um2"],
                      target_pair_width_deltas_um=manifest["per_cell_width_delta_um"],
                      placement_claim="DPL movement recorded; not fixed placement")
    if reuse_n02_eco:
        reuse = validated["s01_reuse"]
        record.update(eco_reuse_origin_dir=S01_REUSE_DIR,
                      eco_reuse_origin_source_commit=S01_SOURCE,
                      eco_reuse_origin_manifest_sha256=S01_REUSE_MANIFEST,
                      eco_reuse_origin_receipt_sha256=S01_REUSE_RECEIPT,
                      eco_reuse_moved_instances=reuse["moved"],
                      eco_reuse_origin_chia_identity=reuse["receipt"]["actual_chia_identity"],
                      eco_reuse_origin_eco=reuse["receipt"]["eco"],
                      eco_reuse_status="VERIFIED_COMPLETED_ECO_ONLY")
    if is_n02_xor3:
        record.update(plan=manifest["plan"], target_count=len(manifest["targets"]),
                      n02_xor3_kernel_sha256=file_hash(repo / "research/ecc_perf_bench/n02_xor3_phase.py"),
                      pure_source_hashes={
                          "proposal": manifest["source_proposal_sha256"],
                          "checker": manifest["source_checker_sha256"],
                          "library": manifest["source_library_sha256"],
                          "artifact_manifest": manifest["source_artifact_manifest_sha256"],
                      },
                      dpl_policy="detailed_placement max_displacement 25um x 10um",
                      target_pair_liberty_area_delta_um2=manifest["liberty_area_delta_um2"],
                      target_pair_db_area_delta_dbu2=manifest["db_area_delta_dbu2"],
                      target_pair_width_deltas_um=manifest["per_cell_width_delta_um"],
                      placement_claim="Both targets shrink; all DPL movement recorded, not fixed placement")
    output.mkdir(parents=True, exist_ok=False)
    os.chmod(output, 0o777)
    receipt = output / "receipt.json"
    write_json(output / "request.json", request)
    write_json(output / "manifest.json", manifest)
    write_json(output / "intent.json", record)
    write_json(receipt, record)
    try:
        for source, name in (
            (parent / "routed.v", "original_routed.v"),
            (parent / "routed.odb", "original_routed.odb"),
            (parent / "routed.spef", "original_routed.spef"),
            (parent / "receipt.json", "parent_receipt.json"),
            (parent / "three_profile/measurement_meta.json", "parent_measurement_meta.json"),
            (Path(request["model_decision_path"]), "model_decision.json"),
        ):
            shutil.copy2(source, output / name)
        if request["parent_id"] != N02_XOR3_PARENT_ID:
            shutil.copy2(parent / "parent_binding.json", output / "parent_binding.json")
        for name, source in recipes.items():
            shutil.copy2(source, output / name)
        if is_composition:
            shutil.copy2(repo / "research/ecc_perf_bench/no_fold_phase_composition_plans.json",
                         output / "no_fold_phase_composition_plans.json")
            record["targets_tsv_sha256"] = write_composition_targets_tsv(
                output / "targets.tsv", parse_cells((parent / "routed.v").read_text()), manifest)
        if is_balanced:
            shutil.copy2(repo / "research/ecc_perf_bench/balanced_phase_replay.py",
                         output / "balanced_phase_replay.py")
            record["targets_tsv_sha256"] = write_balanced_targets_tsv(
                output / "targets.tsv", parse_cells((parent / "routed.v").read_text()), manifest)
        if is_n02_xor3:
            for filename in ("n02_xor3_phase.py", "n02_xor3_phase_source_proposal.json",
                             "n02_xor3_phase_source_checker.json", "n02_xor3_phase_source_library.json"):
                shutil.copy2(repo / "research/ecc_perf_bench" / filename, output / filename)
            record["targets_tsv_sha256"] = write_n02_xor3_targets_tsv(
                output / "targets.tsv", parse_cells((parent / "routed.v").read_text()), manifest)
        write_json(output / "denominator.json", DENOMINATORS)
        record["stage"] = "eco"
        write_json(receipt, record)
        env = None if (is_composition or is_balanced or is_n02_xor3) else {
            "CHIA_REPLAY_TARGETS": " ".join(manifest["targets"])}
        if reuse_balanced_eco:
            reuse = validated["r01_reuse"]
            for src, dstname in (("eco_pre_route.v","eco_pre_route.v"),("eco_pre_route.odb","eco_pre_route.odb"),
                                 ("eco_placement.def","eco_placement.def"),("original_placement.def","original_placement.def"),
                                 ("eco.log","eco_reuse_origin.log"),("receipt.json","eco_reuse_origin/receipt.json"),
                                 ("artifact_manifest.json","eco_reuse_origin/artifact_manifest.json"),
                                 ("request.json","eco_reuse_origin/request.json")):
                dst = output / dstname
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(reuse["root"] / src, dst)
            eco = {"returncode": 0, "status": "REUSED_VERIFIED", "new_run": False,
                   "wall_s": 0.0, "original_wall_s": reuse["receipt"]["eco"]["wall_s"],
                   "origin_source_commit": R01_SOURCE,
                   "origin_log_sha256": reuse["receipt"]["eco"]["log_sha256"],
                   "origin_command": reuse["receipt"]["eco"]["command"]}
            record["balanced_area_check"] = reuse["area"]
        elif reuse_n02_eco:
            reuse = validated["s01_reuse"]
            for src, dstname in (("eco_pre_route.v", "eco_pre_route.v"),
                                 ("eco_pre_route.odb", "eco_pre_route.odb"),
                                 ("eco_placement.def", "eco_placement.def"),
                                 ("original_placement.def", "original_placement.def"),
                                 ("eco.log", "eco_reuse_origin.log"),
                                 ("receipt.json", "eco_reuse_origin/receipt.json"),
                                 ("artifact_manifest.json", "eco_reuse_origin/artifact_manifest.json"),
                                 ("request.json", "eco_reuse_origin/request.json")):
                dst = output / dstname
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(reuse["root"] / src, dst)
            eco = {"returncode": 0, "status": "REUSED_VERIFIED", "new_run": False,
                   "wall_s": 0.0, "original_wall_s": reuse["receipt"]["eco"]["wall_s"],
                   "origin_source_commit": S01_SOURCE,
                   "origin_log_sha256": reuse["receipt"]["eco"]["log_sha256"],
                   "origin_command": reuse["receipt"]["eco"]["command"]}
            record["n02_area_check"] = reuse["area"]
        else:
            eco = run_openroad(output, "eco.tcl", "eco", env)
        record["eco"] = eco
        eco_marker = ("CHIA_N02_XOR3_COMPLETE" if is_n02_xor3 else
                      "CHIA_BALANCED_WIDTH_COMPLETE" if is_balanced else
                      "CHIA_PHASE_ASSIGNMENT_COMPLETE" if is_composition else "CHIA_PHASE_REPLAY_COMPLETE")
        if reuse_balanced_eco or reuse_n02_eco:
            eco_log = (output / "eco_reuse_origin.log").read_text(errors="replace")
        else:
            eco_log = (output / "eco.log").read_text(errors="replace")
            if eco["returncode"] != 0 or eco_marker not in eco_log:
                raise EcoError("replay ECO failed")
        if is_balanced:
            record.setdefault("balanced_area_check", balanced_area_check(eco_log))
            dpl_marker = "CHIA_BALANCED_WIDTH_DPL_LEGALIZATION_COMPLETE"
            if dpl_marker not in eco_log:
                raise EcoError("balanced ECO omitted DPL legalization completion marker")
        if is_n02_xor3:
            record["n02_area_check"] = n02_area_check(eco_log)
            if "CHIA_N02_XOR3_DPL_LEGALIZATION_COMPLETE" not in eco_log:
                raise EcoError("N02 XOR3 ECO omitted DPL legalization marker")
        pre_v = output / "eco_pre_route.v"
        if not (output / "eco_pre_route.odb").is_file():
            raise EcoError("replay ECO ODB missing")
        validate_child_graph((output / "original_routed.v").read_text(), pre_v.read_text(), manifest)
        if is_balanced:
            moved = validate_balanced_placement(output / "original_placement.def",
                                                output / "eco_placement.def",
                                                manifest["target_specs"], allow_dpl_movement=True)
            record["dpl_moved_instances"] = moved
            record["dpl_moved_instance_count"] = len(moved)
            before_map, after_map = placement_map(output / "original_placement.def"), placement_map(output / "eco_placement.def")
            record["balanced_target_placements"] = {
                name: {"parent": before_map[name], "after_dpl": after_map[name]}
                for name in manifest["targets"]
            }
            movement_receipt = {
                "placement_policy": "controlled detailed placement; movement is expected and recorded",
                "moved_instances": moved,
                "balanced_target_placements": record["balanced_target_placements"],
            }
            write_json(output / "dpl_moved_instances.json", movement_receipt)
            record["dpl_moved_instances_sha256"] = file_hash(output / "dpl_moved_instances.json")
            record["placement_guard"] = "DPL_LEGALIZED_MOVEMENTS_RECORDED"
        elif is_n02_xor3:
            moved = validate_n02_xor3_placement(output / "original_placement.def",
                                                 output / "eco_placement.def",
                                                 manifest["target_specs"], allow_dpl_movement=True)
            record["dpl_moved_instances"] = moved
            record["dpl_moved_instance_count"] = len(moved)
            before_map = placement_map(output / "original_placement.def")
            after_map = placement_map(output / "eco_placement.def")
            record["n02_target_placements"] = {
                name: {"parent": before_map[name], "after_dpl": after_map[name]}
                for name in manifest["targets"]
            }
            write_json(output / "dpl_moved_instances.json", {
                "placement_policy": "controlled detailed placement; all movement recorded",
                "moved_instances": moved,
                "n02_target_placements": record["n02_target_placements"],
            })
            record["dpl_moved_instances_sha256"] = file_hash(output / "dpl_moved_instances.json")
            record["placement_guard"] = "DPL_LEGALIZED_MOVEMENTS_RECORDED"
        else:
            validate_placement(output / "original_placement.def", output / "eco_placement.def",
                               manifest["target_specs"])
            record["placement_guard"] = "PASS"
        record["stage"] = "pre_route_proof"
        write_json(receipt, record)
        pre = proof(output, "pre_route_proof", output / "original_routed.v", pre_v,
                    repo / "eda/ecc_f1/ecc_f1_equivalence.ys")
        record["pre_route_proof"] = pre
        if not proof_valid(pre):
            raise EcoError(f"replay pre-route proof was {pre['status']}")
        record["stage"] = "reroute"
        write_json(receipt, record)
        route = run_openroad(output, "reroute.tcl", "reroute")
        record["reroute"] = route
        log = (output / "reroute.log").read_text(errors="replace")
        marker_prefix = "CHIA_PHASE_ASSIGNMENT" if (is_composition or is_balanced or is_n02_xor3) else "CHIA_PHASE_REPLAY"
        markers = (f"{marker_prefix}_ROUTING_SDC 2.575 0.05 0.005",
                   f"{marker_prefix}_OLD_SIGNAL_WIRES_CLEARED",
                   f"{marker_prefix}_PLACEMENT_CHECKED",
                   f"{marker_prefix}_RCX_COMPLETE")
        if route["returncode"] != 0 or any(marker not in log for marker in markers):
            raise EcoError("replay fresh route, wire clearance, or RCX failed")
        routed_v, routed_spef = output / "routed.v", output / "routed.spef"
        if not (output / "routed.odb").is_file() or file_hash(routed_spef) == validated["hashes"]["eco_routed_spef"]:
            raise EcoError("replay fresh ODB or SPEF missing")
        validate_child_graph((output / "original_routed.v").read_text(), routed_v.read_text(), manifest)
        if parse_cells(pre_v.read_text()) != parse_cells(routed_v.read_text()):
            raise EcoError("replay route changed logic graph")
        if is_balanced:
            validate_balanced_placement(output / "eco_placement.def", output / "routed_placement.def",
                                        manifest["target_specs"], allow_dpl_movement=False,
                                        before_is_parent=False)
        elif is_n02_xor3:
            validate_n02_xor3_placement(output / "eco_placement.def",
                                        output / "routed_placement.def",
                                        manifest["target_specs"], allow_dpl_movement=False,
                                        before_is_parent=False)
        else:
            validate_placement(output / "original_placement.def", output / "routed_placement.def",
                               manifest["target_specs"])
        record["stage"] = "final_proof"
        write_json(receipt, record)
        if pre_v.read_bytes() == routed_v.read_bytes():
            final = reuse_proof(output, pre, file_hash(output / "original_routed.v"),
                                file_hash(routed_v), PROOF_SHA)
        else:
            final = proof(output, "final_proof", output / "original_routed.v", routed_v,
                          repo / "eda/ecc_f1/ecc_f1_equivalence.ys")
        record["final_proof"] = final
        if not proof_valid(final):
            raise EcoError(f"replay final proof was {final['status']}")
        area = parse_routed_area_from_log(output / "reroute.log")
        if area is None:
            raise EcoError("replay routed area missing")
        command = [request["python"], str(repo / "research/ecc_perf_bench/bench_ecc_routed_three_profile.py"),
                   "--repo-root", str(repo), "--routed-netlist", str(routed_v), "--spef", str(routed_spef),
                   "--artifact-dir", str(output / "three_profile"), "--width", "64", "--python", request["python"],
                   "--cpus", "2", "--denominator-json", str(output / "denominator.json"),
                   "--delay-ceiling", "2.40", "--routed-area-um2", str(area), "--power-diagnostic"]
        if retain_vcd:
            command.append("--keep-vcd")
        record["stage"] = "measurement"
        write_json(receipt, record)
        started = time.monotonic()
        measured = subprocess.run(command, capture_output=True, text=True, check=False)
        (output / "measurement.log").write_text(measured.stdout + measured.stderr, encoding="utf-8")
        record.update(measurement_command=command, measurement_exit_code=measured.returncode,
                      measurement_wall_s=round(time.monotonic() - started, 3))
        summary = read_json(output / "three_profile/routed_3p_summary.json")
        record["measurement"] = summary
        meta = read_json(output / "three_profile/measurement_meta.json")
        validate_goal_workloads(meta)
        profiles = summary.get("per_profile", {})
        if (measured.returncode != 0 or summary.get("measurement_valid") is not True
            or summary.get("denominator_energies") != DENOMINATORS
            or meta.get("width") != 64 or meta.get("count") != 1024
            or meta.get("interval_ps") != 10000
            or meta.get("input_slew_ns") != 0.05 or meta.get("output_load_pf") != 0.005
            or meta.get("vcd_retained") is not retain_vcd
            or meta.get("netlist_sha256") != file_hash(routed_v)
            or meta.get("spef_sha256") != file_hash(routed_spef)
            or summary.get("hashes", {}).get("routed_netlist") != file_hash(routed_v)
            or summary.get("hashes", {}).get("spef") != file_hash(routed_spef)
            or not isinstance(profiles, dict) or set(profiles) != set(DENOMINATORS)
            or any(profiles[name].get("valid") is not True
                   or profiles[name].get("completed") != 1024
                   or (retain_vcd and not (output / "three_profile" / f"activity_{name}.vcd").is_file())
                   or profiles[name].get("oracle_mismatches") != 0
                   or profiles[name].get("vcd_sha256") != summary.get("hashes", {}).get("vcd", {}).get(name)
                   for name in DENOMINATORS)):
            raise EcoError("replay fresh three-profile measurement invalid")
        record.update(
            status="OK", stage="complete", functional_valid=True, route_valid=True,
            measurement_valid=True, feasible=summary.get("feasible") is True,
            routed_delay_ns=summary.get("routed_delay_ns"), routed_area_um2=area,
            raw_energies_pj=summary.get("raw_energies_pj"), j_score=summary.get("j_score"),
            measurement=summary,
            hashes={"eco_pre_route": file_hash(pre_v), "eco_routed_netlist": file_hash(routed_v),
                    "eco_routed_odb": file_hash(output / "routed.odb"),
                    "eco_routed_spef": file_hash(routed_spef),
                    "final_proof_log": final["log_sha256"]},
        )
        write_json(receipt, record)
        write_artifact_manifest(output)
        return record
    except Exception as exc:
        if is_balanced or is_n02_xor3:
            functional, measurement_valid = balanced_failure_flags(record)
        else:
            functional, measurement_valid = False, False
        record.update(status="ERROR_OR_UNKNOWN", error=f"{type(exc).__name__}: {exc}",
                      functional_valid=functional, route_valid=False,
                      measurement_valid=measurement_valid)
        write_json(receipt, record)
        write_artifact_manifest(output)
        return record


def balanced_failure_flags(record: dict) -> tuple[bool | None, bool | None]:
    final = record.get("final_proof")
    pre = record.get("pre_route_proof")
    if isinstance(final, dict) and final.get("status") in {"PASS", "FAIL"}:
        functional = final.get("status") == "PASS"
    elif isinstance(pre, dict) and pre.get("status") == "FAIL":
        functional = False
    else:
        functional = None
    measurement = None
    summary = record.get("measurement")
    if isinstance(summary, dict) and isinstance(summary.get("measurement_valid"), bool):
        measurement = summary["measurement_valid"]
    return functional, measurement


def result_summary(record: dict, request: dict) -> dict:
    keys = ("status", "stage", "error", "functional_valid", "measurement_valid", "route_valid",
            "feasible", "routed_delay_ns", "routed_area_um2", "raw_energies_pj", "j_score",
            "hashes", "actual_chia_identity", "source_commit", "parent_id", "parent_root",
            "action", "goal_id", "dpl_moved_instance_count", "n02_area_check")
    result = {key: record.get(key) for key in keys}
    artifact = Path(request["artifact_dir"]).resolve()
    result.update(artifact_dir=str(artifact), receipt_path=str(artifact / "receipt.json"),
                  artifact_manifest_path=str(artifact / "artifact_manifest.json"))
    return result
