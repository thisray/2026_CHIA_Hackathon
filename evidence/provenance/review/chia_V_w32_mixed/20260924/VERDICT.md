# V｜混合 arity 閉包帶來新的 W32 成果

**V02 全域組合是新的 W32 最低可行 J**，相對原 c6，delay、area 與三種 energy 全部改善。Native Flash 先量到 singleton 的 profile 取捨，再讀回饋選全域組合；兩筆皆真正經 CHIA/Ray、全輸出 proof 與 fresh route／RCX／三 activity。V 最終使用 2 route／3 API；第三次模型已選同 count 的 weighted alternate，但依使用者收尾要求未送 EDA，最後 route 額度釋放。

| 候選 | D ns | A µm² | stress／uniform／low E pJ | J |
|---|---:|---:|---|---:|
| O32 c6 親本 | 2.098243 | 1299 | 1.279070711／.8860687376／.2669597961 | .7976462300 |
| V01 phase003 | 2.080952 | 1297 | 1.277263218／.8862236427／.2673304698 | .7976856388 |
| V02 global | 2.081588 | 1296 | 1.275677205／.8836139023／.2662638326 | .7955110409 |

V02 對 c6：D 快 16.655ps、A 少 3µm²、J 相對改善 0.267686%。V01 更快 0.636ps，但 J 較高，保留完整取捨，不拼接成另一列。

新工具把閉包從 XOR2／XNOR2 擴到 XOR3／XNOR3，可用相位變數 41→56；所有 public／assign／非 parity 邊界保持固定。V01 翻轉 `_003_`，三個 target 補償後 XOR2／XNOR2 數量保持 77／11，一個 XOR3→XNOR3 縮寬。V02 從同一原 c6 親本重算 20 個 phase nets，9 個 master 改變：4 XNOR2→XOR2、3 XOR2→XNOR2、2 XOR3→XNOR3；counts 77／11／2／5→78／10／0／7。drive、net connectivity 與完整148-cell map 均受 checker 保護；各自新 proof 才提供正式功能證據。

全域提案使用 area-first／XNOR2 tie-break 代理，並非直接 energy 最佳化或最優證明。首 solver 遭 CPU 上限終止；修正後兩個22秒 worker 在合計2CPU／8GiB內、總26秒找到並原子保存候選，最終摘要 JSON 發生 circular-reference 錯誤。原錯誤保留，候選由 checkpoint 獨立檢查，不重跑 solver、不冒稱正常完成。原型 `phase_rhs` 欄其實表示新 intrinsic polarity；production 不信任該命名，從相位向量獨立重算。

兩筆 DPL 都沒有移動 cell；實際 DB area 分別減 1.2512／2.5024µm²，整數 routed area 如表。三者 worst path 均 data_i[29]→data_o[31]；`_130_` XOR3→XNOR3 的觀測 arc 由 .528880ns 變為 .511691／.512314ns。這是實際路徑觀察，route／RCX 也重新產生，不能隔離成 cell-only 因果效果。

[V01 receipt](v01-receipt.json)／[native 選擇](model-01.json)、[V02 receipt](v02-receipt.json)／[讀回饋後選擇](model-02.json)、[完整診斷](diagnosis.json)。V01 source `aa31341`，98 case 檔；V02 source `9696c19`，105 case 檔；全部逐 SHA 核對，各自三份新 VCD 保留。V01／V02 新 pre-proof .847／.844s、route 8.547／9.198s、三 E 4.232／4.247s；final 僅因本次 graph bytes 與 pre-proof 相同才重用 proof。W32 goal／三個 workload／原始分母／2.4ns ceiling 全部不變。

[V01／V02 保存](archive-checkpoint-v02.json)與[晚到資料／未啟動 V03 保存](archive-checkpoint-v03-closeout.json)均在 SSD／NAS 逐 hash 核對；合計263檔／21,198,744bytes。[V03 checkpoint](v03-not-started-closeout.json)是未執行的恢復資料，不是第三筆量測。
