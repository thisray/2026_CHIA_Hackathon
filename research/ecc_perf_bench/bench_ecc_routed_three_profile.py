#!/usr/bin/env python3
"""Routed three-profile measurement helper for ECC designs.

Drives the routed netlist and matching SPEF through the three-profile measurement context:
  * Profiles: stress_encoded, valid_uniform, valid_low_toggle
  * Workload: 1024 vectors each, 10000 ps interval
  * Electrical: input slew 0.05 ns, output load 0.005 pF, fixed corner
  * Timing: delay is max over all external outputs; feasibility is D <= 2.40 ns
  * Metric: J = geomean_p(E(x,F,p) / E(b271,F0,p)) using common b271/F0 denominator
  * Preserves per-profile raw energy, delay, and area
  * Requires explicit final routed netlist and matching SPEF (never renamed to mapped.v)
  * Generates fresh VCD per profile, preserving SHA-256 before optional deletion
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

PROFILES = ("stress_encoded", "valid_uniform", "valid_low_toggle")
DEFAULT_VECTORS_COUNT = 1024
DEFAULT_INTERVAL_PS = 10000
DEFAULT_INPUT_SLEW_NS = 0.05
DEFAULT_OUTPUT_LOAD_PF = 0.005
DEFAULT_FEASIBILITY_DELAY_NS = 2.40
DEFAULT_LIBERTY_CORNER = (
    "/foss/pdks/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib"
)
POWER_DIAGNOSTIC_VERSION = "ecc_instance_power_v1"
POWER_DIAGNOSTIC_SOURCE = Path(__file__).resolve().parents[2] / "eda/ecc_power_diagnostic/instance_power.tcl"
DEFAULT_IMAGE = (
    "docker.io/hpretl/iic-osic-tools@sha256:"
    "65852976cad4af640c9d848762215137e87ec125111a6d06c850c3ab4e9695fb"
)
GEOMETRY = {
    8: (4, 12),
    11: (4, 15),
    16: (5, 21),
    26: (5, 31),
    32: (6, 38),
    64: (7, 71),
}

STAGE_RE = re.compile(
    r"^\s*(?P<f1>-?[\d.]+)\s+(?P<f2>-?[\d.]+)\s+(?P<f3>-?[\d.]+)\s+"
    r"(?P<f4>-?[\d.]+)\s+(?P<f5>-?[\d.]+)\s*(?P<edge>[\^v])?\s+"
    r"(?P<pin>[\w\[\]./\\$:-]+)\s*(?:\((?P<cell>[\w$.]+)\))?\s*$"
)

ROUTED_3P_STA_TCL = """\
# Routed 3-profile post-route STA with symmetric electrical constraints
set liberty {liberty}
set_units -time ns -capacitance pF -voltage V -power W
read_liberty $liberty
read_verilog /artifacts/routed.v
link_design familyrtl_ecc_ppa
create_clock -name virtual_clock -period 10.0
set_input_delay 0.0 -clock virtual_clock [all_inputs]
set_output_delay 0.0 -clock virtual_clock [all_outputs]
set_input_transition {input_slew_ns} [all_inputs]
set_load {output_load_pf} [all_outputs]
set_max_delay 10.0 -from [all_inputs] -to [all_outputs]
read_spef /artifacts/routed.spef
report_checks -path_delay max -format full -fields {{slew cap input_pin net fanout}} -digits 6
report_wns
report_tns
check_setup -verbose
puts "FAMILYRTL_ROUTED_3P_STA_COMPLETE"
"""

ROUTED_3P_POWER_TCL = """\
# Routed 3-profile post-route activity power with symmetric electrical constraints
set liberty {liberty}
set_units -time ns -capacitance pF -voltage V -power W
read_liberty $liberty
read_verilog /artifacts/routed.v
link_design familyrtl_ecc_ppa
create_clock -name measurement_window -period 10.0
set_input_delay 0.0 -clock measurement_window [all_inputs]
set_output_delay 0.0 -clock measurement_window [all_outputs]
set_input_transition {input_slew_ns} [all_inputs]
set_load {output_load_pf} [all_outputs]
read_spef /artifacts/routed.spef
read_vcd -scope ecc_v3_tb/dut /artifacts/current_activity.vcd
report_activity_annotation -report_annotated > /artifacts/current_activity_annotation.log
report_power -digits 9 > /artifacts/current_power.log
puts "FAMILYRTL_ROUTED_3P_POWER_COMPLETE"
"""

RUN_SCRIPT_TEMPLATE = """\
#!/usr/bin/env bash
set -uo pipefail

