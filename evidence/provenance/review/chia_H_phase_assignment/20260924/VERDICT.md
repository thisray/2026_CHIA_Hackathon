# H｜全域 phase 指派的真實能耗收益與時序反例

H 已封口：2／2 route、3 次 native API（含一次 Flash 429）。原 E、F、G32 的預算不變。兩筆都是原 bbf15474 的後繼，H2 不是從 H1 再改寫。

| 同一候選 | Delay ns | Area | stress／uniform／low E pJ | J | D≤2.4 |
|---|---:|---:|---|---:|---|
| bbf15474 原 parent | 2.362535 | 2427 | 2.534645901／1.911262370／.3754500722 | .932080374 | 是 |
| H1 a4202284 | 2.528992 | 2427 | 2.428729786／1.814035495／.3478267172 | .880344665 | 否 |
| H2 e267f8bd | 2.452134 | 2427 | 2.440835378／1.823997882／.3506278517 | .885781300 | 否 |

兩筆 whole-output equivalence、固定 placement、新 route／RCX／三 workload activity 均有效；低 J 不能抵銷時序不可行。採用方案仍保留 67c95564／60e350de／bbf15474 的完整取捨。上述 E／J 僅屬固定 W64 routed context `routed3_w64_d240_b271F0_v1`，分母 2.541007707／2.027927403／.4358843944 pJ。

外層提供 phase-law kernel、候選保護策略與先前硬體知識，程式處理 GF(2) 與 bounded search。H1 runtime Flash 實際選 `critical_protected`；60→18 XNOR 是淨減42，但實際48個 gate 翻轉，不能寫成只改42個。H1 原保護路徑仍2.367570 ns，新的 data_i[61]→syndrome5 路徑達2.528992 ns。這支持下一步增加反例 cone 約束，而不是宣告 phase 方法無效。

H2 Flash 429 後，同 project Pro 讀到 H1 量測，選 `counterexample_protected`。新計畫在原 bbf 上同時保護舊路徑與新 cone，23 XNOR／47個 gate 翻轉；top3 與 worst-only 約束空間相同，沒有重跑兩套矩陣。H2 比 H1 快76.858 ps，能耗略增，仍超時52.134 ps。bounded solver 不主張最適解。

後續唯讀 STA 各檢查72個 primary input 到 all outputs 的最差路徑。H1 有14條超過2.4 ns、15條在2.35–2.4；H2 有6條超過、7條近界，主要觀察群為 syndrome3／data_o57 與 syndrome4／data_o22。分組不是已證明互不相交的邏輯 cone。

已另立 I 的2 route／6 API 有限實驗：讓 native 模型決定對 H2 或 bbf 使用固定標準 timing repair，測試 phase 改寫能否與工具互補。優化目標2.35 ns與最終量測限制2.40 ns分開記錄。H2 extracted D2.452134／WNS−.102134；placement RC proxy D2.427424／WNS−.077424，確有 violation，但 proxy 並非修復後 PPA。另一條並行 prototype 由所有已知超時／近界路徑加入 phase 保護約束，只做純求解與 audit，尚無新 PPA。

證據：[H1 receipt](h01-receipt.json)、[H2 receipt](h02-receipt.json)、[H1 native](h01-model.json)、[H2 Flash failure](h02-flash-model.json)、[H2 Pro native](h02-pro-model.json)、[refinement audit](refinement-audit.json)、[frontier summary](input-frontier-summary.json)、[proxy receipt](repair-proxy-receipt.json)。

Source H1 `656e6387ef3fff36b8e243eff8d455ac44be23d6`、H2 `00710c9a05b7d704467903a168cb5c4ce465a319` 已整合 main。完整 raw 保留於 GB10 `.../chia-top1-20260923/H-phase-assignment/run-01/raw/case` 與 `run-02/raw/case`；GCP→GB10→M4 的 executor manifest 已逐檔核對。新 NAS checkpoint 由獨立保存 worker 處理；不能只把短期雲端磁碟當成持久備份。
