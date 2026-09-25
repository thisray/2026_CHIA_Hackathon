"""Exact-parent W32 mixed-arity XOR/XNOR phase law for one stored proposal."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path

from research.ecc_perf_bench.netlist_fanout import OUT_PINS
from research.ecc_perf_bench.phase_replay_execute import port_signature
from research.ecc_perf_bench.polarity_kernel import parse_cells

PARENT_ID = "c6c10558"
PARENT_SHA = "c6c10558e367fd345b17c3b1a70898ddb8bcca9414833f0fcb34e7fd83478d95"
ACTION_KIND = "mixed_phase_assignment"
PROPOSAL_NAME = "phase003_xor3_absorb_singleton_v1"
PROPOSAL_PATH = "research/ecc_perf_bench/w32_mixed_phase_source_proposal.json"
PROPOSAL_SHA = "4ac58e31b92cd8820a7f9802363fea26088113b950657585b0fe2a5eba09bfc4"
LIBERTY_SHA = "8e78e14442062dba34d414fca6490b2f6b96038d4510d1438ca44fee31487135"
LEF_SHA = "3a3ea4e9d0973402702764d897659e52fe3d413eb48c306cd811de40a75264fa"
SOURCE_INVENTORY_SHA = "7986f6372c27fe0a9a4bf946c7a69f875ea81a3ee13549a2fb6b90be31a1c5c0"
SOURCE_EXPECTED_MAP_SHA = "8c461d1708bb64c42b960346b708ae88ae4e69f365f2b609c410169560c63393"
SOURCE_CANDIDATE_SHA = "8e5b08be4e99d6f34e2fc0afea284f7d99ec7d6fdca5104907300c40a8dcbdd3"
SOURCE_GENERATOR_SHA = "5e6be2e33378934d6317d0c865cd508c40f92c98974e145816c725bb399a7dbb"
SOURCE_KERNEL_SHA = "b28ee38015d881f33cdb5c86a36011f528b88783f1b593588d70209f78f251a3"
EXPECTED_CELL_MAP_SHA = "a31af6c371b8ff5a5d31c87d7fe3365d7861bdedf59c5b6a5944455b1704c54f"
PARENT_CELL_MAP_SHA = "8afe8a7dae817035c4e8c5f6690b82580d59f0c75904122cf578d724c86bc7bc"
INTERNAL = re.compile(r"^_[0-9]+_$")
ASSIGN = re.compile(r"\bassign\b([^;]*);", re.S)
MASTERS = {
    "sky130_fd_sc_hd__xor2_1": (2, 1, 0, "X", 3220, 2720, "sky130_fd_sc_hd__xnor2_1"),
    "sky130_fd_sc_hd__xnor2_1": (2, 1, 1, "Y", 3220, 2720, "sky130_fd_sc_hd__xor2_1"),
    "sky130_fd_sc_hd__xor3_1": (3, 1, 0, "X", 8740, 2720, "sky130_fd_sc_hd__xnor3_1"),
    "sky130_fd_sc_hd__xnor3_1": (3, 1, 1, "X", 8280, 2720, "sky130_fd_sc_hd__xor3_1"),
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def cell_map_sha(cells: dict) -> str:
    return digest(json.dumps(cells, sort_keys=True, separators=(",", ":")).encode())


def assign_signature(text: str) -> tuple[str, ...]:
    uncommented = re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)
    return tuple(sorted(re.sub(r"\s+", "", match.group(1))
                        for match in ASSIGN.finditer(uncommented)))


def parent_graph(parent_text: str) -> dict:
    if digest(parent_text.encode()) != PARENT_SHA:
        raise ValueError("W32 mixed phase requires the exact c6 routed parent")
    cells = parse_cells(parent_text)
    assigned = set()
    for match in ASSIGN.finditer(parent_text):
        assigned.update(re.findall(r"\b_[0-9]+_\b", match.group(1)))
    gates = {}
    drivers: dict[str, list[tuple[str, str]]] = {}
    consumers: dict[str, list[tuple[str, str]]] = {}
    for name, row in cells.items():
        for pin, net in row["pins"].items():
            table = drivers if pin in OUT_PINS else consumers
            table.setdefault(net, []).append((name, pin))
        master = MASTERS.get(row["cell"])
        if master is None:
            continue
        arity, drive, bit, output_pin, _width, _height, _opposite = master
        input_pins = ("A", "B") if arity == 2 else ("A", "B", "C")
        if set(row["pins"]) != set(input_pins) | {output_pin}:
            raise ValueError(f"unsupported W32 mixed parity pin map: {name}")
        gates[name] = {"arity": arity, "drive": drive, "b": bit,
                       "output_pin": output_pin, "output_net": row["pins"][output_pin],
                       "input_nets": {pin: row["pins"][pin] for pin in input_pins}}
    eligible = {}
    for name, gate in gates.items():
        net = gate["output_net"]
        fanout = consumers.get(net, [])
        if (INTERNAL.fullmatch(net) and net not in assigned
            and drivers.get(net) == [(name, gate["output_pin"])]
            and fanout and all(child in gates and pin in gates[child]["input_nets"]
                               for child, pin in fanout)):
            eligible[net] = {"producer": name, "consumers": sorted(fanout)}
    counts = (
        len(cells), len(gates), sum(gate["arity"] == 2 for gate in gates.values()),
        sum(gate["arity"] == 3 for gate in gates.values()), len(eligible),
        sum(gate["b"] for gate in gates.values() if gate["arity"] == 2),
        sum(gate["b"] for gate in gates.values() if gate["arity"] == 3),
    )
    if counts != (148, 95, 88, 7, 56, 11, 5):
        raise ValueError(f"W32 mixed exact graph/eligible boundary changed: {counts}")
    return {"cells": cells, "gates": gates, "eligible": eligible, "assigned": assigned}


def phase_child(parent_text: str, phases: list[str]) -> dict:
    source = parent_graph(parent_text)
    if (not isinstance(phases, list) or not phases
        or len(phases) != len(set(phases)) or phases != sorted(phases)
        or not set(phases).issubset(source["eligible"])):
        raise ValueError("W32 mixed phase vector crosses an ineligible boundary")
    phase = set(phases)
    expected = copy.deepcopy(source["cells"])
    target_specs = {}
    counts = {2: 0, 3: 0}
    area_delta_dbu2 = 0
    for name, gate in source["gates"].items():
        old = source["cells"][name]
        input_nets = gate["input_nets"]
        phase_rhs = (int(gate["output_net"] in phase)
                     + sum(int(net in phase) for net in input_nets.values())) & 1
        new_bit = gate["b"] ^ phase_rhs
        counts[gate["arity"]] += new_bit
        if new_bit == gate["b"]:
            continue
        old_master = old["cell"]
        new_master = MASTERS[old_master][6]
        new_output_pin = MASTERS[new_master][3]
        new_pins = dict(old["pins"])
        output_net = new_pins.pop(gate["output_pin"])
        new_pins[new_output_pin] = output_net
        expected[name] = {"cell": new_master, "pins": new_pins}
        target_specs[name] = {
            "old_master": old_master, "new_master": new_master,
            "old_output_pin": gate["output_pin"], "new_output_pin": new_output_pin,
            "old_output_net": output_net, "input_nets": input_nets,
            "arity": gate["arity"], "drive": gate["drive"], "phase_rhs": phase_rhs,
        }
        area_delta_dbu2 += (
            MASTERS[new_master][4] * MASTERS[new_master][5]
            - MASTERS[old_master][4] * MASTERS[old_master][5]
        )
    if not target_specs:
        raise ValueError("W32 mixed fixed phase vector changes no gate")
    return {
        "phase_one_nets": phases, "eligible_phase_nets": source["eligible"],
        "targets": sorted(target_specs), "target_specs": target_specs,
        "expected_cells": expected, "expected_cell_map_sha256": cell_map_sha(expected),
        "baseline_xnor2_count": 11, "baseline_xnor3_count": 5,
        "candidate_xnor2_count": counts[2], "candidate_xnor3_count": counts[3],
        "parity_gate_count": 95, "db_area_delta_dbu2": area_delta_dbu2,
        "gf2_rule": "b_prime=b xor z(output) xor z(A) xor z(B) xor z(C_if_present)",
    }


def derive(parent_text: str, action: dict, repo: Path) -> dict:
    if action == {"kind": ACTION_KIND, "proposal": WORKER2_PROPOSAL_NAME}:
        return derive_worker2(parent_text, action, repo)
    if action == {"kind": ACTION_KIND, "proposal": GLOBAL_PROPOSAL_NAME}:
        return derive_global(parent_text, action, repo)
    if action != {"kind": ACTION_KIND, "proposal": PROPOSAL_NAME}:
        raise ValueError("model may select only the fixed W32 mixed phase proposal")
    base = repo / "research/ecc_perf_bench"
    sources = {
        "proposal": (base / "w32_mixed_phase_source_proposal.json", PROPOSAL_SHA),
        "inventory": (base / "w32_mixed_phase_source_inventory.json", SOURCE_INVENTORY_SHA),
        "expected_map": (base / "w32_mixed_phase_source_expected_cell_map.json", SOURCE_EXPECTED_MAP_SHA),
        "candidate": (base / "w32_mixed_phase_source_candidate.v", SOURCE_CANDIDATE_SHA),
        "generator": (base / "w32_mixed_phase_source_generator.py", SOURCE_GENERATOR_SHA),
        "solver": (base / "w32_mixed_phase_source_solver.py", SOURCE_KERNEL_SHA),
    }
    for name, (path, expected_sha) in sources.items():
        if not path.is_file() or digest(path.read_bytes()) != expected_sha:
            raise ValueError(f"W32 mixed source {name} snapshot changed")
    proposal = json.loads(sources["proposal"][0].read_text())
    inventory = json.loads(sources["inventory"][0].read_text())
    if (inventory.get("parent_graph_sha256") != PARENT_SHA
        or inventory.get("library_sha256") != LIBERTY_SHA
        or inventory.get("lef_sha256") != LEF_SHA
        or inventory.get("mapped_cell_count") != 148
        or inventory.get("parity_gate_count") != 95
        or inventory.get("legacy_xor2_only_eligible_count") != 41
        or inventory.get("mixed_eligible_count") != 56
        or set(inventory.get("pinned_parity_cell_specs", {})) != set(MASTERS)):
        raise ValueError("W32 mixed pinned Liberty/LEF inventory changed")
    for name, (arity, drive, bit, output_pin, width, height, _opposite) in MASTERS.items():
        item = inventory["pinned_parity_cell_specs"][name]
        input_pins = ["A", "B"] if arity == 2 else ["A", "B", "C"]
        if (item.get("arity") != arity or item.get("drive") != str(drive)
            or item.get("polarity") != bit or item.get("output_pin") != output_pin
            or item.get("input_pins") != input_pins
            or round(item.get("width_um", -1) * 1000) != width
            or round(item.get("height_um", -1) * 1000) != height
            or round(item.get("area_um2", -1) * 10000) != (width * height // 100)):
            raise ValueError(f"W32 mixed pinned master geometry/function differs: {name}")
    if (proposal.get("schema") != "w32.mixed_arity_phase_proposal.v1"
        or proposal.get("proposal_id") != PROPOSAL_NAME
        or proposal.get("parent_id") != PARENT_ID
        or proposal.get("parent_graph_sha256") != PARENT_SHA
        or proposal.get("parent_cell_map_sha256") != PARENT_CELL_MAP_SHA
        or proposal.get("candidate_graph_sha256") != SOURCE_CANDIDATE_SHA
        or proposal.get("source_kernel_sha256") != SOURCE_KERNEL_SHA
        or proposal.get("generator_sha256") != SOURCE_GENERATOR_SHA
        or proposal.get("library_sha256") != LIBERTY_SHA
        or proposal.get("lef_sha256") != LEF_SHA
        or proposal.get("phase_one_nets") != ["_003_"]
        or proposal.get("phase_vector") != {"_003_": 1}
        or proposal.get("eligible_counts") != {
            "additional_variables": 15, "mixed_arity": 56, "xor2_only": 41}
        or proposal.get("expected_cell_map") != {
            "cell_count": 148, "path": "expected_cell_map.json",
            "schema": "JSON mapping instance->{cell,pins}; keys recursively sorted, UTF-8, separators=(',',':'), trailing newline excluded from SHA",
            "sha256": EXPECTED_CELL_MAP_SHA,
        }
        or proposal.get("formal_equivalence") != "NOT_RUN"
        or proposal.get("route") != "NOT_RUN"
        or proposal.get("PPA") != "NOT_RUN"
        or proposal.get("pure_checker", {}).get("GB10_status") != "PASS"
        or proposal.get("pure_checker", {}).get("GCP02_status") not in {"PENDING", "PASS"}):
        raise ValueError("W32 mixed prototype source context changed")
    candidate = phase_child(parent_text, proposal["phase_one_nets"])
    if (cell_map_sha(parse_cells(parent_text)) != PARENT_CELL_MAP_SHA
        or candidate["expected_cell_map_sha256"] != EXPECTED_CELL_MAP_SHA
        or candidate["targets"] != ["_129_", "_130_", "_135_"]
        or candidate["candidate_xnor2_count"] != 11
        or candidate["candidate_xnor3_count"] != 6
        or candidate["db_area_delta_dbu2"] != -1251200
        or proposal.get("baseline_parity_cell_area_um2") != 930.8928
        or proposal.get("candidate_parity_cell_area_um2") != 929.6416
        or proposal.get("parity_cell_area_delta_um2") != -1.2512):
        raise ValueError("W32 mixed 95-gate parity law differs from stored proposal")
    expected_map = json.loads(sources["expected_map"][0].read_text())
    if expected_map != candidate["expected_cells"]:
        raise ValueError("W32 mixed source complete cell map differs from phase law")
    proposal_specs = proposal.get("target_specs")
    if not isinstance(proposal_specs, dict) or set(proposal_specs) != set(candidate["targets"]):
        raise ValueError("W32 mixed source target set changed")
    parent_cells = parse_cells(parent_text)
    for name in candidate["targets"]:
        actual = candidate["target_specs"][name]
        source = proposal_specs[name]
        input_pins = ("A", "B") if actual["arity"] == 2 else ("A", "B", "C")
        if (source.get("instance") != name
            or source.get("old_master") != actual["old_master"]
            or source.get("new_master") != actual["new_master"]
            or source.get("old_output_pin") != actual["old_output_pin"]
            or source.get("new_output_pin") != actual["new_output_pin"]
            or source.get("output_net") != actual["old_output_net"]
            or source.get("input_nets") != [actual["input_nets"][pin] for pin in input_pins]
            or source.get("arity") != actual["arity"]
            or source.get("drive") != str(actual["drive"])
            or source.get("old_pins") != parent_cells[name]["pins"]
            or source.get("new_pins") != expected_map[name]["pins"]
            or actual["phase_rhs"] != 1):
            raise ValueError(f"W32 mixed source pin/arity/drive mismatch at {name}")
    candidate_text = sources["candidate"][0].read_text()
    if (parse_cells(candidate_text) != expected_map
        or port_signature(parent_text) != port_signature(candidate_text)
        or assign_signature(parent_text) != assign_signature(candidate_text)):
        raise ValueError("W32 mixed source candidate graph/ports/assigns differ")
    return {
        **candidate, "kind": ACTION_KIND, "proposal": PROPOSAL_NAME,
        "action": action, "parent_id": PARENT_ID, "parent_graph_sha256": PARENT_SHA,
        "source_proposal_sha256": PROPOSAL_SHA,
        "source_inventory_sha256": SOURCE_INVENTORY_SHA,
        "source_expected_map_file_sha256": SOURCE_EXPECTED_MAP_SHA,
        "source_candidate_graph_sha256": SOURCE_CANDIDATE_SHA,
        "source_generator_sha256": SOURCE_GENERATOR_SHA,
        "source_kernel_sha256": SOURCE_KERNEL_SHA,
        "liberty_sha256": LIBERTY_SHA, "lef_sha256": LEF_SHA,
        "functional_proof": "NOT_RUN", "route": "NOT_RUN", "measurement": "NOT_RUN",
    }


def validate_child(parent_text: str, child_text: str, manifest: dict, repo: Path) -> None:
    expected = derive(parent_text, manifest["action"], repo)
    if manifest != expected:
        raise ValueError("W32 mixed manifest differs from exact stored proposal")
    if port_signature(parent_text) != port_signature(child_text):
        raise ValueError("W32 mixed ECO changed public module ports")
    if assign_signature(parent_text) != assign_signature(child_text):
        raise ValueError("W32 mixed ECO changed continuous assignments")
    if parse_cells(child_text) != manifest["expected_cells"]:
        raise ValueError("W32 mixed ECO child full cell map differs from phase law")
GLOBAL_PROPOSAL_NAME = "mixed_global_area_then_xnor2_v1"
GLOBAL_SOURCE_PROPOSAL_ID = "mixed_global_search_best_worker1_v1"
GLOBAL_PHASE_ONE = (
    "_001_", "_002_", "_003_", "_005_", "_007_", "_008_", "_025_", "_026_",
    "_027_", "_033_", "_035_", "_040_", "_041_", "_090_", "_091_", "_095_",
    "_100_", "_101_", "_102_", "_106_",
)
GLOBAL_SOURCE_FILES = {
    "proposal": ("w32_mixed_phase_global_proposal.json",
                 "bb39e6169ccce2641530ef7f0814a306e99a8b470c9cbe563c30ab060a511ae9"),
    "expected_map": ("w32_mixed_phase_global_expected_cell_map.json",
                     "48fe25eaae4220651ec625ed6def5e888710c7fd1ca458396663a8b918adc015"),
    "candidate": ("w32_mixed_phase_global_candidate.v",
                  "2a2873494f4d097e9e33786de3db0681e22e62a5e480f7407b1a5e59870acb28"),
    "remote_check": ("w32_mixed_phase_global_remote_check.json",
                     "fcdf462e9a4497a5060e13401a0464caea0da0e5783d022d57e67abb866c438c"),
    "checker_source": ("w32_mixed_phase_global_checker.py",
                       "9ec49a866f44202f09b1fb93af35ef0f667aed9d161314e2d2d5ea71e709c149"),
    "retry_solver": ("w32_mixed_phase_global_retry_solver.py",
                     "4a21a8f9d5663c6d8189312524f27b31b34c7bb9c60fb3e5f933c9c5d52bb33f"),
    "worker1_progress": ("w32_mixed_phase_global_worker1_progress.json",
                         "f94de6a564466c7ac3dd2be9372ee4609be93d10ed080eb6ef95996c56297f4a"),
}
GLOBAL_EXPECTED_CELL_MAP_SHA = "e79c5b59a20d697fefbcab3efc6893ae3e0dbd866834c70065a384067f1ff6da"
GLOBAL_TARGETS = (
    "_108_", "_118_", "_125_", "_129_", "_130_", "_132_", "_155_", "_157_", "_166_",
)


def derive_global(parent_text: str, action: dict, repo: Path) -> dict:
    if action != {"kind": ACTION_KIND, "proposal": GLOBAL_PROPOSAL_NAME}:
        raise ValueError("model action differs from fixed W32 global mixed proposal")
    base = repo / "research/ecc_perf_bench"
    sources = {}
    for name, (filename, expected_sha) in GLOBAL_SOURCE_FILES.items():
        path = base / filename
        if not path.is_file() or digest(path.read_bytes()) != expected_sha:
            raise ValueError(f"W32 global mixed source {name} snapshot changed")
        sources[name] = path
    proposal = json.loads(sources["proposal"].read_text())
    remote_check = json.loads(sources["remote_check"].read_text())
    progress = json.loads(sources["worker1_progress"].read_text())
    if (proposal.get("schema") != "w32.mixed_arity_phase_proposal.v1"
        or proposal.get("proposal_id") != GLOBAL_SOURCE_PROPOSAL_ID
        or proposal.get("parent_id") != PARENT_ID
        or proposal.get("parent_graph_sha256") != PARENT_SHA
        or proposal.get("parent_cellmap_sha256") != PARENT_CELL_MAP_SHA
        or proposal.get("candidate_graph_sha256") != GLOBAL_SOURCE_FILES["candidate"][1]
        or proposal.get("phase_one_nets") != list(GLOBAL_PHASE_ONE)
        or proposal.get("phase_vector") != {net: 1 for net in GLOBAL_PHASE_ONE}
        or proposal.get("library_sha256") != LIBERTY_SHA
        or proposal.get("lef_sha256") != LEF_SHA
        or proposal.get("kernel_sha256") != SOURCE_KERNEL_SHA
        or proposal.get("checker_sha256") != GLOBAL_SOURCE_FILES["checker_source"][1]
        or proposal.get("retry_solver_sha256") != GLOBAL_SOURCE_FILES["retry_solver"][1]
        or proposal.get("candidate_cellmap", {}).get("canonical_sha256")
            != GLOBAL_EXPECTED_CELL_MAP_SHA
        or proposal.get("candidate_cellmap", {}).get("entries") != 148
        or proposal.get("remote_pure_checker", {}).get("sha256")
            != GLOBAL_SOURCE_FILES["remote_check"][1]
        or proposal.get("remote_pure_checker", {}).get("status") != "PASS"
        or proposal.get("formal_equivalence") != "NOT_RUN"
        or proposal.get("route") != "NOT_RUN" or proposal.get("PPA") != "NOT_RUN"
        or proposal.get("baseline_parity_cell_area_um2") != 930.8928
        or proposal.get("candidate_parity_cell_area_um2") != 928.3904
        or proposal.get("parity_cell_area_delta_um2") != -2.5024
        or remote_check.get("status") != "PASS"
        or remote_check.get("candidate_graph_sha256") != GLOBAL_SOURCE_FILES["candidate"][1]
        or remote_check.get("candidate_cellmap_sha256") != GLOBAL_EXPECTED_CELL_MAP_SHA
        or remote_check.get("parent_graph_sha256") != PARENT_SHA
        or remote_check.get("whole_graph_pure_check", {}).get("status") != "PASS"
        or remote_check.get("formal_equivalence") != "NOT_RUN"
        or remote_check.get("route") != "NOT_RUN" or remote_check.get("PPA") != "NOT_RUN"
        or progress.get("candidate_graph_sha256") != GLOBAL_SOURCE_FILES["candidate"][1]
        or progress.get("phase_one_nets") != list(GLOBAL_PHASE_ONE)):
        raise ValueError("W32 global mixed source/checker context changed")
    candidate = phase_child(parent_text, list(GLOBAL_PHASE_ONE))
    if (candidate["expected_cell_map_sha256"] != GLOBAL_EXPECTED_CELL_MAP_SHA
        or candidate["targets"] != list(GLOBAL_TARGETS)
        or candidate["candidate_xnor2_count"] != 10
        or candidate["candidate_xnor3_count"] != 7
        or candidate["db_area_delta_dbu2"] != -2502400
        or cell_map_sha(parse_cells(parent_text)) != PARENT_CELL_MAP_SHA):
        raise ValueError("W32 global mixed GF2 cellmap/count/area differs")
    expected_map = json.loads(sources["expected_map"].read_text())
    if expected_map != candidate["expected_cells"]:
        raise ValueError("W32 global mixed complete map differs from stored expected cells")
    source_specs = proposal.get("target_specs")
    if not isinstance(source_specs, dict) or set(source_specs) != set(GLOBAL_TARGETS):
        raise ValueError("W32 global mixed source target set changed")
    parent_cells = parse_cells(parent_text)
    for name in GLOBAL_TARGETS:
        actual = candidate["target_specs"][name]
        source = source_specs[name]
        input_pins = ("A", "B") if actual["arity"] == 2 else ("A", "B", "C")
        if (source.get("instance") != name
            or source.get("old_master") != actual["old_master"]
            or source.get("new_master") != actual["new_master"]
            or source.get("old_output_pin") != actual["old_output_pin"]
            or source.get("new_output_pin") != actual["new_output_pin"]
            or source.get("output_net") != actual["old_output_net"]
            or source.get("input_nets") != [actual["input_nets"][pin] for pin in input_pins]
            or source.get("arity") != actual["arity"]
            or source.get("drive") != str(actual["drive"])
            or source.get("old_pins") != parent_cells[name]["pins"]
            or source.get("new_pins") != expected_map[name]["pins"]
            or actual["phase_rhs"] != 1):
            raise ValueError(f"W32 global mixed source target differs at {name}")
    text = sources["candidate"].read_text()
    if (parse_cells(text) != expected_map
        or port_signature(parent_text) != port_signature(text)
        or assign_signature(parent_text) != assign_signature(text)):
        raise ValueError("W32 global mixed source candidate ports/assigns/cellmap differ")
    return {
        **candidate, "kind": ACTION_KIND, "proposal": GLOBAL_PROPOSAL_NAME,
        "action": action, "parent_id": PARENT_ID, "parent_graph_sha256": PARENT_SHA,
        "source_proposal_sha256": GLOBAL_SOURCE_FILES["proposal"][1],
        "source_expected_map_file_sha256": GLOBAL_SOURCE_FILES["expected_map"][1],
        "source_candidate_graph_sha256": GLOBAL_SOURCE_FILES["candidate"][1],
        "source_generator_sha256": GLOBAL_SOURCE_FILES["retry_solver"][1],
        "source_kernel_sha256": SOURCE_KERNEL_SHA,
        "source_inventory_sha256": SOURCE_INVENTORY_SHA,
        "source_remote_check_sha256": GLOBAL_SOURCE_FILES["remote_check"][1],
        "source_worker1_progress_sha256": GLOBAL_SOURCE_FILES["worker1_progress"][1],
        "liberty_sha256": LIBERTY_SHA, "lef_sha256": LEF_SHA,
        "source_phase_rhs_note": (
            "Raw solver progress phase_rhs denotes new intrinsic polarity b-prime; "
            "runtime phase_rhs is independently recomputed phase delta."
        ),
        "functional_proof": "NOT_RUN", "route": "NOT_RUN", "measurement": "NOT_RUN",
    }
WORKER2_PROPOSAL_NAME = "mixed_count10_v02_weighted_alternate_v1"
WORKER2_PHASE_ONE = (
    "_021_", "_022_", "_027_", "_028_", "_032_", "_033_", "_041_",
    "_090_", "_091_", "_095_", "_100_", "_101_", "_102_",
)
WORKER2_TARGETS = (
    "_108_", "_118_", "_130_", "_150_", "_152_", "_157_", "_162_", "_163_", "_166_",
)
WORKER2_EXPECTED_CELL_MAP_SHA = "aa21b54502f4b7e5b5faf14311ebacc79d96ae9974ebd623b5b85e378002b39a"
WORKER2_SOURCE_FILES = {
    "plan": ("w32_mixed_phase_worker2_plan.json",
             "fc16a378f2a479d5193a91bf1e8dd936aac2e979ec3ae23f0ac8d58745db1e95"),
    "progress": ("w32_mixed_phase_worker2_progress.json",
                 "aecf721fa2d84224a0e19b4a25649d4edd7a7d1d80aed23a712f28ba97d7688e"),
    "candidate": ("w32_mixed_phase_worker2_candidate.v",
                  "59432b57c86765dfde93cb2660937c8ca2c6930f9a40df5cab9e9dd7fa7eab28"),
    "expected_map": ("w32_mixed_phase_worker2_expected_cell_map.json",
                     "dcf0de9404408af5598049284f077c31d3f1544d0bb9524f2c9ad2941e3b01d4"),
    "proxy": ("w32_mixed_phase_worker2_proxy.json",
              "f193a9cfeef7550b0964944d91f0e1c8717588a79dcfd888e266dc9713a84c54"),
}


def derive_worker2(parent_text: str, action: dict, repo: Path) -> dict:
    if action != {"kind": ACTION_KIND, "proposal": WORKER2_PROPOSAL_NAME}:
        raise ValueError("model action differs from fixed W32 worker2 proposal")
    base = repo / "research/ecc_perf_bench"
    sources = {}
    for name, (filename, expected_sha) in WORKER2_SOURCE_FILES.items():
        path = base / filename
        if not path.is_file() or digest(path.read_bytes()) != expected_sha:
            raise ValueError(f"W32 worker2 source {name} snapshot changed")
        sources[name] = path
    plan = json.loads(sources["plan"].read_text())
    progress = json.loads(sources["progress"].read_text())
    proxy = json.loads(sources["proxy"].read_text())
    if (plan.get("schema") != "w32.fixed_mixed_phase_worker2.v1"
        or plan.get("proposal_id") != WORKER2_PROPOSAL_NAME
        or plan.get("parent_id") != PARENT_ID
        or plan.get("parent_graph_sha256") != PARENT_SHA
        or plan.get("candidate_graph_sha256") != WORKER2_SOURCE_FILES["candidate"][1]
        or plan.get("candidate_cell_map_sha256") != WORKER2_EXPECTED_CELL_MAP_SHA
        or plan.get("candidate_cell_map_file_sha256") != WORKER2_SOURCE_FILES["expected_map"][1]
        or plan.get("phase_one_nets") != list(WORKER2_PHASE_ONE)
        or plan.get("source_progress_sha256") != WORKER2_SOURCE_FILES["progress"][1]
        or plan.get("source_candidate_sha256") != WORKER2_SOURCE_FILES["candidate"][1]
        or plan.get("source_proxy_sha256") != WORKER2_SOURCE_FILES["proxy"][1]
        or plan.get("source_kernel_sha256") != SOURCE_KERNEL_SHA
        or plan.get("source_retry_solver_sha256") != GLOBAL_SOURCE_FILES["retry_solver"][1]
        or plan.get("liberty_sha256") != LIBERTY_SHA
        or plan.get("lef_sha256") != LEF_SHA
        or plan.get("remote_pure_checker_status")
            != "NOT_PINNED_NOT_REQUIRED_FOR_SOURCE_PREFLIGHT"
        or plan.get("functional_proof") != "NOT_RUN"
        or plan.get("route") != "NOT_RUN" or plan.get("PPA") != "NOT_RUN"
        or plan.get("baseline_xnor2_count") != 11
        or plan.get("baseline_xnor3_count") != 5
        or plan.get("candidate_xnor2_count") != 10
        or plan.get("candidate_xnor3_count") != 7
        or plan.get("db_area_delta_dbu2") != -2502400
        or plan.get("parity_library_area_delta_um2") != -2.5024
        or progress.get("candidate_graph_sha256") != WORKER2_SOURCE_FILES["candidate"][1]
        or progress.get("phase_one_nets") != list(WORKER2_PHASE_ONE)
        or proxy.get("status") != "READ_ONLY_CANDIDATE_PROXY_COMPARISON"
        or proxy.get("parent_graph_sha256") != PARENT_SHA
        or proxy.get("worker2", {}).get("sha256") != WORKER2_SOURCE_FILES["candidate"][1]
        or proxy.get("worker2", {}).get("cellmap_sha256") != WORKER2_EXPECTED_CELL_MAP_SHA
        or proxy.get("V02_true_measurement", {}).get("graph_sha256")
            != GLOBAL_SOURCE_FILES["candidate"][1]
        or plan.get("proxy_method") != proxy.get("proxy_method")
        or plan.get("proxy_worker1_score")
            != proxy.get("residual_xnor2_comparison", {}).get("worker1_weighted_importance")
        or plan.get("proxy_worker2_score")
            != proxy.get("residual_xnor2_comparison", {}).get("worker2_weighted_importance")):
        raise ValueError("W32 worker2 source/proxy context changed")
    candidate = phase_child(parent_text, list(WORKER2_PHASE_ONE))
    if (candidate["targets"] != list(WORKER2_TARGETS)
        or candidate["expected_cell_map_sha256"] != WORKER2_EXPECTED_CELL_MAP_SHA
        or candidate["candidate_xnor2_count"] != 10
        or candidate["candidate_xnor3_count"] != 7
        or candidate["db_area_delta_dbu2"] != -2502400
        or cell_map_sha(parse_cells(parent_text)) != PARENT_CELL_MAP_SHA):
        raise ValueError("W32 worker2 exact GF2 cellmap/count/area differs")
    expected_map = json.loads(sources["expected_map"].read_text())
    if expected_map != candidate["expected_cells"]:
        raise ValueError("W32 worker2 full stored map differs from phase law")
    source_specs = plan.get("target_specs_normalized")
    if not isinstance(source_specs, dict) or set(source_specs) != set(WORKER2_TARGETS):
        raise ValueError("W32 worker2 source target set changed")
    parent_cells = parse_cells(parent_text)
    for name in WORKER2_TARGETS:
        actual = candidate["target_specs"][name]
        source = source_specs[name]
        input_pins = ("A", "B") if actual["arity"] == 2 else ("A", "B", "C")
        if (source.get("instance") != name
            or source.get("old_master") != actual["old_master"]
            or source.get("new_master") != actual["new_master"]
            or source.get("old_output_pin") != actual["old_output_pin"]
            or source.get("new_output_pin") != actual["new_output_pin"]
            or source.get("output_net") != actual["old_output_net"]
            or source.get("input_nets") != [actual["input_nets"][pin] for pin in input_pins]
            or source.get("arity") != actual["arity"]
            or source.get("drive") != str(actual["drive"])
            or source.get("old_pins") != parent_cells[name]["pins"]
            or source.get("new_pins") != expected_map[name]["pins"]
            or source.get("old_polarity_bit") != MASTERS[actual["old_master"]][2]
            or source.get("new_polarity_bit") != MASTERS[actual["new_master"]][2]
            or source.get("phase_delta_bit") != actual["phase_rhs"]
            or actual["phase_rhs"] != 1):
            raise ValueError(f"W32 worker2 normalized target differs at {name}")
    child_text = sources["candidate"].read_text()
    if (parse_cells(child_text) != expected_map
        or port_signature(parent_text) != port_signature(child_text)
        or assign_signature(parent_text) != assign_signature(child_text)):
        raise ValueError("W32 worker2 source candidate ports/assigns/cellmap differ")
    return {
        **candidate, "kind": ACTION_KIND, "proposal": WORKER2_PROPOSAL_NAME,
        "action": action, "parent_id": PARENT_ID, "parent_graph_sha256": PARENT_SHA,
        "source_proposal_sha256": WORKER2_SOURCE_FILES["plan"][1],
        "source_packet_manifest_sha256": WORKER2_SOURCE_FILES["plan"][1],
        "source_expected_map_file_sha256": WORKER2_SOURCE_FILES["expected_map"][1],
        "source_candidate_graph_sha256": WORKER2_SOURCE_FILES["candidate"][1],
        "source_generator_sha256": GLOBAL_SOURCE_FILES["retry_solver"][1],
        "source_kernel_sha256": SOURCE_KERNEL_SHA,
        "source_inventory_sha256": SOURCE_INVENTORY_SHA,
        "source_remote_check_sha256": None,
        "source_worker2_progress_sha256": WORKER2_SOURCE_FILES["progress"][1],
        "source_proxy_sha256": WORKER2_SOURCE_FILES["proxy"][1],
        "source_phase_rhs_note": plan["raw_progress_phase_rhs_note"],
        "liberty_sha256": LIBERTY_SHA, "lef_sha256": LEF_SHA,
        "functional_proof": "NOT_RUN", "route": "NOT_RUN", "measurement": "NOT_RUN",
    }
