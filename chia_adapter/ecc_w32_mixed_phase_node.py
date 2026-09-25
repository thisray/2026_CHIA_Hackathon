"""CHIA Ray leaf for the exact-parent W32 mixed-arity phase candidate."""

from __future__ import annotations

from typing import Any

from chia.base.ChiaFunction import ChiaFunction
from chia_adapter.ecc_research_node import _worker_identity
from research.ecc_perf_bench.w32_mixed_phase_execute import execute, result_summary


@ChiaFunction(num_cpus=2, resources={"ecc_w32_mixed_phase": 1})
def evaluate_ecc_w32_mixed_phase(request: dict[str, Any]) -> dict[str, Any]:
    identity = _worker_identity()
    if not all((identity.get("in_ray_worker"), identity.get("chia_task_id"),
                identity.get("chia_worker_id"), identity.get("chia_node_id"),
                identity.get("chia_job_id"), identity.get("pid"))):
        return {"status": "NOT_IN_CHIA_RAY_WORKER", "functional_valid": False,
                "measurement_valid": False, "route_valid": False,
                "actual_chia_identity": identity, "error": "complete Ray identity required"}
    return result_summary(execute(request, identity), request)
