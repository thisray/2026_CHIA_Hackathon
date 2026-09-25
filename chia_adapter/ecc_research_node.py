"""Record CHIA worker identity for ECC replay nodes."""

from __future__ import annotations

import os
import socket
import sys
from typing import Any


def _id_text(value: Any) -> str | None:
    if value is None:
        return None
    try:
        return value.hex()
    except Exception:
        return str(value)


def _worker_identity() -> dict[str, Any]:
    identity: dict[str, Any] = {
        "hostname": socket.gethostname(),
        "pid": os.getpid(),
        "executable": sys.executable,
        "in_ray_worker": False,
    }
    try:
        import ray

        context = ray.get_runtime_context()
        identity.update({
            "chia_task_id": _id_text(context.get_task_id()),
            "chia_node_id": _id_text(context.get_node_id()),
            "chia_worker_id": _id_text(context.get_worker_id()),
            "chia_job_id": _id_text(context.get_job_id()),
            "chia_node_ip": ray.util.get_node_ip_address(),
            "in_ray_worker": context.get_task_id() is not None,
        })
    except Exception as exc:
        identity["identity_error"] = repr(exc)
    return identity
