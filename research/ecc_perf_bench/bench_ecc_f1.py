#!/usr/bin/env python3
"""Bounded F1-v1 route, formal equivalence proof, and three-profile measurement helper.

CLI Interface:
  --repo-root --mapped-netlist --expected-mapped-sha256 --artifact-dir --python --width=32|64 --cpus=2 --flow=F1-v1

Enforces:
  * Input mapped netlist SHA-256 match
  * Unique, fresh artifact directory (cannot overwrite existing jobs)
  * Exact container ID lifecycle cleanup (no host-wide ray stop or docker prune)
  * Whole-output miter equivalence proof verifying pre-repair vs routed netlists
  * Verification that excluded tap/decap instances are portless physical cells
  * Proof timeout/UNKNOWN is strictly not PASS
  * Route-only three-profile measurement handover to W4 helper preserving IDs & cost
  * Strict separation of functional_valid and measurement_valid (dryrun cannot PASS)
"""

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
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from .recovery_target import target_ns
except ImportError:
    from recovery_target import target_ns

F1_TCL_SHA256 = "68ec5ad365c6e5cd86d93df5dd24df58ba5deb766c380cb28909ac01c282a415"
F1_V1_TCL_SHA256 = F1_TCL_SHA256
F1_V2_TCL_SHA256 = "3e60f578a14a88e05d42206eda175e07115afa46ade80b853ea20481a26fb923"
F1_V3_TCL_SHA256 = "39806753c4dacf0473f28443df96a202358ba6ffbae7e4f7ff3d2b41424af93a"
F1_V4_TCL_SHA256 = "d08ca5d15da104ec9dcc7c56e6aeee46553e4f029fa407b8d0bd99c97afbdb48"
F1_V5_TCL_SHA256 = "de032b7154c4fd619708b15f81e829926bb6aa8c5a38c5aa886826883c89cb01"
F1_V6_TCL_SHA256 = "d27d0e6dc06c91a486e1aefa1922204cba3fc613207acfa1951fae72cdb03417"
F1_V7_TCL_SHA256 = "0b78b010b5b499ec910bad971fdbae3cc94a0c8371e05ede5ad939e3b5846f27"
F1_V8_TCL_SHA256 = "99b5db032dc064c496b2e652dfe2e75e5cf356c446d0affcbf15fbda2b140d9a"
F1_V9_TCL_SHA256 = "b8b483943d5c713253be97257e3ecb4d318caff1c9a8877a09474d1c8e0bd948"
F1_V10_TCL_SHA256 = "f3fb94f504552925f920978733ad5e4f377c69346b249473f28ca4a224f3a225"
F1_V11_TCL_SHA256 = "9dde26da482f24f2acf7a054ddee6cad8805a78fe90645e30294e5f85a74d9c2"
F1_YS_SHA256 = "d3036fb932303b6e65f59cba7196559b29d2856884096b9f70f98eaab34ff9a0"