echo "=== Stage 1: Post-route STA ==="
sta -exit /artifacts/routed_3p_sta.tcl > /artifacts/postroute_sta.log 2>&1
sta_status=$?
echo "sta_status=${{sta_status}}"

echo "=== Stage 2: Gate-level simulation compilation ==="
iverilog -g2012 -DFUNCTIONAL \\
  -DECC_V3_DATA_WIDTH={width} \\
  -DECC_V3_PARITY_WIDTH={parity_width} \\
  -DECC_V3_CODEWORD_WIDTH={codeword_width} \\
  -o /artifacts/simv \\
  /foss/pdks/sky130A/libs.ref/sky130_fd_sc_hd/verilog/primitives.v \\
  /foss/pdks/sky130A/libs.ref/sky130_fd_sc_hd/verilog/sky130_fd_sc_hd.v \\
  /artifacts/routed.v /workspace/eda/ecc_v3/ecc_v3_tb.sv \\
  > /artifacts/iverilog.log 2>&1
iverilog_status=$?
echo "iverilog_status=${{iverilog_status}}"

sim_status=0
power_status=0

for p in {profiles}; do
  if [[ ${{sta_status}} -eq 0 && ${{iverilog_status}} -eq 0 ]]; then
    echo "=== Profile $p: Simulation ==="
    cd /artifacts && vvp /artifacts/simv \\
      +workload=/artifacts/workload_${{p}}.hex \\
      +vcd=/artifacts/activity_${{p}}.vcd \\
      +profile=${{p}} +expected={count} +interval_ps={interval_ps} \\
      > /artifacts/sim_${{p}}.log 2>&1
    p_sim_exit=$?
    echo "${{p_sim_exit}}" > /artifacts/sim_${{p}}.exit
    if [[ ${{p_sim_exit}} -ne 0 ]]; then
      sim_status=1
    fi

    if [[ -f /artifacts/activity_${{p}}.vcd ]]; then
      sha256sum /artifacts/activity_${{p}}.vcd | awk '{{print $1}}' > /artifacts/vcd_${{p}}.sha256
      cp /artifacts/activity_${{p}}.vcd /artifacts/current_activity.vcd
      sta -exit /artifacts/routed_3p_power.tcl > /artifacts/opensta_${{p}}.log 2>&1
      p_power_exit=$?
      echo "${{p_power_exit}}" > /artifacts/power_${{p}}.exit
      if [[ ${{p_power_exit}} -ne 0 ]]; then
        power_status=1
      fi
      mv /artifacts/current_power.log /artifacts/power_${{p}}.log 2>/dev/null
      mv /artifacts/current_activity_annotation.log /artifacts/annotation_${{p}}.log 2>/dev/null
      rm -f /artifacts/current_activity.vcd
      if [[ "{delete_vcd}" == "True" ]]; then
        rm -f /artifacts/activity_${{p}}.vcd
      fi
    else
      sim_status=1
      power_status=1
    fi
  else
    sim_status=1
    power_status=1
  fi
done

cat > /artifacts/stage_status.json <<EOF
{{
  "postroute_sta": ${{sta_status}},
  "iverilog_compile": ${{iverilog_status}},
  "simulation": ${{sim_status}},
  "power": ${{power_status}}
}}
EOF

