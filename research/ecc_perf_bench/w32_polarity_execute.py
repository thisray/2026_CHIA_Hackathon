"""Execute one native-selected W32 same-footprint XOR/XNOR star batch."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from research.ecc_perf_bench.bench_ecc_f1 import parse_routed_area_from_log
from research.ecc_perf_bench.polarity_kernel import XNOR, catalog, derive, parse_cells, validate_child
from research.ecc_perf_bench.polarity_execute import (
    EcoError, file_hash, head, proof_valid, read_json, reuse_proof, write_artifact_manifest,
)
from research.ecc_perf_bench.postroute_star_phase import (
    IMAGE, PROOF_SHA, placement_map, proof, run_openroad, write_json,
)

PARENT_SHA = "18644d78fe11fa5859ca7f882313e18969dec467d433f1e7b85adab7a8f66aec"
PARENT_ID = "18644d78-w32"
GOAL = "routed3_w32_d240_maskedF0_v1"
REFERENCE = "ecc_masked_reduction::F0::routed3_w32_v1"
LIBERTY_SHA = "8e78e14442062dba34d414fca6490b2f6b96038d4510d1438ca44fee31487135"
DENOMINATORS = {
    "stress_encoded": 1.595184585,
    "valid_uniform": 1.140097229,
    "valid_low_toggle": 0.32781139449999996,
    "width": 32,
}
THREE_DENOMINATORS = {key: value for key, value in DENOMINATORS.items() if key != "width"}
WORKLOAD_HASHES = {
    "stress_encoded": {
        "content_sha256": "77e642a37e9ae44e13260e2b5fd12887d88b8d4eb1de66df29e157cd63850b34",
        "vectors_sha256": "6843543c69fd5c61fd3dc2c34ad5ad0823a09247b9b3b425d54bd1e364ccecdf",
    },
    "valid_uniform": {
        "content_sha256": "fbe631e49dac8be5224e798c66b80f47e660cfe507b738bb510c65e9aa13d233",
        "vectors_sha256": "083b237e51e5c76e7758060f5a537497c97d8b9ca62d68a6ca573dbdd530487d",
    },
    "valid_low_toggle": {
        "content_sha256": "f1cc46eefb0dc32c4f2e0f67af0e95fa701d6c577717444dc8f7e9dda0005a52",
        "vectors_sha256": "98009b595f270217038f2b4272ef075bd7a816cec331eb2171b25998117d3a8d",
    },
}


def validate_workload_context(meta: dict) -> None:
    fixed = {"width": 32, "seed": 2026092101, "count": 1024,
             "interval_ps": 10000, "input_slew_ns": 0.05, "output_load_pf": 0.005}
    if any(meta.get(key) != value for key, value in fixed.items()):
        raise EcoError("W32 workload parameters differ from fixed goal")
    workloads = meta.get("workloads")
    if not isinstance(workloads, dict) or set(workloads) != set(WORKLOAD_HASHES):
        raise EcoError("W32 workload profile set changed")
    for name, hashes in WORKLOAD_HASHES.items():
        item = workloads[name]
        if (not isinstance(item, dict) or item.get("profile") != name
            or item.get("profile_kind") != "energy"
            or item.get("expected_completions") != 1024
            or item.get("intended_interval_ps") != 10000
            or any(item.get(key) != value for key, value in hashes.items())):
            raise EcoError(f"W32 workload identity changed: {name}")


def validate_parent(request: dict, repo: Path) -> dict:
    parent = Path(request["parent_root"]).resolve()
    receipt = read_json(parent / "receipt.json")
    if (receipt.get("kind") != "w32_phase" or receipt.get("status") != "OK"
        or receipt.get("goal_id") != GOAL or receipt.get("reference_measurement_id") != REFERENCE
        or receipt.get("width") != 32):
        raise EcoError("parent is not the exact W32 postroute phase receipt")
    hashes = receipt.get("hashes", {})
    for filename, key in (("routed.v", "eco_routed_netlist"),
                          ("routed.odb", "eco_routed_odb"),
                          ("routed.spef", "eco_routed_spef")):
        if file_hash(parent / filename) != hashes.get(key):
            raise EcoError(f"W32 parent {filename} hash differs from receipt")
    if hashes.get("eco_routed_netlist") != PARENT_SHA:
        raise EcoError("W32 parent graph SHA differs from fixed parent")
    binding = read_json(parent / "parent_binding.json")
    if (binding.get("width") != 32 or binding.get("goal_id") != GOAL
        or binding.get("reference_measurement_id") != REFERENCE
        or binding.get("denominator_energies") != DENOMINATORS
        or binding.get("liberty_sha256") != LIBERTY_SHA
        or read_json(parent / "denominator.json") != DENOMINATORS):
        raise EcoError("W32 parent binding or raw denominator changed")
    final = receipt.get("final_proof", {})
    final_dir = parent / "final_proof"
    log = final_dir / "proof.log"
    if (final.get("status") != "PASS" or final.get("complete_marker") is not True
        or final.get("exit_code") != "0"
        or (final_dir / "proof-exit_code").read_text().strip() != "0"
        or "SAT proof finished - no model found: SUCCESS!" not in log.read_text()
        or file_hash(log) != final.get("log_sha256")
        or file_hash(log) != hashes.get("final_proof_log")
        or file_hash(final_dir / "routed.v") != PARENT_SHA
        or file_hash(final_dir / "pre_repair.v") != receipt.get("parent_graph_sha256")
        or file_hash(final_dir / "f1-equivalence.ys") != PROOF_SHA
        or file_hash(repo / "eda/ecc_f1/ecc_f1_equivalence.ys") != PROOF_SHA):
        raise EcoError("W32 parent whole-output proof incomplete or unbound")
    measurement = receipt.get("measurement", {})
    meta = read_json(parent / "three_profile/measurement_meta.json")
    validate_workload_context(meta)
    if (measurement.get("measurement_valid") is not True or measurement.get("feasible") is not True
        or measurement.get("denominator_energies") != THREE_DENOMINATORS
        or meta.get("netlist_sha256") != PARENT_SHA
        or meta.get("spef_sha256") != hashes.get("eco_routed_spef")
        or measurement.get("hashes", {}).get("routed_netlist") != PARENT_SHA
        or measurement.get("hashes", {}).get("spef") != hashes.get("eco_routed_spef")):
        raise EcoError("W32 parent three-profile measurement context invalid")
    return {"receipt": receipt, "hashes": hashes, "meta": meta}


def normalize_action(cells: dict, action: dict) -> dict:
    if not isinstance(action, dict) or set(action) != {"kind", "roots"} or action["kind"] != "star_batch":
        raise EcoError("W32 action must be a 2..4 star_batch")
    manifest = derive(cells, action)
    chosen = manifest["action"]
    if len(chosen["roots"]) not in (2, 3, 4):
        raise EcoError("W32 star count must be 2..4")
    available = {s["root"]: s for s in catalog(cells)["stars"]}
    for root in chosen["roots"]:
        star = available[root]
        if len(star["consumers"]) != 2 or any(cells[name]["cell"] != XNOR for name in (root, *star["consumers"])):
            raise EcoError(f"W32 star is not an all-XNOR two-consumer action: {root}")
    if len(manifest["targets"]) != 3 * len(chosen["roots"]):
        raise EcoError("W32 star batch target set is incomplete")
    return manifest


def validate_request(request: dict) -> tuple[dict, dict]:
    required = {
        "repo_root", "python", "source_commit", "parent_id", "parent_root",
        "expected_parent_sha256", "action", "model_decision_path", "artifact_dir",
        "goal_id", "reference_measurement_id",
    }
    if not isinstance(request, dict) or not required.issubset(request):
        raise EcoError("W32 polarity request fields missing")
    if (request["goal_id"] != GOAL or request["reference_measurement_id"] != REFERENCE
        or request["parent_id"] != PARENT_ID or request["expected_parent_sha256"] != PARENT_SHA):
        raise EcoError("W32 fixed goal, reference, or parent identity mismatch")
    if (Path(request["python"]).resolve() != Path(sys.executable).resolve()
        or not (Path(sys.prefix) / "conda-meta").is_dir()):
        raise EcoError("request must use active conda Python")
    repo = Path(request["repo_root"]).resolve()
    if head(repo) != request["source_commit"]:
        raise EcoError("source commit differs from repository HEAD")
    parent = Path(request["parent_root"]).resolve()
    if file_hash(parent / "routed.v") != PARENT_SHA:
        raise EcoError("W32 routed parent SHA mismatch")
    validated = validate_parent(request, repo)
    cells = parse_cells((parent / "routed.v").read_text())
    manifest = normalize_action(cells, request["action"])
    decision = read_json(Path(request["model_decision_path"]))
    parsed = decision.get("parsed_object")
    if (decision.get("http_status") != 200 or not isinstance(parsed, dict)
        or parsed.get("decision") != "RUN" or parsed.get("parent_id") != PARENT_ID
        or not isinstance(parsed.get("reason"), str)):
        raise EcoError("native model did not select W32 RUN on exact parent")
    selected = normalize_action(cells, parsed.get("action"))
    if selected["action"] != manifest["action"]:
        raise EcoError("native W32 action does not match request after normalization")
    return validated, manifest


def validate_placement(original: Path, after: Path, specs: dict) -> None:
    before_map, after_map = placement_map(original), placement_map(after)
    if before_map.keys() != after_map.keys():
        raise EcoError("W32 placement instance set changed")
    for name, old in before_map.items():
        new = after_map[name]
        expected = specs[name]["new_master"] if name in specs else old[0]
        if new[0] != expected or new[1:] != old[1:]:
            raise EcoError(f"W32 placement changed unexpectedly: {name}")
        if name in specs and old[0] != specs[name]["old_master"]:
            raise EcoError(f"W32 original placement master mismatch: {name}")


def execute(request: dict, identity: dict) -> dict:
    validated, manifest = validate_request(request)
    repo = Path(request["repo_root"]).resolve()
    parent = Path(request["parent_root"]).resolve()
    output = Path(request["artifact_dir"]).resolve()
    if output.exists():
        raise EcoError("unique W32 artifact directory already exists")
    recipes = {name: repo / "eda/ecc_w32_polarity" / name for name in ("eco.tcl", "reroute.tcl")}
    record: dict[str, Any] = {
        "kind": "w32_polarity_star_batch", "status": "STARTED", "stage": "intent",
        "source_commit": request["source_commit"], "parent_id": PARENT_ID,
        "parent_root": str(parent), "goal_id": GOAL, "reference_measurement_id": REFERENCE,
        "width": 32, "action": manifest["action"], "actual_chia_identity": identity,
        "parent_graph_sha256": PARENT_SHA,
        "parent_receipt_sha256": file_hash(parent / "receipt.json"),
        "parent_binding_sha256": file_hash(parent / "parent_binding.json"),
        "parent_odb_sha256": validated["hashes"]["eco_routed_odb"],
        "parent_spef_sha256": validated["hashes"]["eco_routed_spef"],
        "parent_proof_log_sha256": validated["receipt"]["final_proof"]["log_sha256"],
        "parent_measurement_meta_sha256": file_hash(parent / "three_profile/measurement_meta.json"),
        "model_decision_sha256": file_hash(Path(request["model_decision_path"])),
        "recipe_hashes": {name: file_hash(path) for name, path in recipes.items()},
        "proof_recipe_sha256": PROOF_SHA, "proof_image": IMAGE, "liberty_sha256": LIBERTY_SHA,
        "measurement_runner_sha256": file_hash(repo / "research/ecc_perf_bench/bench_ecc_routed_three_profile.py"),
        "route_submission_counted": 1, "mapped_submission_counted": 0,
    }
    output.mkdir(parents=True, exist_ok=False)
    os.chmod(output, 0o777)
    receipt = output / "receipt.json"
    write_json(output / "request.json", request)
    write_json(output / "kernel_manifest.json", manifest)
    write_json(output / "intent.json", record)
    write_json(receipt, record)
    try:
        for source, name in (
            (parent / "routed.v", "original_routed.v"),
            (parent / "routed.odb", "original_routed.odb"),
            (parent / "routed.spef", "original_routed.spef"),
            (parent / "receipt.json", "parent_receipt.json"),
            (parent / "parent_binding.json", "parent_binding.json"),
            (parent / "three_profile/measurement_meta.json", "parent_measurement_meta.json"),
            (parent / "denominator.json", "parent_denominator.json"),
            (Path(request["model_decision_path"]), "model_decision.json"),
        ):
            shutil.copy2(source, output / name)
        for name, source in recipes.items():
            shutil.copy2(source, output / name)
        write_json(output / "denominator.json", DENOMINATORS)
        record["stage"] = "eco"
        write_json(receipt, record)
        eco = run_openroad(output, "eco.tcl", "eco", {
            "CHIA_W32_POLARITY_TARGETS": " ".join(manifest["targets"]),
        })
        record["eco"] = eco
        if eco["returncode"] != 0 or "CHIA_W32_POLARITY_COMPLETE" not in (output / "eco.log").read_text(errors="replace"):
            raise EcoError("W32 star batch ECO failed")
        pre_v = output / "eco_pre_route.v"
        if not (output / "eco_pre_route.odb").is_file():
            raise EcoError("W32 ECO ODB missing")
        validate_child(parse_cells((output / "original_routed.v").read_text()),
                       parse_cells(pre_v.read_text()), manifest)
        validate_placement(output / "original_placement.def", output / "eco_placement.def",
                           manifest["target_specs"])
        record["placement_guard"] = "PASS"
        record["stage"] = "pre_route_proof"
        write_json(receipt, record)
        pre = proof(output, "pre_route_proof", output / "original_routed.v", pre_v,
                    repo / "eda/ecc_f1/ecc_f1_equivalence.ys")
        record["pre_route_proof"] = pre
        if not proof_valid(pre):
            raise EcoError(f"W32 pre-route proof was {pre['status']}")
        record["stage"] = "reroute"
        write_json(receipt, record)
        route = run_openroad(output, "reroute.tcl", "reroute")
        record["reroute"] = route
        log = (output / "reroute.log").read_text(errors="replace")
        markers = (
            "CHIA_W32_POLARITY_ROUTING_SDC 2.575 0.05 0.005",
            "CHIA_W32_POLARITY_OLD_SIGNAL_WIRES_CLEARED",
            "CHIA_W32_POLARITY_PLACEMENT_CHECKED",
            "CHIA_W32_POLARITY_RCX_COMPLETE",
        )
        if route["returncode"] != 0 or any(marker not in log for marker in markers):
            raise EcoError("W32 fresh route, wire clearance, or RCX failed")
        routed_v, routed_spef = output / "routed.v", output / "routed.spef"
        if not (output / "routed.odb").is_file() or file_hash(routed_spef) == validated["hashes"]["eco_routed_spef"]:
            raise EcoError("W32 fresh ODB or SPEF missing")
        validate_child(parse_cells((output / "original_routed.v").read_text()),
                       parse_cells(routed_v.read_text()), manifest)
        if parse_cells(pre_v.read_text()) != parse_cells(routed_v.read_text()):
            raise EcoError("W32 reroute changed logic graph")
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
            raise EcoError(f"W32 final proof was {final['status']}")
        area = parse_routed_area_from_log(output / "reroute.log")
        if area is None:
            raise EcoError("W32 fresh routed area missing")
        command = [request["python"], str(repo / "research/ecc_perf_bench/bench_ecc_routed_three_profile.py"),
                   "--repo-root", str(repo), "--routed-netlist", str(routed_v), "--spef", str(routed_spef),
                   "--artifact-dir", str(output / "three_profile"), "--width", "32", "--python", request["python"],
                   "--cpus", "2", "--denominator-json", str(output / "denominator.json"),
                   "--delay-ceiling", "2.40", "--routed-area-um2", str(area), "--power-diagnostic"]
        record["stage"] = "measurement"
        write_json(receipt, record)
        started = time.monotonic()
        measured = subprocess.run(command, capture_output=True, text=True, check=False)
        (output / "measurement.log").write_text(measured.stdout + measured.stderr, encoding="utf-8")
        record.update(measurement_command=command, measurement_exit_code=measured.returncode,
                      measurement_wall_s=round(time.monotonic() - started, 3))
        summary = read_json(output / "three_profile/routed_3p_summary.json")
        meta = read_json(output / "three_profile/measurement_meta.json")
        validate_workload_context(meta)
        profiles = summary.get("per_profile", {})
        if (measured.returncode != 0 or summary.get("measurement_valid") is not True
            or summary.get("denominator_energies") != THREE_DENOMINATORS
            or meta.get("netlist_sha256") != file_hash(routed_v)
            or meta.get("spef_sha256") != file_hash(routed_spef)
            or summary.get("hashes", {}).get("routed_netlist") != file_hash(routed_v)
            or summary.get("hashes", {}).get("spef") != file_hash(routed_spef)
            or not isinstance(profiles, dict) or set(profiles) != set(WORKLOAD_HASHES)
            or any(profiles[name].get("valid") is not True
                   or profiles[name].get("completed") != 1024
                   or profiles[name].get("oracle_mismatches") != 0
                   or profiles[name].get("vcd_sha256") != summary.get("hashes", {}).get("vcd", {}).get(name)
                   for name in WORKLOAD_HASHES)):
            raise EcoError("W32 fresh three-profile measurement invalid")
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
        record.update(status="ERROR_OR_UNKNOWN", error=f"{type(exc).__name__}: {exc}",
                      functional_valid=False, route_valid=False, measurement_valid=False)
        write_json(receipt, record)
        write_artifact_manifest(output)
        return record


def result_summary(record: dict, request: dict) -> dict:
    keys = ("status", "stage", "error", "functional_valid", "measurement_valid", "route_valid",
            "feasible", "routed_delay_ns", "routed_area_um2", "raw_energies_pj", "j_score",
            "hashes", "actual_chia_identity", "source_commit", "parent_id", "parent_root",
            "action", "goal_id", "reference_measurement_id", "width")
    result = {key: record.get(key) for key in keys}
    artifact = Path(request["artifact_dir"]).resolve()
    result.update(artifact_dir=str(artifact), receipt_path=str(artifact / "receipt.json"),
                  artifact_manifest_path=str(artifact / "artifact_manifest.json"))
    return result