FLOW_RECIPES: dict[str, dict[str, Any]] = {
    "F1-v1": {
        "recipe": "eda/ecc_f1/ecc_f1_v1.tcl",
        "hash": F1_TCL_SHA256,
        "optimizer_target_ns": 2.40,
        "tcl_staged_name": "f1-v1.tcl",
    },
    "F1-v2": {
        "recipe": "eda/ecc_f1/ecc_f1_v2.tcl",
        "hash": F1_V2_TCL_SHA256,
        "optimizer_target_ns": 2.35,
        "tcl_staged_name": "f1-v2.tcl",
    },
    "F1-v4-route-control": {
        "recipe": "eda/ecc_f1/ecc_f1_v4_route_control.tcl",
        "hash": "100dbad8ff927f826cfddfd22101e37b2c5be7c54c087ecd27d5ae0a9866c2ae",
        "optimizer_target_ns": 2.35,
        "tcl_staged_name": "f1-v4-route-control.tcl",
    },
    "F1-v4": {
        "recipe": "eda/ecc_f1/ecc_f1_v4.tcl",
        "hash": F1_V4_TCL_SHA256,
        "optimizer_target_ns": 2.35,
        "tcl_staged_name": "f1-v4.tcl",
    },
    "F1-v5": {
        "recipe": "eda/ecc_f1/ecc_f1_v5.tcl",
        "hash": F1_V5_TCL_SHA256,
        "optimizer_target_ns": 2.35,
        "tcl_staged_name": "f1-v5.tcl",
    },
    "F1-v6": {
        "recipe": "eda/ecc_f1/ecc_f1_v6.tcl",
        "hash": F1_V6_TCL_SHA256,
        "optimizer_target_ns": 2.35,
        "tcl_staged_name": "f1-v6.tcl",
    },
    "F1-v7": {
        "recipe": "eda/ecc_f1/ecc_f1_v7.tcl",
        "hash": F1_V7_TCL_SHA256,
        "optimizer_target_ns": 2.35,
        "setup_target_ns": 2.35,
        "recovery_target_ns": 2.40,
        "tcl_staged_name": "f1-v7.tcl",
    },
    "F1-v8": {
        "recipe": "eda/ecc_f1/ecc_f1_v8.tcl",
        "hash": F1_V8_TCL_SHA256,
        "optimizer_target_ns": 2.35,
        "setup_target_ns": 2.35,
        "recovery_target_ns": 2.575,
        "proxy_offset_prior_ns": 0.173345,
        "proxy_offset_reference": "338a/M0 F1-v5 global-route arrival minus final extracted delay; approximate prior",
        "tcl_staged_name": "f1-v8.tcl",
    },
    "F1-v11-timing-place-virtual": {
        "recipe": "eda/ecc_f1/ecc_f1_v11.tcl",
        "hash": F1_V11_TCL_SHA256,
        "optimizer_target_ns": 2.35,
        "setup_target_ns": 2.35,
        "recovery_target_ns": 2.575,
        "placement_mode": "timing_driven_routability_driven_keep_resize_below_overflow_0",
        "tcl_staged_name": "f1-v11.tcl",
    },
    "F1-v10-timing-place": {
        "recipe": "eda/ecc_f1/ecc_f1_v10.tcl",
        "hash": F1_V10_TCL_SHA256,
        "optimizer_target_ns": 2.35,
        "setup_target_ns": 2.35,
        "recovery_target_ns": 2.575,
        "placement_mode": "timing_driven_and_routability_driven",
        "tcl_staged_name": "f1-v10.tcl",
    },
    "F1-v9": {
        "recipe": "eda/ecc_f1/ecc_f1_v9.tcl",
        "hash": F1_V9_TCL_SHA256,
        "optimizer_target_ns": 2.35,
        "setup_target_ns": 2.35,
        "tcl_staged_name": "f1-v9.tcl",
    },
    "F1-v3": {
        "recipe": "eda/ecc_f1/ecc_f1_v3.tcl",
        "hash": F1_V3_TCL_SHA256,
        "optimizer_target_ns": 2.35,
        "tcl_staged_name": "f1-v3.tcl",
    },
}

B271_F0_DENOMINATOR_ENERGIES = {
    "stress_encoded": 2.541007707,
    "valid_uniform": 2.027927403,
    "valid_low_toggle": 0.4358843944,
}

