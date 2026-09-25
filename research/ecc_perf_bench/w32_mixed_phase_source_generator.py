#!/usr/bin/env python3
"""Emit one exact c6 single-net mixed-parity proposal and its proof obligations."""
import importlib.util,json,hashlib,pathlib,sys
root=pathlib.Path(sys.argv[1]); source=pathlib.Path(sys.argv[2])
spec=importlib.util.spec_from_file_location("w32mixed",source);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
parent=root/"inputs/parent_c6_routed.v";lib_path=root/"inputs/sky130_fd_sc_hd__tt_025C_1v80.lib";lef_path=root/"inputs/sky130_fd_sc_hd.lef"
expected="c6c10558e367fd345b17c3b1a70898ddb8bcca9414833f0fcb34e7fd83478d95"
assert mod.sha(parent)==expected
lib=mod.parse_liberty(lib_path);lef=mod.parse_lef(lef_path);catalog=mod.master_catalog(lib,lef);before=parent.read_text();analysis=mod.build_inventory(before,lib,expected)
phase={net:0 for net in analysis["mixed_eligible"]};phase["_003_"]=1
candidate,targets=mod.rewrite(before,analysis,phase,catalog)
check=mod.structural_check(before,candidate,analysis,phase,targets,lib,catalog)
out=root/"proposal_phase003_mixed_unrouted.v";out.write_text(candidate)
parent_parsed=mod.parse_cells(before,lib)[0];candidate_parsed=mod.parse_cells(candidate,lib)[0]
def cellmap(graph):
    return {inst:{"cell":spec["master"],"pins":dict(sorted(spec["pins"].items()))} for inst,spec in sorted(graph["cells"].items())}
def canonical_sha(value):
    data=json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    return hashlib.sha256(data).hexdigest()
def masters(graph):
    return dict(sorted(__import__("collections").Counter(spec["master"] for spec in graph["cells"].values()).items()))
def parity_masters(graph):
    return dict(sorted(__import__("collections").Counter(g["master"] for g in graph["gates"].values()).items()))
oldmap=cellmap(parent_parsed);newmap=cellmap(candidate_parsed)
assert len(oldmap)==len(newmap)==148
assert parent_parsed["ports"]==candidate_parsed["ports"]
assert parent_parsed["assigned_internal_nets"]==candidate_parsed["assigned_internal_nets"]
cellmap_path=root/"expected_cell_map.json";cellmap_path.write_text(json.dumps(newmap,sort_keys=True,separators=(",",":"))+"\n")
target_specs={}
for inst,spec in targets.items():
    target_specs[inst]={"instance":inst,"old_master":spec["old_master"],"new_master":spec["new_master"],
       "old_output_pin":spec["old_output_pin"],"new_output_pin":spec["new_output_pin"],"output_net":spec["old_output_net"],
       "arity":spec["arity"],"drive":spec["drive"],"input_nets":spec["input_nets"],
       "old_pins":parent_parsed["cells"][inst]["pins"],"new_pins":candidate_parsed["cells"][inst]["pins"]}
# Exact master areas from Liberty for parity cells.
def parity_area(graph):
    return sum(lib[spec["master"]]["area_um2"] for spec in graph["cells"].values() if mod.classify_parity(spec["master"],lib[spec["master"]]) is not None)
manifest={"schema":"w32.mixed_arity_phase_proposal.v1","proposal_id":"phase003_xor3_absorb_singleton_v1",
 "parent_id":"c6c10558","parent_graph_sha256":expected,"parent_path":"inputs/parent_c6_routed.v",
 "candidate_path":out.name,"candidate_graph_sha256":mod.sha(out),"library_path":"inputs/sky130_fd_sc_hd__tt_025C_1v80.lib",
 "library_sha256":mod.sha(lib_path),"lef_path":"inputs/sky130_fd_sc_hd.lef","lef_sha256":mod.sha(lef_path),
 "source_kernel":"inputs/w32_mixed_arity_phase.py","source_kernel_sha256":mod.sha(source),
 "generator_path":"inputs/generate_phase003.py","generator_sha256":mod.sha(root/"inputs/generate_phase003.py"),
 "phase_law":"b_prime = b xor z(output) xor parity(z(inputs)); XOR2/XNOR2 and XOR3/XNOR3 truth functions are classified from the pinned Liberty table.",
 "closure":"Only internal single-driver nets driven by an exact XOR2/XNOR2/XOR3/XNOR3 cell, not a port/assign boundary, and whose every sink is a parity input pin of an exact XOR2/XNOR2/XOR3/XNOR3 cell can receive phase 1.",
 "phase_one_nets":["_003_"],"phase_vector":{"_003_":1},"eligible_counts":{"xor2_only":len(analysis["legacy_eligible"]),"mixed_arity":len(analysis["mixed_eligible"]),"additional_variables":len(set(analysis["mixed_eligible"])-set(analysis["legacy_eligible"]))},
 "expected_cell_map":{"path":cellmap_path.name,"schema":"JSON mapping instance->{cell,pins}; keys recursively sorted, UTF-8, separators=(',',':'), trailing newline excluded from SHA","cell_count":len(newmap),"sha256":canonical_sha(newmap)},
 "parent_cell_map_sha256":canonical_sha(oldmap),"parent_cell_count":len(oldmap),
 "parent_parity_master_counts":parity_masters(parent_parsed),"candidate_parity_master_counts":parity_masters(candidate_parsed),
 "all_parent_master_counts":masters(parent_parsed),"all_candidate_master_counts":masters(candidate_parsed),
 "baseline_parity_cell_area_um2":round(parity_area(parent_parsed),6),"candidate_parity_cell_area_um2":round(parity_area(candidate_parsed),6),
 "parity_cell_area_delta_um2":round(parity_area(candidate_parsed)-parity_area(parent_parsed),6),
 "target_specs":target_specs,"ports":parent_parsed["ports"],"continuous_assign_internal_nets":parent_parsed["assigned_internal_nets"],
 "pure_checker":{"GB10_status":check["status"],"GB10_details":check,"GCP02_status":"PENDING","structural_validation_contract":"Exact ports and assigns, complete 148-entry cell map and all pin nets; only listed same-drive parity master/output-pin rewrites; per-gate GF2 phase law; all other cells unchanged."},
 "formal_equivalence":"NOT_RUN","route":"NOT_RUN","PPA":"NOT_RUN","candidate_selection":"One of 56 one-net phase vectors; exact parity-cell area first, XNOR2 count as tie-break, then changed-cell count and net name. Not a global optimum claim."}
(root/"proposal.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
print(json.dumps({"parent_graph_sha256":expected,"candidate_graph_sha256":manifest["candidate_graph_sha256"],"cellmap_sha256":manifest["expected_cell_map"]["sha256"],"cell_count":len(newmap),"changed_cells":target_specs,"parent_parity_counts":manifest["parent_parity_master_counts"],"candidate_parity_counts":manifest["candidate_parity_master_counts"],"area_delta_um2":manifest["parity_cell_area_delta_um2"],"check":check},sort_keys=True))
