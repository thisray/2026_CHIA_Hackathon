# Supplemental power and connectivity in the already loaded VCD/SPEF context.
# OpenSTA does not expose raw toggle counts or a distinct glitch component here.
set cells [get_cells -hierarchical *]
report_power -instances $cells -digits 12 -format json > /artifacts/current_instance_power.json
set mapping_file [open /artifacts/current_instance_pin_nets.tsv w]
puts $mapping_file "instance\tliberty_cell\tpin\tnet"
foreach cell $cells {
  set instance_name [get_full_name $cell]
  set liberty_object [lindex [get_lib_cells -of_objects $cell] 0]
  set liberty_name "UNKNOWN"
  if {$liberty_object ne "" && $liberty_object ne "NULL"} {
    if {[catch {get_full_name $liberty_object} resolved_liberty] == 0} {
      set liberty_name $resolved_liberty
    }
  }
  set pins [get_pins -of_objects $cell]
  if {$pins eq "" || $pins eq "NULL"} {continue}
  foreach pin $pins {
    if {$pin eq "" || $pin eq "NULL"} {continue}
    set net_object [lindex [get_nets -of_objects $pin] 0]
    set net_name "UNCONNECTED"
    if {$net_object ne "" && $net_object ne "NULL"} {
      if {[catch {get_full_name $net_object} resolved_net] == 0} {
        set net_name $resolved_net
      }
    }
    puts $mapping_file "$instance_name\t$liberty_name\t[get_full_name $pin]\t$net_name"
  }
}
close $mapping_file
puts "FAMILYRTL_ECC_INSTANCE_POWER_DIAGNOSTIC_COMPLETE"
