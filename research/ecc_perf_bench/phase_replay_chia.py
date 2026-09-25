"""Dispatch the exact six-star replay experiment through CHIA Ray."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

from research.ecc_perf_bench.phase_replay_execute import validate_request


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    request = json.loads(args.request.read_text(encoding="utf-8"))
    if not isinstance(request, dict):
        raise ValueError("request must be an object")
    artifact = Path(request["artifact_dir"]).resolve()
    output = args.output.resolve()
    if artifact == output or artifact in output.parents:
        raise ValueError("phase replay result path must be outside the artifact directory")
    intent_path = args.output.with_name(args.output.name + ".intent.json")
    if artifact.exists() or args.output.exists() or intent_path.exists():
        raise ValueError("unique phase replay artifact, result, and intent paths required")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    try:
        validated, manifest = validate_request(request)
        if request["action"] == {"kind": "STOP"}:
            result = {
                "status": "STOP", "stage": "native_decision", "functional_valid": None,
                "measurement_valid": None, "route_valid": False,
                "source_commit": request["source_commit"], "parent_id": request["parent_id"],
                "parent_root": request["parent_root"], "action": request["action"],
                "artifact_dir": str(artifact), "goal_id": request["goal_id"],
                "expected_parent_sha256": request["expected_parent_sha256"],
                "parent_validation": "PASS", "submission_counted": 0,
            }
            args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print(json.dumps({"status": "STOP", "route_valid": False,
                              "result_path": str(args.output)}, sort_keys=True))
            return 0
        intent = {
            "status": "DISPATCHING", "stage": "before_chia_leaf",
            "request_sha256": hashlib.sha256(args.request.read_bytes()).hexdigest(),
            "source_commit": request["source_commit"], "parent_id": request["parent_id"],
            "parent_root": request["parent_root"], "action": request["action"],
            "artifact_dir": str(artifact), "goal_id": request["goal_id"],
            "model_decision_path": request["model_decision_path"],
            "started_unix_s": time.time(),
        }
        intent_path.write_text(json.dumps(intent, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        import ray
        from chia.base.ChiaFunction import get
        from chia_adapter.ecc_phase_replay_node import evaluate_ecc_phase_replay

        ray.init(
            address="local", num_cpus=2, resources={"ecc_phase_replay": 1},
            include_dashboard=False,
            runtime_env={"env_vars": {"PYTHONPATH": str(Path(request["repo_root"]).resolve())}},
        )
        try:
            result = get(evaluate_ecc_phase_replay.chia_remote(request))
        finally:
            ray.shutdown()
    except Exception as exc:
        result = {
            "status": "ERROR_OR_UNKNOWN", "stage": "preflight_or_dispatch",
            "error": f"{type(exc).__name__}: {exc}",
            "functional_valid": False, "measurement_valid": False, "route_valid": False,
            "source_commit": request.get("source_commit"), "parent_id": request.get("parent_id"),
            "parent_root": request.get("parent_root"), "action": request.get("action"),
            "artifact_dir": str(artifact), "receipt_path": str(artifact / "receipt.json"),
            "artifact_manifest_path": str(artifact / "artifact_manifest.json"),
            "goal_id": request.get("goal_id"), "actual_chia_identity": None,
        }
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result.get("status"), "route_valid": result.get("route_valid"),
                      "result_path": str(args.output)}, sort_keys=True))
    return 0 if result.get("status") == "OK" and result.get("route_valid") else 1


if __name__ == "__main__":
    raise SystemExit(main())
