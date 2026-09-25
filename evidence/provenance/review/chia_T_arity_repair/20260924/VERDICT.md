# T｜跨 arity phase 與標準 timing repair 的互補

T 已完成 1 次 route、3 次 native API（RUN、429、STOP），第二次 route 額度釋放。新圖 `2525e560` 全 proof／fresh route／三 E 有效且可行，形成比 S 更快、更小，但 J 稍高的取捨。

| 候選 | D ns | A µm² | stress／uniform／low E pJ | J |
|---|---:|---:|---|---:|
| R02 e07e2ce0（親本，不可行） | 2.425037 | 2416 | 2.466217848／1.856532035／.3514162017 | .8947643094 |
| T01 2525e560（可行） | 2.370334 | 2424 | 2.470196341／1.862394856／.3519423262 | .8966336020 |
| S02 eefeb2af（不同親本，可行） | 2.374088 | 2425 | 2.470198669／1.854111761／.3517976802 | .8951799620 |

[Native Flash 選擇](native-run.json) 是在看見 R 的實際 25.037ps 違規與 placement 估計偏差後，使用既有 2.35ns repair 配方。新 2.38ns 配方只作有限可選工具，沒有被本次執行；benchmark 的 delay ceiling 仍是 2.4ns，三 workload 與分母不變。

標準工具只將 `_318_` XNOR2_1 升至 XNOR2_2；placement proxy 由 2.390937 降至 2.342855ns，fresh routed 結果才是表中 2.370334ns。相對 R，delay 快 54.703ps，area 加 8µm²，三 E 都增加；完整187個 XOR2／XNOR2 function family 保留。這證明此 arity-phase 配置與標準 repair 能組合得到可行結果，不證明所有新 RTL 都有互補收益。

Source `cf8c954` 已 main，[T01 receipt](t01-receipt.json) 保留真 CHIA/Ray identity。新 ECO 1.044s、pre whole proof 1.102s、route 16.584s；final graph 與本次 pre-proof graph 相同才重用 proof。86 個 case 檔案逐 SHA 通過，manifest SHA `7326eaae6489a54dc5b9847b46e002edae26582509dd2a76b6dcfebeee9a271f`，三份新 VCD 保留。

模型讀實際單一 resize 與 proxy 落差後[選 STOP](native-feedback.json)：它判斷 2.38 可能導致相同離散 move，最後一筆 route 的資訊價值低。這是預期價值判斷，沒有實測證明兩 recipe 相同；429 與重試照實計入。S 仍是最低 J，T 是速度／面積取捨，兩者不同 parent，不能拿來作 phase 與 repair 的因果隔離。

原始資料位於 GB10 ART `T-arity-standard-repair/`；保存以獨立 archive checkpoint 為準。原 R／S 額度皆未延長。
