"""Execute one proof-bound W64 XOR/XNOR phase action on a routed parent."""

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
from research.ecc_perf_bench.polarity_kernel import derive, parse_cells, validate_child
from research.ecc_perf_bench.postroute_star_phase import (
    EcoError, IMAGE, PROOF_SHA, file_hash, placement_map, proof, run_openroad, write_json,
)

GOAL = "routed3_w64_d240_b271F0_v1"
DENOMINATORS = {
    "stress_encoded": 2.541007707,
    "valid_uniform": 2.027927403,
    "valid_low_toggle": 0.4358843944,
}
GOAL_SEED = 2026092101
GOAL_WORKLOAD_HASHES = {
    "stress_encoded": {
        "content_sha256": "3964b97076ff47713916b0bd3eed4804f78173efd6ba19c58b2bd3fb56a2e28e",
        "vectors_sha256": "7535ac11bc88eb2a7de116acd1984072634039c735c45a2872d9010650389658",
    },
    "valid_uniform": {
        "content_sha256": "965d54a194f5439fbe1348b9ee54f7a443ca102083d76b0949790376db328809",
        "vectors_sha256": "3c5c8ec1dbf34aca4e4580d82fc5e4bf9173e303ab47dec147020eb752e5cd68",
    },
    "valid_low_toggle": {
        "content_sha256": "6381ed9378cbff6a128125ab39d2314661794a2ae07d45e2e6fc7cd1cbf73a9d",
        "vectors_sha256": "35dc1f61f762ff270dd61998033405cb47b1850561a8118961c06d1e0c77235f",
    },
}
INSTANCE = re.compile(r"^_\d+_$")
SHA = re.compile(r"^[0-9a-f]{64}$")
MARKER = "SAT proof finished - no model found: SUCCESS!"
SUPPORTED_PARENT_RECEIPT_KINDS = frozenset({
    "e5e_local_phase", "mixed_phase", "phase_batch", "star_phase",
    "polarity_action", "syndrome2_fold", "phase_timing_repair",
    "bounded_phase_assignment", "phase_replay_no_fold", "balanced_phase_replay",
    "xor3_phase_replay",
})


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise EcoError(f"JSON object required: {path}")
    return value


def head(repo: Path) -> str:
    return subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()


def validate_request(request: dict) -> dict:
    required = {
        "repo_root", "python", "source_commit", "parent_id", "parent_root",
        "expected_parent_sha256", "action", "model_decision_path", "artifact_dir", "goal_id",
    }
    if not isinstance(request, dict) or not required.issubset(request):
        raise EcoError("request fields missing")
    if request["goal_id"] != GOAL:
        raise EcoError("unsupported goal")
    if not SHA.fullmatch(str(request["expected_parent_sha256"])):
        raise EcoError("invalid parent SHA")
    if not isinstance(request["parent_id"], str) or not request["parent_id"]:
        raise EcoError("parent ID missing")
    repo = Path(request["repo_root"]).resolve()
    if head(repo) != request["source_commit"]:
        raise EcoError("source commit differs from repository HEAD")
    if (Path(request["python"]).resolve() != Path(sys.executable).resolve()
        or not (Path(sys.prefix) / "conda-meta").is_dir()):
        raise EcoError("request must use the active conda Python")
    parent = Path(request["parent_root"]).resolve()
    graph = parent / "routed.v"
    if file_hash(graph) != request["expected_parent_sha256"]:
        raise EcoError("expected parent SHA differs from routed.v")
    cells = parse_cells(graph.read_text(encoding="utf-8"))
    manifest = derive(cells, request["action"])
    if not manifest["targets"] or any(not INSTANCE.fullmatch(name) for name in manifest["targets"]):
        raise EcoError("unsafe target instance name")
    decision = read_json(Path(request["model_decision_path"]))
    parsed = decision.get("parsed_object")
    if decision.get("http_status") != 200 or not isinstance(parsed, dict):
        raise EcoError("model response is not native HTTP 200 object")
    if parsed.get("decision") != "RUN" or parsed.get("parent_id") != request["parent_id"]:
        raise EcoError("model decision or parent ID mismatch")
    if not isinstance(parsed.get("reason"), str):
        raise EcoError("model reason missing")
    if derive(cells, parsed.get("action"))["action"] != manifest["action"]:
        raise EcoError("model action does not match normalized request action")
    return manifest


