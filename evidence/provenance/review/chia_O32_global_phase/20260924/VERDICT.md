# O32｜全域 phase 與同最小數量內的能耗選樣

O32 **2route／2次native Flash LOW已封口**；原G32預算不延長。固定獨立W32 goal `routed3_w32_d240_maskedF0_v1`、reference `ecc_masked_reduction::F0::routed3_w32_v1`，分母stress1.595184585／uniform1.140097229／low.32781139449999996pJ，不能與W64的J直接比。

| 同一候選 | D ns | A µm² | stress／uniform／low E pJ | J |
|---|---:|---:|---|---:|
| ff6f3194親本 | 2.110139 | 1299 | 1.331617095／.9302863327／.2848759686 | .8396371501 |
| O01 f8a77599 | 2.069854 | 1299 | 1.280009747／.8892433107／.2677222983 | .7995528633 |
| O02 c6c10558 | 2.098243 | 1299 | 1.279070711／.8860687376／.2669597961 | .7976462300 |

兩個O候選皆whole-output proof／fresh route-RCX／三profile／placement guard有效。O01對ff6：三E全降、D快40.285ps，J改善約4.77%，area不變。O02對O01：三E再降，但D慢28.389ps，因此保留較快O01。O02時序餘裕301.757ps；不是跨角落signoff。

首個global phase從exact ff6的88 XOR/XNOR gates與41個eligible internal phase variables推導：31→11個XNOR、17個phase-one nets、24個改動。非XOR與public boundary固定。外層Flash CLI兩次timeout／400後，native Vertex Flash局部codegen與機械finalizer完成prototype；GCP03 solver一次22秒，wrapper在candidate生成後因header-regex錯誤退出，未保存的solver内部report明列missing，沒有重跑。純GF2檢查不替代後續真wholeproof。Flash runtime[選RUN](o01-model.json)，source5da3ccc在GCP02真CHIA執行。

其後一次pinned Yosys SAT判定 `count≤10` UNSAT，已有11 witness，故**在此41-variable／固定boundary／XOR2-XNOR2表示內，11是最小數量**；不是J或PPA最優。7個XNOR不可變、4個mutable；全部148 cells均drive1，無直接_2/_4 downsizing候選。[count證據](count-bound.json)保留首容器UID log失敗（未執行SAT）、唯一實際SAT及classifier修正（未重跑）。

第二條純搜尋在同count11空間枚舉：工具實際輸出17個，事前宣告只評分前16，第17保留raw不使用。以原ff6三profile internal_w／whole-design total_w平均重要度，選第9個不同phase圖；proxy從.0529943降至.0459956（−13.21%），不能寫成實測J改善。候選11XNOR／26改動。[Flash依第一筆實測與SAT資料選RUN](o02-model.json)，source9fc6f87取得上表O02。模型reason的「11 replacements」字眼不精確：11是XNOR cell數，實際替換26個。

O01/O02 pre wholeproof各PASS0.83s，final因本次pre/final bytes及完整context一致而合法重用，未借舊candidate proof，也未依模型F0字樣更換proof input。兩個case manifest89／96檔核對；O02 keep_vcd僅為保留選項，不改power Tcl／公式／SDC／workload／分母。三VCD bytes/hash已保存（897478／829980／317140B），與summary及retention欄一致。

[O01 receipt](o01-receipt.json)／[診斷](o01-diagnosis.json)、[O02 receipt](o02-receipt.json)／[診斷](o02-diagnosis.json)保留完整同候選取捨、actual CHIA/Ray identity與hash。GB10 `.../chia-top1-20260923/O32-global-phase-transfer/`、W32 prototype、兩個SAT probe與全部model raw共289檔／19,429,247bytes已copy-first至SSD/NAS逐SHA核對，source manifest `3e2968220bb9577bada7a2f04881aa6520e18d733133b6c7c7f1cb497600e916`。
