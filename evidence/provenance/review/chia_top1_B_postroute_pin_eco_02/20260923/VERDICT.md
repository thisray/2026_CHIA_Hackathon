# EF373 第二次 pin ECO

這一筆從已驗證的 EF373 routed graph 出發。parent 身分由原始 `remote.sha256`、完整輸出 proof receipt 與三 profile measurement 程式化產生並綁定；外部唯讀 extracted STA 只提名 `_384_ sky130_fd_sc_hd__or3_1` 的 B↔C。Liberty 的 OR3 函數允許交換，但原弧觀察受不同 slew 和 RC 影響，未被當成收益預測。native Vertex Flash 3.8 在此唯一候選和 STOP 之間選擇執行。

新候選在真正 CHIA Ray worker 中執行，保存 job、node、task、worker ID 與 source SHA。只有 `_384_` 兩條輸入 net 互換；pre-route 與 final 全輸出 miter 均 PASS，舊 non-special signal wires 已清除，按原 2.575 ns routing SDC 重新繞線、RCX 和三 profile 量測。新圖 D=2.359425 ns、A=2424 µm²、J=0.9904285736703958，三種原始能量依序為 stress 2.631109965、uniform 2.013202902、low-toggle 0.4119766891 pJ。相對 EF373，delay 改善 5.889 ps，但 J 增加約 0.000092963；未取代最低能量 f59 incumbent（J=0.9899229945846846）。這是單一 pin permutation 加配套新路由的整體結果，不能把所有 PPA 差異單獨歸於 pin arc。

本 reservation 1/1 route submission、0 mapped；實際新 ECO graph、pre/final proof、fresh detailed route、三 profile 各一次。router 完成並在內部達到零 violations；量測 receipt 沒有獨立 DRC 結果，因此不聲稱獨立 DRC signoff。詳細 source、模型、CHIA identity、證據與 graph/SPEF/VCD 雜湊見同目錄 `parent_binding.json`、`receipt.json`。GCP raw 72 個 run 檔與 GB10 逐檔 SHA 彙總一致；GB10/M4 外接鏡像共 90 檔一致。
