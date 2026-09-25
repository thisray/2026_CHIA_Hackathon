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
puts CHIA_W32_MIXED_ORIGINAL_EXTRACTED_BEGIN
report_checks -path_delay max -format full -digits 6
report_design_area
puts CHIA_W32_MIXED_ORIGINAL_EXTRACTED_END

if {![info exists ::env(CHIA_W32_MIXED_TARGET_COUNT)] ||
    ![string is integer -strict $::env(CHIA_W32_MIXED_TARGET_COUNT)]} {
  error "W32 mixed target count missing"
}
if {![info exists ::env(CHIA_W32_MIXED_DB_AREA_DELTA)] ||
    ![string is integer -strict $::env(CHIA_W32_MIXED_DB_AREA_DELTA)]} {
  error "W32 mixed expected DB area delta missing"
}
set expected_count $::env(CHIA_W32_MIXED_TARGET_COUNT)
set expected_delta $::env(CHIA_W32_MIXED_DB_AREA_DELTA)
if {$expected_count < 1 || $expected_count > 95} {
  error "W32 mixed target count outside fixed parity family"
}

set master_specs [dict create   sky130_fd_sc_hd__xor2_1  [list 2 1 X 3220 2720]   sky130_fd_sc_hd__xnor2_1 [list 2 1 Y 3220 2720]   sky130_fd_sc_hd__xor3_1  [list 3 1 X 8740 2720]   sky130_fd_sc_hd__xnor3_1 [list 3 1 X 8280 2720]]
set opposites [dict create   sky130_fd_sc_hd__xor2_1 sky130_fd_sc_hd__xnor2_1   sky130_fd_sc_hd__xnor2_1 sky130_fd_sc_hd__xor2_1   sky130_fd_sc_hd__xor3_1 sky130_fd_sc_hd__xnor3_1   sky130_fd_sc_hd__xnor3_1 sky130_fd_sc_hd__xor3_1]

set handle [open /artifacts/targets.tsv r]
set contents [read $handle]
close $handle
set rows [list]
set target_names [dict create]
foreach line [split $contents "
"] {
  if {[string trim $line] eq ""} { continue }
  set fields [split $line "	"]
  if {[llength $fields] != 5} { error "invalid W32 mixed target row" }
  set name [lindex $fields 0]
  if {![regexp {^_[0-9]+_$} $name] || [dict exists $target_names $name]} {
    error "unsafe or duplicate W32 mixed target name"
  }
  dict set target_names $name 1
  lappend rows $fields
}
if {[llength $rows] != $expected_count} {
  error "W32 mixed target count differs from exact manifest"
}

proc mixed_block_area {block} {
  set area 0
  foreach inst [$block getInsts] {
    set master [$inst getMaster]
    set area [expr {$area + [$master getWidth] * [$master getHeight]}]
  }
  return $area
}

set db [ord::get_db]
set block [ord::get_db_block]
set instance_count_before [llength [$block getInsts]]
set design_area_before [mixed_block_area $block]
set masters_before [dict create]
foreach inst [$block getInsts] {
  dict set masters_before [$inst getName] [[$inst getMaster] getName]
}
set target_area_before 0

foreach row $rows {
  lassign $row name old_name new_name old_out new_out
  if {![dict exists $master_specs $old_name] ||
      ![dict exists $master_specs $new_name] ||
      [dict get $opposites $old_name] ne $new_name} {
    error "W32 mixed master transition outside finite same-drive parity family"
  }
  lassign [dict get $master_specs $old_name] old_arity old_drive expected_old_out old_width old_height
  lassign [dict get $master_specs $new_name] new_arity new_drive expected_new_out new_width new_height
  if {$old_arity != $new_arity || $old_drive != $new_drive ||
      $old_out ne $expected_old_out || $new_out ne $expected_new_out ||
      $old_height != $new_height} {
    error "W32 mixed arity/drive/output/height guard failed"
  }
  set old_master [$db findMaster $old_name]
  set new_master [$db findMaster $new_name]
  if {$old_master eq "NULL" || $new_master eq "NULL" ||
      [$old_master getWidth] != $old_width || [$new_master getWidth] != $new_width ||
      [$old_master getHeight] != $old_height || [$new_master getHeight] != $new_height} {
    error "W32 mixed pinned LEF geometry differs"
  }
  set inst [$block findInst $name]
  if {$inst eq "NULL" || [[$inst getMaster] getName] ne $old_name} {
    error "W32 mixed target old instance/master mismatch"
  }
  set target_area_before [expr {$target_area_before + $old_width * $old_height}]
  set pins [list A B]
  if {$old_arity == 3} { lappend pins C }
  set saved_nets [dict create]
  foreach pin [concat $pins [list $old_out]] {
    set iterm [$inst findITerm $pin]
    if {$iterm eq "NULL" || [$iterm getNet] eq "NULL"} {
      error "W32 mixed target pin/net missing"
    }
    dict set saved_nets $pin [$iterm getNet]
  }
  lassign [$inst getLocation] loc_x loc_y
  set orient [$inst getOrient]
  set status [$inst getPlacementStatus]
  odb::dbInst_destroy $inst
  set new_inst [odb::dbInst_create $block $new_master $name]
  if {$new_inst eq "NULL"} { error "W32 mixed replacement instance creation failed" }
  $new_inst setOrient $orient
  $new_inst setLocation $loc_x $loc_y
  $new_inst setPlacementStatus $status
  foreach pin $pins {
    [$new_inst findITerm $pin] connect [dict get $saved_nets $pin]
  }
  [$new_inst findITerm $new_out] connect [dict get $saved_nets $old_out]
}

set target_area_after 0
foreach row $rows {
  lassign $row name old_name new_name old_out new_out
  set inst [$block findInst $name]
  if {$inst eq "NULL" || [[$inst getMaster] getName] ne $new_name} {
    error "W32 mixed target replacement mismatch"
  }
  set master [$inst getMaster]
  set target_area_after [expr {$target_area_after + [$master getWidth] * [$master getHeight]}]
}
set design_area_after [mixed_block_area $block]
if {$target_area_after - $target_area_before != $expected_delta ||
    $design_area_after - $design_area_before != $expected_delta} {
  error "W32 mixed target/design DB area delta differs from exact phase plan"
}
if {[llength [$block getInsts]] != $instance_count_before} {
  error "W32 mixed ECO changed complete instance count"
}
foreach inst [$block getInsts] {
  set name [$inst getName]
  set master_name [[$inst getMaster] getName]
  if {![dict exists $target_names $name] &&
      $master_name ne [dict get $masters_before $name]} {
    error "W32 mixed ECO changed a non-target master"
  }
}
puts "CHIA_W32_MIXED_AREA_CHECK $target_area_before $target_area_after $design_area_before $design_area_after"
puts CHIA_W32_MIXED_TARGETS_INSTALLED

detailed_placement -max_displacement {25 10} -disallow_one_site_gaps
check_placement -verbose -disallow_one_site_gaps
puts CHIA_W32_MIXED_DPL_LEGALIZATION_COMPLETE

write_verilog /artifacts/eco_pre_route.v
write_db /artifacts/eco_pre_route.odb
write_def /artifacts/eco_placement.def
puts CHIA_W32_MIXED_COMPLETE