def validate_goal_workloads(meta: dict) -> None:
    if meta.get("seed") != GOAL_SEED:
        raise EcoError("parent workload seed differs from fixed goal")
    workloads = meta.get("workloads")
    if not isinstance(workloads, dict) or set(workloads) != set(GOAL_WORKLOAD_HASHES):
        raise EcoError("parent workload profiles differ from fixed goal")
    for name, expected in GOAL_WORKLOAD_HASHES.items():
        item = workloads[name]
        if (not isinstance(item, dict)
            or item.get("profile") != name
            or item.get("profile_kind") != "energy"
            or item.get("expected_completions") != 1024
            or item.get("intended_interval_ps") != 10000
            or any(item.get(key) != value for key, value in expected.items())):
            raise EcoError(f"parent workload identity differs from fixed goal: {name}")


def validate_parent(request: dict, repo: Path) -> dict:
    parent = Path(request["parent_root"]).resolve()
    receipt = read_json(parent / "receipt.json")
    if receipt.get("kind") not in SUPPORTED_PARENT_RECEIPT_KINDS:
        raise EcoError("parent is not a supported postroute ECO receipt")
    hashes = receipt.get("hashes", {})
    for name, key in (
        ("routed.v", "eco_routed_netlist"),
        ("routed.odb", "eco_routed_odb"),
        ("routed.spef", "eco_routed_spef"),
    ):
        if file_hash(parent / name) != hashes.get(key):
            raise EcoError(f"parent {name} hash differs from receipt")
    if hashes["eco_routed_netlist"] != request["expected_parent_sha256"]:
        raise EcoError("parent graph hash differs from expected SHA")
    final = receipt.get("final_proof", {})
    proof_dir = parent / "final_proof"
    if (receipt.get("status") != "OK" or final.get("status") != "PASS"
        or final.get("complete_marker") is not True or final.get("exit_code") != "0"
        or (proof_dir / "proof-exit_code").read_text().strip() != "0"
        or MARKER not in (proof_dir / "proof.log").read_text()
        or file_hash(proof_dir / "proof.log") != final.get("log_sha256")
        or file_hash(proof_dir / "proof.log") != hashes.get("final_proof_log")
        or file_hash(proof_dir / "routed.v") != hashes["eco_routed_netlist"]
        or file_hash(proof_dir / "f1-equivalence.ys") != PROOF_SHA
        or file_hash(proof_dir / "pre_repair.v") != receipt.get("parent_graph_sha256")):
        raise EcoError("parent final whole-output proof is incomplete or unbound")
    recipe = repo / "eda/ecc_f1/ecc_f1_equivalence.ys"
    if file_hash(recipe) != PROOF_SHA:
        raise EcoError("whole-output proof recipe changed")
    measurement = receipt.get("measurement", {})
    meta = read_json(parent / "three_profile" / "measurement_meta.json")
    validate_goal_workloads(meta)
    if (measurement.get("measurement_valid") is not True
        or measurement.get("denominator_energies") != DENOMINATORS
        or meta.get("width") != 64 or meta.get("count") != 1024
        or meta.get("interval_ps") != 10000
        or meta.get("input_slew_ns") != 0.05
        or meta.get("output_load_pf") != 0.005
        or meta.get("netlist_sha256") != hashes["eco_routed_netlist"]
        or meta.get("spef_sha256") != hashes["eco_routed_spef"]
        or measurement.get("hashes", {}).get("routed_netlist") != hashes["eco_routed_netlist"]
        or measurement.get("hashes", {}).get("spef") != hashes["eco_routed_spef"]):
        raise EcoError("parent W64 three-profile measurement context invalid")
    return {"receipt": receipt, "hashes": hashes, "meta": meta}


