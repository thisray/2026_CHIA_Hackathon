#!/usr/bin/env python3
"""Run mixed phase relocation ECO on the exact 437f routed parent."""

from __future__ import annotations

import argparse
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

from research.ecc_perf_bench.bench_ecc_f1 import parse_routed_area_from_log, run_yosys_miter_proof
from research.ecc_perf_bench.netlist_fanout import CELL_RE, CONN_RE, OUT_PINS

IMAGE = 'docker.io/hpretl/iic-osic-tools@sha256:65852976cad4af640c9d848762215137e87ec125111a6d06c850c3ab4e9695fb'
PROOF_SHA = "d3036fb932303b6e65f59cba7196559b29d2856884096b9f70f98eaab34ff9a0"
ARRIVAL_RE = re.compile(r'(?m)^\s*([0-9]+(?:\.[0-9]+)?)\s+data arrival time\s*$')
PHYSICAL_TYPES = {'sky130_fd_sc_hd__tapvpwrvgnd_1', 'sky130_fd_sc_hd__decap_3'}
EXPECTED_PARENT_V = '437fa753c395a29e8592ce0f668a6ed2f5d1219f381a3ba137141452991bff39'


class EcoError(RuntimeError):
    pass


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def run_openroad(artifact_dir: Path, script: str, label: str, environment: dict[str, str] | None = None) -> dict[str, Any]:
    command = ['docker', 'run', '--rm', '--cpus', '2', '--memory', '12g', '--network', 'none', '--entrypoint', '/bin/bash']
    for key, value in sorted((environment or {}).items()):
        command.extend(['-e', f'{key}={value}'])
    command.extend(['-v', f'{artifact_dir}:/artifacts', IMAGE, '-lc', f'openroad -no_init -exit /artifacts/{script}'])
    started = time.monotonic()
    try:
        process = subprocess.run(command, capture_output=True, text=True, timeout=600, check=False)
        log = process.stdout + process.stderr
        rc = process.returncode
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout.decode(errors='replace') if isinstance(exc.stdout, bytes) else (exc.stdout or '')
        err = exc.stderr.decode(errors='replace') if isinstance(exc.stderr, bytes) else (exc.stderr or '')
        log = out + err
        rc = None
        timed_out = True
    log_path = artifact_dir / f'{label}.log'
    log_path.write_text(log, encoding='utf-8')
    return {'command': command, 'returncode': rc, 'timed_out': timed_out, 'wall_s': round(time.monotonic() - started, 3), 'log_sha256': file_hash(log_path), 'log_path': str(log_path)}


def netlist_cells(path: Path) -> dict[str, dict[str, Any]]:
    found = {}
    for match in CELL_RE.finditer(path.read_text(encoding='utf-8')):
        name = match.group(2)
        if name in found:
            raise EcoError(f'duplicate cell instance {name}')
        if match.group(1) in PHYSICAL_TYPES:
            continue
        pins = {}
        for pin, net in CONN_RE.findall(match.group('conns')):
            if pin in pins:
                raise EcoError(f'duplicate pin {name}.{pin}')
            pins[pin] = net.strip()
        found[name] = {'cell': match.group(1), 'pins': pins}
    return found


def verify_parent(inputs: Path, binding: dict[str, Any]) -> None:
    if binding["parent_routed_files_sha256"]["routed.v"] != EXPECTED_PARENT_V:
        raise EcoError("this experiment requires the exact 437f parent")
    for name, expected in binding["parent_routed_files_sha256"].items():
        if file_hash(inputs / name) != expected:
            raise EcoError(f"verified 437f parent {name} mismatch")
    if file_hash(inputs / "receipt.json") != binding["parent_receipt_sha256"]:
        raise EcoError("verified parent receipt changed")
    if file_hash(inputs / "final_proof/proof.log") != binding["parent_final_proof_log_sha256"]:
        raise EcoError("verified parent final proof log changed")
    parent = json.loads((inputs / "receipt.json").read_text(encoding="utf-8"))
    if parent["status"] != "OK" or parent["final_proof"]["status"] != "PASS" or parent["final_proof"]["log_sha256"] != binding["parent_final_proof_log_sha256"]:
        raise EcoError("437f parent whole-output proof not bound PASS")
    if not parent["measurement"]["measurement_valid"] or not parent["measurement"]["feasible"]:
        raise EcoError("437f parent three-profile measurement invalid")
    if parent["hashes"]["eco_routed_netlist"] != binding["parent_routed_files_sha256"]["routed.v"]:
        raise EcoError("437f parent graph differs from receipt")