DEFAULT_IMAGE = (
    "docker.io/hpretl/iic-osic-tools@sha256:"
    "65852976cad4af640c9d848762215137e87ec125111a6d06c850c3ab4e9695fb"
)
ALLOWED_PHYSICAL_CELL_TYPES = {
    "sky130_fd_sc_hd__tapvpwrvgnd_1",
    "sky130_fd_sc_hd__decap_3",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_physical_cells_are_portless(verilog_path: Path) -> tuple[bool, str, list[str]]:
    """Verify that all excluded tap/decap instances in the netlist are portless physical cells.

    Only disconnected physical tap and decap cells may be excluded.
    Any instance with signal connections or any other cell type excluded is invalid.
    """
    if not verilog_path.is_file():
        return False, f"verilog file not found: {verilog_path}", []

    text = verilog_path.read_text(encoding="utf-8", errors="replace")
    inst_pattern = re.compile(
        r"\b(sky130_fd_sc_hd__\w+)\s+([\w\\$]+)\s*\((.*?)\)\s*;",
        re.DOTALL,
    )

    found_instances: list[str] = []
    for match in inst_pattern.finditer(text):
        cell_type = match.group(1)
        inst_name = match.group(2)
        ports = match.group(3).strip()

        if cell_type in ALLOWED_PHYSICAL_CELL_TYPES:
            if ports:
                return (
                    False,
                    f"physical cell {cell_type} instance {inst_name} has connected ports: {ports}",
                    [],
                )
            found_instances.append(inst_name)

    return True, f"verified {len(found_instances)} portless physical cell instances", found_instances


def compute_j_metric(
    candidate_energies: dict[str, float],
    denominator_energies: dict[str, float] = B271_F0_DENOMINATOR_ENERGIES,
) -> dict[str, Any]:
    """Compute J-score as geometric mean of per-profile energy ratios against baseline denominator."""
    ratios: dict[str, float] = {}
    for p in ("stress_encoded", "valid_uniform", "valid_low_toggle"):
        cand_e = candidate_energies.get(p)
        denom_e = denominator_energies.get(p)
        if cand_e is None or denom_e is None or cand_e <= 0.0 or denom_e <= 0.0:
            raise ValueError(f"invalid energy for profile {p}")
        ratios[p] = cand_e / denom_e

    product = 1.0
    for val in ratios.values():
        product *= val
    j_score = product ** (1.0 / len(ratios))
    return {
        "j_score": j_score,
        "energy_ratios": ratios,
        "denominator_energies": {p: float(denominator_energies[p]) for p in ratios},
    }


def parse_routed_area_from_log(log_path: Path) -> float | None:
    """Parse routed design area in um^2 from OpenROAD log."""
    if not log_path.is_file():
        return None
    text = log_path.read_text(encoding="utf-8", errors="replace")
    areas = re.findall(r"^Design area\s+([\d.eE+-]+)\s+um\^2", text, re.MULTILINE)
    return float(areas[-1]) if areas else None


def locate_three_profile_helper(repo_root: Path, explicit_path: str | None = None) -> Path:
    """Locate the W4 three-profile measurement helper."""
    if explicit_path:
        p = Path(explicit_path).resolve()
        if p.is_file():
            return p
    in_repo = repo_root / "research/ecc_perf_bench/bench_ecc_routed_three_profile.py"
    if in_repo.is_file():
        return in_repo
    w4_canonical = Path(
        "/home/thisray/projects/260908_CHIA_Hackathon_workers/chia-top1-w4-20260923/research/ecc_perf_bench/bench_ecc_routed_three_profile.py"
    )
    if w4_canonical.is_file():
        return w4_canonical
    raise FileNotFoundError("bench_ecc_routed_three_profile.py not found in repo or W4 workspace")


def run_bounded_f1_route(
    artifact_dir: Path,
    image: str,
    width: int,
    cpus: int,
    timeout_s: int = 600,
    tcl_name: str = "f1-v1.tcl",
    recovery_target_ns: float | None = None,
) -> tuple[int, str]:
    """Execute OpenROAD F1 container with exact single container ID cleanup."""
    container_name = f"chia-f1-{artifact_dir.name}-{uuid.uuid4().hex}"
    target_env = (["-e", f"FAMILYRTL_RECOVERY_TARGET_NS={recovery_target_ns:.3f}"]
                  if recovery_target_ns is not None else [])
    create_cmd = [
        "docker", "create",
        "--name", container_name,
        "--cpus", str(cpus),
        "--memory", "12g",
        "--network", "none",
        "--entrypoint", "/bin/bash",
        "-e", f"ECC_ROUTE_WIDTH={width}",
        *target_env,
        "-v", f"{artifact_dir}:/artifacts",
        image,
        "-lc", f"openroad -no_init -exit /artifacts/{tcl_name}",
    ]
    proc = subprocess.run(create_cmd, capture_output=True, text=True, check=True)
    container_id = proc.stdout.strip()
    (artifact_dir / "container_id.txt").write_text(container_id + "\n", encoding="utf-8")

    try:
        (artifact_dir / "submitted_at.txt").write_text(
            datetime.now(timezone.utc).isoformat() + "\n", encoding="utf-8"
        )
        subprocess.run(["docker", "start", container_id], check=True, capture_output=True)
        try:
            wait_proc = subprocess.run(
                ["docker", "wait", container_id],
                capture_output=True,
                text=True,
                timeout=timeout_s,
            )
            exit_code_str = wait_proc.stdout.strip()
            exit_code = int(exit_code_str) if exit_code_str.isdigit() else 1
        except subprocess.TimeoutExpired:
            exit_code = 124
            exit_code_str = "TIMEOUT"

        (artifact_dir / "exit_code").write_text(exit_code_str + "\n", encoding="utf-8")
        logs_proc = subprocess.run(
            ["docker", "logs", container_id],
            capture_output=True,
            text=True,
            check=False,
        )
        log_text = logs_proc.stdout + logs_proc.stderr
        (artifact_dir / "openroad.log").write_text(log_text, encoding="utf-8")
        return exit_code, log_text
    finally:
        subprocess.run(["docker", "rm", "-f", container_id], capture_output=True, check=False)


def proof_log_is_pass(exit_code: str, log_text: str) -> bool:
    """Return true only for a complete successful whole-output SAT proof."""
    return (
        exit_code == "0"
        and "SAT proof finished - no model found: SUCCESS!" in log_text
        and "SAT proof failed" not in log_text
    )


def run_yosys_miter_proof(
    artifact_dir: Path,
    image: str,
    cpus: int,
    timeout_s: int = 300,
) -> tuple[str, str]:
    """Execute whole-output miter equivalence proof with exact single container ID cleanup."""
    proof_name = f"chia-proof-{artifact_dir.name}-{uuid.uuid4().hex}"
    create_cmd = [
        "docker", "create",
        "--name", proof_name,
        "--cpus", str(cpus),
        "--memory", "12g",
        "--network", "none",
        "--entrypoint", "/bin/bash",
        "-v", f"{artifact_dir}:/artifacts",
        image,
        "-lc", "yosys -s /artifacts/f1-equivalence.ys",
    ]
    proc = subprocess.run(create_cmd, capture_output=True, text=True, check=True)
    container_id = proc.stdout.strip()
    (artifact_dir / "proof_container_id.txt").write_text(container_id + "\n", encoding="utf-8")

    try:
        subprocess.run(["docker", "start", container_id], check=True, capture_output=True)
        try:
            wait_proc = subprocess.run(
                ["docker", "wait", container_id],
                capture_output=True,
                text=True,
                timeout=timeout_s,
            )
            exit_code_str = wait_proc.stdout.strip()
        except subprocess.TimeoutExpired:
            exit_code_str = "TIMEOUT"

        (artifact_dir / "proof-exit_code").write_text(exit_code_str + "\n", encoding="utf-8")
        logs_proc = subprocess.run(
            ["docker", "logs", container_id],
            capture_output=True,
            text=True,
            check=False,
        )
        log_text = logs_proc.stdout + logs_proc.stderr
        (artifact_dir / "proof.log").write_text(log_text, encoding="utf-8")

        if exit_code_str == "TIMEOUT":
            return "UNKNOWN", log_text
        if proof_log_is_pass(exit_code_str, log_text):
            return "PASS", log_text
        return "FAIL", log_text
    finally:
        subprocess.run(["docker", "rm", "-f", container_id], capture_output=True, check=False)


def execute_f1_flow(
    repo_root: Path,
    mapped_netlist: Path,
    expected_mapped_sha256: str,
    artifact_dir: Path,
    python_bin: str,
    width: int = 64,
    cpus: int = 2,
    flow: str = "F1-v1",
    recovery_target_ns: float | None = None,
    delay_ceiling: float = 2.40,
    denominator_json: str | None = None,
    reuse_artifacts_dir: str | None = None,
    dry_run: bool = False,
    three_profile_helper: str | None = None,
    image: str = DEFAULT_IMAGE,
    timeout_s: int = 600,
) -> dict[str, Any]:
    """Execute or verify the F1-v1 route, proof, and three-profile measurement flow."""
    t_start = time.monotonic()

    # Preflight validations
    if reuse_artifacts_dir:
        raise ValueError("unsafe artifact reuse is explicitly rejected in this runtime")
    if not mapped_netlist.is_file():
        raise FileNotFoundError(f"mapped netlist not found: {mapped_netlist}")
    actual_mapped_sha256 = sha256_file(mapped_netlist)
    if actual_mapped_sha256 != expected_mapped_sha256:
        raise ValueError(
            f"mapped netlist SHA mismatch: expected {expected_mapped_sha256}, got {actual_mapped_sha256}"
        )
    if width not in (32, 64) or cpus != 2 or flow not in FLOW_RECIPES:
        raise ValueError(f"helper requires width in (32, 64), cpus=2, and flow in {sorted(FLOW_RECIPES)}")
    recovery_target_ns = target_ns(recovery_target_ns, flow)

    flow_cfg = FLOW_RECIPES[flow]
    optimizer_target_ns = flow_cfg["optimizer_target_ns"]
    tcl_recipe_rel = flow_cfg["recipe"]
    tcl_expected_sha256 = flow_cfg["hash"]
    tcl_staged_name = flow_cfg["tcl_staged_name"]

    # Artifact directory freshness check
    if artifact_dir.exists() and any(artifact_dir.iterdir()):
        raise ValueError(f"artifact directory already exists and is not empty: {artifact_dir}")
    artifact_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(artifact_dir, 0o777)

    # Check and stage recipes
    tcl_recipe = repo_root / tcl_recipe_rel
    ys_recipe = repo_root / "eda/ecc_f1/ecc_f1_equivalence.ys"
    if not tcl_recipe.is_file() or sha256_file(tcl_recipe) != tcl_expected_sha256:
        raise ValueError(f"frozen {flow} Tcl recipe missing or hash mismatch")
    if not ys_recipe.is_file() or sha256_file(ys_recipe) != F1_YS_SHA256:
        raise ValueError(f"frozen {flow} equivalence proof recipe missing or hash mismatch")

    staged_mapped = artifact_dir / "mapped.v"
    staged_tcl = artifact_dir / tcl_staged_name
    staged_ys = artifact_dir / "f1-equivalence.ys"

    shutil.copy2(mapped_netlist, staged_mapped)
    shutil.copy2(tcl_recipe, staged_tcl)
    shutil.copy2(ys_recipe, staged_ys)

    # Prepare denominator
    denominator = dict(B271_F0_DENOMINATOR_ENERGIES)
    if denominator_json:
        denom_path = Path(denominator_json).resolve()
        if denom_path.is_file():
            denominator = json.loads(denom_path.read_text(encoding="utf-8"))
    if width == 32:
        required_profiles = ("stress_encoded", "valid_uniform", "valid_low_toggle")
        if not isinstance(denominator, dict) or denominator.get("width") != 32:
            raise ValueError("width=32 requires a denominator JSON explicitly bound with width=32")
        if any(not isinstance(denominator.get(profile), (int, float)) or denominator[profile] <= 0 for profile in required_profiles):
            raise ValueError("width=32 denominator must contain finite positive values for all three profiles")

    context_dict: dict[str, Any] = {
        "input_slew_ns": 0.05,
        "output_load_pf": 0.005,
        "optimization_target_ns": optimizer_target_ns,
        "measurement_virtual_clock_period_ns": 10.0,
        "measurement_interval_ps": 10000,
        "corner": "sky130_fd_sc_hd__tt_025C_1v80",
        "width": width,
        "cpus": cpus,
        "memory": "12g",
    }
    if "recovery_target_ns" in flow_cfg or flow == "F1-v9":
        context_dict["recovery_target_ns"] = (recovery_target_ns if flow == "F1-v9" else flow_cfg["recovery_target_ns"])
        context_dict["setup_target_ns"] = flow_cfg.get("setup_target_ns", optimizer_target_ns)
    if "placement_mode" in flow_cfg:
        context_dict["placement_mode"] = flow_cfg["placement_mode"]
    if "proxy_offset_prior_ns" in flow_cfg:
        context_dict["proxy_offset_prior_ns"] = flow_cfg["proxy_offset_prior_ns"]
        context_dict["proxy_offset_reference"] = flow_cfg["proxy_offset_reference"]

    if dry_run:
        summary = {
            "flow": flow,
            "width": width,
            "status": "DRY_RUN_PREPARED",
            "functional_valid": False,
            "measurement_valid": False,
            "route_valid": False,
            "feasible": False,
            "delay_ceiling_ns": delay_ceiling,
            "routed_delay_ns": None,
            "routed_area_um2": None,
            "raw_energies_pj": {},
            "j_score": None,
            "energy_ratios": {},
            "denominator_energies": denominator,
            "proof": {"status": "DRY_RUN", "method": "yosys_sat_whole_output_miter"},
            "hashes": {
                "mapped_netlist": actual_mapped_sha256,
                "tcl_recipe": tcl_expected_sha256,
                "proof_recipe": F1_YS_SHA256,
            },
            "ids": {
                "flow": flow,
                "workloads": ["stress_encoded", "valid_uniform", "valid_low_toggle"],
                "context": context_dict,
            },
            "cost": {"wall_s": round(time.monotonic() - t_start, 3)},
            "artifacts": {"artifact_dir": str(artifact_dir)},
        }
        (artifact_dir / "f1_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return summary

    # Handle Route Stage (run docker)
    routed_netlist = artifact_dir / "routed.v"
    routed_spef = artifact_dir / "routed.spef"
    pre_repair = artifact_dir / "pre_repair.v"
    openroad_log = artifact_dir / "openroad.log"

    route_exit, _ = run_bounded_f1_route(artifact_dir, image, width, cpus, timeout_s, tcl_name=tcl_staged_name, recovery_target_ns=recovery_target_ns)
    if route_exit != 0:
        summary = {
            "flow": flow,
            "status": "ROUTE_FAILED",
            "functional_valid": False,
            "measurement_valid": False,
            "route_valid": False,
            "feasible": False,
            "error": f"OpenROAD returned exit code {route_exit}",
            "recovery_target_ns": recovery_target_ns,
            "artifacts": {"artifact_dir": str(artifact_dir)},
        }
        (artifact_dir / "f1_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return summary

    if not routed_netlist.is_file() or not routed_spef.is_file() or not pre_repair.is_file():
        summary = {
            "flow": flow,
            "status": "MISSING_ROUTE_OUTPUTS",
            "functional_valid": False,
            "measurement_valid": False,
            "route_valid": False,
            "feasible": False,
            "error": "routed.v, routed.spef, or pre_repair.v not produced",
            "artifacts": {"artifact_dir": str(artifact_dir)},
        }
        (artifact_dir / "f1_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return summary

    # Stage: Formal Equivalence Proof
    portless_pre, portless_pre_msg, _ = verify_physical_cells_are_portless(pre_repair)
    portless_routed, portless_routed_msg, _ = verify_physical_cells_are_portless(routed_netlist)
    portless_ok = portless_pre and portless_routed

    if not portless_ok:
        proof_status = "FAIL"
        proof_error = f"Physical cell portless check failed: pre={portless_pre_msg}; routed={portless_routed_msg}"
        functional_valid = False
    else:
        proof_status, _ = run_yosys_miter_proof(artifact_dir, image, cpus)
        functional_valid = (proof_status == "PASS")
        proof_error = None if functional_valid else f"Yosys miter proof returned {proof_status}"

    placement_proof: dict[str, Any] | None = None
    if flow in ("F1-v10-timing-place", "F1-v11-timing-place-virtual"):
        # Timing-driven placement can keep buffer insertions before pre_repair.v.
        placement_case = artifact_dir / "placement_input_proof"
        placement_case.mkdir(parents=True, exist_ok=False)
        os.chmod(placement_case, 0o777)
        shutil.copy2(staged_mapped, placement_case / "pre_repair.v")
        shutil.copy2(pre_repair, placement_case / "routed.v")
        shutil.copy2(staged_ys, placement_case / "f1-equivalence.ys")
        try:
            placement_status, _ = run_yosys_miter_proof(placement_case, image, cpus)
            placement_error = None
        except Exception as exc:
            placement_status = "UNKNOWN"
            placement_error = f"{type(exc).__name__}: {exc}"
        placement_log = placement_case / "proof.log"
        placement_proof = {
            "status": placement_status,
            "method": "yosys_sat_whole_output_miter",
            "from_sha256": actual_mapped_sha256,
            "to_sha256": sha256_file(pre_repair),
            "log_sha256": sha256_file(placement_log) if placement_log.is_file() else None,
            "error": placement_error,
        }
        if placement_status != "PASS":
            functional_valid = False
            proof_status = placement_status
            proof_error = f"mapped-to-postplacement proof was {placement_status}: {placement_error or 'complete proof missing'}"

    # Stage: Three-Profile Measurement Handover
    tp_helper = locate_three_profile_helper(repo_root, three_profile_helper)
    tp_dir = artifact_dir / "three_profile"

    measurement_valid = False
    routed_delay_ns = None
    raw_energies_pj: dict[str, float] = {}
    j_metric_data: dict[str, Any] = {}

    denom_file = artifact_dir / "denominator.json"
    denom_file.write_text(json.dumps(denominator, indent=2), encoding="utf-8")
    tp_cmd = [
        python_bin,
        str(tp_helper),
        "--repo-root", str(repo_root),
        "--routed-netlist", str(routed_netlist),
        "--spef", str(routed_spef),
        "--artifact-dir", str(tp_dir),
        "--width", str(width),
        "--python", python_bin,
        "--cpus", str(cpus),
        "--denominator-json", str(denom_file),
        "--delay-ceiling", str(delay_ceiling),
    ]
    tp_proc = subprocess.run(tp_cmd, capture_output=True, text=True, check=False)
    (artifact_dir / "tp_helper.log").write_text(tp_proc.stdout + tp_proc.stderr, encoding="utf-8")

    summary_3p_path = tp_dir / "routed_3p_summary.json"
    if summary_3p_path.is_file():
        try:
            tp_summary = json.loads(summary_3p_path.read_text(encoding="utf-8"))
            measurement_valid = bool(tp_summary.get("measurement_valid"))
            routed_delay_ns = tp_summary.get("routed_delay_ns")
            raw_energies_pj = tp_summary.get("raw_energies_pj") or {}
            if raw_energies_pj and len(raw_energies_pj) == 3:
                j_metric_data = compute_j_metric(raw_energies_pj, denominator)
        except (OSError, json.JSONDecodeError, ValueError):
            measurement_valid = False

    routed_area_um2 = parse_routed_area_from_log(openroad_log)

    route_valid = bool(functional_valid and measurement_valid)
    feasible = bool(
        route_valid
        and routed_delay_ns is not None
        and routed_delay_ns <= delay_ceiling
    )

    hashes = {
        "mapped_netlist": actual_mapped_sha256,
        "pre_repair_netlist": sha256_file(pre_repair) if pre_repair.is_file() else None,
        "routed_netlist": sha256_file(routed_netlist) if routed_netlist.is_file() else None,
        "spef": sha256_file(routed_spef) if routed_spef.is_file() else None,
        "tcl_recipe": tcl_expected_sha256,
        "proof_recipe": F1_YS_SHA256,
    }
    for p_num in (1, 2, 3):
        pre_p = artifact_dir / f"pre_power_recovery_pass{p_num}.v"
        post_p = artifact_dir / f"post_power_recovery_pass{p_num}.v"
        if pre_p.is_file():
            hashes[f"pre_power_recovery_pass{p_num}"] = sha256_file(pre_p)
        if post_p.is_file():
            hashes[f"post_power_recovery_pass{p_num}"] = sha256_file(post_p)
    if (artifact_dir / "post_power_recovery.v").is_file():
        hashes["post_power_recovery"] = sha256_file(artifact_dir / "post_power_recovery.v")
    if placement_proof is not None:
        hashes["placement_input_proof_log"] = placement_proof["log_sha256"]

    artifacts_dict: dict[str, Any] = {
        "artifact_dir": str(artifact_dir),
        "mapped_netlist": str(staged_mapped),
        "routed_netlist": str(routed_netlist),
        "spef": str(routed_spef),
        "pre_repair": str(pre_repair),
        "tcl_recipe": str(staged_tcl),
        "proof_recipe": str(staged_ys),
        "openroad_log": str(openroad_log) if openroad_log.is_file() else None,
        "proof_log": str(artifact_dir / "proof.log") if (artifact_dir / "proof.log").is_file() else None,
    }
    if placement_proof is not None:
        artifacts_dict["placement_input_proof"] = str(artifact_dir / "placement_input_proof")
    for p_num in (1, 2, 3):
        pre_p = artifact_dir / f"pre_power_recovery_pass{p_num}.v"
        post_p = artifact_dir / f"post_power_recovery_pass{p_num}.v"
        if pre_p.is_file():
            artifacts_dict[f"pre_power_recovery_pass{p_num}"] = str(pre_p)
        if post_p.is_file():
            artifacts_dict[f"post_power_recovery_pass{p_num}"] = str(post_p)
    if (artifact_dir / "post_power_recovery.v").is_file():
        artifacts_dict["post_power_recovery"] = str(artifact_dir / "post_power_recovery.v")

    power_passes = {}
    if openroad_log.is_file():
        log_text = openroad_log.read_text(encoding="utf-8", errors="replace")
        converged_match = re.search(r"CHIA_F1_V6_POWER_RECOVERY_CONVERGED_AT_PASS_(\d+)", log_text)
        converged_pass = int(converged_match.group(1)) if converged_match else None
        passes_info = {}
        for p_num in (1, 2, 3):
            pat = rf"CHIA_F1_V6_BEFORE_POWER_RECOVERY_PASS_{p_num}(.*?)CHIA_F1_V6_AFTER_POWER_RECOVERY_PASS_{p_num}"
            m = re.search(pat, log_text, re.DOTALL)
            if m:
                chunk = m.group(1)
                resized_m = re.search(r"\[INFO RSZ-0141\] Resized (\d+) instances\.", chunk)
                resized = int(resized_m.group(1)) if resized_m else 0
                passes_info[f"pass_{p_num}"] = {"resized_instances": resized}
        if passes_info or converged_pass is not None:
            power_passes = {
                "passes": passes_info,
                "converged_at_pass": converged_pass,
            }

    final_summary: dict[str, Any] = {
        "flow": flow,
        "width": width,
        "status": "OK" if route_valid else ("PROOF_FAIL" if not functional_valid else "MEASUREMENT_FAIL"),
        "functional_valid": functional_valid,
        "measurement_valid": measurement_valid,
        "route_valid": route_valid,
        "feasible": feasible,
        "delay_ceiling_ns": delay_ceiling,
        "routed_delay_ns": routed_delay_ns,
        "routed_area_um2": routed_area_um2,
        "raw_energies_pj": raw_energies_pj,
        "j_score": j_metric_data.get("j_score"),
        "energy_ratios": j_metric_data.get("energy_ratios"),
        "denominator_energies": denominator,
        "proof": {
            "status": proof_status,
            "method": "yosys_sat_whole_output_miter",
            "excluded_physical_cells": sorted(ALLOWED_PHYSICAL_CELL_TYPES),
            "portless_verified": portless_ok,
            "error": proof_error,
        },
        "hashes": hashes,
        "ids": {
            "flow": flow,
            "workloads": ["stress_encoded", "valid_uniform", "valid_low_toggle"],
            "context": context_dict,
        },
        "cost": {
            "wall_s": round(time.monotonic() - t_start, 3),
            "delay_ns": routed_delay_ns,
            "area_um2": routed_area_um2,
            "raw_energies_pj": raw_energies_pj,
            "j_score": j_metric_data.get("j_score"),
        },
        "artifacts": artifacts_dict,
    }
    if power_passes:
        final_summary["power_recovery_passes"] = power_passes
    if placement_proof is not None:
        final_summary["placement_input_proof"] = placement_proof
        final_summary["proof"]["postplacement_to_final_status"] = (
            "PASS" if (artifact_dir / "proof-exit_code").is_file()
            and (artifact_dir / "proof-exit_code").read_text().strip() == "0"
            and "SAT proof finished - no model found: SUCCESS!" in (artifact_dir / "proof.log").read_text(errors="replace")
            else "UNKNOWN"
        )

    (artifact_dir / "f1_summary.json").write_text(json.dumps(final_summary, indent=2), encoding="utf-8")
    return final_summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True, help="Repository root directory")
    parser.add_argument("--mapped-netlist", required=True, help="Path to input mapped.v")
    parser.add_argument("--expected-mapped-sha256", required=True, help="Expected SHA-256 of mapped.v")
    parser.add_argument("--artifact-dir", required=True, help="Fresh unique output directory")
    parser.add_argument("--python", default=sys.executable, help="Python executable to use")
    parser.add_argument("--width", type=int, default=64, help="ECC data width")
    parser.add_argument("--cpus", type=int, default=2, help="Number of CPU cores")
    parser.add_argument("--flow", default="F1-v1", choices=list(FLOW_RECIPES.keys()), help="Flow identifier")
    parser.add_argument("--recovery-target-ns", type=float, default=None, help="Required F1-v9 recovery target in ns")
    parser.add_argument("--delay-ceiling", type=float, default=2.40, help="Feasibility timing ceiling in ns")
    parser.add_argument("--denominator-json", default=None, help="Baseline denominator JSON path")
    parser.add_argument("--reuse-artifacts-dir", default=None, help="Directory of existing artifacts to reuse")
    parser.add_argument("--three-profile-helper", default=None, help="Explicit path to three profile helper")
    parser.add_argument("--image", default=DEFAULT_IMAGE, help="Docker container image")
    parser.add_argument("--timeout", type=int, default=600, help="Docker route timeout in seconds")
    parser.add_argument("--dry-run", action="store_true", help="Prepare directories and scripts without running EDA")

    args = parser.parse_args()

    repo = Path(args.repo_root).resolve()
    mapped = Path(args.mapped_netlist).resolve()
    artifact = Path(args.artifact_dir).resolve()

    summary = execute_f1_flow(
        repo_root=repo,
        mapped_netlist=mapped,
        expected_mapped_sha256=args.expected_mapped_sha256,
        artifact_dir=artifact,
        python_bin=args.python,
        width=args.width,
        cpus=args.cpus,
        flow=args.flow,
        recovery_target_ns=args.recovery_target_ns,
        delay_ceiling=args.delay_ceiling,
        denominator_json=args.denominator_json,
        reuse_artifacts_dir=args.reuse_artifacts_dir,
        dry_run=args.dry_run,
        three_profile_helper=args.three_profile_helper,
        image=args.image,
        timeout_s=args.timeout,
    )

    print(json.dumps(summary, indent=2))
    if args.dry_run:
        return 0
    return 0 if summary.get("route_valid") else 1


if __name__ == "__main__":
    raise SystemExit(main())