def validate_placement(before_path: Path, after_path: Path, specs: dict) -> None:
    before, after = placement_map(before_path), placement_map(after_path)
    if before.keys() != after.keys():
        raise EcoError("placement instance set changed")
    for name, old in before.items():
        new = after[name]
        expected = specs[name]["new_master"] if name in specs else old[0]
        if new[0] != expected or new[1:] != old[1:]:
            raise EcoError(f"placement changed unexpectedly: {name}")
        if name in specs and old[0] != specs[name]["old_master"]:
            raise EcoError(f"old placement master mismatch: {name}")


def proof_valid(item: dict) -> bool:
    return (item.get("status") == "PASS" and item.get("complete_marker") is True
            and item.get("exit_code") == "0" and SHA.fullmatch(str(item.get("log_sha256"))) is not None)


def reuse_proof(output: Path, pre: dict, parent_sha: str, graph_sha: str, recipe_sha: str) -> dict:
    source = Path(pre["artifact_dir"])
    if not proof_valid(pre):
        raise EcoError("pre-route proof cache is not valid")
    if (file_hash(source / "pre_repair.v") != parent_sha
        or file_hash(source / "routed.v") != graph_sha
        or file_hash(source / "f1-equivalence.ys") != recipe_sha
        or file_hash(source / "proof.log") != pre["log_sha256"]
        or (source / "proof-exit_code").read_text().strip() != "0"
        or MARKER not in (source / "proof.log").read_text()):
        raise EcoError("pre-route proof cache inputs or result changed")
    target = output / "final_proof"
    target.mkdir(exist_ok=False)
    for name in ("pre_repair.v", "routed.v", "f1-equivalence.ys", "proof.log", "proof-exit_code"):
        shutil.copy2(source / name, target / name)
    return {**pre, "artifact_dir": str(target), "new_run": False,
            "original_wall_s": pre.get("wall_s"), "wall_s": 0.0,
            "reused_from": {"artifact_dir": str(source), "log_sha256": pre["log_sha256"],
                            "parent_sha256": parent_sha, "child_sha256": graph_sha,
                            "proof_recipe_sha256": recipe_sha, "image": IMAGE}}


def write_artifact_manifest(output: Path) -> Path:
    path = output / "artifact_manifest.json"
    files = [
        {"path": str(candidate.relative_to(output)), "sha256": file_hash(candidate)}
        for candidate in sorted(output.rglob("*"))
        if candidate.is_file() and candidate != path
    ]
    write_json(path, {"files": files})
    return path


