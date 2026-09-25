set_thread_count 2
set liberty /foss/pdks/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
set rcx_rules /foss/pdks/sky130A/libs.tech/librelane/rules.openrcx.sky130A.nom.spef_extractor
set_units -time ns -capacitance pF -voltage V -power W
read_db /artifacts/eco_pre_route.odb
read_liberty $liberty
create_clock -name virtual_clock -period 2.575
set_input_delay 0.0 -clock virtual_clock [all_inputs]
set_output_delay 0.0 -clock virtual_clock [all_outputs]
set_input_transition 0.05 [all_inputs]
set_load 0.005 [all_outputs]
set_max_delay 2.575 -from [all_inputs] -to [all_outputs]
puts "CHIA_PHASE_ASSIGNMENT_ROUTING_SDC 2.575 0.05 0.005"
set block [ord::get_db_block]
set cleared 0
foreach net [$block getNets] {
  if {[$net isSpecial] || [$net getSigType] ne "SIGNAL"} { continue }
  set wire [$net getWire]
  if {$wire ne "NULL"} {
    odb::dbWire_destroy $wire
    incr cleared
  }
}
set remaining 0
foreach net [$block getNets] {
  if {[$net isSpecial] || [$net getSigType] ne "SIGNAL"} { continue }
  if {[$net getWire] ne "NULL"} { incr remaining }
}
if {$remaining != 0} { error "old signal wires still remaining: $remaining" }
puts "CHIA_PHASE_ASSIGNMENT_OLD_SIGNAL_WIRES_CLEARED $cleared"
check_placement -verbose -disallow_one_site_gaps -report_file_name /artifacts/post_power_placement_check.rpt
puts "CHIA_PHASE_ASSIGNMENT_PLACEMENT_CHECKED"
set_wire_rc -signal -layer met2
set_wire_rc -clock -layer met3
set_routing_layers -signal met1-met5 -clock met2-met5
set_global_routing_layer_adjustment met1-met5 0.50
global_route -guide_file /artifacts/eco_route.guide -congestion_iterations 30 -congestion_report_file /artifacts/eco_congestion.rpt -resistance_aware
puts "CHIA_PHASE_ASSIGNMENT_GRT_COMPLETE"
detailed_route -output_drc /artifacts/eco_route_drc.rpt -output_guide_coverage /artifacts/eco_guide_coverage.rpt -or_seed 20260921
set new_wires 0
foreach net [$block getNets] {
  if {[$net isSpecial] || [$net getSigType] ne "SIGNAL"} { continue }
  if {[$net getWire] ne "NULL"} { incr new_wires }
}
if {$new_wires == 0} { error "detailed route created 0 signal wires" }
write_verilog /artifacts/routed.v
write_db /artifacts/routed.odb
write_def /artifacts/routed_placement.def
report_design_area
set_extraction_rules_file $rcx_rules
extract_parasitics -corner 0
write_spef /artifacts/routed.spef
puts "CHIA_PHASE_ASSIGNMENT_RCX_COMPLETE"
