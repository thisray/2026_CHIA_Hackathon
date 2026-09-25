# f441 與 XOR 樹旋轉的真實互補收益

Native Vertex Flash 在看到原 f441 與先前獨立 327_A 旋轉結果後選擇 COMPOSE；首次429與後續完整200回覆均保留。這個改寫家族及組合由外層研究提出，模型選擇量測，不宣稱模型發明算子。真 CHIA/Ray 在 exact f441 parent 上只交換 `_327_/A` 與 `_328_/A` 的 `_006_`／`_066_`，`_333_/A` 仍接原 `_066_`。Instance/master/placement/output 與其他連線守衛通過，parent→pre、parent→fresh-final 全輸出 miter 均 PASS；新 route、RCX、三 profile 有效。

新圖 **e5e837de** 得 **D=2.358853ns、A=2416µm²、J=0.9876137311390889**，三 E 為 **2.625896304／2.008363954／0.410271241pJ**（stress／uniform／low-toggle），固定原 b271/F0 分母與 D≤2.40 門檻。相對前一可行最佳 f441，J約降0.0801%、D快15.057ps、area相同；uniform能量略高，不能說三profile全勝。保留 f441 原件，新的時序餘裕為41.147ps。

先前從原M0起步的327_A/F1-v8 D2.408977超限；此次組合在不同已改善的routed parent上可行且降低J，支持這一具體工具組合的互補價值。不能把不同物理context的delta相加作預測，也不能推論所有旋轉或模型都優於固定搜尋。

Codex協調子agent用量中斷後，三個Flash coding workers各35步未改source；Pro生成骨架後，root修正殘留的downsize接線、模型檔案綁定和位置守衛才提交 immutable source `ead8529`。Pro曾在source-only階段誤做兩次GB10本機Ray helper前置嘗試，皆在EDA前失敗、0物理結果；第一份tmp結果曾被覆寫，兩次工具trace與最後tmp snapshot已保存，並記2次submission及1次局部超額。成功GCP重試另開1route額度，沒有抹除先前成本。

此次同session optional per-cell power JSON及pin/net TSV皆產生，三profile無sidecar error；原score計算未改。90個run檔已GCP→GB10→M4逐檔SHA一致。完整Ray身份、proof／graph／SPEF／model與量測身分見receipt；不是獨立foundry signoff。