def execute(request: dict, identity: dict | None = None) -> dict:
    repo = Path(request["repo_root"]).resolve()
    parent = Path(request["parent_root"]).resolve()
    output = Path(request["artifact_dir"]).resolve()
    if output.exists():
        raise EcoError("unique artifact directory already exists")
    manifest = validate_request(request)
    validated = validate_parent(request, repo)
    recipes = {name: repo / "eda/ecc_polarity_action" / name for name in ("eco.tcl", "reroute.tcl")}
    recipe_hashes = {name: file_hash(path) for name, path in recipes.items()}
    decision_path = Path(request["model_decision_path"])
    parent_receipt = parent / "receipt.json"
    record: dict[str, Any] = {
        "kind": "polarity_action", "status": "STARTED", "stage": "intent",
        "source_commit": request["source_commit"], "parent_id": request["parent_id"],
        "parent_root": str(parent), "parent_graph_sha256": request["expected_parent_sha256"],
        "parent_receipt_sha256": file_hash(parent_receipt),
        "parent_odb_sha256": validated["hashes"]["eco_routed_odb"],
        "parent_spef_sha256": validated["hashes"]["eco_routed_spef"],
        "parent_proof_log_sha256": validated["receipt"]["final_proof"]["log_sha256"],
        "parent_measurement_meta_sha256": file_hash(parent / "three_profile" / "measurement_meta.json"),
        "model_decision_sha256": file_hash(decision_path), "proof_recipe_sha256": PROOF_SHA,
        "proof_image": IMAGE, "recipe_hashes": recipe_hashes,
        "measurement_runner_sha256": file_hash(repo / "research/ecc_perf_bench/bench_ecc_routed_three_profile.py"),
        "goal_id": GOAL, "action": manifest["action"],
        "target_specs": manifest["target_specs"], "actual_chia_identity": identity,
        "route_submission_counted": 1, "mapped_submission_counted": 0,
    }
    output.mkdir(parents=True, exist_ok=False)
    os.chmod(output, 0o777)
    receipt_path = output / "receipt.json"
    write_json(output / "request.json", request)
    write_json(output / "manifest.json", manifest)
    write_json(output / "intent.json", record)
    write_json(receipt_path, record)
    try:
        for source, dest in (
            (parent / "routed.v", "original_routed.v"),
            (parent / "routed.odb", "original_routed.odb"),
            (parent / "routed.spef", "original_routed.spef"),
            (parent_receipt, "parent_receipt.json"),
            (decision_path, "model_decision.json"),
            (parent / "three_profile" / "measurement_meta.json", "parent_measurement_meta.json"),
        ):
            shutil.copy2(source, output / dest)
        for name, path in recipes.items():
            shutil.copy2(path, output / name)
        with (output / "targets.tsv").open("w", encoding="ascii") as handle:
            for name in manifest["targets"]:
                spec = manifest["target_specs"][name]
                handle.write("\t".join((name, spec["old_master"], spec["new_master"],
                                        spec["old_output_pin"], spec["new_output_pin"])) + "\n")
        write_json(output / "denominator.json", DENOMINATORS)
        record["stage"] = "eco"
        write_json(receipt_path, record)
        eco = run_openroad(output, "eco.tcl", "eco")
        record["eco"] = eco
        log = (output / "eco.log").read_text(errors="replace")
        if eco["returncode"] != 0 or "CHIA_POLARITY_ACTION_COMPLETE" not in log:
            raise EcoError("phase ECO failed")
        validate_placement(output / "original_placement.def", output / "eco_placement.def",
                           manifest["target_specs"])
        pre_v = output / "eco_pre_route.v"
        if not (output / "eco_pre_route.odb").is_file():
            raise EcoError("phase ECO omitted ODB")
        validate_child(parse_cells((output / "original_routed.v").read_text()),
                       parse_cells(pre_v.read_text()), manifest)
        record["placement_guard"] = "PASS"
        record["cell_change"] = {"modified_instances": manifest["targets"]}
        record["stage"] = "pre_route_proof"
        write_json(receipt_path, record)
        pre = proof(output, "pre_route_proof", output / "original_routed.v", pre_v,
                    repo / "eda/ecc_f1/ecc_f1_equivalence.ys")
        record["pre_route_proof"] = pre
        if not proof_valid(pre):
            raise EcoError(f"pre-route proof was {pre['status']}")
        record["stage"] = "reroute"
        write_json(receipt_path, record)
        routed = run_openroad(output, "reroute.tcl", "reroute")
        record["reroute"] = routed
        route_log = (output / "reroute.log").read_text(errors="replace")
        markers = ("CHIA_POLARITY_ACTION_ROUTING_SDC 2.575 0.05 0.005",
                   "CHIA_POLARITY_ACTION_OLD_SIGNAL_WIRES_CLEARED",
                   "CHIA_POLARITY_ACTION_PLACEMENT_CHECKED",
                   "CHIA_POLARITY_ACTION_RCX_COMPLETE")
        if routed["returncode"] != 0 or any(marker not in route_log for marker in markers):
            raise EcoError("fresh route, signal wire clearance, or RCX failed")
        routed_v, routed_spef = output / "routed.v", output / "routed.spef"
        if not (output / "routed.odb").is_file() or file_hash(routed_spef) == validated["hashes"]["eco_routed_spef"]:
            raise EcoError("fresh ODB or SPEF missing")
        validate_child(parse_cells((output / "original_routed.v").read_text()),
                       parse_cells(routed_v.read_text()), manifest)
        if parse_cells(pre_v.read_text()) != parse_cells(routed_v.read_text()):
            raise EcoError("reroute changed logic graph")
        validate_placement(output / "original_placement.def", output / "routed_placement.def",
                           manifest["target_specs"])
        record["stage"] = "final_proof"
        write_json(receipt_path, record)
        if file_hash(pre_v) == file_hash(routed_v):
            final = reuse_proof(output, pre, file_hash(output / "original_routed.v"),
                                file_hash(routed_v), PROOF_SHA)
        else:
            final = proof(output, "final_proof", output / "original_routed.v", routed_v,
                          repo / "eda/ecc_f1/ecc_f1_equivalence.ys")
        record["final_proof"] = final
        if not proof_valid(final):
            raise EcoError(f"final routed proof was {final['status']}")
        area = parse_routed_area_from_log(output / "reroute.log")
        if area is None:
            raise EcoError("fresh routed area missing")
        record["stage"] = "measurement"
        write_json(receipt_path, record)
        command = [request["python"], str(repo / "research/ecc_perf_bench/bench_ecc_routed_three_profile.py"),
                   "--repo-root", str(repo), "--routed-netlist", str(routed_v), "--spef", str(routed_spef),
                   "--artifact-dir", str(output / "three_profile"), "--width", "64", "--python", request["python"],
                   "--cpus", "2", "--denominator-json", str(output / "denominator.json"),
                   "--delay-ceiling", "2.40", "--routed-area-um2", str(area), "--power-diagnostic"]
        started = time.monotonic()
        process = subprocess.run(command, capture_output=True, text=True, check=False)
        (output / "measurement.log").write_text(process.stdout + process.stderr, encoding="utf-8")
        record["measurement_command"] = command
        record["measurement_exit_code"] = process.returncode
        record["measurement_wall_s"] = round(time.monotonic() - started, 3)
        summary = read_json(output / "three_profile" / "routed_3p_summary.json")
        record["measurement"] = summary
        if (process.returncode != 0 or summary.get("measurement_valid") is not True
            or summary.get("denominator_energies") != DENOMINATORS
            or summary.get("hashes", {}).get("routed_netlist") != file_hash(routed_v)
            or summary.get("hashes", {}).get("spef") != file_hash(routed_spef)):
            raise EcoError("fresh three-profile measurement invalid")
        record.update(
            status="OK", stage="complete", functional_valid=True, measurement_valid=True,
            route_valid=True, feasible=summary.get("feasible") is True,
            routed_delay_ns=summary.get("routed_delay_ns"), routed_area_um2=area,
            raw_energies_pj=summary.get("raw_energies_pj"), j_score=summary.get("j_score"),
            hashes={"eco_pre_route": file_hash(pre_v),
                    "eco_routed_netlist": file_hash(routed_v),
                    "eco_routed_odb": file_hash(output / "routed.odb"),
                    "eco_routed_spef": file_hash(routed_spef),
                    "final_proof_log": final["log_sha256"]},
        )
        write_json(receipt_path, record)
        write_artifact_manifest(output)
        return record
    except Exception as exc:
        record.update(status="ERROR_OR_UNKNOWN", error=f"{type(exc).__name__}: {exc}",
                      functional_valid=False, measurement_valid=False, route_valid=False)
        write_json(receipt_path, record)
        write_artifact_manifest(output)
        return record


def result_summary(record: dict, request: dict) -> dict:
    keys = ("status", "functional_valid", "measurement_valid", "route_valid",
            "feasible", "routed_delay_ns", "routed_area_um2", "raw_energies_pj",
            "j_score", "hashes", "actual_chia_identity", "source_commit", "parent_id",
            "parent_root", "action", "goal_id", "stage", "error")
    result = {key: record.get(key) for key in keys}
    result["receipt_path"] = str(Path(request["artifact_dir"]).resolve() / "receipt.json")
    result["artifact_dir"] = str(Path(request["artifact_dir"]).resolve())
    result["artifact_manifest_path"] = str(Path(request["artifact_dir"]).resolve() / "artifact_manifest.json")
    return result
