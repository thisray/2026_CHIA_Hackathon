set_thread_count 2
set liberty /foss/pdks/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
set_units -time ns -capacitance pF -voltage V -power W
read_db /artifacts/original_routed.odb
read_liberty $liberty
write_def /artifacts/original_placement.def
create_clock -name virtual_clock -period 10.0
set_input_delay 0.0 -clock virtual_clock [all_inputs]
set_output_delay 0.0 -clock virtual_clock [all_outputs]
set_input_transition 0.05 [all_inputs]
set_load 0.005 [all_outputs]
set_max_delay 10.0 -from [all_inputs] -to [all_outputs]
read_spef /artifacts/original_routed.spef
puts CHIA_N02_XOR3_ORIGINAL_EXTRACTED_BEGIN
report_checks -path_delay max -format full -digits 6
report_design_area
puts CHIA_N02_XOR3_ORIGINAL_EXTRACTED_END

set db [ord::get_db]
set block [ord::get_db_block]
set handle [open /artifacts/targets.tsv r]
set contents [read $handle]
close $handle
set rows [list]
foreach line [split $contents "
"] {
  if {[string trim $line] eq ""} { continue }
  set fields [split $line "	"]
  if {[llength $fields] != 5} { error "invalid N02 XOR3 target specification" }
  lappend rows $fields
}
if {[llength $rows] != 2} { error "N02 XOR3 requires exactly two fixed targets" }
set target_names [list]
foreach spec $rows { lappend target_names [lindex $spec 0] }
if {$target_names ne [list _326_ _328_]} { error "N02 XOR3 target set changed" }

proc n02_design_area {block} {
  set area 0
  foreach inst [$block getInsts] {
    set master [$inst getMaster]
    set area [expr {$area + [$master getWidth] * [$master getHeight]}]
  }
  return $area
}
set design_area_before [n02_design_area $block]
set pair_area_before 0
set prior_masters [dict create]
foreach inst [$block getInsts] {
  dict set prior_masters [$inst getName] [[$inst getMaster] getName]
}
set instance_count_before [llength [$block getInsts]]

foreach spec $rows {
  lassign $spec inst_name old_name new_name old_out new_out
  if {$old_out ne "X" || $new_out ne "X"} { error "$inst_name output pin changed" }
  if {$inst_name eq "_326_"} {
    if {$old_name ne "sky130_fd_sc_hd__xor3_1" || $new_name ne "sky130_fd_sc_hd__xnor3_1"} {
      error "_326_ N02 XOR3 action changed"
    }
    set expected_old_width 8740
    set expected_new_width 8280
  } elseif {$inst_name eq "_328_"} {
    if {$old_name ne "sky130_fd_sc_hd__xor3_2" || $new_name ne "sky130_fd_sc_hd__xnor3_2"} {
      error "_328_ N02 XOR3 action changed"
    }
    set expected_old_width 9200
    set expected_new_width 8740
  } else { error "unsupported N02 XOR3 target $inst_name" }
  set old_master [$db findMaster $old_name]
  set new_master [$db findMaster $new_name]
  if {$old_master eq "NULL" || $new_master eq "NULL"} { error "$inst_name master missing" }
  if {[$old_master getWidth] != $expected_old_width || [$new_master getWidth] != $expected_new_width
      || [$old_master getHeight] != 2720 || [$new_master getHeight] != 2720} {
    error "$inst_name pinned DB width/height differs from Liberty/LEF evidence"
  }
  if {[expr {[$new_master getWidth] - [$old_master getWidth]}] != -460} {
    error "$inst_name width delta differs from -460 DBU"
  }
  set inst [$block findInst $inst_name]
  if {$inst eq "NULL" || [[$inst getMaster] getName] ne $old_name} {
    error "$inst_name old instance/master mismatch"
  }
  set pair_area_before [expr {$pair_area_before + [$old_master getWidth] * [$old_master getHeight]}]
  set a_net [[$inst findITerm A] getNet]
  set b_net [[$inst findITerm B] getNet]
  set c_net [[$inst findITerm C] getNet]
  set x_net [[$inst findITerm X] getNet]
  if {$a_net eq "NULL" || $b_net eq "NULL" || $c_net eq "NULL" || $x_net eq "NULL"} {
    error "$inst_name pin or net missing"
  }
  lassign [$inst getLocation] loc_x loc_y
  set orient [$inst getOrient]
  set status [$inst getPlacementStatus]
  odb::dbInst_destroy $inst
  set new_inst [odb::dbInst_create $block $new_master $inst_name]
  $new_inst setOrient $orient
  $new_inst setLocation $loc_x $loc_y
  $new_inst setPlacementStatus $status
  [$new_inst findITerm A] connect $a_net
  [$new_inst findITerm B] connect $b_net
  [$new_inst findITerm C] connect $c_net
  [$new_inst findITerm X] connect $x_net
}

set pair_area_after 0
foreach inst_name [list _326_ _328_] {
  set inst [$block findInst $inst_name]
  set master [$inst getMaster]
  set pair_area_after [expr {$pair_area_after + [$master getWidth] * [$master getHeight]}]
}
set design_area_after [n02_design_area $block]
if {$pair_area_before != 48796800 || $pair_area_after != 46294400
    || [expr {$pair_area_after - $pair_area_before}] != -2502400} {
  error "N02 XOR3 pair DB area does not shrink by exact 2502400 DBU2"
}
if {[expr {$design_area_after - $design_area_before}] != -2502400} {
  error "N02 XOR3 whole DB area delta differs from target pair"
}
if {[llength [$block getInsts]] != $instance_count_before} {
  error "N02 XOR3 ECO changed instance count"
}
foreach inst [$block getInsts] {
  set name [$inst getName]
  set master_name [[$inst getMaster] getName]
  if {$name eq "_326_"} {
    if {$master_name ne "sky130_fd_sc_hd__xnor3_1"} { error "_326_ replacement mismatch" }
  } elseif {$name eq "_328_"} {
    if {$master_name ne "sky130_fd_sc_hd__xnor3_2"} { error "_328_ replacement mismatch" }
  } elseif {$master_name ne [dict get $prior_masters $name]} {
    error "N02 XOR3 ECO changed non-target master: $name"
  }
}
puts "CHIA_N02_XOR3_AREA_CHECK $pair_area_before $pair_area_after $design_area_before $design_area_after"
puts CHIA_N02_XOR3_TARGETS_INSTALLED

detailed_placement -max_displacement {25 10} -disallow_one_site_gaps
check_placement -verbose -disallow_one_site_gaps -report_file_name /artifacts/n02_xor3_placement_check.rpt
puts CHIA_N02_XOR3_DPL_LEGALIZATION_COMPLETE

write_verilog /artifacts/eco_pre_route.v
write_db /artifacts/eco_pre_route.odb
write_def /artifacts/eco_placement.def
puts CHIA_N02_XOR3_COMPLETE
