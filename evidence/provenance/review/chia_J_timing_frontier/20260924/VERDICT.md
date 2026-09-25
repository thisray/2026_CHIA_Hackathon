# J｜多路徑保護的全域 phase 指派

J01 新可行候選 **8e038f9f**：D **2.376334ns**、A **2427µm²**、J **.8993419995**，同一候選三E stress **2.476976952**／uniform **1.859090553**／low **.3547985398pJ/vector**。固定W64 context及D≤2.40ns限制，餘裕 **23.666ps**；whole-output proof、fresh route／RCX／各1024向量的三量測均有效且0 mismatch。86個case artifact逐SHA核對通過。

相對I01及K最佳，J／delay／area皆改善；相對K，stress／uniform能耗較高，low-toggle較低，故保留K／M的profile取捨。相對原bbf，三E和J降低但delay較慢；不拼接不同候選的最佳欄位。完整[receipt](j01-receipt.json)與[診斷](j01-diagnosis.json)保留同候選全部數字。

機制是從H1/H2已量到的時序反例擴充phase約束：原bbf路徑＋H1 data61＋H2全部13條fail/near input paths，34個phase變數固定、33個path gate保持極性；在原bbf上bounded GF(2)求解得到37 XNOR／33個改動。局部代數checker沒有代替本次whole proof，solver不宣稱最適解。新worst仍為已保護的data_i[13]→data_o[57]、經_384_/C，對應路徑XOR gate均受保護；相較H2同input最差路徑慢9.699ps，仍可行。這不是宣稱凍結gate就保證固定route時序。

外層建造constraint集合與solver，程式精確展開；Flash LOW讀H/I實驗回饋後[選RUN](j01-model.json)，真CHIA/Ray執行source `4adaff7929d1dee7941e3f0d4429aadacd2f7121`。完整raw位於GB10 `.../chia-top1-20260923/J-timing-frontier-assignment/run-01/case`；process記錄PID存檔時shell quoting錯誤，實際leaf只啟動一次，沒有重送。

J事前cap2route／6API，**2route／2API已封口**。第二筆source6a67a、Flash LOW從實際parent選STAR270，得D2.447725／A2427／J.8975820293，不可行；三E2.470767649／1.858312316／.3537541488。85檔核對、全proof與量測有效，保留原J winner。它翻轉原33個保護gate中的_316_，原實測arc .234045→.311811ns（+77.766ps），new endpoint data_o59；這是該具體動作破壞保護策略的反例，不否定所有local phase。

[後繼receipt](j02-receipt.json)、[native](j02-decision.json)、[critical path比較](j02-diagnosis.json)完整保留。後續N在相同保護集合使用power重要度，取得更好的可行點，見[N證據](../../chia_N_weighted_phase/20260924/VERDICT.md)。