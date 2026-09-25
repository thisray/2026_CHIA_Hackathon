# b441 selective XNOR downsize：新可行能量最佳點

從已驗證 b441 routed graph 出發，native Vertex Flash 3.8 在唯讀 extracted STA／Liberty 證據下選擇一次 `_318_ xnor2_2 → xnor2_1`。真 CHIA Ray leaf 僅改此 instance 的 master，A/B/Y net 均未變；parent→pre-route 與 parent→final 的全輸出 miter 均 PASS。舊 non-special signal wires 已清除、較小 cell 已重新合法化並 fresh routing／RCX／三 profile。沒有新 mapping，原 goal、SDC 與分母未改。

新圖 **D=2.373910 ns、A=2416 µm²、J=0.9884059071531012**，三 profile 原始能量為 stress 2.626159403、uniform 2.006511349、low-toggle 0.4115977572 pJ。D≤2.400 ns 可行，且在 D、A、J 三項均優於先前最低能量 incumbent f59（D=2.397587、A=2424、J=0.9899229945846846）。新結果相對 b441 parent（D=2.359425、A=2424、J=0.9904285736703958）犧牲 14.485 ps 時序，換得面積與能量下降；剩餘 timing margin 26.090 ps。這是 **b441 上明確 selective resize 加新路由的整體收益**，沒有證明先做 pin ECO 是必要條件。

本獨立 reservation 為 **1/1 route、0 mapped**。執行 source `5b9032e`、parent binding、Flash prompt/response、真 Ray job/node/task/worker ID、兩次 proof、graph/ODB/SPEF/VCD 與完整三 profile 數字見同目錄 `receipt.json`。GCP02↔GB10 raw run 73 檔及 GB10↔M4 外接鏡像 88 檔均逐檔 SHA 彙總一致。量測未提供獨立 DRC signoff，不作該主張；dual 的可選 per-instance power sidecar 未加入此次 frozen 三 profile。