def validate_phase_pairing(parent: Path, child: Path) -> dict[str, Any]:
    before, after = netlist_cells(parent), netlist_cells(child)
    if before.keys() != after.keys():
        raise EcoError("phase relocation added or removed instances")
    target_specs = {'_318_': ('sky130_fd_sc_hd__xnor2_1', 'sky130_fd_sc_hd__xor2_1', 'Y', 'X'), '_320_': ('sky130_fd_sc_hd__xnor2_1', 'sky130_fd_sc_hd__xor2_1', 'Y', 'X'), '_378_': ('sky130_fd_sc_hd__xnor2_1', 'sky130_fd_sc_hd__xor2_1', 'Y', 'X')}
    changed = []
    for name in sorted(before):
        old, new = before[name], after[name]
        if name in target_specs:
            old_m, new_m, old_out, new_out = target_specs[name]
            if old["cell"] != old_m or new["cell"] != new_m:
                raise EcoError(f"{name} master not converted {old_m} -> {new_m}")
            if set(new["pins"].keys()) != {"A", "B", new_out}:
                raise EcoError(f"{name} pin set invalid")
            if new["pins"]["A"] != old["pins"]["A"] or new["pins"]["B"] != old["pins"]["B"]:
                raise EcoError(f"{name} input net changed")
            if new["pins"][new_out] != old["pins"][old_out]:
                raise EcoError(f"{name} output net changed")
            changed.append(name)
        else:
            if old["cell"] != new["cell"] or old["pins"] != new["pins"]:
                raise EcoError(f"unexpected modification to instance {name}")
    if len(changed) != 3:
        raise EcoError("phase relocation targets mismatch")
    uses_selected = set((n, p) for n, c in before.items() for p, net in c["pins"].items() if net == '_060_' and p not in OUT_PINS)
    if uses_selected != {('_378_', 'A'), ('_320_', 'A')}:
        raise EcoError("selected root complete fanout differs")
    return {"modified_instances": changed}


def placement_map(path: Path) -> dict[str, tuple[str, str, str, str]]:
    text = path.read_text()
    match = re.search(r"\bCOMPONENTS\s+\d+\s*;(.*?)END COMPONENTS", text, re.S)
    if not match:
        raise EcoError("DEF component section missing")
    result = {}
    for block in match.group(1).split(";"):
        head = re.match(r"\s*-\s+(\S+)\s+(\S+)", block)
        if not head:
            continue
        pos = re.search(r"\+\s+(?:PLACED|FIXED|COVER)\s+\(\s*(-?\d+)\s+(-?\d+)\s*\)\s+(\S+)", block)
        if not pos or head[1] in result:
            raise EcoError("unplaced or duplicate DEF instance")
        result[head[1]] = (head[2], *pos.groups())
    if not result:
        raise EcoError("empty placement snapshot")
    return result


def check_placement_consistency(before_p: Path, after_p: Path) -> None:
    specs = {'_318_': ('sky130_fd_sc_hd__xnor2_1', 'sky130_fd_sc_hd__xor2_1', 'Y', 'X'), '_320_': ('sky130_fd_sc_hd__xnor2_1', 'sky130_fd_sc_hd__xor2_1', 'Y', 'X'), '_378_': ('sky130_fd_sc_hd__xnor2_1', 'sky130_fd_sc_hd__xor2_1', 'Y', 'X')}
    before, after = placement_map(before_p), placement_map(after_p)
    if before.keys() != after.keys():
        raise EcoError("instance set changed")
    for name, old in before.items():
        new = after[name]
        if old[1:] != new[1:]:
            raise EcoError("instance moved or reoriented")
        expected = specs[name][1] if name in specs else old[0]
        if new[0] != expected or (name in specs and old[0] != specs[name][0]):
            raise EcoError("unexpected master change")


