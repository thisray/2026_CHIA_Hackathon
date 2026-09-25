# I｜全域 phase 硬體與標準 timing repair 的互補實測

I01 取得新可行 J 最佳候選 **39bb3c78**：D **2.398176 ns**、A **2447 µm²**、J **.9037091361**；同一候選三 workload 能耗 stress **2.475488873**／uniform **1.848241809**／low **.3623230441 pJ/vector**。時序餘裕僅 **1.824 ps**，不是跨角落 signoff 或穩健性宣稱。

相對之前最低 J 的67c95564（D2.399661／A2416／J.930111555），新 J 降約2.84%，三 E 皆降低，但 area多31；保留67c的小面積及bbf的較大時序餘裕取捨。相對 H2 原親本，修復令D快53.958 ps、A多20、J增加.017928，但由不可行變可行。不能把 H2 未修復的低 J 與新候選的 delay 拼接。

Native Flash LOW 讀 H2 實測與 proxy 證據後，選 `h2-e267f8bd`＋固定 `h_phase_postroute_setup_repair_v1`。外層設計 phase solver及工具介面，runtime決定 parent／動作；實際 GCP03 CHIA/Ray leaf `pid166554` 完成，不把外層 coding agent當成runtime。

固定新優化 recipe以2.35ns為setup目標，從既有route graph清除舊signal wires、以met2/met3 placement RC作一次 bounded setup repair；新route/RCX後仍用原W64 D≤2.40ns目標及原三profile／分母量測。優化context已明示，沒有改動評分分母。

修復確實改圖：`_307_ xor2_1→xor2_2`、`_384_ or3_1→or3_4`、`_315_ A/B`對調、新增`rebuffer1 buf_4`至`_392_.B`，DPL移動`_261_／_403_`。原187個XOR/XNOR instance的邏輯極性family保持。H2舊最差data29→data57在新圖為2.317084ns（快135.050ps），新worst轉data53→data60；不是NOP，也不能把局部改善當global改善。

新的whole-output proof PASS（1.129s）；pre與final網表位元組一致，故本次新proof合法重用於final，沒有借用parent proof。fresh route／RCX與三profile活動量測全部有效。source `71a8bfff46e46b3cf5f6a7c9bea02fb017b42e24` 已main；graph `39bb3c78f833f66da8b508fcfdabea8bb185e74e75919b25536899fb57478a0c`。兩筆case各83檔已GCP→GB10逐檔核對；I01 100檔、I02+models 102檔也已SSD／NAS逐檔核對，見current所列獨立preservation checkpoint。

I campaign **2／2 route、3 API（含一次Flash429）已封口**。第二筆由Pro LOW在I01真實回饋後選bbf同recipe control。該ECO為NOP：0 resize／rewire／buffer／move，網表仍bbf；新route／RCX後D2.365566、A2427、J.932319967，三E2.53571925／1.911527652／.375528507，完整proof與三量測有效。與原bbf的小差異來自本次新physical結果，未冒稱同圖等於同實驗。

在這組exact parents／同recipe對照中，phase＋repair比tool-only的J低約3.0688%，但A多20、D慢32.610ps；兩者皆可行。支持這次組合的額外價值，不推論所有固定搜尋或其他硬體皆被擊敗，也不宣稱phase普遍必要。原bbf與H2的物理態不同，這是條件式比較的邊界。[四列完整比較](matched-comparison.json)保留每列同候選D/A/三E及receipt identity。

下一步已實作派工：將已驗repair receipt接入原polarity runtime parent seam，讓真模型能在新winner上續選局部動作；另一個全域prototype保護所有已知超時／近界路徑。兩者尚未新增EDA，後續另立campaign，不延長I。

證據：[receipt](i01-receipt.json)、[native decision](i01-model.json)、[result](i01-result.json)、[diagnosis](i01-diagnosis.json)、[control receipt](i02-receipt.json)、[control native](i02-pro-model.json)、[control diagnosis](i02-diagnosis.json)。完整raw位於GB10 `.../chia-top1-20260923/I-phase-timing-repair/run-01/raw/case`，hash manifest／原請求／模型原始回應均保留。背景shell OS exit code未觀測，未擅填0；實際leaf與工具exit見receipt。
