"""Check frozen evidence and prepare or execute bounded recorded CHIA replays."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = {
    "v02": {
        "receipt": "review/chia_V_w32_mixed/20260924/v02-receipt.json",
        "decision": "review/chia_V_w32_mixed/20260924/model-02.json",
        "module": "research.ecc_perf_bench.w32_mixed_phase_chia",
        "paper_label": "Final mixed-arity assignment",
        "historical_id": "V2",
    },
    "s02": {
        "receipt": "review/chia_S_folded_xor3/20260924/s02-receipt.json",
        "decision": "review/chia_S_folded_xor3/20260924/native-run.json",
        "module": "research.ecc_perf_bench.phase_replay_chia",
        "paper_label": "Final three-input refinement",
        "historical_id": "S2",
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def source_head() -> str:
    top = Path(subprocess.check_output(
        ["git", "-C", str(ROOT), "rev-parse", "--show-toplevel"], text=True
    ).strip()).resolve()
    if top != ROOT:
        raise ValueError("runtime source root must be a Git checkout for HEAD binding")
    return subprocess.check_output(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
    ).strip()


def evidence_check(data_root: Path | None = None) -> dict:
    rows = {}
    for example, spec in EXAMPLES.items():
        receipt = read_json(ROOT / spec["receipt"])
        measurement = receipt.get("measurement", {})
        raw = measurement.get("raw_energies_pj", receipt.get("raw_energies_pj"))
        denominator = measurement.get("denominator_energies")
        if not isinstance(raw, dict) or not isinstance(denominator, dict):
            raise ValueError(f"{example}: missing energy evidence")
        profiles = ("stress_encoded", "valid_uniform", "valid_low_toggle")
        if any(not isinstance(raw.get(key), (int, float)) or raw[key] <= 0
               or not isinstance(denominator.get(key), (int, float)) or denominator[key] <= 0
               for key in profiles):
            raise ValueError(f"{example}: invalid energy context")
        score = math.exp(sum(math.log(raw[key] / denominator[key])
                             for key in profiles) / len(profiles))
        claimed = receipt.get("j_score")
        if not isinstance(claimed, (int, float)) or not math.isclose(score, claimed, rel_tol=1e-9):
            raise ValueError(f"{example}: J mismatch")
        delay = receipt.get("routed_delay_ns")
        ceiling = measurement.get("delay_ceiling_ns")
        if (not isinstance(delay, (int, float)) or ceiling != 2.4
            or receipt.get("feasible") != (delay <= ceiling)
            or receipt.get("status") != "OK"
            or receipt.get("functional_valid") is not True
            or receipt.get("route_valid") is not True
            or receipt.get("measurement_valid") is not True):
            raise ValueError(f"{example}: feasibility or evidence status mismatch")
        hashes = receipt.get("hashes", {})
        measured_hashes = measurement.get("hashes", {})
        if (hashes.get("eco_routed_netlist") != measured_hashes.get("routed_netlist")
            or hashes.get("eco_routed_spef") != measured_hashes.get("spef")):
            raise ValueError(f"{example}: measured candidate identity mismatch")
        rows[example] = {"e_norm": score, "j_score": score,
                         "paper_label": spec["paper_label"],
                         "historical_id": spec["historical_id"],
                         "delay_ns": delay,
                         "area_um2": receipt.get("routed_area_um2"),
                         "feasible": True, "receipt_sha256": sha256(ROOT / spec["receipt"]),
                         "historical_source_commit": receipt["source_commit"],
                         "netlist_sha256": hashes["eco_routed_netlist"],
                         "spef_sha256": hashes["eco_routed_spef"]}
    result = {"status": "PASS", "scope": "offline_saved_evidence_only", "examples": rows}
    if data_root is None:
        return result
    data_root = data_root.resolve()
    manifest, indexed = load_data(data_root)
    path = indexed.get("views/results.json")
    if path is None:
        raise ValueError("DATA manifest has no views/results.json")
    table = read_json(path)
    denominator_by_width = table.get("denominators_pj_by_width")
    entries = table.get("rows")
    if not isinstance(denominator_by_width, dict) or not isinstance(entries, list) or len(entries) != 21:
        raise ValueError("DATA result table must contain 21 rows and denominators")
    profiles = ("stress_encoded", "valid_uniform", "valid_low_toggle")
    checked = []
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("width") not in (32, 64):
            raise ValueError("DATA result row width invalid")
        denominator = denominator_by_width.get(str(entry["width"]))
        energies = entry.get("energy_pj")
        if (not isinstance(denominator, dict) or not isinstance(energies, dict)
            or any(not isinstance(energies.get(key), (float, int)) or energies[key] <= 0
                   or not isinstance(denominator.get(key), (float, int)) or denominator[key] <= 0
                   for key in profiles)):
            raise ValueError(f"DATA result row energy invalid: {entry.get('id')}")
        score = math.exp(sum(math.log(energies[key] / denominator[key]) for key in profiles) / 3)
        if (not math.isclose(score, entry.get("j", float("nan")), rel_tol=1e-9)
            or entry.get("feasible") != (entry.get("delay_ns", float("inf")) <= table.get("delay_ceiling_ns"))
            or not isinstance(entry.get("netlist_sha256"), str)
            or not isinstance(entry.get("spef_sha256"), str)):
            raise ValueError(f"DATA result row metric or identity mismatch: {entry.get('id')}")
        checked.append(entry["id"])
    result["scope"] = "offline_saved_evidence_plus_21_selected_rows"
    result["data_manifest_sha256"] = sha256(data_root / "manifest.json")
    result["data_research_base_revision"] = manifest["research_base_revision"]
    result["selected_row_ids"] = checked
    return result


def safe_asset_path(data_root: Path, value: str) -> Path:
    if not isinstance(value, str):
        raise ValueError("replay data path must be a string")
    relative = PurePosixPath(value)
    if (not value or relative.is_absolute() or ".." in relative.parts
        or relative.as_posix() != value):
        raise ValueError(f"unsafe replay data path: {value}")
    return data_root.joinpath(*relative.parts)


def load_data(data_root: Path) -> tuple[dict, dict[str, Path]]:
    manifest = read_json(data_root / "manifest.json")
    if (manifest.get("schema") != "chia_minimal_replay_data_v1"
        or manifest.get("schema_version", 1) != 1
        or not isinstance(manifest.get("research_base_revision"), str)
        or not isinstance(manifest.get("examples"), dict)
        or not {"v02", "s02"}.issubset(manifest["examples"])
        or not isinstance(manifest.get("files"), list)):
        raise ValueError("replay data manifest version 1 or examples are incomplete")
    indexed = {}
    for row in manifest["files"]:
        required = {"exported_path", "exported_sha256", "original_sha256",
                    "upstream_path", "upstream_root", "source_revision", "transform"}
        if not isinstance(row, dict) or not required.issubset(row):
            raise ValueError("replay data file row is incomplete")
        name = row["exported_path"]
        path = safe_asset_path(data_root, name)
        if name in indexed:
            raise ValueError(f"duplicate replay data path: {name}")
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(data_root):
            raise ValueError(f"replay data file missing or unsafe: {name}")
        if sha256(path) != row["exported_sha256"]:
            raise ValueError(f"replay data file hash mismatch: {name}")
        if row["transform"] == "byte_copy" and row["original_sha256"] != row["exported_sha256"]:
            raise ValueError(f"replay data byte-copy provenance mismatch: {name}")
        indexed[name] = path
    for example in EXAMPLES:
        entry = manifest["examples"][example]
        if not isinstance(entry, dict) or not {"parent_relpath", "decision_relpath", "case_relpath"}.issubset(entry):
            raise ValueError(f"{example}: example paths missing")
        for key in ("parent_relpath", "decision_relpath", "case_relpath"):
            safe_asset_path(data_root, entry[key])
        if entry["decision_relpath"] not in indexed:
            raise ValueError(f"{example}: decision not listed in manifest")
        parent_prefix = entry["parent_relpath"] + "/"
        if not any(name.startswith(parent_prefix) for name in indexed):
            raise ValueError(f"{example}: parent files not listed in manifest")
    return manifest, indexed


def ensure_separate(data_root: Path, output_root: Path) -> None:
    if (output_root.exists() or output_root == data_root
        or output_root.is_relative_to(data_root)
        or data_root.is_relative_to(output_root)
        or output_root.is_relative_to(ROOT)):
        raise ValueError("output root must be new and distinct from data and source roots")


def request_for(example: str, parent: Path, decision: Path, artifact: Path) -> dict:
    receipt = read_json(ROOT / EXAMPLES[example]["receipt"])
    parsed = read_json(decision).get("parsed_object", {})
    if (parsed.get("decision") != "RUN" or parsed.get("parent_id") != receipt.get("parent_id")
        or parsed.get("action") != receipt.get("action")):
        raise ValueError(f"{example}: recorded decision differs from saved action")
    request = {
        "repo_root": str(ROOT), "python": sys.executable, "source_commit": source_head(),
        "parent_id": receipt["parent_id"], "parent_root": str(parent),
        "expected_parent_sha256": receipt["parent_graph_sha256"],
        "action": receipt["action"], "model_decision_path": str(decision),
        "artifact_dir": str(artifact), "goal_id": receipt["goal_id"],
        "keep_vcd": True,
    }
    if example == "v02":
        request["reference_measurement_id"] = receipt["reference_measurement_id"]
    return request


def replay(example: str, data_root: Path, output_root: Path, execute: bool) -> dict:
    data_root, output_root = data_root.resolve(), output_root.resolve()
    ensure_separate(data_root, output_root)
    if not (Path(sys.prefix) / "conda-meta").is_dir():
        raise ValueError("active Python must be from a conda environment")
    manifest, indexed = load_data(data_root)
    historical = read_json(ROOT / EXAMPLES[example]["receipt"])
    entry = manifest["examples"][example]
    parent_prefix = entry["parent_relpath"] + "/"
    assets = [(path, Path(name[len(parent_prefix):])) for name, path in indexed.items()
              if name.startswith(parent_prefix)]
    expected_count = manifest.get("cases", {}).get(example + "_parent", {}).get("file_count")
    if expected_count != len(assets):
        raise ValueError(f"{example}: parent file count differs from case manifest")
    output_root.mkdir(parents=True)
    parent = output_root / "inputs/parent"
    for source, relative in assets:
        target = parent / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    decision = output_root / "inputs/recorded_decision.json"
    decision.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(indexed[entry["decision_relpath"]], decision)
    request = request_for(example, parent, decision, output_root / "case")
    request_path = output_root / "request.json"
    write_json(request_path, request)
    report = {
        "example": example, "mode": "recorded_decision",
        "paper_label": EXAMPLES[example]["paper_label"],
        "historical_id": EXAMPLES[example]["historical_id"],
        "status": "NOT_RUN", "source_commit": request["source_commit"],
        "historical_source_commit": historical["source_commit"],
        "data_manifest_sha256": sha256(data_root / "manifest.json"),
        "data_source_revision": manifest["cases"][example]["source_revision"],
        "parent_file_count": len(assets), "request_path": str(request_path),
        "s01_lineage": {
            "original_s02_reused_verified_s01_eco": True,
            "s01_receipt_sha256": sha256(ROOT / "review/chia_S_folded_xor3/20260924/s01-receipt.json"),
            "s01_eco_manifest_sha256": historical.get("eco_reuse_origin_manifest_sha256"),
            "new_replay_reuses_s01_eco": False,
        } if example == "s02" else None,
    }
    try:
        if example == "v02":
            from research.ecc_perf_bench.w32_mixed_phase_execute import validate_request
        else:
            from research.ecc_perf_bench.phase_replay_execute import validate_request
        validate_request(request)
        report["preflight"] = "PASS"
    except Exception as exc:
        report["status"] = "BLOCKED"
        report["execution"] = "NOT_RUN"
        report["preflight"] = "BLOCKED"
        report["blocker"] = f"{type(exc).__name__}: {exc}"
        write_json(output_root / "runtime_report.json", report)
        return report
    if not execute:
        report["blocker"] = "CHIA/EDA replay requires explicit --execute"
        write_json(output_root / "runtime_report.json", report)
        return report
    return dispatch_chia(example, request_path, output_root, report)


def dispatch_chia(example: str, request_path: Path, output_root: Path, report: dict) -> dict:
    result_path = output_root / "result.json"
    command = [sys.executable, "-m", EXAMPLES[example]["module"],
               "--request", str(request_path), "--output", str(result_path)]
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT)
    completed = subprocess.run(command, cwd=ROOT, env=environment, check=False)
    report["command"] = command
    report["exit_code"] = completed.returncode
    if result_path.is_file():
        result = read_json(result_path)
        report["result_path"] = str(result_path)
        report["result_sha256"] = sha256(result_path)
        report["reported_status"] = result.get("status")
        report["status"] = result.get("status", "ERROR_OR_UNKNOWN")
        report["route_valid"] = result.get("route_valid")
        report["functional_valid"] = result.get("functional_valid")
        report["measurement_valid"] = result.get("measurement_valid")
        if (report["status"] == "OK" and
            not all(report[key] is True for key in
                    ("route_valid", "functional_valid", "measurement_valid"))):
            report["status"] = "ERROR_OR_UNKNOWN"
            report["blocker"] = "CHIA result has incomplete proof, route, or measurement validity"
    else:
        report["status"] = "ERROR_OR_UNKNOWN"
        report["blocker"] = "CHIA dispatcher produced no result file"
    if completed.returncode != 0:
        report["status"] = "ERROR_OR_UNKNOWN"
        report["blocker"] = f"CHIA dispatcher exited nonzero: {completed.returncode}"
    write_json(output_root / "runtime_report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    offline_parser = subparsers.add_parser("offline-check", help="recompute saved J and identity without EDA")
    offline_parser.add_argument("--data-root", type=Path, help="also verify DATA and 21 selected rows")
    replay_parser = subparsers.add_parser("replay", help="prepare or execute a recorded example")
    replay_parser.add_argument("--example", choices=sorted(EXAMPLES), required=True)
    replay_parser.add_argument("--data-root", type=Path, required=True)
    replay_parser.add_argument("--output-root", type=Path, required=True)
    replay_parser.add_argument("--execute", action="store_true", help="run local CHIA and EDA")
    gate_parser = subparsers.add_parser("model-gate", help="opt-in fixed-plan RUN/STOP gate")
    gate_parser.add_argument("--example", choices=sorted(EXAMPLES), required=True)
    gate_parser.add_argument("--data-root", type=Path, required=True)
    gate_parser.add_argument("--output-root", type=Path, required=True)
    gate_parser.add_argument("--execute", action="store_true", required=True)
    gate_parser.add_argument("--endpoint")
    gate_parser.add_argument("--model")
    gate_parser.add_argument("--auth-env")
    gate_parser.add_argument("--enable-network-model", action="store_true")
    gate_parser.add_argument("--mock-responses", type=Path)
    gate_parser.add_argument("--assess-feedback", action="store_true")
    gate_parser.add_argument("--timeout-s", type=float, required=True)
    gate_parser.add_argument("--max-output-tokens", type=int, required=True)
    args = parser.parse_args()
    try:
        if args.command == "offline-check":
            result = evidence_check(args.data_root)
        elif args.command == "replay":
            result = replay(args.example, args.data_root, args.output_root, args.execute)
        else:
            from public_release.runtime.model_gate import model_gate
            result = model_gate(args)
    except Exception as exc:
        result = {"status": "BLOCKED", "error": f"{type(exc).__name__}: {exc}"}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] in {"PASS", "NOT_RUN", "OK", "STOP"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
