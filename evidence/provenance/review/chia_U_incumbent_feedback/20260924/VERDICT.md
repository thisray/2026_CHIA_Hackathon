# U｜新 XOR3 結果重新進入原生回饋 loop

U 已封口，3 次 native Flash LOW／3 次 route，三筆完整 proof、fresh route 與三 E 均有效。source `813fed79` 只使通過原有完整 guards 的 `xor3_phase_replay` receipt 可作 parent；S02 實際 parent 驗證與 74 pair／29 star catalog 均成立。

| 候選 | D ns | A µm² | stress／uniform／low E pJ | J | 可行 |
|---|---:|---:|---|---:|---|
| S02 起點 | 2.374088 | 2425 | 2.470198669／1.854111761／.3517976802 | .8951799620 | 是 |
| U01 pair309/310 | 2.430113 | 2425 | 2.461443073／1.846514788／.3513453703 | .8925153722 | 否 |
| U02 撤銷＋新 route | 2.375888 | 2425 | 2.468786261／1.853478461／.3517407458 | .8948591221 | 是 |
| U03 起點 pair299/300 | 2.373983 | 2425 | 2.475585788／1.859103650／.3522472616 | .8970152664 | 是 |

U02 為最低已量測可行 J 的物理候選，但**不是新 Boolean／phase 機制增益**。模型看到 U01 的時序違規後，明確選擇再次作用相同 pair 撤銷前一步。U02 的 `routed.v` 與 S02 byte-identical，287-cell 完整 map 及 553-instance placement（master／XY／orientation）皆相同；ODB 與 SPEF 不同。[recipe 核對](route-context-comparison.json) 確認兩個 route Tcl 只差 log marker，routing／seed／RCX 與 measurement runner 相同；這不等於 ODB input/history 相同。J 的微小差異屬這次 fresh route／RCX／activity 量測，不能歸因於新的邏輯改寫，亦未建立路由擾動的普遍收益。保留 S02 較快 1.800ps 的物理版本。

U03 是不同邏輯候選，但 J 較差；僅 0.105ps 的單次 delay 差異不作穩健速度優勢主張。U01 的低 J 不因不可行而混入 winner。這是實際模型讀回結果後的後繼決策，沒有公平方法／模型優勢主張。

[完整 hash／歸因診斷](diagnosis.json)、[U01](u01-receipt.json)／[原決策](u01-decision.json)、[U02](u02-receipt.json)／[原決策](u02-decision.json)、[U03](u03-receipt.json)／[原決策](u03-decision.json)。每 case 85 檔、共255個 artifact hash 核對。舊 polarity runner 三次皆 `vcd_retained=false`；新 activity 確實用於量測，原 hash sidecars 與 simulation／power logs 保留，但 VCD bytes 已依原預設刪除，不能借 S 波形冒充。

[SSD／NAS checkpoint](archive-checkpoint.json) 含291檔／32,536,718bytes，逐 SHA 與 size 核對；scope manifest `b726f15c9bd971de3891e367dac538260adad5c880397078be0b9d50f6346d34`。原 GB10／GCP 檔案保留，未再派第四筆 route。

下一個局部改善是向 runtime 明確揭露候選是否回到已知完整 cell map，以及可以直接選既有 parent；保留有意探索新 route 的能力，不自動借用舊 proof／PPA。較高上限的 mixed-arity 閉包研究並行，不因 U 沒有新邏輯 gain 而停止。
