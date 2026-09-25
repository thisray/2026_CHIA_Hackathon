#!/usr/bin/env python3
"""Remote full-netlist structural GF2 checker for fixed W32 mixed-phase candidates."""
import collections,hashlib,importlib.util,json,pathlib,sys
art=pathlib.Path(sys.argv[1]); source=art/"inputs/w32_mixed_arity_phase.py"
spec=importlib.util.spec_from_file_location("w32mixed",source);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
parent=art/"inputs/parent_c6_routed.v";libpath=art/"inputs/sky130_fd_sc_hd__tt_025C_1v80.lib";lefpath=art/"inputs/sky130_fd_sc_hd.lef"
lib=mod.parse_liberty(libpath);lef=mod.parse_lef(lefpath);catalog=mod.master_catalog(lib,lef);before=parent.read_text();graph=mod.build_inventory(before,lib,mod.sha(parent))
def canonical_sha(value):
 return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def cellmap(parsed):
 return {n:{"cell":v["master"],"pins":dict(sorted(v["pins"].items()))} for n,v in sorted(parsed["cells"].items())}
def parity_counts(parsed):
 return dict(sorted(collections.Counter(g["master"] for g in parsed["gates"].values()).items()))
def parity_area(parsed):
 return round(sum(lib[spec["master"]]["area_um2"] for spec in parsed["cells"].values()
                  if mod.classify_parity(spec["master"],lib[spec["master"]]) is not None),6)
def check(name,candidate_path,phase_nets,expected_candidate_sha,expected_cellmap_sha=None):
 phase={n:0 for n in graph["mixed_eligible"]}
 for n in phase_nets:
  if n not in phase:raise AssertionError(f"{name}: phase net is outside exact mixed closure: {n}")
  phase[n]=1
 expected,targets=mod.rewrite(before,graph,phase,catalog)
 child_path=pathlib.Path(candidate_path);child=child_path.read_text()
 if expected!=child:raise AssertionError(f"{name}: child bytes do not match exact phase vector")
 if mod.sha(child_path)!=expected_candidate_sha:raise AssertionError(f"{name}: candidate hash mismatch")
 pure=mod.structural_check(before,child,graph,phase,targets,lib,catalog)
 before_graph=mod.parse_cells(before,lib)[0];after_graph=mod.parse_cells(child,lib)[0]
 before_map=cellmap(before_graph);after_map=cellmap(after_graph)
 map_sha=canonical_sha(after_map)
 if expected_cellmap_sha and map_sha!=expected_cellmap_sha:raise AssertionError(f"{name}: full-map SHA mismatch")
 bcounts=parity_counts(before_graph);acounts=parity_counts(after_graph)
 result={"name":name,"status":"PASS","parent_graph_sha256":mod.sha(parent),"candidate_graph_sha256":mod.sha(child_path),
  "candidate_path":str(child_path),"cell_count_before":len(before_map),"cell_count_after":len(after_map),
  "parent_cellmap_sha256":canonical_sha(before_map),"candidate_cellmap_sha256":map_sha,
  "parity_master_counts_before":bcounts,"parity_master_counts_after":acounts,
  "parity_area_um2_before":parity_area(before_graph),"parity_area_um2_after":parity_area(after_graph),
  "parity_area_delta_um2":round(parity_area(after_graph)-parity_area(before_graph),6),
  "phase_one_nets":sorted(phase_nets),"changed_cells":targets,"changed_cell_count":len(targets),
  "ports":before_graph["ports"],"assigns_unchanged":True,"whole_graph_pure_check":pure,
  "formal_equivalence":"NOT_RUN","route":"NOT_RUN","PPA":"NOT_RUN"}
 return result
phase003=check("phase003_singleton",art/"proposal_phase003_mixed_unrouted.v",["_003_"],"8e5b08be4e99d6f34e2fc0afea284f7d99ec7d6fdca5104907300c40a8dcbdd3","a31af6c371b8ff5a5d31c87d7fe3365d7861bdedf59c5b6a5944455b1704c54f")
progress=json.loads((art/"solver-retry-01/progress/worker-1/best_progress.json").read_text())
best=check("two_worker_search_best",art/"solver-retry-01/candidate_c6_mixed_phase_unrouted.v",progress["phase_one_nets"],"2a2873494f4d097e9e33786de3db0681e22e62a5e480f7407b1a5e59870acb28")
solver_result={"selected_worker":1,"workers":2,"seeds":[2026092401,2026092402],"budget_wall_seconds_each":22,
 "hard_container_wall_seconds":35,"docker_cpu_limit":2,"docker_memory_limit_bytes":8589934592,
 "worker_1_best":progress,"worker_2_best":json.loads((art/"solver-retry-01/progress/worker-2/best_progress.json").read_text()),
 "solver_process_exit_code":int((art/"solver-retry-01/solver.exit-code").read_text().strip()),
 "serialization_error":"Final result serialization failed after candidate/checkpoint writes: Circular reference detected. Candidate and per-worker best progress were preserved and independently rederived here; no solver rerun."}
(art/"remote_check_phase003.json").write_text(json.dumps(phase003,indent=2,sort_keys=True)+"\n")
(art/"remote_check_searchbest.json").write_text(json.dumps(best,indent=2,sort_keys=True)+"\n")
(art/"search_retry_receipt.json").write_text(json.dumps(solver_result,indent=2,sort_keys=True)+"\n")
print(json.dumps({"phase003":{k:phase003[k] for k in ("status","candidate_graph_sha256","candidate_cellmap_sha256","parity_master_counts_after","parity_area_delta_um2","changed_cell_count")},
 "search_best":{k:best[k] for k in ("status","candidate_graph_sha256","candidate_cellmap_sha256","parity_master_counts_after","parity_area_delta_um2","changed_cell_count","phase_one_nets")},
 "search_attempt":{"exit_code":solver_result["solver_process_exit_code"],"workers":2}},sort_keys=True))
