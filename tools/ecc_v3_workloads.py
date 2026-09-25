#!/usr/bin/env python3
"""Generate deterministic ECC measurement workloads for ``recipe_ecc_v3``.

The generator only produces stimulus and the expected SECDED response of an
independent algorithmic reference. It makes no claim about real memory error
rates and it never records a measured duration: the intended vector interval is
a *request* to the testbench, while the receipt must always be built from the
interval that the simulator and the VCD actually produced.

The workload is deliberately candidate-agnostic. It is a function of the data
width, the profile, the seed and the count only, so the candidate and every
baseline in a cohort are driven with byte-identical stimulus.

Profiles
--------
``stress_encoded``     uniformly random encoded words (worst-case toggling)
``valid_uniform``      uniformly random payloads, always legal codewords
``valid_low_toggle``   single payload bit flipped per vector, legal codewords
``single_fault_sweep`` functional/sensitivity appendix, one injected bit error
``double_fault_sweep`` functional/sensitivity appendix, two injected bit errors

Only the first three are energy-measurement profiles; the fault sweeps stay in
the functional sensitivity appendix and are never averaged into an energy metric.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
RECIPE_NAME = "recipe_ecc_v3"
ENERGY_PROFILES = ("stress_encoded", "valid_uniform", "valid_low_toggle")
SENSITIVITY_PROFILES = ("single_fault_sweep", "double_fault_sweep")
PROFILES = ENERGY_PROFILES + SENSITIVITY_PROFILES
SUPPORTED_WIDTHS = (8, 11, 16, 26, 32, 64)

#: The workload manifest never records a measured window. This sentinel is what
#: the parser sees if anything ever tries to use the manifest as a measurement.
WINDOW_SENTINEL = "MUST_BE_READ_FROM_SIMULATION_MONITORS_AND_VCD"


class WorkloadError(ValueError):
    """Fail-closed rejection of a workload request."""


def dimensions(width: int) -> tuple[int, int]:
    """Return ``(parity_width, codeword_width)`` exactly as ``cc_pkg`` does."""

    if not isinstance(width, int) or isinstance(width, bool) or not 1 <= width <= 256:
        raise WorkloadError("data width must be an integer in [1,256]")
    parity = 2
    while (1 << parity) < parity + width + 1:
        parity += 1
    return parity, parity + width


def encode(width: int, payload: int) -> int:
    """Encode ``payload`` into the SECDED word consumed by ``data_i``."""

    parity_width, codeword_width = dimensions(width)
    if not isinstance(payload, int) or isinstance(payload, bool):
        raise WorkloadError("payload must be an integer")
    if not 0 <= payload < (1 << width):
        raise WorkloadError("payload outside data width")
    code = 0
    data_index = 0
    for position in range(1, codeword_width + 1):
        if position & (position - 1):
            code |= ((payload >> data_index) & 1) << (position - 1)
            data_index += 1
    for parity_index in range(parity_width):
        parity = 0
        for position in range(1, codeword_width + 1):
            if position & (1 << parity_index):
                parity ^= (code >> (position - 1)) & 1
        code |= parity << ((1 << parity_index) - 1)
    overall = bin(code).count("1") & 1
    return code | (overall << codeword_width)


def reference(width: int, encoded: int) -> tuple[int, int, int, int, int]:
    """Independent SECDED reference decode of ``encoded``.

    Returns ``(data_o, syndrome_o, single_error_o, parity_error_o,
    double_error_o)`` with the same semantics as ``cc_ecc_decode``.
    """

    parity_width, codeword_width = dimensions(width)
    if not isinstance(encoded, int) or isinstance(encoded, bool):
        raise WorkloadError("encoded word must be an integer")
    if not 0 <= encoded < (1 << (codeword_width + 1)):
        raise WorkloadError("encoded word outside encoded width")
    syndrome = 0
    for parity_index in range(parity_width):
        parity = 0
        for position in range(1, codeword_width + 1):
            if position & (1 << parity_index):
                parity ^= (encoded >> (position - 1)) & 1
        syndrome |= parity << parity_index
    overall_parity = bin(encoded).count("1") & 1
    corrected = encoded & ((1 << codeword_width) - 1)
    if syndrome != 0 and syndrome <= codeword_width:
        corrected ^= 1 << (syndrome - 1)
    data = 0
    data_index = 0
    for position in range(1, codeword_width + 1):
        if position & (position - 1):
            data |= ((corrected >> (position - 1)) & 1) << data_index
            data_index += 1
    single_error = int(bool(overall_parity) and syndrome != 0)
    parity_error = int(bool(overall_parity) and syndrome == 0)
    double_error = int(not overall_parity and syndrome != 0)
    return data, syndrome, single_error, parity_error, double_error


def _validate(width: int, profile: str, seed: int, count: int, interval_ps: int) -> None:
    dimensions(width)
    if width not in SUPPORTED_WIDTHS:
        raise WorkloadError(f"unsupported data width: {width!r}")
    if profile not in PROFILES:
        raise WorkloadError(f"unknown profile: {profile}")
    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
        raise WorkloadError("seed must be a non-negative integer")
    if not isinstance(count, int) or isinstance(count, bool) or count < 1:
        raise WorkloadError("count must be a positive integer")
    if not isinstance(interval_ps, int) or isinstance(interval_ps, bool) or interval_ps < 1:
        raise WorkloadError("interval must be a positive integer number of picoseconds")


def workload(
    width: int,
    profile: str,
    seed: int,
    count: int = 1024,
    interval_ps: int = 10000,
) -> dict[str, Any]:
    """Build the workload body; ``content_sha256`` binds every stimulus bit."""

    _validate(width, profile, seed, count, interval_ps)
    parity_width, codeword_width = dimensions(width)
    encoded_width = codeword_width + 1
    rng = random.Random(f"{RECIPE_NAME}:{width}:{profile}:{seed}")
    payload = rng.getrandbits(width)
    vectors: list[dict[str, Any]] = []
    for index in range(count):
        if profile == "stress_encoded":
            code = rng.getrandbits(encoded_width)
        else:
            if profile == "valid_low_toggle":
                payload ^= 1 << rng.randrange(width)
            else:
                payload = rng.getrandbits(width)
            code = encode(width, payload)
            if profile == "single_fault_sweep":
                code ^= 1 << (index % encoded_width)
            elif profile == "double_fault_sweep":
                first, second = rng.sample(range(encoded_width), 2)
                code ^= (1 << first) | (1 << second)
        vectors.append(
            {
                "index": index,
                "encoded_hex": format(code, "x"),
                "expected": list(reference(width, code)),
            }
        )
    body: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "recipe": RECIPE_NAME,
        "data_width": width,
        "parity_width": parity_width,
        "codeword_width": codeword_width,
        "encoded_width": encoded_width,
        "profile": profile,
        "profile_kind": "energy" if profile in ENERGY_PROFILES else "functional_sensitivity",
        "seed": seed,
        "expected_completions": count,
        "intended_interval_ps": interval_ps,
        "status": "GENERATED_NOT_SIMULATED",
        "synthetic": True,
        "actual_measurement_window": WINDOW_SENTINEL,
        "reference": "independent_algorithmic_secded",
        "vector_hex_digits": (encoded_width + 3) // 4,
        "vectors": vectors,
    }
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    body["content_sha256"] = hashlib.sha256(canonical).hexdigest()
    body["vectors_sha256"] = hashlib.sha256(render_vectors(body).encode()).hexdigest()
    return body


def render_vectors(body: dict[str, Any]) -> str:
    """Render the ``$readmemh`` stimulus file consumed by the v3 testbench."""

    digits = body["vector_hex_digits"]
    lines = [format(int(row["encoded_hex"], 16), f"0{digits}x") for row in body["vectors"]]
    return "\n".join(lines) + "\n"


def verify_workload(body: Any, vectors_text: str) -> dict[str, Any]:
    """Re-derive a workload manifest from its own contents, or fail closed."""

    if not isinstance(body, dict):
        raise WorkloadError("workload manifest must be a JSON object")
    declared_content = body.get("content_sha256")
    declared_vectors = body.get("vectors_sha256")
    stripped = {
        key: value
        for key, value in body.items()
        if key not in {"content_sha256", "vectors_sha256"}
    }
    canonical = json.dumps(stripped, sort_keys=True, separators=(",", ":")).encode()
    if hashlib.sha256(canonical).hexdigest() != declared_content:
        raise WorkloadError("workload content_sha256 does not match the manifest body")
    if hashlib.sha256(render_vectors(body).encode()).hexdigest() != declared_vectors:
        raise WorkloadError("workload vectors_sha256 does not match the rendered stimulus")
    if hashlib.sha256(vectors_text.encode()).hexdigest() != declared_vectors:
        raise WorkloadError("the stimulus file on disk is not the stimulus the manifest binds")
    rebuilt = workload(
        int(body["data_width"]),
        str(body["profile"]),
        int(body["seed"]),
        int(body["expected_completions"]),
        int(body["intended_interval_ps"]),
    )
    if rebuilt["content_sha256"] != declared_content:
        raise WorkloadError(
            "the workload manifest is not what this generator produces for its own "
            "declared width/profile/seed/count/interval"
        )
    if body.get("actual_measurement_window") != WINDOW_SENTINEL:
        raise WorkloadError("the workload manifest must not claim a measured window")
    return body


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--width", type=int, required=True, choices=SUPPORTED_WIDTHS)
    parser.add_argument("--profile", choices=PROFILES, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--count", type=int, default=1024)
    parser.add_argument("--interval-ps", type=int, default=10000)
    parser.add_argument("--out", type=Path, required=True, help="workload JSON (exclusive create)")
    parser.add_argument(
        "--vectors-out", type=Path, help="optional $readmemh stimulus file (exclusive create)"
    )
    args = parser.parse_args()

    body = workload(args.width, args.profile, args.seed, args.count, args.interval_ps)
    with args.out.open("x", encoding="utf-8") as handle:
        json.dump(body, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    if args.vectors_out is not None:
        with args.vectors_out.open("x", encoding="utf-8") as handle:
            handle.write(render_vectors(body))
    print(
        json.dumps(
            {
                "out": str(args.out),
                "vectors_out": str(args.vectors_out) if args.vectors_out else None,
                "profile": body["profile"],
                "profile_kind": body["profile_kind"],
                "expected_completions": body["expected_completions"],
                "intended_interval_ps": body["intended_interval_ps"],
                "content_sha256": body["content_sha256"],
                "vectors_sha256": body["vectors_sha256"],
                "status": body["status"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