echo "FAMILYRTL_ECC_ROUTED_3P_MEASUREMENT_COMPLETE"
"""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _finite_positive(val: Any) -> bool:
    return (
        isinstance(val, (int, float))
        and not isinstance(val, bool)
        and math.isfinite(val)
        and val > 0.0
    )


def compute_j_metric(
    candidate_energies: dict[str, float],
    denominator_energies: dict[str, float],
) -> dict[str, Any]:
    """Compute J-score as geometric mean of per-profile energy ratios against baseline denominator."""
    ratios: dict[str, float] = {}
    for p in PROFILES:
        cand_e = candidate_energies.get(p)
        denom_e = denominator_energies.get(p)
        if not _finite_positive(cand_e) or not _finite_positive(denom_e):
            raise ValueError(f"profile {p} energy must be finite positive in candidate and denominator")
        ratios[p] = cand_e / denom_e

    product = 1.0
    for val in ratios.values():
        product *= val
    j_score = product ** (1.0 / len(PROFILES))
    return {
        "j_score": j_score,
        "energy_ratios": ratios,
        "denominator_energies": {p: float(denominator_energies[p]) for p in PROFILES},
    }


def parse_sta_report(path: Path) -> dict[str, Any]:
    """Parse routed STA timing report."""
    if not path.is_file():
        return {"status": "MISSING"}
    text = path.read_text(encoding="utf-8", errors="replace")
    out: dict[str, Any] = {
        "status": "OK",
        "complete_marker": (
            "FAMILYRTL_ROUTED_3P_STA_COMPLETE" in text
            or "FAMILYRTL_POSTROUTE_STA_COMPLETE" in text
        ),
    }

    startpoint_m = re.search(r"^Startpoint:\s*(\S+)", text, re.MULTILINE)
    if startpoint_m:
        out["startpoint"] = startpoint_m.group(1)

    endpoint_m = re.search(r"^Endpoint:\s*(\S+)", text, re.MULTILINE)
    if endpoint_m:
        out["endpoint"] = endpoint_m.group(1)

    # All data arrival times in the report
    arrivals = [
        float(val)
        for val in re.findall(r"^\s*([\d.]+)\s+data arrival time", text, re.MULTILINE)
    ]
    if arrivals:
        out["arrival_ns"] = arrivals[0]
        out["max_arrival_ns"] = max(arrivals)
    else:
        out["arrival_ns"] = None
        out["max_arrival_ns"] = None

    slack_m = re.search(r"^\s*(-?[\d.]+)\s+slack", text, re.MULTILINE)
    if slack_m:
        out["slack_ns"] = float(slack_m.group(1))

    wns_m = re.search(r"^wns\s+(-?[\d.eE+]+)", text, re.MULTILINE)
    if wns_m:
        out["wns"] = float(wns_m.group(1))

    tns_m = re.search(r"^tns\s+(-?[\d.eE+]+)", text, re.MULTILINE)
    if tns_m:
        out["tns"] = float(tns_m.group(1))

    # Parse stages of critical path
    stages: list[dict[str, Any]] = []
    prev_total = 0.0
    in_block = False
    for line in text.splitlines():
        if "Startpoint:" in line:
            in_block = True
            stages = []
            prev_total = 0.0
            continue
        if not in_block:
            continue
        if "data arrival time" in line:
            break
        m = STAGE_RE.match(line)
        if not m:
            continue
        nums = [float(m.group(k)) for k in ("f1", "f2", "f3", "f4", "f5")]
        fanout, cap, slew, delay, total = nums
        stages.append(
            {
                "pin": m.group("pin"),
                "cell": m.group("cell"),
                "fanout": fanout,
                "cap_pf": cap,
                "slew_ns": slew,
                "delay_ns": delay,
                "arrival_ns": total,
                "incr_ns": round(total - prev_total, 6),
            }
        )
        prev_total = total
    out["path_stages"] = stages
    out["path_depth_cells"] = sum(1 for s in stages if s.get("cell"))
    return out


def parse_profile_sim(
    case: Path,
    profile: str,
    expected_completions: int = DEFAULT_VECTORS_COUNT,
    expected_interval_ps: int = DEFAULT_INTERVAL_PS,
) -> dict[str, Any]:
    """Parse gate-level simulation log for a given profile."""
    log_path = case / f"sim_{profile}.log"
    if not log_path.is_file():
        return {"profile": profile, "status": "MISSING"}

    text = log_path.read_text(encoding="utf-8", errors="replace")
    out: dict[str, Any] = {"profile": profile, "status": "OK"}

    for key, pat in (
        ("start_ps", r"MEASUREMENT_END[^\n]*?\bstart_ps=(\d+)"),
        ("end_ps", r"MEASUREMENT_END[^\n]*?\bend_ps=(\d+)"),
        ("completed", r"MEASUREMENT_END[^\n]*?\bcompleted=(\d+)"),
        ("interval_ps", r"MEASUREMENT_END[^\n]*?\binterval_ps=(\d+)"),
        ("mismatches", r"FAMILYRTL_ECC_V3_COMPLETE[^\n]*?\bmismatches=(\d+)"),
    ):
        m = re.search(pat, text)
        if m:
            out[key] = int(m.group(1))

    out["complete_marker"] = "FAMILYRTL_ECC_V3_COMPLETE" in text
    out["mismatch_lines"] = len(re.findall(r"ECC_V3_MISMATCH", text))

    start = out.get("start_ps")
    end = out.get("end_ps")
    completed = out.get("completed")
    interval = out.get("interval_ps") or expected_interval_ps

    if start is not None and end is not None and end > start:
        actual_window_ps = end - start
        out["actual_window_ps"] = actual_window_ps
        out["window_consistent"] = bool(
            completed is not None
            and actual_window_ps == completed * interval
        )
    else:
        out["actual_window_ps"] = None
        out["window_consistent"] = False

    out["vectors_matched"] = bool(
        completed == expected_completions
        and out.get("mismatches", -1) == 0
        and out["mismatch_lines"] == 0
    )
    return out


def parse_profile_power(case: Path, profile: str) -> dict[str, Any]:
    """Parse OpenSTA power log for a given profile."""
    log_path = case / f"power_{profile}.log"
    opensta_log_path = case / f"opensta_{profile}.log"
    
    if not log_path.is_file():
        return {"profile": profile, "status": "MISSING"}

    text = log_path.read_text(encoding="utf-8", errors="replace")
    
    complete_marker = False
    if opensta_log_path.is_file():
        opensta_text = opensta_log_path.read_text(encoding="utf-8", errors="replace")
        complete_marker = "FAMILYRTL_ROUTED_3P_POWER_COMPLETE" in opensta_text

    out: dict[str, Any] = {
        "profile": profile,
        "status": "OK",
        "complete_marker": complete_marker,
    }

    # Matches: Total <internal> <switching> <leakage> <total>
    m = re.search(
        r"(?mi)^Total\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)",
        text,
    )
    if m:
        out["internal_w"] = float(m.group(1))
        out["switching_w"] = float(m.group(2))
        out["leakage_w"] = float(m.group(3))
        out["total_w"] = float(m.group(4))
    else:
        out["status"] = "INCOMPLETE"
    return out


def parse_profile_annotation(case: Path, profile: str) -> dict[str, Any]:
    """Parse OpenSTA activity annotation log."""
    log_path = case / f"annotation_{profile}.log"
    if not log_path.is_file():
        return {"profile": profile, "status": "MISSING"}

    text = log_path.read_text(encoding="utf-8", errors="replace")
    out: dict[str, Any] = {"profile": profile, "status": "OK"}
    annotated_m = re.search(r"(?mi)^vcd\s+(\d+)", text)
    if annotated_m:
        out["annotated_pins"] = int(annotated_m.group(1))
    unannotated_m = re.search(r"(?mi)^unannotated\s+(\d+)", text)
    if unannotated_m:
        out["unannotated_pins"] = int(unannotated_m.group(1))
    return out


def parse_routed_area(case: Path) -> dict[str, Any]:
    """Parse routed area from openroad.log or route metadata."""
    openroad_log = case / "openroad.log"
    area: float | None = None
    drc_violations: int | None = None
    drc_available = False

    if openroad_log.is_file():
        text = openroad_log.read_text(encoding="utf-8", errors="replace")
        areas = re.findall(r"^Design area\s+([\d.eE+-]+)\s+um\^2", text, re.MULTILINE)
        if areas:
            area = float(areas[-1])
        violations = re.findall(r"Number of violations\s*=\s*(\d+)", text)
        if violations:
            drc_violations = int(violations[-1])
            drc_available = True

    route_meta_path = case / "route_meta.json"
    if area is None and route_meta_path.is_file():
        try:
            meta = json.loads(route_meta_path.read_text(encoding="utf-8"))
            if "routed_area_um2" in meta:
                area = float(meta["routed_area_um2"])
        except (OSError, json.JSONDecodeError, ValueError):
            pass

    return {
        "routed_area_um2": area,
        "drc_available": drc_available,
        "drc_violations": drc_violations,
    }


def summarize_routed_three_profile(
    case: Path,
    denominator: dict[str, float] | None = None,
    delay_ceiling: float = DEFAULT_FEASIBILITY_DELAY_NS,
    override_routed_area_um2: float | None = None,
) -> dict[str, Any]:
    """Parse and summarize full routed three-profile measurement results.

    Validates:
      * STA log: arrival time, markers, max over external outputs
      * Simulation logs: window consistency, 1024 completions, 0 mismatches
      * Power logs: total power W, zero unannotated pins
      * Netlist and SPEF hashes
      * VCD hashes preserved before optional deletion
      * Calculation: Energy = W * actual_window_ps / completions
      * Feasibility: delay <= delay_ceiling (2.40 ns) and 0 mismatches
      * Geometric mean J score if denominator provided
    """
    case = case.resolve()
    sta = parse_sta_report(case / "postroute_sta.log")
    area_info = parse_routed_area(case)

    # Stage status
    stage_path = case / "stage_status.json"
    stages = None
    if stage_path.is_file():
        try:
            stages = json.loads(stage_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            stages = None

    stages_ok = bool(
        isinstance(stages, dict)
        and "postroute_sta" in stages and stages["postroute_sta"] == 0
        and "iverilog_compile" in stages and stages["iverilog_compile"] == 0
        and "simulation" in stages and stages["simulation"] == 0
        and "power" in stages and stages["power"] == 0
    )

    # Netlist and SPEF verification: routed netlist must exist and NOT be mapped.v
    routed_netlist_path = case / "routed.v"
    spef_path = case / "routed.spef"

    netlist_sha256 = sha256_file(routed_netlist_path) if routed_netlist_path.is_file() else None
    spef_sha256 = sha256_file(spef_path) if spef_path.is_file() else None

    # Profiles parsing
    per_profile: dict[str, Any] = {}
    energies_pj: dict[str, float] = {}
    vcd_hashes: dict[str, str | None] = {}
    profiles_valid = True

    for p in PROFILES:
        sim = parse_profile_sim(case, p)
        pwr = parse_profile_power(case, p)
        ann = parse_profile_annotation(case, p)

        sim_exit_file = case / f"sim_{p}.exit"
        power_exit_file = case / f"power_{p}.exit"
        
        sim_exit_ok = sim_exit_file.is_file() and sim_exit_file.read_text(encoding="utf-8").strip() == "0"
        power_exit_ok = power_exit_file.is_file() and power_exit_file.read_text(encoding="utf-8").strip() == "0"

        # Look for preserved VCD sha256 file
        vcd_sha_file = case / f"vcd_{p}.sha256"
        vcd_file = case / f"activity_{p}.vcd"
        vcd_sha: str | None = None
        if vcd_sha_file.is_file():
            vcd_sha = vcd_sha_file.read_text(encoding="utf-8").strip()
        elif vcd_file.is_file():
            vcd_sha = sha256_file(vcd_file)
        vcd_hashes[p] = vcd_sha

        total_w = pwr.get("total_w")
        completed = sim.get("completed")
        actual_window_ps = sim.get("actual_window_ps")

        energy_pj_per_vector = None
        energy_j = None
        if (
            total_w is not None
            and completed is not None
            and completed > 0
            and actual_window_ps is not None
            and actual_window_ps > 0
        ):
            # Formula: W * actual_window_ps / completions
            # Units: W * (actual_window_ps * 1e-12 s) * 1e12 pJ/J / completed
            #      = W * actual_window_ps / completed (in pJ/vector)
            energy_pj_per_vector = total_w * actual_window_ps / completed
            energy_j = total_w * actual_window_ps * 1e-12

        profile_ok = bool(
            sim_exit_ok
            and power_exit_ok
            and sim.get("complete_marker")
            and sim.get("vectors_matched")
            and sim.get("window_consistent")
            and pwr.get("status") == "OK"
            and pwr.get("complete_marker")
            and ann.get("unannotated_pins") == 0
            and _finite_positive(energy_pj_per_vector)
            and vcd_sha is not None
        )
        if not profile_ok:
            profiles_valid = False

        if energy_pj_per_vector is not None:
            energies_pj[p] = energy_pj_per_vector

        per_profile[p] = {
            "valid": profile_ok,
            "total_w": total_w,
            "internal_w": pwr.get("internal_w"),
            "switching_w": pwr.get("switching_w"),
            "leakage_w": pwr.get("leakage_w"),
            "energy_pj_per_vector": energy_pj_per_vector,
            "energy_j": energy_j,
            "start_ps": sim.get("start_ps"),
            "end_ps": sim.get("end_ps"),
            "actual_window_ps": actual_window_ps,
            "completed": completed,
            "oracle_mismatches": sim.get("mismatches", 0),
            "annotated_pins": ann.get("annotated_pins"),
            "unannotated_pins": ann.get("unannotated_pins"),
            "vcd_sha256": vcd_sha,
        }

    # Delay is max over external outputs
    routed_delay_ns = sta.get("max_arrival_ns") or sta.get("arrival_ns")
    delay_ok = _finite_positive(routed_delay_ns) and sta.get("complete_marker", False)
    area_um2 = override_routed_area_um2 if override_routed_area_um2 is not None else area_info.get("routed_area_um2")
    netlists_ok = bool(netlist_sha256 and spef_sha256)

    measurement_valid = bool(
        stages_ok
        and profiles_valid
        and delay_ok
        and netlists_ok
        and len(energies_pj) == len(PROFILES)
    )

    # Feasibility: delay <= delay_ceiling (2.40 ns) and 0 mismatches
    total_mismatches = sum(per_profile[p].get("oracle_mismatches", 0) for p in PROFILES)
    feasible = bool(
        measurement_valid
        and routed_delay_ns is not None
        and routed_delay_ns <= delay_ceiling
        and total_mismatches == 0
    )

    # J score if denominator is provided
    j_data: dict[str, Any] = {"j_score": None, "energy_ratios": None, "denominator_energies": None}
    if denominator and len(energies_pj) == len(PROFILES):
        try:
            j_data = compute_j_metric(energies_pj, denominator)
        except (KeyError, ValueError):
            pass

    return {
        "measurement_valid": measurement_valid,
        "feasible": feasible,
        "delay_ceiling_ns": delay_ceiling,
        "routed_delay_ns": routed_delay_ns,
        "routed_area_um2": area_um2,
        "raw_energies_pj": energies_pj,
        "per_profile": per_profile,
        "j_score": j_data.get("j_score"),
        "energy_ratios": j_data.get("energy_ratios"),
        "denominator_energies": j_data.get("denominator_energies"),
        "hashes": {
            "routed_netlist": netlist_sha256,
            "spef": spef_sha256,
            "vcd": vcd_hashes,
        },
        "critical_path": {
            "startpoint": sta.get("startpoint"),
            "endpoint": sta.get("endpoint"),
            "arrival_ns": routed_delay_ns,
            "slack_ns": sta.get("slack_ns"),
            "path_depth_cells": sta.get("path_depth_cells"),
        },
        "stage_status": stages,
        "drc": {
            "available": area_info.get("drc_available"),
            "violations": area_info.get("drc_violations"),
        },
        "claim_scope": (
            "routed three-profile measurement context (stress_encoded, valid_uniform, "
            "valid_low_toggle; 1024 vectors, 10000 ps interval, 0.05 ns slew, 0.005 pF load, "
            f"fixed corner, matched SPEF, feasibility ceiling D <= {delay_ceiling:.2f} ns)"
        ),
    }


def prepare_routed_three_profile_case(
    repo_root: Path,
    routed_netlist: Path,
    spef: Path,
    case_dir: Path,
    width: int = 64,
    seed: int = 2026092101,
    count: int = DEFAULT_VECTORS_COUNT,
    interval_ps: int = DEFAULT_INTERVAL_PS,
    input_slew_ns: float = DEFAULT_INPUT_SLEW_NS,
    output_load_pf: float = DEFAULT_OUTPUT_LOAD_PF,
    delete_vcd: bool = True,
    python_bin: str = "python3",
    power_diagnostic: bool = False,
) -> dict[str, Any]:
    """Prepare case directory, stimulus, and Tcl/sh scripts for routed 3-profile measurement."""
    repo_root = repo_root.resolve()
    routed_netlist = routed_netlist.resolve()
    spef = spef.resolve()
    case_dir = case_dir.resolve()

    if not routed_netlist.is_file():
        raise FileNotFoundError(f"routed netlist not found: {routed_netlist}")
    if routed_netlist.name == "mapped.v":
        raise ValueError("routed netlist must not be named mapped.v (renaming routed netlist to mapped.v is forbidden)")
    if not spef.is_file():
        raise FileNotFoundError(f"spef not found: {spef}")
    if width not in GEOMETRY:
        raise ValueError(f"unsupported width {width}; expected one of {sorted(GEOMETRY)}")

    case_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(case_dir, 0o777)

    # Copy routed netlist and spef explicitly
    dest_netlist = case_dir / "routed.v"
    dest_spef = case_dir / "routed.spef"
    if dest_netlist != routed_netlist:
        shutil.copy2(routed_netlist, dest_netlist)
    if dest_spef != spef:
        shutil.copy2(spef, dest_spef)

    # Generate workloads for all three profiles
    workload_generator = repo_root / "tools" / "ecc_v3_workloads.py"
    if not workload_generator.is_file():
        raise FileNotFoundError(f"workload generator not found: {workload_generator}")

    workloads: dict[str, Any] = {}
    for p in PROFILES:
        out_json = case_dir / f"workload_{p}.json"
        out_hex = case_dir / f"workload_{p}.hex"
        proc = subprocess.run(
            [
                python_bin,
                str(workload_generator),
                "--width",
                str(width),
                "--profile",
                p,
                "--seed",
                str(seed),
                "--count",
                str(count),
                "--interval-ps",
                str(interval_ps),
                "--out",
                str(out_json),
                "--vectors-out",
                str(out_hex),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"workload generation failed for {p}: {proc.stderr}")
        workloads[p] = json.loads(proc.stdout)

    # Write STA Tcl
    (case_dir / "routed_3p_sta.tcl").write_text(
        ROUTED_3P_STA_TCL.format(
            liberty=DEFAULT_LIBERTY_CORNER,
            input_slew_ns=input_slew_ns,
            output_load_pf=output_load_pf,
        ),
        encoding="utf-8",
    )

    # Keep the default scoring Tcl byte-for-byte identical.
    power_tcl = ROUTED_3P_POWER_TCL.format(
        liberty=DEFAULT_LIBERTY_CORNER,
        input_slew_ns=input_slew_ns,
        output_load_pf=output_load_pf,
    )
    if power_diagnostic:
        if not POWER_DIAGNOSTIC_SOURCE.is_file():
            raise FileNotFoundError(f"power diagnostic sidecar is missing: {POWER_DIAGNOSTIC_SOURCE}")
        shutil.copy2(POWER_DIAGNOSTIC_SOURCE, case_dir / "instance_power_diagnostic.tcl")
        anchor = "report_power -digits 9 > /artifacts/current_power.log\n"
        if power_tcl.count(anchor) != 1:
            raise ValueError("power diagnostic insertion point changed")
        hook = (
            "if {[catch {source /artifacts/instance_power_diagnostic.tcl} diagnostic_error]} {\n"
            "  set diagnostic_file [open /artifacts/current_instance_power_error.txt w]\n"
            "  puts $diagnostic_file $diagnostic_error\n"
            "  close $diagnostic_file\n"
            "}\n"
        )
        power_tcl = power_tcl.replace(anchor, anchor + hook, 1)
    (case_dir / "routed_3p_power.tcl").write_text(power_tcl, encoding="utf-8")

    # Write Runner Shell Script
    pw, cw = GEOMETRY[width]
    run_script = RUN_SCRIPT_TEMPLATE.format(
        width=width,
        parity_width=pw,
        codeword_width=cw,
        profiles=" ".join(PROFILES),
        count=count,
        interval_ps=interval_ps,
        delete_vcd=str(delete_vcd),
    )
    if power_diagnostic:
        anchor = "      rm -f /artifacts/current_activity.vcd\n"
        if run_script.count(anchor) != 1:
            raise ValueError("power diagnostic profile output insertion point changed")
        moves = (
            "      mv /artifacts/current_instance_power.json /artifacts/instance_power_${p}.json 2>/dev/null || true\n"
            "      mv /artifacts/current_instance_pin_nets.tsv /artifacts/instance_pin_nets_${p}.tsv 2>/dev/null || true\n"
            "      mv /artifacts/current_instance_power_error.txt /artifacts/instance_power_${p}.error.txt 2>/dev/null || true\n"
        )
        run_script = run_script.replace(anchor, moves + anchor, 1)
    (case_dir / "run_measurement.sh").write_text(run_script, encoding="utf-8")
    os.chmod(case_dir / "run_measurement.sh", 0o755)

    meta = {
        "width": width,
        "seed": seed,
        "count": count,
        "interval_ps": interval_ps,
        "input_slew_ns": input_slew_ns,
        "output_load_pf": output_load_pf,
        "netlist_sha256": sha256_file(dest_netlist),
        "spef_sha256": sha256_file(dest_spef),
        "workloads": workloads,
        "vcd_retained": not delete_vcd,
    }
    if power_diagnostic:
        meta["optional_power_diagnostic"] = {
            "version": POWER_DIAGNOSTIC_VERSION,
            "enabled": True,
            "sidecar_sha256": sha256_file(case_dir / "instance_power_diagnostic.tcl"),
            "measurement_runner_sha256": sha256_file(Path(__file__)),
            "power_tcl_sha256": sha256_file(case_dir / "routed_3p_power.tcl"),
            "run_script_sha256": sha256_file(case_dir / "run_measurement.sh"),
            "scope": "supplemental instance power only; no scoring or glitch attribution",
        }
    (case_dir / "measurement_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo-root", required=True)
    ap.add_argument("--routed-netlist", required=True, help="Path to routed netlist (never mapped.v)")
    ap.add_argument("--spef", required=True, help="Path to matching routed SPEF")
    ap.add_argument("--artifact-dir", required=True, help="Directory for measurement artifacts")
    ap.add_argument("--width", type=int, default=64)
    ap.add_argument("--seed", type=int, default=2026092101)
    ap.add_argument("--count", type=int, default=DEFAULT_VECTORS_COUNT)
    ap.add_argument("--interval-ps", type=int, default=DEFAULT_INTERVAL_PS)
    ap.add_argument("--slew", type=float, default=DEFAULT_INPUT_SLEW_NS)
    ap.add_argument("--load", type=float, default=DEFAULT_OUTPUT_LOAD_PF)
    ap.add_argument("--delay-ceiling", type=float, default=DEFAULT_FEASIBILITY_DELAY_NS)
    ap.add_argument("--denominator-json", default=None, help="JSON file with b271/F0 baseline energies")
    ap.add_argument("--dry-run", action="store_true", help="Prepare files without running docker")
    ap.add_argument("--power-diagnostic", action="store_true", help="Add optional per-instance power sidecar to existing VCD/SPEF load")
    ap.add_argument("--keep-vcd", action="store_true", help="Retain generated per-profile VCD files after measurement")
    ap.add_argument("--execute-only", action="store_true", help="Skip preparation and use existing case directory")
    ap.add_argument("--routed-area-um2", type=float, default=None, help="Explicit routed area to preserve")
    ap.add_argument("--python", default="python3")
    ap.add_argument("--cpus", default="2")
    ap.add_argument("--memory", default="12g")
    ap.add_argument("--image", default=DEFAULT_IMAGE)
    args = ap.parse_args()

    repo = Path(args.repo_root).resolve()
    netlist = Path(args.routed_netlist).resolve()
    spef = Path(args.spef).resolve()
    case = Path(args.artifact_dir).resolve()

    denominator = None
    if args.denominator_json:
        denom_path = Path(args.denominator_json).resolve()
        if denom_path.is_file():
            denominator = json.loads(denom_path.read_text(encoding="utf-8"))

    if not args.execute_only:
        meta = prepare_routed_three_profile_case(
            repo_root=repo,
            routed_netlist=netlist,
            spef=spef,
            case_dir=case,
            width=args.width,
            seed=args.seed,
            count=args.count,
            interval_ps=args.interval_ps,
            input_slew_ns=args.slew,
            output_load_pf=args.load,
            delete_vcd=not args.keep_vcd,
            python_bin=args.python,
            power_diagnostic=args.power_diagnostic,
        )
    else:
        # Load existing meta to pass to dry run if needed
        meta_path = case / "measurement_meta.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.is_file() else {}
        diagnostic = meta.get("optional_power_diagnostic", {})
        if args.power_diagnostic and not diagnostic.get("enabled"):
            raise ValueError("execute-only case was not prepared with power diagnostic")
        if diagnostic.get("enabled"):
            for name, expected in (
                ("instance_power_diagnostic.tcl", diagnostic["sidecar_sha256"]),
                ("routed_3p_power.tcl", diagnostic["power_tcl_sha256"]),
                ("run_measurement.sh", diagnostic["run_script_sha256"]),
            ):
                path = case / name
                if not path.is_file() or sha256_file(path) != expected:
                    raise ValueError(f"execute-only diagnostic input hash mismatch: {name}")

    if args.dry_run:
        print(json.dumps({"status": "DRY_RUN_PREPARED", "artifact_dir": str(case), "meta": meta}, indent=2))
        return 0

    cmd = [
        "docker", "run", "--rm",
        "--cpus", args.cpus, "--memory", args.memory,
        "--pids-limit", "512", "--network", "none",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "--mount", f"type=bind,src={repo},dst=/workspace,readonly",
        "--mount", f"type=bind,src={case},dst=/artifacts",
        "--workdir", "/workspace", args.image, "--skip",
        "bash", "/artifacts/run_measurement.sh",
    ]
    t0 = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    (case / "docker_run.log").write_text(proc.stdout + proc.stderr, encoding="utf-8")

    summary = summarize_routed_three_profile(
        case=case,
        denominator=denominator,
        delay_ceiling=args.delay_ceiling,
        override_routed_area_um2=args.routed_area_um2,
    )
    summary["wall_s"] = round(time.time() - t0, 2)
    if meta.get("optional_power_diagnostic", {}).get("enabled"):
        summary["optional_power_diagnostic"] = {
            **meta["optional_power_diagnostic"],
            "profiles": {
                profile: {
                    "instance_power_sha256": (
                        sha256_file(case / f"instance_power_{profile}.json")
                        if (case / f"instance_power_{profile}.json").is_file() else None
                    ),
                    "pin_net_mapping_sha256": (
                        sha256_file(case / f"instance_pin_nets_{profile}.tsv")
                        if (case / f"instance_pin_nets_{profile}.tsv").is_file() else None
                    ),
                    "error_sha256": (
                        sha256_file(case / f"instance_power_{profile}.error.txt")
                        if (case / f"instance_power_{profile}.error.txt").is_file() else None
                    ),
                }
                for profile in PROFILES
            },
        }
    (case / "routed_3p_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if summary.get("measurement_valid") else 1


if __name__ == "__main__":
    raise SystemExit(main())
