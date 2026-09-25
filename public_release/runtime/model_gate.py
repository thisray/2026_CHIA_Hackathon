"""Explicit reader-configured RUN/STOP gate for one fixed CHIA proposal."""

from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from public_release.runtime.cli import (
    EXAMPLES, ROOT, dispatch_chia, read_json, replay, sha256, write_json,
)


def validate_options(args: Any) -> list[dict] | None:
    if not args.execute:
        raise ValueError("model-gate requires explicit --execute")
    if not 0 < args.timeout_s <= 120 or not 0 < args.max_output_tokens <= 2048:
        raise ValueError("timeout must be <=120s and max output <=2048 tokens")
    if args.mock_responses:
        if any((args.endpoint, args.model, args.auth_env, args.enable_network_model)):
            raise ValueError("mock responses cannot be combined with network model settings")
        mock = read_json(args.mock_responses)
        responses = mock.get("responses")
        if (mock.get("mode") != "MOCK" or not isinstance(responses, list)
            or len(responses) != (2 if args.assess_feedback else 1)
            or any(not isinstance(row, dict) for row in responses)):
            raise ValueError("mock file must declare mode MOCK and the exact response count")
        return responses
    if not all((args.enable_network_model, args.endpoint, args.model, args.auth_env)):
        raise ValueError("live gate requires --enable-network-model, --endpoint, --model, and --auth-env")
    parsed = urllib.parse.urlparse(args.endpoint)
    if (parsed.scheme != "https" or not parsed.netloc or parsed.username
        or parsed.password or parsed.query or parsed.fragment):
        raise ValueError("model endpoint must be an HTTPS URL without embedded credentials or query")
    if not os.environ.get(args.auth_env):
        raise ValueError("reader-supplied auth environment variable is missing")
    return None


def first_prompt(example: str, parent: Path, fixed: dict) -> str:
    receipt = read_json(parent / "receipt.json")
    measurement = receipt.get("measurement", {})
    prompt = {
        "kind": "fixed_plan_run_stop_gate_v1",
        "example": example,
        "parent": {
            "id": fixed["parent_id"],
            "routed_netlist_sha256": fixed["expected_parent_sha256"],
            "goal_id": fixed["goal_id"],
        },
        "historical_feedback": {
            "source": "saved parent receipt; target child outcome withheld",
            "receipt_sha256": sha256(parent / "receipt.json"),
            "delay_ns": receipt.get("routed_delay_ns"),
            "area_um2": receipt.get("routed_area_um2"),
            "j_score": receipt.get("j_score"),
            "raw_energies_pj": measurement.get("raw_energies_pj"),
            "feasible": receipt.get("feasible"),
        },
        "fixed_action": fixed["action"],
        "budget": {"model_calls_max": 2, "route_calls_max": 1},
        "response_rule": "Return one JSON object: RUN with exact parent_id/action and nonempty reason, or STOP with exact parent_id and nonempty reason. Do not propose a different action.",
    }
    return json.dumps(prompt, sort_keys=True, separators=(",", ":"))


def validate_first(parsed: dict, request: dict) -> dict:
    if (not isinstance(parsed, dict) or parsed.get("decision") not in {"RUN", "STOP"}
        or parsed.get("parent_id") != request["parent_id"]
        or not isinstance(parsed.get("reason"), str) or not parsed["reason"].strip()):
        raise ValueError("model first response must choose RUN or STOP for the exact parent with a reason")
    if parsed["decision"] == "RUN":
        if parsed.get("action") != request["action"]:
            raise ValueError("model RUN changed the fixed action")
    elif "action" in parsed and parsed["action"] not in (None, {"kind": "STOP"}):
        raise ValueError("model STOP cannot carry another action")
    return parsed


def validate_assessment(parsed: dict, parent_id: str) -> dict:
    if (not isinstance(parsed, dict) or parsed.get("decision") != "STOP"
        or parsed.get("parent_id") != parent_id or "action" in parsed
        or not isinstance(parsed.get("reason"), str) or not parsed["reason"].strip()):
        raise ValueError("second model call can only STOP and assess the measured feedback")
    return parsed


