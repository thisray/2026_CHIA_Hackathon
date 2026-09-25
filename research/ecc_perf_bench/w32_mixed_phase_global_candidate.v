module familyrtl_ecc_ppa (double_error_o,
    parity_error_o,
    single_error_o,
    data_i,
    data_o,
    syndrome_o);
 output double_error_o;
 output parity_error_o;
 output single_error_o;
 input [38:0] data_i;
 output [31:0] data_o;
 output [5:0] syndrome_o;

 wire _000_;
 wire _001_;
 wire _002_;
 wire _003_;
 wire _004_;
 wire _005_;
 wire _006_;
 wire _007_;
 wire _008_;
 wire _009_;
 wire _010_;
 wire _011_;
 wire _012_;
 wire _013_;
 wire _014_;
 wire _015_;
 wire _016_;
 wire _017_;
 wire _018_;
 wire _019_;
 wire _020_;
 wire _021_;
 wire _022_;
 wire _023_;
 wire _024_;
 wire _025_;
 wire _026_;
 wire _027_;
 wire _028_;
 wire _029_;
 wire _030_;
 wire _031_;
 wire _032_;
 wire _033_;
 wire _034_;
 wire _035_;
 wire _036_;
 wire _037_;
 wire _038_;
 wire _039_;
 wire _040_;
 wire _041_;
 wire _042_;
 wire _043_;
 wire _044_;
 wire _045_;
 wire _046_;
 wire _047_;
 wire _048_;
 wire _049_;
 wire _050_;
 wire _051_;
 wire _052_;
 wire _053_;
 wire _054_;
 wire _055_;
 wire _056_;
 wire _057_;
 wire _058_;
 wire _059_;
 wire _060_;
 wire _061_;
 wire _062_;
 wire _063_;
 wire _064_;
 wire _065_;
 wire _066_;
 wire _067_;
 wire _068_;
 wire _069_;
 wire _070_;
 wire _071_;
 wire _072_;
 wire _073_;
 wire _074_;
 wire _075_;
 wire _076_;
 wire _077_;
 wire _078_;
 wire _079_;
 wire _080_;
 wire _081_;
 wire _082_;
 wire _083_;
 wire _084_;
 wire _085_;
 wire _086_;
 wire _087_;
 wire _088_;
 wire _089_;
 wire _090_;
 wire _091_;
 wire _092_;
 wire _093_;
 wire _094_;
 wire _095_;
 wire _096_;
 wire _097_;
 wire _098_;
 wire _099_;
 wire _100_;
 wire _101_;
 wire _102_;
 wire _103_;
 wire _104_;
 wire _105_;
 wire _106_;

 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_0_Left_32 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_0_Right_0 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_10_Left_42 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_10_Right_10 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_11_Left_43 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_11_Right_11 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_12_Left_44 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_12_Right_12 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_13_Left_45 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_13_Right_13 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_14_Left_46 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_14_Right_14 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_15_Left_47 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_15_Right_15 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_16_Left_48 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_16_Right_16 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_17_Left_49 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_17_Right_17 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_18_Left_50 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_18_Right_18 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_19_Left_51 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_19_Right_19 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_1_Left_33 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_1_Right_1 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_20_Left_52 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_20_Right_20 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_21_Left_53 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_21_Right_21 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_22_Left_54 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_22_Right_22 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_23_Left_55 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_23_Right_23 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_24_Left_56 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_24_Right_24 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_25_Left_57 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_25_Right_25 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_26_Left_58 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_26_Right_26 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_27_Left_59 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_27_Right_27 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_28_Left_60 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_28_Right_28 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_29_Left_61 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_29_Right_29 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_2_Left_34 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_2_Right_2 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_30_Left_62 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_30_Right_30 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_31_Left_63 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_31_Right_31 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_3_Left_35 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_3_Right_3 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_4_Left_36 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_4_Right_4 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_5_Left_37 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_5_Right_5 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_6_Left_38 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_6_Right_6 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_7_Left_39 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_7_Right_7 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_8_Left_40 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_8_Right_8 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_9_Left_41 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_9_Right_9 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_0_64 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_0_65 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_0_66 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_0_67 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_0_68 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_0_69 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_10_97 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_10_98 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_10_99 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_11_100 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_11_101 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_11_102 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_12_103 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_12_104 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_12_105 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_13_106 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_13_107 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_13_108 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_14_109 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_14_110 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_14_111 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_15_112 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_15_113 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_15_114 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_16_115 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_16_116 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_16_117 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_17_118 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_17_119 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_17_120 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_18_121 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_18_122 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_18_123 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_19_124 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_19_125 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_19_126 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_1_70 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_1_71 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_1_72 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_20_127 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_20_128 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_20_129 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_21_130 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_21_131 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_21_132 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_22_133 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_22_134 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_22_135 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_23_136 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_23_137 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_23_138 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_24_139 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_24_140 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_24_141 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_25_142 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_25_143 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_25_144 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_26_145 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_26_146 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_26_147 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_27_148 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_27_149 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_27_150 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_28_151 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_28_152 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_28_153 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_29_154 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_29_155 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_29_156 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_2_73 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_2_74 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_2_75 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_30_157 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_30_158 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_30_159 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_31_160 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_31_161 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_31_162 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_31_163 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_31_164 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_31_165 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_3_76 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_3_77 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_3_78 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_4_79 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_4_80 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_4_81 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_5_82 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_5_83 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_5_84 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_6_85 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_6_86 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_6_87 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_7_88 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_7_89 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_7_90 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_8_91 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_8_92 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_8_93 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_9_94 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_9_95 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_9_96 ();
 sky130_fd_sc_hd__xor2_1 _107_ (.A(data_i[29]),
    .B(data_i[30]),
    .X(_089_));
 sky130_fd_sc_hd__xor2_1 _108_ (.A(data_i[21]),
    .B(data_i[22]),
    .X(_090_));
 sky130_fd_sc_hd__xor2_1 _109_ (.A(_089_),
    .B(_090_),
    .X(_091_));
 sky130_fd_sc_hd__xor2_1 _110_ (.A(data_i[25]),
    .B(data_i[26]),
    .X(_092_));
 sky130_fd_sc_hd__xor2_1 _111_ (.A(data_i[17]),
    .B(data_i[18]),
    .X(_093_));
 sky130_fd_sc_hd__xor2_1 _112_ (.A(_092_),
    .B(_093_),
    .X(_094_));
 sky130_fd_sc_hd__xor2_1 _113_ (.A(_091_),
    .B(_094_),
    .X(_095_));
 sky130_fd_sc_hd__xor2_1 _114_ (.A(data_i[23]),
    .B(data_i[24]),
    .X(_096_));
 sky130_fd_sc_hd__xor2_1 _115_ (.A(data_i[15]),
    .B(data_i[16]),
    .X(_097_));
 sky130_fd_sc_hd__xor2_1 _116_ (.A(_096_),
    .B(_097_),
    .X(_098_));
 sky130_fd_sc_hd__xor2_1 _117_ (.A(data_i[27]),
    .B(data_i[28]),
    .X(_099_));
 sky130_fd_sc_hd__xor2_1 _118_ (.A(data_i[19]),
    .B(data_i[20]),
    .X(_100_));
 sky130_fd_sc_hd__xor2_1 _119_ (.A(_099_),
    .B(_100_),
    .X(_101_));
 sky130_fd_sc_hd__xor2_1 _120_ (.A(_098_),
    .B(_101_),
    .X(_102_));
 sky130_fd_sc_hd__xor2_1 _121_ (.A(_095_),
    .B(_102_),
    .X(syndrome_o[4]));
 sky130_fd_sc_hd__xnor3_1 _122_ (.A(data_i[5]),
    .B(data_i[37]),
    .C(data_i[6]),
    .X(_103_));
 sky130_fd_sc_hd__xor2_1 _123_ (.A(data_i[13]),
    .B(data_i[14]),
    .X(_104_));
 sky130_fd_sc_hd__xor2_1 _124_ (.A(_103_),
    .B(_104_),
    .X(_105_));
 sky130_fd_sc_hd__xnor2_1 _125_ (.A(data_i[2]),
    .B(data_i[34]),
    .Y(_106_));
 sky130_fd_sc_hd__xor2_1 _126_ (.A(data_i[1]),
    .B(data_i[33]),
    .X(_000_));
 sky130_fd_sc_hd__xor2_1 _127_ (.A(_106_),
    .B(_000_),
    .X(_001_));
 sky130_fd_sc_hd__xor2_1 _128_ (.A(_105_),
    .B(_001_),
    .X(_002_));
 sky130_fd_sc_hd__xor2_1 _129_ (.A(data_i[9]),
    .B(data_i[10]),
    .X(_003_));
 sky130_fd_sc_hd__xnor3_1 _130_ (.A(_095_),
    .B(_002_),
    .C(_003_),
    .X(_004_));
 sky130_fd_sc_hd__clkinv_1 _131_ (.A(_004_),
    .Y(syndrome_o[1]));
 sky130_fd_sc_hd__xnor2_1 _132_ (.A(data_i[7]),
    .B(data_i[8]),
    .Y(_005_));
 sky130_fd_sc_hd__xor2_1 _133_ (.A(data_i[11]),
    .B(data_i[12]),
    .X(_006_));
 sky130_fd_sc_hd__xor2_1 _134_ (.A(_005_),
    .B(_006_),
    .X(_007_));
 sky130_fd_sc_hd__xor2_1 _135_ (.A(_104_),
    .B(_003_),
    .X(_008_));
 sky130_fd_sc_hd__xor2_1 _136_ (.A(_089_),
    .B(_092_),
    .X(_009_));
 sky130_fd_sc_hd__xor2_1 _137_ (.A(_096_),
    .B(_099_),
    .X(_010_));
 sky130_fd_sc_hd__xor2_1 _138_ (.A(_009_),
    .B(_010_),
    .X(_011_));
 sky130_fd_sc_hd__xnor3_1 _139_ (.A(_007_),
    .B(_008_),
    .C(_011_),
    .X(syndrome_o[3]));
 sky130_fd_sc_hd__xor2_1 _140_ (.A(_091_),
    .B(_101_),
    .X(_012_));
 sky130_fd_sc_hd__xnor3_1 _141_ (.A(data_i[4]),
    .B(data_i[36]),
    .C(data_i[12]),
    .X(_013_));
 sky130_fd_sc_hd__xnor3_1 _142_ (.A(data_i[3]),
    .B(data_i[35]),
    .C(data_i[11]),
    .X(_014_));
 sky130_fd_sc_hd__xor2_1 _143_ (.A(_013_),
    .B(_014_),
    .X(_015_));
 sky130_fd_sc_hd__xor2_1 _144_ (.A(_105_),
    .B(_015_),
    .X(_016_));
 sky130_fd_sc_hd__xor2_1 _145_ (.A(_012_),
    .B(_016_),
    .X(_017_));
 sky130_fd_sc_hd__clkinv_1 _146_ (.A(_017_),
    .Y(syndrome_o[2]));
 sky130_fd_sc_hd__xor2_1 _147_ (.A(data_i[34]),
    .B(data_i[37]),
    .X(_018_));
 sky130_fd_sc_hd__xor2_1 _148_ (.A(data_i[33]),
    .B(_018_),
    .X(_019_));
 sky130_fd_sc_hd__xor2_1 _149_ (.A(data_i[35]),
    .B(data_i[36]),
    .X(_020_));
 sky130_fd_sc_hd__xor2_1 _150_ (.A(data_i[31]),
    .B(data_i[32]),
    .X(_021_));
 sky130_fd_sc_hd__xor2_1 _151_ (.A(_020_),
    .B(_021_),
    .X(_022_));
 sky130_fd_sc_hd__xnor2_1 _152_ (.A(_019_),
    .B(_022_),
    .Y(_023_));
 sky130_fd_sc_hd__clkinv_1 _153_ (.A(_023_),
    .Y(syndrome_o[5]));
 sky130_fd_sc_hd__xor2_1 _154_ (.A(data_i[20]),
    .B(data_i[28]),
    .X(_024_));
 sky130_fd_sc_hd__xnor2_1 _155_ (.A(data_i[16]),
    .B(data_i[24]),
    .Y(_025_));
 sky130_fd_sc_hd__xor2_1 _156_ (.A(_024_),
    .B(_025_),
    .X(_026_));
 sky130_fd_sc_hd__xor2_1 _157_ (.A(data_i[32]),
    .B(data_i[0]),
    .X(_027_));
 sky130_fd_sc_hd__xor2_1 _158_ (.A(_026_),
    .B(_027_),
    .X(_028_));
 sky130_fd_sc_hd__xor2_1 _159_ (.A(data_i[8]),
    .B(_013_),
    .X(_029_));
 sky130_fd_sc_hd__xor2_1 _160_ (.A(data_i[22]),
    .B(data_i[30]),
    .X(_030_));
 sky130_fd_sc_hd__xor2_1 _161_ (.A(data_i[6]),
    .B(data_i[14]),
    .X(_031_));
 sky130_fd_sc_hd__xor2_1 _162_ (.A(_030_),
    .B(_031_),
    .X(_032_));
 sky130_fd_sc_hd__xor2_1 _163_ (.A(data_i[10]),
    .B(_106_),
    .X(_033_));
 sky130_fd_sc_hd__xor2_1 _164_ (.A(data_i[18]),
    .B(data_i[26]),
    .X(_034_));
 sky130_fd_sc_hd__xnor3_1 _165_ (.A(_032_),
    .B(_033_),
    .C(_034_),
    .X(_035_));
 sky130_fd_sc_hd__xnor3_1 _166_ (.A(_028_),
    .B(_029_),
    .C(_035_),
    .X(_036_));
 sky130_fd_sc_hd__clkinv_1 _167_ (.A(_036_),
    .Y(syndrome_o[0]));
 sky130_fd_sc_hd__or3_1 _168_ (.A(syndrome_o[4]),
    .B(syndrome_o[3]),
    .C(syndrome_o[5]),
    .X(_037_));
 sky130_fd_sc_hd__nand3_1 _169_ (.A(_004_),
    .B(_017_),
    .C(_036_),
    .Y(_038_));
 sky130_fd_sc_hd__nor2_1 _170_ (.A(_037_),
    .B(_038_),
    .Y(_039_));
 sky130_fd_sc_hd__xor2_1 _171_ (.A(data_i[0]),
    .B(_005_),
    .X(_040_));
 sky130_fd_sc_hd__xor2_1 _172_ (.A(_021_),
    .B(_040_),
    .X(_041_));
 sky130_fd_sc_hd__xor2_1 _173_ (.A(_102_),
    .B(_041_),
    .X(_042_));
 sky130_fd_sc_hd__xor2_1 _174_ (.A(data_i[38]),
    .B(_015_),
    .X(_043_));
 sky130_fd_sc_hd__xor2_1 _175_ (.A(_042_),
    .B(_043_),
    .X(_044_));
 sky130_fd_sc_hd__xor2_1 _176_ (.A(syndrome_o[1]),
    .B(_044_),
    .X(_045_));
 sky130_fd_sc_hd__nor2_1 _177_ (.A(_039_),
    .B(_045_),
    .Y(single_error_o));
 sky130_fd_sc_hd__nor3_1 _178_ (.A(_037_),
    .B(_038_),
    .C(_045_),
    .Y(parity_error_o));
 sky130_fd_sc_hd__nor2b_1 _179_ (.A(_039_),
    .B_N(_045_),
    .Y(double_error_o));
 sky130_fd_sc_hd__nand3_1 _180_ (.A(syndrome_o[1]),
    .B(_017_),
    .C(syndrome_o[0]),
    .Y(_046_));
 sky130_fd_sc_hd__nor2_1 _181_ (.A(_037_),
    .B(_046_),
    .Y(_047_));
 sky130_fd_sc_hd__xor2_1 _182_ (.A(data_i[2]),
    .B(_047_),
    .X(data_o[0]));
 sky130_fd_sc_hd__nand3_1 _183_ (.A(_004_),
    .B(syndrome_o[2]),
    .C(syndrome_o[0]),
    .Y(_048_));
 sky130_fd_sc_hd__nor2_1 _184_ (.A(_037_),
    .B(_048_),
    .Y(_049_));
 sky130_fd_sc_hd__xor2_1 _185_ (.A(data_i[4]),
    .B(_049_),
    .X(data_o[1]));
 sky130_fd_sc_hd__nand3_1 _186_ (.A(syndrome_o[1]),
    .B(syndrome_o[2]),
    .C(_036_),
    .Y(_050_));
 sky130_fd_sc_hd__nor2_1 _187_ (.A(_037_),
    .B(_050_),
    .Y(_051_));
 sky130_fd_sc_hd__xor2_1 _188_ (.A(data_i[5]),
    .B(_051_),
    .X(data_o[2]));
 sky130_fd_sc_hd__nand3_1 _189_ (.A(syndrome_o[1]),
    .B(syndrome_o[2]),
    .C(syndrome_o[0]),
    .Y(_052_));
 sky130_fd_sc_hd__nor2_1 _190_ (.A(_037_),
    .B(_052_),
    .Y(_053_));
 sky130_fd_sc_hd__xor2_1 _191_ (.A(data_i[6]),
    .B(_053_),
    .X(data_o[3]));
 sky130_fd_sc_hd__nand3_1 _192_ (.A(_004_),
    .B(_017_),
    .C(syndrome_o[0]),
    .Y(_054_));
 sky130_fd_sc_hd__nand3b_1 _193_ (.A_N(syndrome_o[4]),
    .B(syndrome_o[3]),
    .C(_023_),
    .Y(_055_));
 sky130_fd_sc_hd__nor2_1 _194_ (.A(_054_),
    .B(_055_),
    .Y(_056_));
 sky130_fd_sc_hd__xor2_1 _195_ (.A(data_i[8]),
    .B(_056_),
    .X(data_o[4]));
 sky130_fd_sc_hd__nand3_1 _196_ (.A(syndrome_o[1]),
    .B(_017_),
    .C(_036_),
    .Y(_057_));
 sky130_fd_sc_hd__nor2_1 _197_ (.A(_055_),
    .B(_057_),
    .Y(_058_));
 sky130_fd_sc_hd__xor2_1 _198_ (.A(data_i[9]),
    .B(_058_),
    .X(data_o[5]));
 sky130_fd_sc_hd__nor2_1 _199_ (.A(_046_),
    .B(_055_),
    .Y(_059_));
 sky130_fd_sc_hd__xor2_1 _200_ (.A(data_i[10]),
    .B(_059_),
    .X(data_o[6]));
 sky130_fd_sc_hd__nand3_1 _201_ (.A(_004_),
    .B(syndrome_o[2]),
    .C(_036_),
    .Y(_060_));
 sky130_fd_sc_hd__nor2_1 _202_ (.A(_055_),
    .B(_060_),
    .Y(_061_));
 sky130_fd_sc_hd__xor2_1 _203_ (.A(data_i[11]),
    .B(_061_),
    .X(data_o[7]));
 sky130_fd_sc_hd__nor2_1 _204_ (.A(_048_),
    .B(_055_),
    .Y(_062_));
 sky130_fd_sc_hd__xor2_1 _205_ (.A(data_i[12]),
    .B(_062_),
    .X(data_o[8]));
 sky130_fd_sc_hd__nor2_1 _206_ (.A(_050_),
    .B(_055_),
    .Y(_063_));
 sky130_fd_sc_hd__xor2_1 _207_ (.A(data_i[13]),
    .B(_063_),
    .X(data_o[9]));
 sky130_fd_sc_hd__nor2_1 _208_ (.A(_052_),
    .B(_055_),
    .Y(_064_));
 sky130_fd_sc_hd__xor2_1 _209_ (.A(data_i[14]),
    .B(_064_),
    .X(data_o[10]));
 sky130_fd_sc_hd__nand3b_1 _210_ (.A_N(syndrome_o[3]),
    .B(_023_),
    .C(syndrome_o[4]),
    .Y(_065_));
 sky130_fd_sc_hd__nor2_1 _211_ (.A(_054_),
    .B(_065_),
    .Y(_066_));
 sky130_fd_sc_hd__xor2_1 _212_ (.A(data_i[16]),
    .B(_066_),
    .X(data_o[11]));
 sky130_fd_sc_hd__nor2_1 _213_ (.A(_057_),
    .B(_065_),
    .Y(_067_));
 sky130_fd_sc_hd__xor2_1 _214_ (.A(data_i[17]),
    .B(_067_),
    .X(data_o[12]));
 sky130_fd_sc_hd__nor2_1 _215_ (.A(_046_),
    .B(_065_),
    .Y(_068_));
 sky130_fd_sc_hd__xor2_1 _216_ (.A(data_i[18]),
    .B(_068_),
    .X(data_o[13]));
 sky130_fd_sc_hd__nor2_1 _217_ (.A(_060_),
    .B(_065_),
    .Y(_069_));
 sky130_fd_sc_hd__xor2_1 _218_ (.A(data_i[19]),
    .B(_069_),
    .X(data_o[14]));
 sky130_fd_sc_hd__nor2_1 _219_ (.A(_048_),
    .B(_065_),
    .Y(_070_));
 sky130_fd_sc_hd__xor2_1 _220_ (.A(data_i[20]),
    .B(_070_),
    .X(data_o[15]));
 sky130_fd_sc_hd__nor2_1 _221_ (.A(_050_),
    .B(_065_),
    .Y(_071_));
 sky130_fd_sc_hd__xor2_1 _222_ (.A(data_i[21]),
    .B(_071_),
    .X(data_o[16]));
 sky130_fd_sc_hd__nor2_1 _223_ (.A(_052_),
    .B(_065_),
    .Y(_072_));
 sky130_fd_sc_hd__xor2_1 _224_ (.A(data_i[22]),
    .B(_072_),
    .X(data_o[17]));
 sky130_fd_sc_hd__nand3_1 _225_ (.A(syndrome_o[4]),
    .B(syndrome_o[3]),
    .C(_023_),
    .Y(_073_));
 sky130_fd_sc_hd__nor2_1 _226_ (.A(_038_),
    .B(_073_),
    .Y(_074_));
 sky130_fd_sc_hd__xor2_1 _227_ (.A(data_i[23]),
    .B(_074_),
    .X(data_o[18]));
 sky130_fd_sc_hd__nor2_1 _228_ (.A(_054_),
    .B(_073_),
    .Y(_075_));
 sky130_fd_sc_hd__xor2_1 _229_ (.A(data_i[24]),
    .B(_075_),
    .X(data_o[19]));
 sky130_fd_sc_hd__nor2_1 _230_ (.A(_057_),
    .B(_073_),
    .Y(_076_));
 sky130_fd_sc_hd__xor2_1 _231_ (.A(data_i[25]),
    .B(_076_),
    .X(data_o[20]));
 sky130_fd_sc_hd__nor2_1 _232_ (.A(_046_),
    .B(_073_),
    .Y(_077_));
 sky130_fd_sc_hd__xor2_1 _233_ (.A(data_i[26]),
    .B(_077_),
    .X(data_o[21]));
 sky130_fd_sc_hd__nor2_1 _234_ (.A(_060_),
    .B(_073_),
    .Y(_078_));
 sky130_fd_sc_hd__xor2_1 _235_ (.A(data_i[27]),
    .B(_078_),
    .X(data_o[22]));
 sky130_fd_sc_hd__nor2_1 _236_ (.A(_048_),
    .B(_073_),
    .Y(_079_));
 sky130_fd_sc_hd__xor2_1 _237_ (.A(data_i[28]),
    .B(_079_),
    .X(data_o[23]));
 sky130_fd_sc_hd__nor2_1 _238_ (.A(_050_),
    .B(_073_),
    .Y(_080_));
 sky130_fd_sc_hd__xor2_1 _239_ (.A(data_i[29]),
    .B(_080_),
    .X(data_o[24]));
 sky130_fd_sc_hd__nor2_1 _240_ (.A(_052_),
    .B(_073_),
    .Y(_081_));
 sky130_fd_sc_hd__xor2_1 _241_ (.A(data_i[30]),
    .B(_081_),
    .X(data_o[25]));
 sky130_fd_sc_hd__nor3_1 _242_ (.A(syndrome_o[4]),
    .B(syndrome_o[3]),
    .C(_023_),
    .Y(_082_));
 sky130_fd_sc_hd__nand2b_1 _243_ (.A_N(_054_),
    .B(_082_),
    .Y(_083_));
 sky130_fd_sc_hd__xnor2_1 _244_ (.A(data_i[32]),
    .B(_083_),
    .Y(data_o[26]));
 sky130_fd_sc_hd__nand2b_1 _245_ (.A_N(_057_),
    .B(_082_),
    .Y(_084_));
 sky130_fd_sc_hd__xnor2_1 _246_ (.A(data_i[33]),
    .B(_084_),
    .Y(data_o[27]));
 sky130_fd_sc_hd__nand2b_1 _247_ (.A_N(_046_),
    .B(_082_),
    .Y(_085_));
 sky130_fd_sc_hd__xnor2_1 _248_ (.A(data_i[34]),
    .B(_085_),
    .Y(data_o[28]));
 sky130_fd_sc_hd__nand2b_1 _249_ (.A_N(_060_),
    .B(_082_),
    .Y(_086_));
 sky130_fd_sc_hd__xnor2_1 _250_ (.A(data_i[35]),
    .B(_086_),
    .Y(data_o[29]));
 sky130_fd_sc_hd__nand2b_1 _251_ (.A_N(_048_),
    .B(_082_),
    .Y(_087_));
 sky130_fd_sc_hd__xnor2_1 _252_ (.A(data_i[36]),
    .B(_087_),
    .Y(data_o[30]));
 sky130_fd_sc_hd__nand2b_1 _253_ (.A_N(_050_),
    .B(_082_),
    .Y(_088_));
 sky130_fd_sc_hd__xnor2_1 _254_ (.A(data_i[37]),
    .B(_088_),
    .Y(data_o[31]));
endmodule
