# S｜可行 parent 上的雙 XOR3 相位縮寬

**S02 eefeb2af 成為同 W64 goal 下的新最低可行 J**。完整 proof、fresh route／RCX／三 workload 能量皆有效；相對原 N02，delay、area 與三種 E 都改善。S 共 2 次提交／3 次 native Flash LOW，已封口。

| 同一候選 | D ns | A µm² | stress／uniform／low E pJ | J |
|---|---:|---:|---|---:|
| N02 320970ab | 2.375917 | 2427 | 2.472119231／1.854768634／.3532727351 | .8967674921 |
| S02 eefeb2af | 2.374088 | 2425 | 2.470198669／1.854111761／.3517976802 | .8951799620 |

J 相對 N02 改善 0.177028%，delay 快 1.829ps，保有 25.912ps 的 2.4ns 約束餘裕。J 相對固定 b271/F0 分母降低 10.482%，但 area 仍高於該 static baseline，不能稱所有指標均胜過 baseline。較快的 N01（2.369255ns）繼續保留。

外層提供精確 parity 補償工具；[native Flash 選 RUN](native-run.json)，將 N02 的 `_326_` XOR3_1 與 `_328_` XOR3_2 分別轉成同 drive 的 XNOR3_1／XNOR3_2。兩者各縮 0.460µm，實際 DB cell area 總減 2.5024µm²；routed area 整數報表由 2427 到 2425。這不是 R 的一縮一增配置。193 parity cell 的預期改動與完整網表守衛成立，DPL 記錄零 cell 移動；仍包含 fresh route，未隔離 cell arc 與 routing 各自貢獻。

第一個模型回覆照 prompt 使用錯誤 `action_if_RUN` 欄，被 schema 拒絕，0 EDA；[原回覆保留](native-format-failure.json)。修正明確 JSON 範例後第二 call 合法。S01 source `68fafe3` 已成功 ECO，卻因 runner 要求 OpenROAD 在合法 placement 時未產生的報告檔而停在 proof 前；原始錯誤與 UNKNOWN 功能狀態保留於 [S01 receipt](s01-receipt.json)，不改寫成 PASS。

source `9f01c4f` 核對原 source／recipe／model／parent 三 hash／23-file manifest／完整 child map／DB area／DEF，重用 S01 成功 ECO。S02 新 pre-proof 1.147s、route 19.305s、三 E 5.967s，ECO 新成本 0s（原 0.945s）；final 網表與本次 pre-proof bytes 相同才重用該 proof。[S02 receipt](s02-receipt.json) 的 96 個 case 檔案逐 SHA 驗證，manifest SHA `b04067831fff5ef3175f88834e90a6652db0144fa7c8d23ccdc13a18aa97e09b`；三份新 VCD 完整保留。

模型讀實際結果後[建議後繼比較](native-feedback.json)，沒有第三次 route。其將 S 對 T 稱作 matched 比較的理由不成立：S 親本 N02，T 親本 R02，兩者不同；這個建議只能作研究方向，不能作 phase 與標準 repair 的因果隔離或已完成公平對照。T 的結果尚待量測。新 critical path 為 data_i[53]→data_o[60]，下一個局部改動需依此新回饋判斷。

原始資料：GB10 ART `S-folded-xor3-phase-20260924/`。Source 已進 canonical main；SSD／NAS 保存以獨立 archive checkpoint 為準。
