// recipe_ecc_v3 measurement testbench.
//
// The device under test is the *pinned T01 wrapper* familyrtl_ecc_ppa, taken
// from the very mapped netlist T01 accepted. recipe_ecc_v3 deliberately owns no
// wrapper of its own: measuring a different top would make every netlist hash
// comparison against T01 structurally impossible and therefore meaningless.
//
// The time unit is 1 ps so that every reported timestamp is an exact integer and
// a 10 ns vector interval can never be reported as a 1 ns interval.
`timescale 1ps/1ps
`ifndef ECC_V3_DATA_WIDTH
`define ECC_V3_DATA_WIDTH 32
`endif
`ifndef ECC_V3_PARITY_WIDTH
`define ECC_V3_PARITY_WIDTH 6
`endif
`ifndef ECC_V3_CODEWORD_WIDTH
`define ECC_V3_CODEWORD_WIDTH 38
`endif
`ifndef ECC_V3_MAX_VECTORS
`define ECC_V3_MAX_VECTORS 65536
`endif

module ecc_v3_tb;
  localparam integer DataWidth = `ECC_V3_DATA_WIDTH;
  localparam integer ParityWidth = `ECC_V3_PARITY_WIDTH;
  localparam integer CodeWordWidth = `ECC_V3_CODEWORD_WIDTH;
  localparam integer EncodedWidth = CodeWordWidth + 1;
  localparam integer MaxVectors = `ECC_V3_MAX_VECTORS;

  logic [EncodedWidth-1:0] data_i;
  wire [DataWidth-1:0] data_o;
  wire [ParityWidth-1:0] syndrome_o;
  wire single_error_o;
  wire parity_error_o;
  wire double_error_o;

  logic [EncodedWidth-1:0] stimulus [0:MaxVectors-1];
  string workload_path;
  string vcd_path;
  string profile_name;
  integer expected_completions;
  integer interval_ps;
  integer sample_index;
  integer completed_count;
  integer mismatch_count;
  // 64-bit time accumulators: a 32-bit `integer` overflows at 2.147 ms, which is
  // only 214k vectors at 10 ns. A silent wrap would corrupt the measured window.
  longint measurement_start_ps;
  longint measurement_end_ps;
  longint measured_window_ps;
  longint declared_window_ps;
  longint interval_ps_wide;

  familyrtl_ecc_ppa dut (
    .data_i         (data_i),
    .data_o         (data_o),
    .syndrome_o     (syndrome_o),
    .single_error_o (single_error_o),
    .parity_error_o (parity_error_o),
    .double_error_o (double_error_o)
  );

  task automatic decode_reference(
    input logic [EncodedWidth-1:0] encoded_word,
    output logic [DataWidth-1:0] reference_data,
    output logic [ParityWidth-1:0] reference_syndrome,
    output logic reference_single_error,
    output logic reference_parity_error,
    output logic reference_double_error
  );
    logic [CodeWordWidth-1:0] corrected_codeword;
    logic overall_parity;
    integer parity_index;
    integer codeword_position;
    integer data_index;
    begin
      reference_syndrome = '0;
      for (parity_index = 0; parity_index < ParityWidth; parity_index = parity_index + 1) begin
        for (codeword_position = 1; codeword_position <= CodeWordWidth;
             codeword_position = codeword_position + 1) begin
          if ((codeword_position & (1 << parity_index)) != 0) begin
            reference_syndrome[parity_index] =
              reference_syndrome[parity_index] ^ encoded_word[codeword_position - 1];
          end
        end
      end
      overall_parity = ^encoded_word;
      corrected_codeword = encoded_word[CodeWordWidth-1:0];
      if ((reference_syndrome != 0) && (reference_syndrome <= CodeWordWidth)) begin
        corrected_codeword[reference_syndrome - 1] = ~corrected_codeword[reference_syndrome - 1];
      end
      reference_data = '0;
      data_index = 0;
      for (codeword_position = 1; codeword_position <= CodeWordWidth;
           codeword_position = codeword_position + 1) begin
        if ((codeword_position & (codeword_position - 1)) != 0) begin
          reference_data[data_index] = corrected_codeword[codeword_position - 1];
          data_index = data_index + 1;
        end
      end
      reference_single_error = overall_parity && (reference_syndrome != 0);
      reference_parity_error = overall_parity && (reference_syndrome == 0);
      reference_double_error = !overall_parity && (reference_syndrome != 0);
    end
  endtask

  task automatic check_outputs;
    logic [DataWidth-1:0] reference_data;
    logic [ParityWidth-1:0] reference_syndrome;
    logic reference_single_error;
    logic reference_parity_error;
    logic reference_double_error;
    begin
      decode_reference(data_i, reference_data, reference_syndrome,
                       reference_single_error, reference_parity_error,
                       reference_double_error);
      // Case inequality: an undefined mapped output is a real mismatch, not a
      // free variable the checker may ignore.
      if (data_o !== reference_data) begin
        mismatch_count = mismatch_count + 1;
        $display("ECC_V3_MISMATCH sample=%0d output=data_o actual=%h expected=%h",
                 sample_index, data_o, reference_data);
      end
      if (syndrome_o !== reference_syndrome) begin
        mismatch_count = mismatch_count + 1;
        $display("ECC_V3_MISMATCH sample=%0d output=syndrome_o actual=%h expected=%h",
                 sample_index, syndrome_o, reference_syndrome);
      end
      if (single_error_o !== reference_single_error) begin
        mismatch_count = mismatch_count + 1;
        $display("ECC_V3_MISMATCH sample=%0d output=single_error_o actual=%b expected=%b",
                 sample_index, single_error_o, reference_single_error);
      end
      if (parity_error_o !== reference_parity_error) begin
        mismatch_count = mismatch_count + 1;
        $display("ECC_V3_MISMATCH sample=%0d output=parity_error_o actual=%b expected=%b",
                 sample_index, parity_error_o, reference_parity_error);
      end
      if (double_error_o !== reference_double_error) begin
        mismatch_count = mismatch_count + 1;
        $display("ECC_V3_MISMATCH sample=%0d output=double_error_o actual=%b expected=%b",
                 sample_index, double_error_o, reference_double_error);
      end
      if (mismatch_count != 0) begin
        $fatal(1, "ECC v3 independent reference mismatch");
      end
      completed_count = completed_count + 1;
    end
  endtask

  initial begin
    data_i = '0;
    completed_count = 0;
    mismatch_count = 0;
    expected_completions = 0;
    interval_ps = 0;
    if (!$value$plusargs("workload=%s", workload_path))
      $fatal(1, "ECC v3 testbench requires +workload=<hex stimulus file>");
    if (!$value$plusargs("vcd=%s", vcd_path))
      $fatal(1, "ECC v3 testbench requires +vcd=<output path>");
    if (!$value$plusargs("profile=%s", profile_name))
      $fatal(1, "ECC v3 testbench requires +profile=<profile name>");
    if (!$value$plusargs("expected=%d", expected_completions))
      $fatal(1, "ECC v3 testbench requires +expected=<vector count>");
    if (!$value$plusargs("interval_ps=%d", interval_ps))
      $fatal(1, "ECC v3 testbench requires +interval_ps=<vector interval in ps>");
    if (expected_completions < 1 || expected_completions > MaxVectors)
      $fatal(1, "ECC v3 expected completions out of range");
    if (interval_ps < 1)
      $fatal(1, "ECC v3 vector interval must be a positive integer number of ps");
    // Widened once so that completed x interval is evaluated in 64 bits and a
    // long run cannot wrap the declared window into a false match.
    interval_ps_wide = interval_ps;

    for (sample_index = 0; sample_index < MaxVectors; sample_index = sample_index + 1)
      stimulus[sample_index] = '0;
    $readmemh(workload_path, stimulus);

    // Warm-up vector: a neutral predecessor ('0) applied and settled before the
    // measurement window opens, so that vector 0's transition is fully captured
    // inside the VCD and no initial-X transient is billed to the candidate.
    data_i = '0;
    #(interval_ps);

    $dumpfile(vcd_path);
    $dumpvars(0, dut);
    measurement_start_ps = $time;
    $display({"FAMILYRTL_ECC_V3_MEASUREMENT_START scope=ecc_v3_tb/dut profile=%0s width=%0d ",
              "interval_ps=%0d start_ps=%0d expected=%0d"},
             profile_name, DataWidth, interval_ps, measurement_start_ps, expected_completions);

    for (sample_index = 0; sample_index < expected_completions; sample_index = sample_index + 1) begin
      data_i = stimulus[sample_index];
      #(interval_ps);
      check_outputs();
    end

    // Force a VCD checkpoint at the closing edge of the window so that the last
    // VCD timestamp is the measured end time and never the last value change.
    // Without this the parser's window-vs-VCD equality check is off by one
    // vector interval whenever the final vector does not toggle anything.
    $dumpall;
    measurement_end_ps = $time;
    measured_window_ps = measurement_end_ps - measurement_start_ps;
    declared_window_ps = completed_count * interval_ps_wide;
    $display({"FAMILYRTL_ECC_V3_MEASUREMENT_END scope=ecc_v3_tb/dut profile=%0s width=%0d ",
              "interval_ps=%0d start_ps=%0d end_ps=%0d completed=%0d mismatches=%0d"},
             profile_name, DataWidth, interval_ps, measurement_start_ps, measurement_end_ps,
             completed_count, mismatch_count);
    if ((completed_count != expected_completions) || (mismatch_count != 0))
      $fatal(1, "ECC v3 workload did not complete exactly");
    if (measured_window_ps != declared_window_ps)
      $fatal(1, "ECC v3 measured window does not match completed work times the interval");
    $display({"FAMILYRTL_ECC_V3_COMPLETE scope=ecc_v3_tb/dut profile=%0s width=%0d ",
              "interval_ps=%0d start_ps=%0d end_ps=%0d completed=%0d expected=%0d ",
              "mismatches=%0d reference=independent_secded"},
             profile_name, DataWidth, interval_ps, measurement_start_ps, measurement_end_ps,
             completed_count, expected_completions, mismatch_count);
    $finish;
  end
endmodule
