"""Exact 1 ps recovery target and identity for the bounded F1-v9 flow."""

from __future__ import annotations

import math
from typing import Any


FLOW = "F1-v9"
MIN_TARGET_PS = 2350
MAX_TARGET_PS = 2800
FINAL_DELAY_CEILING_NS = 2.40


def target_ps(value: Any, flow: str) -> int | None:
    """Validate a required v9 target and reject target overrides on older flows."""
    if flow != FLOW:
        if value is not None:
            raise ValueError("recovery_target_ns is only valid for F1-v9")
        return None
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError("F1-v9 requires finite recovery_target_ns")
    scaled = value * 1000
    quantized = round(scaled)
    if abs(scaled - quantized) > 1e-7:
        raise ValueError("recovery_target_ns must be quantized to 0.001 ns")
    if not MIN_TARGET_PS <= quantized <= MAX_TARGET_PS:
        raise ValueError("recovery_target_ns must be in 2.350..2.800 ns")
    return quantized


def target_ns(value: Any, flow: str) -> float | None:
    """Return a canonical three-decimal v9 target or no target for old flows."""
    picoseconds = target_ps(value, flow)
    return picoseconds / 1000 if picoseconds is not None else None


def calibrated_target_ns(gr_arrival_ns: float, final_delay_ns: float, alpha: float) -> float:
    """Evaluate the bounded per-parent G + alpha * (2.40 - D) rule."""
    if type(alpha) not in (int, float) or alpha not in (0.5, 1.0):
        raise ValueError("alpha must be 0.5 or 1.0")
    if any(type(value) not in (int, float) or not math.isfinite(value)
           for value in (gr_arrival_ns, final_delay_ns)):
        raise ValueError("G and D must be finite numeric measurements")
    raw = gr_arrival_ns + alpha * (FINAL_DELAY_CEILING_NS - final_delay_ns)
    quantized = math.floor(raw * 1000 + 0.5)
    if not MIN_TARGET_PS <= quantized <= MAX_TARGET_PS:
        raise ValueError("calibrated target is outside 2.350..2.800 ns")
    return quantized / 1000


def mapped_graph_sha256(mapped_result: Any) -> str:
    """Require the exact mapped graph identity before routing."""
    if not isinstance(mapped_result, dict):
        raise ValueError("mapped_result is required for F1-v9 identity")
    hashes = mapped_result.get("hashes")
    digest = hashes.get("mapped_netlist") if isinstance(hashes, dict) else None
    if not isinstance(digest, str) or len(digest) != 64 or any(
        character not in "0123456789abcdef" for character in digest
    ):
        raise ValueError("mapped_result.hashes.mapped_netlist must be full lowercase SHA-256")
    return digest


def identities(
    candidate_id: str, mapped_result: Any, recovery_target_ns: float
) -> tuple[str, str]:
    """Bind opaque mapped lineage, exact mapped graph, and recovery target."""
    picoseconds = target_ps(recovery_target_ns, FLOW)
    digest = mapped_graph_sha256(mapped_result)
    base = mapped_result.get("mapped_implementation_id") or mapped_result.get("implementation_id") or candidate_id
    if not isinstance(base, str) or not base:
        raise ValueError("mapped implementation identity must be nonempty")
    implementation_id = f"{base}::g{digest}::{FLOW}::r{picoseconds}"
    return implementation_id, f"{implementation_id}::routed3_v1"
