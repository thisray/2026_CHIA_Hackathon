"""Execute one fixed W32 mixed-arity phase proposal through CHIA."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path, PurePosixPath
from typing import Any

from research.ecc_perf_bench.bench_ecc_f1 import parse_routed_area_from_log
from research.ecc_perf_bench.polarity_kernel import parse_cells
from research.ecc_perf_bench.polarity_execute import (
    EcoError, file_hash, head, proof_valid, read_json, reuse_proof,
    write_artifact_manifest,
)
from research.ecc_perf_bench.postroute_star_phase import (
    IMAGE, PROOF_SHA, placement_map, proof, run_openroad, write_json,
)
from research.ecc_perf_bench.w32_polarity_execute import (
    DENOMINATORS, GOAL, LIBERTY_SHA, REFERENCE, THREE_DENOMINATORS,
    WORKLOAD_HASHES, validate_workload_context,
)
from research.ecc_perf_bench.w32_mixed_phase_kernel import (
    ACTION_KIND, GLOBAL_PROPOSAL_NAME, GLOBAL_SOURCE_FILES, MASTERS,
    PARENT_ID, PARENT_SHA, PROPOSAL_NAME, WORKER2_PROPOSAL_NAME,
    WORKER2_SOURCE_FILES, derive, validate_child,
)


def validate_parent(parent: Path, repo: Path) -> dict:
    receipt = read_json(parent / "receipt.json")
    if (receipt.get("kind") != "bounded_w32_phase_assignment" or receipt.get("status") != "OK"
        or receipt.get("functional_valid") is not True
        or receipt.get("route_valid") is not True
        or receipt.get("measurement_valid") is not True
        or receipt.get("feasible") is not True
        or receipt.get("goal_id") != GOAL
        or receipt.get("reference_measurement_id") != REFERENCE
        or receipt.get("width") != 32
        or not isinstance(receipt.get("source_commit"), str)
        or not receipt["source_commit"]
        or receipt.get("actual_chia_identity", {}).get("in_ray_worker") is not True
        or receipt.get("proof_image") != IMAGE
        or receipt.get("proof_recipe_sha256") != PROOF_SHA):
        raise EcoError("W32 phase-assignment parent receipt context differs")
    hashes = receipt.get("hashes", {})
    for filename, key in (("routed.v", "eco_routed_netlist"),
                          ("routed.odb", "eco_routed_odb"),
                          ("routed.spef", "eco_routed_spef")):
        if file_hash(parent / filename) != hashes.get(key):
            raise EcoError(f"W32 parent {filename} hash differs from receipt")
    if hashes.get("eco_routed_netlist") != PARENT_SHA:
        raise EcoError("W32 parent graph SHA differs from fixed parent")
    binding_path = parent / "parent_binding.json"
    binding = read_json(binding_path)
    if (file_hash(binding_path) != receipt.get("parent_binding_sha256")
        or binding.get("width") != 32 or binding.get("goal_id") != GOAL
        or binding.get("reference_measurement_id") != REFERENCE
        or binding.get("denominator_energies") != DENOMINATORS
        or binding.get("liberty_sha256") != LIBERTY_SHA
        or read_json(parent / "denominator.json") != DENOMINATORS):
        raise EcoError("W32 parent binding or denominator changed")
    final = receipt.get("final_proof", {})
    proof_dir = parent / "final_proof"
    proof_log = proof_dir / "proof.log"
    if (final.get("status") != "PASS" or final.get("complete_marker") is not True
        or final.get("exit_code") != "0"
        or (proof_dir / "proof-exit_code").read_text().strip() != "0"
        or "SAT proof finished - no model found: SUCCESS!" not in proof_log.read_text(errors="replace")
        or file_hash(proof_log) != final.get("log_sha256")
        or file_hash(proof_log) != hashes.get("final_proof_log")
        or file_hash(proof_dir / "routed.v") != PARENT_SHA
        or file_hash(proof_dir / "pre_repair.v") != receipt.get("parent_graph_sha256")
        or file_hash(proof_dir / "f1-equivalence.ys") != PROOF_SHA
        or file_hash(repo / "eda/ecc_f1/ecc_f1_equivalence.ys") != PROOF_SHA):
        raise EcoError("W32 parent whole-output proof is incomplete or unbound")
    measurement = receipt.get("measurement", {})
    meta = read_json(parent / "three_profile/measurement_meta.json")
    validate_workload_context(meta)
    if (measurement.get("measurement_valid") is not True
        or measurement.get("feasible") is not True
        or measurement.get("denominator_energies") != THREE_DENOMINATORS
        or meta.get("netlist_sha256") != PARENT_SHA
        or meta.get("spef_sha256") != hashes.get("eco_routed_spef")
        or measurement.get("hashes", {}).get("routed_netlist") != PARENT_SHA
        or measurement.get("hashes", {}).get("spef") != hashes.get("eco_routed_spef")):
        raise EcoError("W32 parent three-profile context differs")
    manifest = read_json(parent / "artifact_manifest.json")
    rows = manifest.get("files")
    if not isinstance(rows, list) or not rows:
        raise EcoError("W32 parent artifact manifest is missing")
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("path"), str):
            raise EcoError("invalid W32 parent manifest row")
        relative = PurePosixPath(row["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise EcoError("unsafe W32 parent manifest path")
        if file_hash(parent.joinpath(*relative.parts)) != row.get("sha256"):
            raise EcoError(f"W32 parent artifact mismatch: {relative}")
    return {"receipt": receipt, "hashes": hashes, "meta": meta}


def validate_request(request: dict) -> tuple[dict, dict | None]:
    required = {
        "repo_root", "python", "source_commit", "parent_id", "parent_root",
        "expected_parent_sha256", "action", "model_decision_path", "artifact_dir",
        "goal_id", "reference_measurement_id",
    }
    if not isinstance(request, dict) or not required.issubset(request):
        raise EcoError("W32 mixed phase request fields missing")
    action = request["action"]
    run_actions = (
        {"kind": ACTION_KIND, "proposal": PROPOSAL_NAME},
        {"kind": ACTION_KIND, "proposal": GLOBAL_PROPOSAL_NAME},
        {"kind": ACTION_KIND, "proposal": WORKER2_PROPOSAL_NAME},
    )
    stop_action = {"kind": "STOP"}
    is_run = action in run_actions
    if (request["goal_id"] != GOAL or request["reference_measurement_id"] != REFERENCE
        or request["parent_id"] != PARENT_ID or request["expected_parent_sha256"] != PARENT_SHA
        or not (is_run or action == stop_action)
        or (is_run and request.get("keep_vcd") is not True)):
        raise EcoError("W32 mixed phase goal, parent, action, or VCD retention mismatch")
    if (Path(request["python"]).resolve() != Path(sys.executable).resolve()
        or not (Path(sys.prefix) / "conda-meta").is_dir()):
        raise EcoError("request must use active conda Python")
    repo = Path(request["repo_root"]).resolve()
    if head(repo) != request["source_commit"]:
        raise EcoError("source commit differs from repository HEAD")
    parent = Path(request["parent_root"]).resolve()
    validated = validate_parent(parent, repo)
    manifest = derive((parent / "routed.v").read_text(), action, repo) if is_run else None
    decision = read_json(Path(request["model_decision_path"]))
    parsed = decision.get("parsed_object")
    if (decision.get("http_status") != 200 or not isinstance(parsed, dict)
        or parsed.get("parent_id") != PARENT_ID
        or not isinstance(parsed.get("reason"), str) or not parsed["reason"].strip()):
        raise EcoError("native W32 mixed decision metadata invalid")
    if is_run:
        if parsed.get("decision") != "RUN" or parsed.get("action") != action:
            raise EcoError("native model did not RUN the exact W32 mixed proposal")
    elif parsed.get("decision") != "STOP":
        raise EcoError("native model did not STOP on the exact W32 mixed parent")
    return validated, manifest


def target_rows(manifest: dict) -> list[str]:
    if (manifest.get("kind") != ACTION_KIND
        or manifest.get("proposal") not in {
            PROPOSAL_NAME, GLOBAL_PROPOSAL_NAME, WORKER2_PROPOSAL_NAME}
        or not isinstance(manifest.get("targets"), list)
        or not manifest["targets"] or manifest["targets"] != sorted(set(manifest["targets"]))
        or set(manifest["targets"]) != set(manifest.get("target_specs", {}))):
        raise EcoError("W32 mixed target set differs from exact proposal")
    rows = []
    for name in manifest["targets"]:
        spec = manifest["target_specs"][name]
        if (not name.startswith("_") or not name.endswith("_") or not name[1:-1].isdigit()
            or spec["old_master"] not in MASTERS or spec["new_master"] not in MASTERS
            or MASTERS[spec["old_master"]][6] != spec["new_master"]
            or spec["old_output_pin"] != MASTERS[spec["old_master"]][3]
            or spec["new_output_pin"] != MASTERS[spec["new_master"]][3]
            or spec["arity"] != MASTERS[spec["old_master"]][0]
            or spec["drive"] != MASTERS[spec["old_master"]][1]):
            raise EcoError(f"unsafe W32 mixed target specification: {name}")
        rows.append("\t".join((name, spec["old_master"], spec["new_master"],
                               spec["old_output_pin"], spec["new_output_pin"])))
    return rows


def validate_mixed_placement(before_path: Path, after_path: Path, specs: dict, *,
                             allow_dpl_movement: bool,
                             before_is_parent: bool = True) -> list[dict]:
    before, after = placement_map(before_path), placement_map(after_path)
    if before.keys() != after.keys() or not set(specs).issubset(before):
        raise EcoError("W32 mixed placement changed the complete instance set")
    moved = []
    for name, old in before.items():
        new = after[name]
        spec = specs.get(name)
        expected_master = spec["new_master"] if spec else old[0]
        if new[0] != expected_master:
            raise EcoError(f"W32 mixed placement master mismatch at {name}")
        if spec:
            old_expected = spec["old_master"] if before_is_parent else spec["new_master"]
            if old[0] != old_expected:
                raise EcoError(f"W32 mixed old placement master mismatch at {name}")
        if old[1:] != new[1:]:
            if not allow_dpl_movement:
                raise EcoError(f"W32 mixed postroute placement changed after DPL: {name}")
            moved.append({
                "instance": name, "target": bool(spec),
                "old_master": old[0], "new_master": new[0],
                "old_x_dbu": int(old[1]), "old_y_dbu": int(old[2]),
                "new_x_dbu": int(new[1]), "new_y_dbu": int(new[2]),
                "old_orient": old[3], "new_orient": new[3],
            })
    return moved


def area_check(log: str, manifest: dict) -> dict:
    import re

    match = re.search(
        r"(?m)^CHIA_W32_MIXED_AREA_CHECK\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*$", log)
    if match is None:
        raise EcoError("W32 mixed ECO omitted target/design DB area marker")
    old_pair, new_pair, old_design, new_design = map(int, match.groups())
    expected_old = sum(
        MASTERS[spec["old_master"]][4] * MASTERS[spec["old_master"]][5]
        for spec in manifest["target_specs"].values()
    )
    expected_new = sum(
        MASTERS[spec["new_master"]][4] * MASTERS[spec["new_master"]][5]
        for spec in manifest["target_specs"].values()
    )
    delta = manifest["db_area_delta_dbu2"]
    if (old_pair != expected_old or new_pair != expected_new
        or new_pair - old_pair != delta or new_design - old_design != delta):
        raise EcoError("W32 mixed target or whole DB area delta differs from pinned geometry")
    return {
        "target_before_dbu2": old_pair, "target_after_dbu2": new_pair,
        "target_delta_dbu2": new_pair - old_pair,
        "design_before_dbu2": old_design, "design_after_dbu2": new_design,
        "design_delta_dbu2": new_design - old_design,
    }


def measurement_command(request: dict, repo: Path, output: Path,
                        routed_v: Path, routed_spef: Path, area: float) -> list[str]:
    return [
        request["python"], str(repo / "research/ecc_perf_bench/bench_ecc_routed_three_profile.py"),
        "--repo-root", str(repo), "--routed-netlist", str(routed_v), "--spef", str(routed_spef),
        "--artifact-dir", str(output / "three_profile"), "--width", "32",
        "--python", request["python"], "--cpus", "2",
        "--denominator-json", str(output / "denominator.json"),
        "--delay-ceiling", "2.40", "--routed-area-um2", str(area),
        "--power-diagnostic", "--keep-vcd",
    ]


def execute(request: dict, identity: dict) -> dict:
    validated, manifest = validate_request(request)
    if manifest is None:
        raise EcoError("STOP cannot dispatch a W32 mixed CHIA leaf")
    repo = Path(request["repo_root"]).resolve()
    parent = Path(request["parent_root"]).resolve()
    output = Path(request["artifact_dir"]).resolve()
    if output.exists():
        raise EcoError("unique W32 mixed artifact directory already exists")
    recipes = {
        "eco.tcl": repo / "eda/ecc_w32_mixed_phase/eco.tcl",
        "reroute.tcl": repo / "eda/ecc_w32_polarity/reroute.tcl",
    }
    source_files = [
        "w32_mixed_phase_kernel.py",
        "w32_mixed_phase_source_proposal.json",
        "w32_mixed_phase_source_inventory.json",
        "w32_mixed_phase_source_expected_cell_map.json",
        "w32_mixed_phase_source_candidate.v",
        "w32_mixed_phase_source_generator.py",
        "w32_mixed_phase_source_solver.py",
    ]
    if manifest["proposal"] == GLOBAL_PROPOSAL_NAME:
        source_files.extend(filename for filename, _sha in GLOBAL_SOURCE_FILES.values())
    if manifest["proposal"] == WORKER2_PROPOSAL_NAME:
        source_files.extend(filename for filename, _sha in WORKER2_SOURCE_FILES.values())
    record: dict[str, Any] = {
        "kind": "w32_mixed_phase_assignment", "status": "STARTED", "stage": "intent",
        "source_commit": request["source_commit"], "parent_id": PARENT_ID,
        "parent_root": str(parent), "goal_id": GOAL, "reference_measurement_id": REFERENCE,
        "width": 32, "action": request["action"], "actual_chia_identity": identity,
        "parent_graph_sha256": PARENT_SHA,
        "parent_receipt_sha256": file_hash(parent / "receipt.json"),
        "parent_binding_sha256": file_hash(parent / "parent_binding.json"),
        "parent_odb_sha256": validated["hashes"]["eco_routed_odb"],
        "parent_spef_sha256": validated["hashes"]["eco_routed_spef"],
        "parent_proof_log_sha256": validated["receipt"]["final_proof"]["log_sha256"],
        "parent_measurement_meta_sha256": file_hash(parent / "three_profile/measurement_meta.json"),
        "model_decision_sha256": file_hash(Path(request["model_decision_path"])),
        "source_proposal_sha256": manifest["source_proposal_sha256"],
        "source_inventory_sha256": manifest["source_inventory_sha256"],
        "source_candidate_graph_sha256": manifest["source_candidate_graph_sha256"],
        "source_expected_cell_map_sha256": manifest["expected_cell_map_sha256"],
        "source_kernel_sha256": manifest["source_kernel_sha256"],
        "source_generator_sha256": manifest["source_generator_sha256"],
        "recipe_hashes": {name: file_hash(path) for name, path in recipes.items()},
        "proof_recipe_sha256": PROOF_SHA, "proof_image": IMAGE, "liberty_sha256": LIBERTY_SHA,
        "lef_sha256": manifest["lef_sha256"],
        "measurement_runner_sha256": file_hash(repo / "research/ecc_perf_bench/bench_ecc_routed_three_profile.py"),
        "route_submission_counted": 1, "mapped_submission_counted": 0,
        "parity_gate_count": manifest["parity_gate_count"],
        "baseline_xnor2_count": manifest["baseline_xnor2_count"],
        "baseline_xnor3_count": manifest["baseline_xnor3_count"],
        "candidate_xnor2_count": manifest["candidate_xnor2_count"],
        "candidate_xnor3_count": manifest["candidate_xnor3_count"],
        "target_count": len(manifest["targets"]),
        "expected_cell_map_sha256": manifest["expected_cell_map_sha256"],
        "expected_db_area_delta_dbu2": manifest["db_area_delta_dbu2"],
        "pure_proof_scope": "95-gate structural GF2/truth only; whole-output proof NOT_RUN at intent",
        "vcd_retention": {"requested": True, "metadata_retained": "NOT_RUN", "files": {}},
    }
    if manifest["proposal"] == GLOBAL_PROPOSAL_NAME:
        record["global_plan_lineage"] = {
            "remote_pure_checker_sha256": manifest["source_remote_check_sha256"],
            "worker1_progress_sha256": manifest["source_worker1_progress_sha256"],
            "raw_phase_rhs_semantics": manifest["source_phase_rhs_note"],
            "formal_equivalence": "NOT_RUN at intent",
            "route": "NOT_RUN at intent",
        }
    if manifest["proposal"] == WORKER2_PROPOSAL_NAME:
        record["worker2_plan_lineage"] = {
            "packet_manifest_sha256": manifest["source_packet_manifest_sha256"],
            "remote_pure_checker_sha256": manifest["source_remote_check_sha256"],
            "V02_internal_proxy_source_sha256": manifest["source_proxy_sha256"],
            "proxy_claim_limit": "Observed V02 internal power importance proxy, not a candidate J prediction.",
            "formal_equivalence": "NOT_RUN at intent",
            "route": "NOT_RUN at intent",
        }
    rows = target_rows(manifest)
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
            (parent / "parent_binding.json", "parent_binding.json"),
            (parent / "three_profile/measurement_meta.json", "parent_measurement_meta.json"),
            (parent / "denominator.json", "parent_denominator.json"),
            (Path(request["model_decision_path"]), "model_decision.json"),
        ):
            shutil.copy2(source, output / name)
        for filename in source_files:
            shutil.copy2(repo / "research/ecc_perf_bench" / filename, output / filename)
        for name, source in recipes.items():
            shutil.copy2(source, output / name)
        (output / "targets.tsv").write_text("\n".join(rows) + "\n", encoding="ascii")
        record["targets_tsv_sha256"] = file_hash(output / "targets.tsv")
        write_json(output / "denominator.json", DENOMINATORS)
        record["stage"] = "eco"
        write_json(receipt, record)
        eco = run_openroad(output, "eco.tcl", "eco", {
            "CHIA_W32_MIXED_TARGET_COUNT": str(len(manifest["targets"])),
            "CHIA_W32_MIXED_DB_AREA_DELTA": str(manifest["db_area_delta_dbu2"]),
        })
        record["eco"] = eco
        eco_log = (output / "eco.log").read_text(errors="replace")
        if (eco["returncode"] != 0 or "CHIA_W32_MIXED_COMPLETE" not in eco_log
            or "CHIA_W32_MIXED_DPL_LEGALIZATION_COMPLETE" not in eco_log
            or "[ERROR" in eco_log):
            raise EcoError("W32 mixed ECO or placement check failed")
        record["area_check"] = area_check(eco_log, manifest)
        pre_v = output / "eco_pre_route.v"
        if not (output / "eco_pre_route.odb").is_file():
            raise EcoError("W32 mixed ECO ODB missing")
        validate_child((output / "original_routed.v").read_text(), pre_v.read_text(), manifest, repo)
        moved = validate_mixed_placement(
            output / "original_placement.def", output / "eco_placement.def",
            manifest["target_specs"], allow_dpl_movement=True)
        record["dpl_moved_instances"] = moved
        record["dpl_moved_instance_count"] = len(moved)
        before_map = placement_map(output / "original_placement.def")
        after_map = placement_map(output / "eco_placement.def")
        record["target_placements"] = {
            name: {"parent": before_map[name], "after_dpl": after_map[name]}
            for name in manifest["targets"]
        }
        write_json(output / "dpl_moved_instances.json", {
            "moved_instances": moved, "target_placements": record["target_placements"],
            "policy": "bounded detailed placement; all instance movement recorded",
        })
        record["dpl_moved_instances_sha256"] = file_hash(output / "dpl_moved_instances.json")
        record["placement_guard"] = "DPL_LEGALIZED_MOVEMENTS_RECORDED"
        record["stage"] = "pre_route_proof"
        write_json(receipt, record)
        pre = proof(output, "pre_route_proof", output / "original_routed.v", pre_v,
                    repo / "eda/ecc_f1/ecc_f1_equivalence.ys")
        record["pre_route_proof"] = pre
        if not proof_valid(pre):
            raise EcoError(f"W32 mixed pre-route proof was {pre['status']}")
        record["stage"] = "reroute"
        write_json(receipt, record)
        route = run_openroad(output, "reroute.tcl", "reroute")
        record["reroute"] = route
        route_log = (output / "reroute.log").read_text(errors="replace")
        markers = (
            "CHIA_W32_POLARITY_ROUTING_SDC 2.575 0.05 0.005",
            "CHIA_W32_POLARITY_OLD_SIGNAL_WIRES_CLEARED",
            "CHIA_W32_POLARITY_PLACEMENT_CHECKED",
            "CHIA_W32_POLARITY_RCX_COMPLETE",
        )
        if route["returncode"] != 0 or any(marker not in route_log for marker in markers):
            raise EcoError("W32 mixed fresh route, wire clearance, or RCX failed")
        routed_v, routed_spef = output / "routed.v", output / "routed.spef"
        if (not (output / "routed.odb").is_file()
            or file_hash(routed_spef) == validated["hashes"]["eco_routed_spef"]):
            raise EcoError("W32 mixed fresh ODB or SPEF missing")
        validate_child((output / "original_routed.v").read_text(), routed_v.read_text(), manifest, repo)
        if parse_cells(pre_v.read_text()) != parse_cells(routed_v.read_text()):
            raise EcoError("W32 mixed reroute changed logic graph")
        validate_mixed_placement(
            output / "eco_placement.def", output / "routed_placement.def",
            manifest["target_specs"], allow_dpl_movement=False, before_is_parent=False)
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
            raise EcoError(f"W32 mixed final proof was {final['status']}")
        area = parse_routed_area_from_log(output / "reroute.log")
        if area is None:
            raise EcoError("W32 mixed fresh routed area missing")
        command = measurement_command(request, repo, output, routed_v, routed_spef, area)
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
        if meta.get("vcd_retained") is not True:
            raise EcoError("W32 mixed VCD retention metadata differs from request")
        retained_files = {}
        for name in WORKLOAD_HASHES:
            vcd = output / "three_profile" / f"activity_{name}.vcd"
            retained_files[name] = file_hash(vcd) if vcd.is_file() else None
            if retained_files[name] != summary.get("hashes", {}).get("vcd", {}).get(name):
                raise EcoError(f"W32 mixed retained VCD missing or mismatched: {name}")
        record["vcd_retention"] = {"requested": True, "metadata_retained": True, "files": retained_files}
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
            raise EcoError("W32 mixed fresh three-profile measurement invalid")
        record.update(
            status="OK", stage="complete", functional_valid=True, route_valid=True,
            measurement_valid=True, functional_proof="PASS",
            feasible=summary.get("feasible") is True,
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
        pre = record.get("pre_route_proof")
        final = record.get("final_proof")
        functional = (
            True if isinstance(final, dict) and proof_valid(final)
            else False if isinstance(final, dict) and final.get("status") == "FAIL"
            else False if isinstance(pre, dict) and pre.get("status") == "FAIL"
            else None
        )
        measurement = record.get("measurement")
        measurement_valid = (measurement.get("measurement_valid")
                             if isinstance(measurement, dict) else None)
        record.update(status="ERROR_OR_UNKNOWN", error=f"{type(exc).__name__}: {exc}",
                      functional_valid=functional, route_valid=False,
                      measurement_valid=measurement_valid)
        write_json(receipt, record)
        write_artifact_manifest(output)
        return record


def result_summary(record: dict, request: dict) -> dict:
    keys = (
        "status", "stage", "error", "functional_valid", "functional_proof",
        "measurement_valid", "route_valid", "feasible", "routed_delay_ns",
        "routed_area_um2", "raw_energies_pj", "j_score", "hashes",
        "actual_chia_identity", "source_commit", "parent_id", "parent_root",
        "action", "goal_id", "reference_measurement_id", "width",
        "baseline_xnor2_count", "baseline_xnor3_count",
        "candidate_xnor2_count", "candidate_xnor3_count",
        "expected_db_area_delta_dbu2", "dpl_moved_instance_count",
        "area_check", "vcd_retention",
    )
    result = {key: record.get(key) for key in keys}
    artifact = Path(request["artifact_dir"]).resolve()
    result.update(
        artifact_dir=str(artifact), receipt_path=str(artifact / "receipt.json"),
        artifact_manifest_path=str(artifact / "artifact_manifest.json"),
    )
    return result