def proof(artifact_dir: Path, label: str, original: Path, changed: Path, proof_recipe: Path) -> dict[str, Any]:
    case = artifact_dir / label
    case.mkdir(parents=True, exist_ok=False)
    os.chmod(case, 0o777)
    shutil.copy2(original, case / "pre_repair.v")
    shutil.copy2(changed, case / "routed.v")
    shutil.copy2(proof_recipe, case / "f1-equivalence.ys")
    started = time.monotonic()
    try:
        status, log = run_yosys_miter_proof(case, IMAGE, 2, timeout_s=300)
        error = None
    except Exception as exc:
        status, log, error = "UNKNOWN", "", f"{type(exc).__name__}: {exc}"
    complete = "SAT proof finished - no model found: SUCCESS!" in log
    exit_path = case / "proof-exit_code"
    exit_code = exit_path.read_text().strip() if exit_path.is_file() else None
    if status == "FAIL" and not ("SAT proof failed" in log or "model found" in log):
        status, error = "UNKNOWN", "proof process failed without complete counterexample"
    if status == "PASS" and (not complete or exit_code != "0"):
        status, error = "UNKNOWN", "PASS reported without complete marker and exit 0"
    log_path = case / "proof.log"
    return {"status": status, "error": error, "complete_marker": complete, "exit_code": exit_code, "log_sha256": file_hash(log_path) if log_path.is_file() else None, "wall_s": round(time.monotonic() - started, 3), "artifact_dir": str(case), "new_run": True}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--parent-root", type=Path, required=True)
    parser.add_argument("--binding", type=Path, required=True)
    parser.add_argument("--analysis", type=Path, required=True)
    parser.add_argument("--decision", type=Path, required=True)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--expected-repo-commit", required=True)
    args = parser.parse_args()
    repo, inputs, output = args.repo_root.resolve(), args.parent_root.resolve(), args.artifact_dir.resolve()
    if output.exists():
        raise EcoError(f"artifact directory already exists: {output}")
    commit = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    if commit != args.expected_repo_commit:
        raise EcoError(f"wrong immutable source commit: {commit}")
    binding = json.loads(args.binding.read_text(encoding="utf-8"))
    verify_parent(inputs, binding)
    decision = json.loads(args.decision.read_text(encoding="utf-8"))
    if (decision.get("http_status") != 200
            or decision.get("parsed_object", {}).get("decision") != "REQUEST_STAR_OTHER"
            or decision.get("parsed_object", {}).get("root") != '_318_'
            or decision.get("analysis_sha256") != file_hash(args.analysis)
            or decision.get("binding_sha256") != file_hash(args.binding)):
        raise EcoError("model did not select STAR_308")
    proof_recipe = repo / "eda/ecc_f1/ecc_f1_equivalence.ys"
    if file_hash(proof_recipe) != PROOF_SHA:
        raise EcoError("whole-output proof recipe changed")
    recipes = {name: repo / "eda/ecc_star_phase" / name for name in ("eco.tcl", "reroute.tcl")}
    recipe_hashes = {name: file_hash(path) for name, path in recipes.items()}
    context = {"source_commit": commit, "parent_binding_sha256": file_hash(args.binding), "parent_graph_sha256": binding["parent_routed_files_sha256"]["routed.v"], "parent_odb_sha256": binding["parent_routed_files_sha256"]["routed.odb"], "parent_spef_sha256": binding["parent_routed_files_sha256"]["routed.spef"], "liberty_sha256": binding["liberty_sha256"], "analysis_sha256": file_hash(args.analysis), "decision_sha256": file_hash(args.decision), "action": "REQUEST_STAR_OTHER", "recipe_hashes": recipe_hashes}
    implementation_key = hashlib.sha256(json.dumps(context, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    output.mkdir(parents=True, exist_ok=False)
    os.chmod(output, 0o777)
    for name, destination in (( "routed.odb", "original_routed.odb"), ("routed.v", "original_routed.v"), ("routed.spef", "original_routed.spef"), ("receipt.json", "parent_receipt.json")):
        shutil.copy2(inputs / name, output / destination)
    for name, path in recipes.items():
        shutil.copy2(path, output / name)
    shutil.copy2(args.binding, output / "parent_binding.json")
    shutil.copy2(args.analysis, output / "read_only_analysis.json")
    shutil.copy2(args.decision, output / "model_decision.json")
    write_json(output / "denominator.json", binding["denominator_energies"])
    record: dict[str, Any] = {"kind": "star_phase", "attribution": "read_only_analysis_relocation_model_selected_in_chia", "source_commit": commit, "parent_binding_sha256": file_hash(args.binding), "parent_graph_sha256": binding["parent_routed_files_sha256"]["routed.v"], "parent_odb_sha256": binding["parent_routed_files_sha256"]["routed.odb"], "parent_spef_sha256": binding["parent_routed_files_sha256"]["routed.spef"], "analysis_sha256": file_hash(args.analysis), "decision_sha256": file_hash(args.decision), "recipe_hashes": recipe_hashes, "implementation_key_sha256": implementation_key, "status": "STARTED", "route_submission_counted": 1, "mapped_submission_counted": 0}
    record["star_root"] = '_318_'
    receipt = output / "receipt.json"
    try:
        eco = run_openroad(output, "eco.tcl", "eco")
        record["eco"] = eco
        eco_text = (output / "eco.log").read_text(encoding="utf-8", errors="replace")
        arrivals = ARRIVAL_RE.findall(eco_text)
        if eco["returncode"] != 0 or "CHIA_STAR_PHASE_COMPLETE" not in eco_text or not arrivals or abs(float(arrivals[0]) - binding["parent_delay_ns"]) > 1e-6:
            raise EcoError("verified parent extracted STA or phase ECO failed")
        record["parent_extracted_delay_ns"] = float(arrivals[0])
        check_placement_consistency(output / "original_placement.def", output / "eco_placement.def")
        record["placement_guard"] = "PASS"
        pre_route, pre_odb = output / "eco_pre_route.v", output / "eco_pre_route.odb"
        if not pre_route.is_file() or not pre_odb.is_file():
            raise EcoError("phase ECO omitted new graph or ODB")
        change = validate_phase_pairing(output / "original_routed.v", pre_route)
        record["cell_change"] = change
        record["eco_pre_route_sha256"] = file_hash(pre_route)
        record["eco_pre_route_odb_sha256"] = file_hash(pre_odb)
        pre_proof = proof(output, "pre_route_proof", output / "original_routed.v", pre_route, proof_recipe)
        record["pre_route_proof"] = pre_proof
        if pre_proof["status"] != "PASS":
            raise EcoError(f"pre-route proof was {pre_proof['status']}")
        routed = run_openroad(output, "reroute.tcl", "reroute")
        record["reroute"] = routed
        reroute_text = (output / "reroute.log").read_text(encoding="utf-8", errors="replace")
        if (routed["returncode"] != 0
                or "CHIA_STAR_PHASE_ROUTING_SDC 2.575 0.05 0.005" not in reroute_text
                or "CHIA_STAR_PHASE_OLD_SIGNAL_WIRES_CLEARED" not in reroute_text
                or "CHIA_STAR_PHASE_PLACEMENT_CHECKED" not in reroute_text
                or "CHIA_STAR_PHASE_RCX_COMPLETE" not in reroute_text):
            raise EcoError("fresh route/RCX or old-wire clearance failed")
        new_route, new_spef = output / "routed.v", output / "routed.spef"
        if not new_route.is_file() or not new_spef.is_file() or file_hash(new_spef) == binding["parent_routed_files_sha256"]["routed.spef"]:
            raise EcoError("new routed graph or fresh SPEF missing")
        if netlist_cells(pre_route) != netlist_cells(new_route):
            raise EcoError("reroute changed phase logic graph")
        check_placement_consistency(output / "original_placement.def", output / "routed_placement.def")
        final_proof = proof(output, "final_proof", output / "original_routed.v", new_route, proof_recipe)
        record["final_proof"] = final_proof
        if final_proof["status"] != "PASS":
            raise EcoError(f"final routed graph proof was {final_proof['status']}")
        area = parse_routed_area_from_log(output / "reroute.log")
        if area is None:
            raise EcoError("fresh routed area missing")
        command = [sys.executable, str(repo / "research/ecc_perf_bench/bench_ecc_routed_three_profile.py"), "--repo-root", str(repo), "--routed-netlist", str(new_route), "--spef", str(new_spef), "--artifact-dir", str(output / "three_profile"), "--width", "64", "--python", sys.executable, "--cpus", "2", "--denominator-json", str(output / "denominator.json"), "--delay-ceiling", "2.40", "--routed-area-um2", str(area), "--power-diagnostic"]
        started = time.monotonic()
        measured = subprocess.run(command, capture_output=True, text=True, check=False)
        (output / "measurement.log").write_text(measured.stdout + measured.stderr, encoding="utf-8")
        record["measurement_command"] = command
        record["measurement_exit_code"] = measured.returncode
        record["measurement_wall_s"] = round(time.monotonic() - started, 3)
        summary_path = output / "three_profile/routed_3p_summary.json"
        if not summary_path.is_file():
            raise EcoError("fresh three-profile summary missing")
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        record["measurement"] = summary
        if measured.returncode != 0 or summary.get("measurement_valid") is not True:
            raise EcoError("fresh three-profile measurement invalid")
        record["status"] = "OK"
        record["feasible"] = summary.get("feasible") is True
        record["routed_delay_ns"] = summary.get("routed_delay_ns")
        record["routed_area_um2"] = area
        record["j_score"] = summary.get("j_score")
        record["raw_energies_pj"] = summary.get("raw_energies_pj")
        record["hashes"] = {"eco_pre_route": file_hash(pre_route), "eco_routed_netlist": file_hash(new_route), "eco_routed_odb": file_hash(output / "routed.odb"), "eco_routed_spef": file_hash(new_spef), "final_proof_log": final_proof["log_sha256"]}
        write_json(receipt, record)
        print(json.dumps({"status": record["status"], "feasible": record["feasible"], "delay_ns": record["routed_delay_ns"], "j_score": record["j_score"], "receipt": str(receipt)}, sort_keys=True))
        return 0
    except Exception as exc:
        record["status"] = "ERROR_OR_UNKNOWN"
        record["error"] = f"{type(exc).__name__}: {exc}"
        write_json(receipt, record)
        print(json.dumps({"status": record["status"], "error": record["error"], "receipt": str(receipt)}, sort_keys=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