def model_call(args: Any, prompt: str, index: int, root: Path,
               mock: list[dict] | None) -> tuple[dict, dict]:
    call_dir = root / f"model_call_{index}"
    call_dir.mkdir()
    prompt_path = call_dir / "prompt.json"
    prompt_path.write_text(prompt + "\n", encoding="utf-8")
    record = {"index": index, "prompt_sha256": sha256(prompt_path),
              "timeout_s": args.timeout_s, "max_output_tokens": args.max_output_tokens,
              "provider_mode": "MOCK" if mock is not None else "READER_HTTP",
              "route_calls_before": 0 if index == 1 else 1,
              "cost_usd": None, "status": "IN_FLIGHT"}
    write_json(call_dir / "attempt.json", record)
    try:
        if mock is not None:
            parsed = mock[index - 1]
            body = json.dumps(parsed, sort_keys=True).encode()
            record.update(http_status_provenance="synthetic_mock_fixture_no_network",
                          http_status=200, model="MOCK", network_call=False)
        else:
            payload = {
                "model": args.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
                "max_tokens": args.max_output_tokens,
            }
            request = urllib.request.Request(
                args.endpoint,
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json",
                         "Authorization": "Bearer " + os.environ[args.auth_env]},
                method="POST",
            )
            class NoRedirect(urllib.request.HTTPRedirectHandler):
                def redirect_request(self, request, file_pointer, code, message, headers, new_url):
                    raise ValueError("model endpoint redirect refused")

            started = time.monotonic()
            opener = urllib.request.build_opener(NoRedirect)
            with opener.open(request, timeout=args.timeout_s) as response:
                body = response.read(65537)
                status = response.status
            record.update(http_status=status, model=args.model, endpoint=args.endpoint,
                          network_call=True, wall_s=round(time.monotonic() - started, 3))
            if status != 200 or len(body) > 65536:
                raise ValueError("model HTTP status or response size invalid")
            decoded = json.loads(body)
            choice = decoded["choices"][0]
            if choice.get("finish_reason") not in (None, "stop", "STOP"):
                raise ValueError("model response ended before a complete decision")
            content = choice["message"]["content"]
            parsed = json.loads(content) if isinstance(content, str) else content
            record["usage"] = decoded.get("usage")
        raw_path = call_dir / "response.json"
        raw_path.write_bytes(body)
        record["response_sha256"] = sha256(raw_path)
        if not isinstance(parsed, dict):
            raise ValueError("model response JSON object required")
        record["status"] = "COMPLETE"
        write_json(call_dir / "attempt.json", record)
        return parsed, record
    except Exception as exc:
        record.update(status="ERROR_OR_UNKNOWN", error=f"{type(exc).__name__}: {exc}")
        write_json(call_dir / "attempt.json", record)
        raise


def normalize_decision(parsed: dict, call: dict) -> dict:
    return {
        "http_status": call["http_status"],
        "http_status_provenance": call.get("http_status_provenance", "reader_http_response"),
        "model": call["model"],
        "transport_kind": call["provider_mode"],
        "network_call": call["network_call"],
        "parsed_object": parsed,
        "response_sha256": call["response_sha256"],
    }


def model_gate(args: Any) -> dict:
    mock = validate_options(args)
    prepared = replay(args.example, args.data_root, args.output_root, execute=False)
    if prepared["status"] != "NOT_RUN" or prepared.get("preflight") != "PASS":
        return prepared
    prepared.pop("blocker", None)
    root = args.output_root.resolve()
    request_path = root / "request.json"
    request = read_json(request_path)
    prompt = first_prompt(args.example, root / "inputs/parent", request)
    report = {
        **prepared, "mode": "fixed_plan_model_gate",
        "model_call_origin": "MOCK" if mock is not None else "READER_HTTP",
        "status": "ERROR_OR_UNKNOWN", "route_count": 0,
        "model_calls_max": 2, "route_calls_max": 1,
        "model_calls": [], "live_model_call": mock is None,
    }
    try:
        parsed, call = model_call(args, prompt, 1, root, mock)
        report["model_calls"].append(call)
        validate_first(parsed, request)
        decision = root / "inputs/model_decision.json"
        write_json(decision, normalize_decision(parsed, call))
        request["model_decision_path"] = str(decision)
        if parsed["decision"] == "STOP":
            request["action"] = {"kind": "STOP"}
        write_json(request_path, request)
        if args.example == "v02":
            from research.ecc_perf_bench.w32_mixed_phase_execute import validate_request
        else:
            from research.ecc_perf_bench.phase_replay_execute import validate_request
        validate_request(request)
        if parsed["decision"] == "STOP":
            result = {"status": "STOP", "stage": "model_gate", "route_valid": False,
                      "functional_valid": None, "measurement_valid": None,
                      "submission_counted": 0, "source_commit": request["source_commit"],
                      "parent_id": request["parent_id"], "action": request["action"],
                      "model_decision_sha256": sha256(decision),
                      "model_call_origin": report["model_call_origin"]}
            write_json(root / "result.json", result)
            report.update(status="STOP", route_count=0, result_path=str(root / "result.json"),
                          result_sha256=sha256(root / "result.json"))
            write_json(root / "runtime_report.json", report)
            return report
        report["route_count"] = 1
        report = dispatch_chia(args.example, request_path, root, report)
        result_path = root / "result.json"
        case_receipt = root / "case/receipt.json"
        feedback = {
            "result": read_json(result_path) if result_path.is_file() else None,
            "case_receipt": read_json(case_receipt) if case_receipt.is_file() else None,
        }
        write_json(root / "feedback.json", feedback)
        report["feedback_path"] = str(root / "feedback.json")
        report["feedback_sha256"] = sha256(root / "feedback.json")
        if args.assess_feedback:
            second_prompt = json.dumps({
                "kind": "fixed_plan_post_route_assessment_v1",
                "parent_id": request["parent_id"],
                "fixed_action": request["action"],
                "feedback": feedback,
                "response_rule": "Return JSON with decision STOP, exact parent_id, and a nonempty reason assessing feedback. No action or route is allowed.",
            }, sort_keys=True, separators=(",", ":"))
            assessed, second_call = model_call(args, second_prompt, 2, root, mock)
            report["model_calls"].append(second_call)
            report["assessment"] = validate_assessment(assessed, request["parent_id"])
    except Exception as exc:
        report["status"] = "ERROR_OR_UNKNOWN"
        report["blocker"] = f"{type(exc).__name__}: {exc}"
        report["execution"] = "NOT_RUN" if report["route_count"] == 0 else "SEE_RESULT_AND_FEEDBACK"
        report["model_attempt_paths"] = [str(path) for path in sorted(root.glob("model_call_*/attempt.json"))]
    write_json(root / "runtime_report.json", report)
    return report
