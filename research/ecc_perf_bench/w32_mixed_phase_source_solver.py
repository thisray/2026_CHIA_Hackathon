#!/usr/bin/env python3
"""Bounded W32 mixed XOR2/XOR3 phase prototype; never runs EDA or formal tools."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import random
import re
import time
import socket
import os
import resource
from collections import Counter, defaultdict
from pathlib import Path

PARENTS = {
    "ff6": "ff6f3194c3e527005aba7bb2b4153e4a2f47454bf627739f0348cae6d120bf59",
    "c6": "c6c10558e367fd345b17c3b1a70898ddb8bcca9414833f0fcb34e7fd83478d95",
}
CELL_RE = re.compile(r"^\s*(sky130_fd_sc_hd__\w+)\s+(\S+)\s*\((?P<conns>[^;]*)\)\s*;", re.M | re.S)
CONN_RE = re.compile(r"\.(\w+)\(([^()]*)\)")
INTERNAL = re.compile(r"^_\d+_$")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def matching_brace(text: str, brace: int) -> int:
    depth = 0
    quoted = False
    escaped = False
    for i in range(brace, len(text)):
        ch = text[i]
        if quoted:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                quoted = False
            continue
        if ch == '"':
            quoted = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i + 1
    raise ValueError("unbalanced Liberty braces")


def liberty_groups(text: str, kind: str):
    pattern = re.compile(rf"\b{kind}\s*\(\s*\"?([^\")]+)\"?\s*\)\s*\{{")
    pos = 0
    while m := pattern.search(text, pos):
        end = matching_brace(text, m.end() - 1)
        yield m.group(1).strip(), text[m.end():end - 1]
        pos = end


class BoolExpr:
    TOK = re.compile(r"[A-Za-z_][A-Za-z0-9_$]*|[01]|[()!~&|+*^]")
    def __init__(self, text: str, env: dict[str, int]):
        self.tokens = self.TOK.findall(text)
        compact = re.sub(r"\s+", "", text)
        if "".join(self.tokens) != compact:
            raise ValueError(f"unsupported Liberty function syntax: {text}")
        self.i = 0
        self.env = env
    def eat(self, token):
        if self.i < len(self.tokens) and self.tokens[self.i] == token:
            self.i += 1
            return True
        return False
    def parse(self):
        value = self.parse_or()
        if self.i != len(self.tokens):
            raise ValueError(f"trailing Liberty function tokens: {self.tokens[self.i:]}")
        return int(bool(value))
    def parse_or(self):
        v = self.parse_xor()
        while self.i < len(self.tokens) and self.tokens[self.i] in ("|", "+"):
            self.i += 1
            rhs = self.parse_xor()
            v = int(bool(v) or bool(rhs))
        return int(bool(v))
    def parse_xor(self):
        v = self.parse_and()
        while self.eat("^"):
            v ^= self.parse_and()
        return v
    def parse_and(self):
        v = self.parse_unary()
        while self.i < len(self.tokens) and self.tokens[self.i] in ("&", "*"):
            self.i += 1
            rhs = self.parse_unary()
            v = int(bool(v) and bool(rhs))
        return int(bool(v))
    def parse_unary(self):
        if self.eat("!") or self.eat("~"):
            return 1 ^ self.parse_unary()
        if self.eat("("):
            v = self.parse_or()
            if not self.eat(")"):
                raise ValueError("unclosed Liberty function parenthesis")
            return v
        if self.i >= len(self.tokens):
            raise ValueError("missing Liberty function atom")
        atom = self.tokens[self.i]
        self.i += 1
        if atom in ("0", "1"):
            return int(atom)
        if atom not in self.env:
            raise ValueError(f"unknown Liberty function atom: {atom}")
        return self.env[atom]


def lib_group_fields(body: str, group_kind: str) -> list[tuple[str, str]]:
    return list(liberty_groups(body, group_kind))


def parse_liberty(path: Path) -> dict:
    text = path.read_text(errors="strict")
    cells = {}
    for name, body in liberty_groups(text, "cell"):
        area_match = re.search(r"\barea\s*:\s*([0-9.eE+-]+)\s*;", body)
        pins = {}
        for pin, pbody in lib_group_fields(body, "pin"):
            direction = re.search(r"\bdirection\s*:\s*\"?(input|output|inout)\"?\s*;", pbody)
            func = re.search(r"\bfunction\s*:\s*\"([^\"]+)\"\s*;", pbody)
            if direction:
                pins[pin] = {"direction": direction.group(1), "function": func.group(1) if func else None}
        cells[name] = {"area_um2": float(area_match.group(1)) if area_match else None, "pins": pins}
    return cells


def parse_lef(path: Path) -> dict:
    text = path.read_text(errors="strict")
    result = {}
    for m in re.finditer(r"(?m)^\s*MACRO\s+(\S+)\s*$", text):
        name = m.group(1)
        end = re.search(r"(?m)^\s*END\s+" + re.escape(name) + r"\s*$", text[m.end():])
        if not end:
            continue
        body = text[m.end():m.end() + end.start()]
        size = re.search(r"(?m)^\s*SIZE\s+([0-9.]+)\s+BY\s+([0-9.]+)\s*;", body)
        if size:
            result[name] = {"width_um": float(size.group(1)), "height_um": float(size.group(2))}
    return result


def expand_port_declarations(text: str) -> set[str]:
    ports = set()
    for direction, decl in re.findall(r"\b(input|output|inout)\b([^;]*);", text):
        decl = re.sub(r"\b(?:wire|reg|logic|signed|unsigned|tri|wand|wor)\b", " ", decl)
        range_match = re.search(r"\[\s*(-?\d+)\s*:\s*(-?\d+)\s*\]", decl)
        indices = list(range(int(range_match.group(1)), int(range_match.group(2)) + (-1 if int(range_match.group(1)) > int(range_match.group(2)) else 1), -1 if int(range_match.group(1)) > int(range_match.group(2)) else 1)) if range_match else None
        decl = re.sub(r"\[[^]]+\]", " ", decl)
        for name in re.findall(r"[A-Za-z_$][A-Za-z0-9_$]*", decl):
            if indices is None:
                ports.add(name)
            else:
                ports.update(f"{name}[{i}]" for i in indices)
    return ports


def classify_parity(name: str, cell: dict) -> dict | None:
    ins = sorted(pin for pin, spec in cell["pins"].items() if spec["direction"] == "input")
    outs = [pin for pin, spec in cell["pins"].items() if spec["direction"] == "output" and spec["function"]]
    if len(ins) not in (2, 3) or len(outs) != 1:
        return None
    function = cell["pins"][outs[0]]["function"]
    atoms = set(BoolExpr.TOK.findall(function)) - {"0", "1", "(", ")", "!", "~", "&", "|", "+", "*", "^"}
    if not atoms.issubset(set(ins)):
        return None
    truth = []
    for state in range(1 << len(ins)):
        env = {pin: (state >> i) & 1 for i, pin in enumerate(ins)}
        try:
            truth.append(BoolExpr(function, env).parse())
        except ValueError as exc:
            raise ValueError(f"{name}/{outs[0]} function {function}: {exc}") from exc
    parity = [((state.bit_count()) & 1) for state in range(1 << len(ins))]
    if truth == parity:
        polarity = 0
    elif truth == [x ^ 1 for x in parity]:
        polarity = 1
    else:
        return None
    drive_match = re.search(r"_(\d+)$", name)
    return {"arity": len(ins), "input_pins": ins, "output_pin": outs[0], "polarity": polarity,
            "drive": drive_match.group(1) if drive_match else None,
            "master": name}


def parse_cells(text: str, library: dict) -> tuple[dict, set[str], set[str]]:
    cells = {}
    drivers = defaultdict(list)
    consumers = defaultdict(list)
    gates = {}
    for m in CELL_RE.finditer(text):
        master, instance = m.group(1), m.group(2)
        if master in {"sky130_fd_sc_hd__tapvpwrvgnd_1", "sky130_fd_sc_hd__decap_3"}:
            continue
        if instance in cells:
            raise ValueError(f"duplicate instance {instance}")
        pins = {pin: net.strip() for pin, net in CONN_RE.findall(m.group("conns"))}
        if len(pins) != len(CONN_RE.findall(m.group("conns"))):
            raise ValueError(f"duplicate connected pin {instance}")
        lib = library.get(master)
        if lib is None and master in {"sky130_fd_sc_hd__tapvpwrvgnd_1", "sky130_fd_sc_hd__decap_3"}:
            continue
        if lib is None:
            raise ValueError(f"master absent from pinned Liberty: {master}")
        cells[instance] = {"master": master, "pins": pins}
        parity = classify_parity(master, lib)
        if parity:
            if set(pins) != set(parity["input_pins"] + [parity["output_pin"]]):
                raise ValueError(f"pin map differs from Liberty for {instance}: {pins}")
            parity.update({"inputs": [pins[p] for p in parity["input_pins"]],
                           "output": pins[parity["output_pin"]], "instance": instance})
            gates[instance] = parity
        for pin, net in pins.items():
            spec = lib["pins"].get(pin)
            if spec is None:
                continue
            if spec["direction"] == "output":
                drivers[net].append((instance, pin))
            elif spec["direction"] == "input":
                consumers[net].append((instance, pin))
            elif spec["direction"] == "inout":
                drivers[net].append((instance, pin))
                consumers[net].append((instance, pin))
    ports = expand_port_declarations(text)
    assigned = set()
    for assign in re.findall(r"\bassign\b([^;]*);", text, re.S):
        assigned.update(re.findall(r"_\d+_", assign))
    return {"cells": cells, "drivers": dict(drivers), "consumers": dict(consumers), "gates": gates,
            "ports": sorted(ports), "assigned_internal_nets": sorted(assigned)}, ports, assigned


def build_inventory(text: str, library: dict, source_sha: str) -> dict:
    graph, ports, assigned = parse_cells(text, library)
    allgates = graph["gates"]
    xor2 = {n: g for n, g in allgates.items() if g["arity"] == 2}
    mixed = {}
    base_reasons = Counter()
    mixed_reasons = Counter()
    drivers, consumers = graph["drivers"], graph["consumers"]
    for inst, gate in allgates.items():
        net = gate["output"]
        sinks = consumers.get(net, [])
        sink_cells = [s for s, _ in sinks]
        def reject(reasons, legacy=False):
            if net in ports:
                reasons["public_port"] += 1
                return True
            if net in assigned:
                reasons["continuous_assign"] += 1
                return True
            if not INTERNAL.fullmatch(net):
                reasons["not_internal"] += 1
                return True
            if len(drivers.get(net, [])) != 1:
                reasons["ambiguous_driver"] += 1
                return True
            if not sinks:
                reasons["no_consumers"] += 1
                return True
            for sink, pin in sinks:
                sg = allgates.get(sink)
                if sg is None or (legacy and sg["arity"] != 2):
                    reasons["non_parity_consumer" if not legacy else "non_xor2_consumer"] += 1
                    return True
                if pin not in sg["input_pins"]:
                    reasons["not_parity_input"] += 1
                    return True
            return False
        if not reject(mixed_reasons):
            mixed[net] = {"producer": inst, "arity": gate["arity"], "consumers": sorted(sinks)}
    legacy = {}
    legacy_reasons = Counter()
    for inst, gate in xor2.items():
        net = gate["output"]
        sinks = consumers.get(net, [])
        if net in ports: why="public_port"
        elif net in assigned: why="continuous_assign"
        elif not INTERNAL.fullmatch(net): why="not_internal"
        elif len(drivers.get(net, [])) != 1: why="ambiguous_driver"
        elif not sinks: why="no_consumers"
        elif any(s not in xor2 or pin not in xor2[s]["input_pins"] for s,pin in sinks): why="non_xor2_consumer"
        else:
            legacy[net]={"producer":inst,"consumers":sorted(sinks)};continue
        legacy_reasons[why]+=1
    mixed_clean={k:v for k,v in mixed.items() if k in mixed}
    # A mixed phase is only legal when every consumer and producer closes within the parity subgraph.
    # Components are connected through parity gate equations and eligible output/input nets.
    nets=sorted(mixed_clean)
    parent={n:n for n in nets}
    def find(x):
        while parent[x]!=x:
            parent[x]=parent[parent[x]];x=parent[x]
        return x
    def union(a,b):
        ra,rb=find(a),find(b)
        if ra!=rb:parent[rb]=ra
    gate_rows={}
    for inst,g in allgates.items():
        vars_=sorted({n for n in [g["output"],*g["inputs"]] if n in mixed_clean})
        gate_rows[inst]={"polarity":g["polarity"],"vars":vars_}
        for n in vars_[1:]:union(vars_[0],n)
    comps=defaultdict(list)
    for n in nets:comps[find(n)].append(n)
    return {"source_graph_sha256":source_sha,"cells":graph["cells"],"drivers":drivers,"consumers":consumers,
            "gates":allgates,"legacy_eligible":legacy,"legacy_reasons":dict(legacy_reasons),
            "mixed_eligible":mixed_clean,"mixed_reasons":dict(mixed_reasons),"gate_rows":gate_rows,
            "components":sorted([sorted(v) for v in comps.values()],key=lambda x:(-len(x),x)),
            "ports":sorted(ports),"assigned_internal_nets":sorted(assigned)}


def master_catalog(library: dict, lef: dict) -> dict:
    catalog={}
    for master, cell in library.items():
        parity=classify_parity(master,cell)
        if parity is None: continue
        info={**parity,"area_um2":cell["area_um2"],**lef.get(master,{})}
        catalog[master]=info
    return catalog


def solve(analysis: dict, budget_s: float, seed: int, catalog: dict) -> tuple[dict, dict]:
    eligible=set(analysis["mixed_eligible"])
    gates=analysis["gates"]
    factors=[]
    for inst,g in gates.items():
        vars_=[n for n in [g["output"],*g["inputs"]] if n in eligible]
        factors.append((inst,g["polarity"],g["arity"],vars_))
    phase={n:0 for n in eligible}
    def factor_polarity(state, factor):
        _,b,_,ns=factor
        return b ^ (sum(state.get(n,0) for n in ns)&1)
    # One XOR3-to-XNOR3 area saving dominates every possible XOR2/XNOR2 tie-break.
    two_count=sum(1 for _,_,arity,_ in factors if arity==2)
    primary_weight=two_count+1
    def local_cost(state):
        return [factor_polarity(state,f) for f in factors]
    def objective(local):
        xnor2=sum(v for v,(_,_,arity,_) in zip(local,factors) if arity==2)
        xor3=sum(1-v for v,(_,_,arity,_) in zip(local,factors) if arity==3)
        xnor_total=sum(local)
        return xor3*primary_weight+xnor2, xor3, xnor2, xnor_total
    costs=local_cost(phase);best_tuple=objective(costs);best=best_tuple[0];best_state=phase.copy()
    incident=defaultdict(list)
    for i,(_,_,_,ns) in enumerate(factors):
        for n,count in Counter(ns).items():
            if count % 2: incident[n].append(i)
    start=time.monotonic();deadline=start+budget_s;steps=0;restarts=0
    rng=random.Random(seed)
    while time.monotonic()<deadline:
        restarts+=1
        state=best_state.copy() if restarts==1 else {n:rng.randrange(2) for n in eligible}
        local=local_cost(state);score=objective(local)[0]
        order=sorted(eligible);rng.shuffle(order)
        temp0=primary_weight*0.8
        for sweep in range(max(30,len(order)*12)):
            if time.monotonic()>=deadline:break
            rng.shuffle(order)
            for net in order:
                affected=incident[net]
                old_vals=[local[i] for i in affected]
                state[net]^=1
                for i in affected:local[i]^=1
                new_score=objective(local)[0]
                delta=new_score-score
                temp=max(0.02,temp0*(1.0-sweep/max(30,len(order)*12)))
                if delta<=0 or rng.random()<math.exp(-delta/temp):
                    score=new_score
                    cand=objective(local)
                    if cand[0]<best or (cand[0]==best and cand[3]<best_tuple[3]):
                        best=cand[0];best_tuple=cand;best_state=state.copy()
                else:
                    state[net]^=1
                    for i,v in zip(affected,old_vals):local[i]=v
                steps+=1
                if time.monotonic()>=deadline:break
    result_xnor2=best_tuple[2];result_xor3=best_tuple[1]
    baseline_xnor2=sum(g["polarity"] for g in gates.values() if g["arity"]==2)
    baseline_xor3=sum(1-g["polarity"] for g in gates.values() if g["arity"]==3)
    base_area=sum(catalog[g["master"]]["area_um2"] for g in gates.values())
    candidate_pols=[factor_polarity(best_state,f) for f in factors]
    cand_area=0.0
    for factor,p in zip(factors,candidate_pols):
        inst,_,arity,_=factor
        fam="xnor" if p else "xor"
        drive=gates[inst]["drive"]
        master=f"sky130_fd_sc_hd__{fam}{arity}_{drive}"
        cand_area+=catalog[master]["area_um2"]
    report={"budget_seconds":budget_s,"elapsed_seconds":round(time.monotonic()-start,4),"seed":seed,
            "restarts":restarts,"flip_evaluations":steps,"baseline_xnor2_count":baseline_xnor2,
            "best_xnor2_count":result_xnor2,"baseline_xor3_count":baseline_xor3,"best_xor3_count":result_xor3,
            "baseline_total_xnor_count":sum(g["polarity"] for g in gates.values()),
            "best_total_xnor_count":best_tuple[3],"baseline_parity_area_um2":round(base_area,6),
            "best_parity_area_um2":round(cand_area,6),"parity_area_delta_um2":round(cand_area-base_area,6),
            "area_objective":"minimize pinned-Liberty parity-cell area; exact costs reduce to minimizing XOR3 count because same-drive XOR3/XNOR3 differ by 1.2512 um2 and XOR2/XNOR2 area is equal; ties minimize XNOR2 count",
            "phase_one_nets":sorted(n for n,v in best_state.items() if v),
            "optimality_proven":False,"solver":"deterministic-seeded simulated annealing over exact mixed-arity GF2 gate costs"}
    return best_state,report


def rewrite(text: str, analysis: dict, phase: dict[str,int], catalog: dict) -> tuple[str,dict]:
    targets={};gates=analysis["gates"]
    for inst,g in gates.items():
        z=g["polarity"] ^ (phase.get(g["output"],0) ^ (sum(phase.get(n,0) for n in g["inputs"])&1))
        if z != g["polarity"]:
            suffix="xor" if z==0 else "xnor"
            new=f"sky130_fd_sc_hd__{suffix}{g['arity']}_{g['drive']}"
            if new not in catalog:raise ValueError(f"missing exact same-drive counterpart {new}")
            srcpin=g["output_pin"];dstpin=catalog[new]["output_pin"]
            targets[inst]={"old_master":g["master"],"new_master":new,"old_output_pin":srcpin,"new_output_pin":dstpin,
                           "old_output_net":g["output"],"arity":g["arity"],"drive":g["drive"],"phase_rhs":z,
                           "input_nets":g["inputs"]}
    emitted=set()
    def replace(m):
        master,inst=m.group(1),m.group(2)
        if inst not in targets:return m.group(0)
        row=m.group(0);spec=targets[inst]
        if master!=spec["old_master"]:raise AssertionError("unexpected source master")
        old=f".{spec['old_output_pin']}(";new=f".{spec['new_output_pin']}("
        if row.count(old)!=1:raise AssertionError(f"expected output pin missing in {inst}")
        emitted.add(inst)
        return row.replace(master,spec["new_master"],1).replace(old,new,1)
    after=CELL_RE.sub(replace,text)
    if emitted!=set(targets):raise AssertionError("rewrite omitted cells")
    return after,targets


def phase_truth_check() -> dict:
    checked=0
    for arity in (2,3):
        for b in (0,1):
            for inputs in range(1<<arity):
                old=(inputs.bit_count()&1)^b
                for phases in range(1<<(arity+1)):
                    zinputs=[(phases>>i)&1 for i in range(arity)]
                    zout=(phases>>arity)&1
                    bprime=b^zout^(sum(zinputs)&1)
                    transformed=((sum(((inputs>>i)&1)^zinputs[i] for i in range(arity))&1)^bprime)
                    if transformed != (old^zout):
                        raise AssertionError("local mixed-arity phase identity failed")
                    checked+=1
    return {"status":"PASS","exhaustive_local_cases":checked,"arities":[2,3],
            "identity":"F_b(x xor z_in) == F_(b xor z_out xor parity(z_in))(x) xor z_out",
            "scope":"Library truth functions are separately classified from exact pinned Liberty; this is a local algebra check, not formal proof."}

def structural_check(before: str, after: str, analysis: dict, phase: dict[str,int], targets: dict, library: dict, catalog: dict) -> dict:
    old,_,_=parse_cells(before,library);new,_,_=parse_cells(after,library)
    if old["ports"]!=new["ports"]:raise AssertionError("ports changed")
    if old["assigned_internal_nets"]!=new["assigned_internal_nets"]:raise AssertionError("continuous assigns changed")
    before_assigns=re.findall(r"\bassign\b[^;]*;",before,re.S)
    after_assigns=re.findall(r"\bassign\b[^;]*;",after,re.S)
    if before_assigns!=after_assigns:raise AssertionError("continuous assignment expressions changed")
    if old["cells"].keys()!=new["cells"].keys():raise AssertionError("instance set changed")
    for inst,oldspec in old["cells"].items():
        a,b=oldspec,new["cells"][inst]
        if inst not in targets:
            if a!=b:raise AssertionError(f"untargeted cell changed {inst}")
        else:
            spec=targets[inst]
            if a["master"]!=spec["old_master"] or b["master"]!=spec["new_master"]:raise AssertionError("target master mismatch")
            ap=a["pins"].copy();bp=b["pins"].copy()
            if ap.pop(spec["old_output_pin"])!=spec["old_output_net"]:raise AssertionError("old target output net changed")
            if bp.pop(spec["new_output_pin"])!=spec["old_output_net"]:raise AssertionError("new target output net changed")
            if ap!=bp:raise AssertionError(f"target input pin connectivity changed {inst}")
    if len(old["cells"])!=len(new["cells"]):raise AssertionError("mapped cell count changed")
    local_truth=phase_truth_check()
    # Re-evaluate the exact GF2 equation for every parity cell and ensure all phase-one nets are closed.
    for net,val in phase.items():
        if not val:continue
        if net not in analysis["mixed_eligible"]:raise AssertionError("phase escaped eligible closure")
        if net in analysis["ports"] or net in analysis["assigned_internal_nets"]:raise AssertionError("phase touched boundary")
    for inst,g in analysis["gates"].items():
        bprime=g["polarity"] ^ phase.get(g["output"],0) ^ (sum(phase.get(n,0) for n in g["inputs"])&1)
        expected=targets[inst]["new_master"] if inst in targets else g["master"]
        expectedpol=catalog[expected]["polarity"]
        if expectedpol!=bprime:raise AssertionError(f"GF2 master equation mismatch {inst}")
    return {"status":"PASS","checker":"whole-graph structural GF2 closure plus exact per-cell Liberty truth classification",
            "ports_unchanged":True,"continuous_assigns_unchanged":True,"cell_connectivity_preserved":True,
            "nonparity_and_untargeted_cells_unchanged":True,"all_phase_one_nets_inside_closed_parity_subgraph":True,
            "parity_gate_equations_checked":len(analysis["gates"]),"local_truth_check":local_truth,"formal_equivalence":"NOT_RUN"}


def inventory_report(parent_key: str, parent: Path, lib_path: Path, lef_path: Path, out: Path) -> None:
    lib=parse_liberty(lib_path);lef=parse_lef(lef_path);text=parent.read_text()
    analysis=build_inventory(text,lib,sha(parent));catalog=master_catalog(lib,lef)
    newly_opened=[]
    for net in sorted(set(analysis["mixed_eligible"])-set(analysis["legacy_eligible"])):
        driver=analysis["drivers"].get(net,[])
        prod=driver[0][0] if len(driver)==1 else None
        newly_opened.append({"net":net,"producer":prod,"producer_arity":analysis["gates"].get(prod,{}).get("arity"),
          "consumers":[{"instance":inst,"arity":analysis["gates"].get(inst,{}).get("arity"),"pin":pin} for inst,pin in analysis["consumers"].get(net,[])]})
    xor3_sink_open=[x for x in newly_opened if x["producer_arity"]==2 and any(c["arity"]==3 for c in x["consumers"])]
    report={"parent_key":parent_key,"parent_path":str(parent),"parent_graph_sha256":sha(parent),
            "library_sha256":sha(lib_path),"lef_sha256":sha(lef_path),"mapped_cell_count":len(analysis["cells"]),
            "parity_gate_count":len(analysis["gates"]),"parity_master_counts":dict(Counter(g["master"] for g in analysis["gates"].values())),
            "baseline_xnor2_count":sum(g["polarity"] for g in analysis["gates"].values() if g["arity"]==2),
            "baseline_xnor3_count":sum(g["polarity"] for g in analysis["gates"].values() if g["arity"]==3),
            "legacy_xor2_only_eligible_count":len(analysis["legacy_eligible"]),"legacy_boundary_reasons":analysis["legacy_reasons"],
            "mixed_eligible_count":len(analysis["mixed_eligible"]),"mixed_boundary_reasons":analysis["mixed_reasons"],
            "newly_opened_vs_xor2_only":newly_opened,"xor2_producer_nets_opened_by_xor3_consumers":xor3_sink_open,
            "eligible_nets":analysis["mixed_eligible"],"component_sizes":[len(x) for x in analysis["components"]],
            "pinned_parity_cell_specs":{k:v for k,v in catalog.items() if k in {"sky130_fd_sc_hd__xor3_1","sky130_fd_sc_hd__xnor3_1","sky130_fd_sc_hd__xor2_1","sky130_fd_sc_hd__xnor2_1"}}}
    (out/f"inventory_{parent_key}.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--parent",choices=sorted(PARENTS),required=True)
    ap.add_argument("--parent-file",type=Path,required=True)
    ap.add_argument("--liberty",type=Path,required=True)
    ap.add_argument("--lef",type=Path,required=True)
    ap.add_argument("--output-dir",type=Path,required=True)
    ap.add_argument("--mode",choices=("inventory","solve"),default="inventory")
    ap.add_argument("--budget-seconds",type=float,default=22.0)
    ap.add_argument("--seed",type=int,default=2026092401)
    ap.add_argument("--expected-hostname",default=None)
    args=ap.parse_args()
    if sha(args.parent_file)!=PARENTS[args.parent]:raise ValueError("parent SHA mismatch")
    if args.budget_seconds<=0 or args.budget_seconds>25:raise ValueError("solver cap must be in (0,25]")
    actual_hostname=socket.gethostname()
    resource_guard=None
    if args.mode=="solve":
        if args.expected_hostname is None or actual_hostname!=args.expected_hostname:
            raise ValueError(f"solver hostname guard failed: actual={actual_hostname}, expected={args.expected_hostname}")
        affinity=sorted(os.sched_getaffinity(0)) if hasattr(os,"sched_getaffinity") else []
        as_limit=resource.getrlimit(resource.RLIMIT_AS)[1]
        if len(affinity)>2 or as_limit==resource.RLIM_INFINITY or as_limit>8*1024**3:
            raise ValueError(f"solver resource guard failed: affinity={affinity}, RLIMIT_AS={as_limit}")
        resource_guard={"hostname":actual_hostname,"cpu_affinity":affinity,"cpu_count":len(affinity),"address_space_limit_bytes":as_limit,"address_space_limit_gib":round(as_limit/1024**3,3)}
    args.output_dir.mkdir(parents=True,exist_ok=True)
    lib=parse_liberty(args.liberty);lef=parse_lef(args.lef);catalog=master_catalog(lib,lef)
    text=args.parent_file.read_text();analysis=build_inventory(text,lib,sha(args.parent_file))
    if args.mode=="inventory":
        inventory_report(args.parent,args.parent_file,args.liberty,args.lef,args.output_dir)
        print(json.dumps({"parent":args.parent,"parity_gates":len(analysis["gates"]),"baseline_xnor2":sum(g["polarity"] for g in analysis["gates"].values() if g["arity"]==2),"baseline_xnor3":sum(g["polarity"] for g in analysis["gates"].values() if g["arity"]==3),"xor2_only_eligible":len(analysis["legacy_eligible"]),"mixed_eligible":len(analysis["mixed_eligible"]),"mixed_reason_counts":analysis["mixed_reasons"]},sort_keys=True))
        return
    drives={g["drive"] for g in analysis["gates"].values()}
    if len(drives)!=1:
        raise ValueError(f"fixed-drive prototype requires exactly one existing parity drive; got {sorted(drives)}")
    phase,sol=solve(analysis,args.budget_seconds,args.seed,catalog)
    after,targets=rewrite(text,analysis,phase,catalog)
    check=structural_check(text,after,analysis,phase,targets,lib,catalog)
    outv=args.output_dir/f"candidate_{args.parent}_mixed_phase_unrouted.v";outv.write_text(after)
    result={"status":"PURE_CANDIDATE_NOT_FORMALLY_PROVED_NOT_ROUTED_NOT_MEASURED","parent_key":args.parent,"parent_graph_sha256":sha(args.parent_file),
            "candidate_graph_sha256":sha(outv),"candidate_path":str(outv),"baseline_xnor2_count":sum(g["polarity"] for g in analysis["gates"].values() if g["arity"]==2),
            "baseline_xnor3_count":sum(g["polarity"] for g in analysis["gates"].values() if g["arity"]==3),
            "mixed_total_baseline_xnor_count":sum(g["polarity"] for g in analysis["gates"].values()),
            "xor2_only_eligible_count":len(analysis["legacy_eligible"]),"mixed_eligible_count":len(analysis["mixed_eligible"]),
            "newly_opened_nets":sorted(set(analysis["mixed_eligible"])-set(analysis["legacy_eligible"])),
            "solver":sol,"resource_guard":resource_guard,"changed_cells":targets,"changed_cell_count":len(targets),
            "candidate_xnor2_count":sum(g["polarity"] ^ phase.get(g["output"],0) ^ (sum(phase.get(n,0) for n in g["inputs"])&1) for g in analysis["gates"].values() if g["arity"]==2),
            "candidate_xnor3_count":sum(g["polarity"] ^ phase.get(g["output"],0) ^ (sum(phase.get(n,0) for n in g["inputs"])&1) for g in analysis["gates"].values() if g["arity"]==3),
            "candidate_total_xnor_count":sol["best_total_xnor_count"],"phase_one_nets":sol["phase_one_nets"],"whole_graph_pure_check":check,
            "mapped_cell_count":len(analysis["cells"]),"parity_gate_count":len(analysis["gates"]),
            "protected_boundary":{"ports":analysis["ports"],"assigned_internal_nets":analysis["assigned_internal_nets"]},
            "limitations":"Pure Liberty-function/GF2 graph check only; no SAT/formal equivalence, place, route, activity, or PPA. Heuristic objective result is not an optimality certificate.",
            "pinned_parity_cell_specs":{k:v for k,v in catalog.items() if k in {"sky130_fd_sc_hd__xor3_1","sky130_fd_sc_hd__xnor3_1","sky130_fd_sc_hd__xor2_1","sky130_fd_sc_hd__xnor2_1"}},
            "route":"NOT_RUN","formal_equivalence":"NOT_RUN","PPA":"NOT_RUN"}
    (args.output_dir/"result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({k:result[k] for k in ("parent_graph_sha256","candidate_graph_sha256","xor2_only_eligible_count","mixed_eligible_count","newly_opened_nets","mixed_total_baseline_xnor_count","candidate_total_xnor_count","changed_cell_count","whole_graph_pure_check")},sort_keys=True))

if __name__=="__main__":main()
