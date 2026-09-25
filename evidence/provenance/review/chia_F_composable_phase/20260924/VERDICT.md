# F：batch組合與真反例回饋

本campaign另立最多8 route／24 native模型calls，固定W64 goal，原E104與公平C封口。下列每列均為同一候選，均全輸出proof PASS、新route/RCX及三profile有效；feasible另看D≤2.4。

| action／parent | D ns | A µm² | J | 結論 |
|---|---:|---:|---:|---|
| F01 native batch271/274/293/330／234 | 2.405758 | 2427 | .9292139506454222 | 超5.758ps，不可採納 |
| F02 native單star271／234 | 2.362283 | 2427 | .937913952776108 | 新可行winner244543a8 |
| F03第一步 native batch274/330／244 | 2.362535 | 2427 | .9320803737308742 | **目前可行winner bbf15474** |
| F03第二步 native batch277/280／bbf | 2.436628 | 2427 | .9230941807096198 | 超36.628ps，保留反例 |

F01三E stress/uniform/low=2.527142642/1.903886005/.3745468712；雖低於static reference，D不合法不能當winner。外層pinned唯讀STA指出新worst經293/295，固定路徑+45.603ps、295arc慢62.261ps。F02看到兩parent自身STA/PPA與已驗歷史，但因窄schema不接受額外欄，**未看到外層逐arc診斷**；首次registry預檢0model/0EDA失敗保留後用既有入口推進，Flash單選271。

F03已正式透過hash-verified diagnostic_context提供那份外層診斷，runtime自行選274/330；新bbf三E=**2.534645901/1.911262370/.3754500722pJ**，三者皆低於固定b271/F0 reference，J低6.792%，但面積2427高於reference2392，不宣稱所有指標同勝。不是prompt ablation，也不證明普遍模型優勢；只主張模型獲得真回饋後的實際行動與有效組合收益。

F03第二步降低J卻失去可行性。只讀診斷顯示277/306新worst的固定路徑慢77.118ps，280分支固定路徑也慢約95–97ps；整批能量不能分攤成個別star能量。外層診斷的284/286 consumer清單曾手填交叉，**尚未送runtime前**已用原始netlist/kernel重算修正，舊版另存unused-before-selector，STA/PPA未改。F04會讀正確版本，自行選完整star撤回／縮小／其他action或STOP，不跑ablation矩陣。

另F structural absorb/drive2 D2.401459/A2436/J.956297631，fullproof/3E有效但不可行，且D/A/J全劣於可行5b；該局部線停止追加。

所有raw、原生API、request/intent/receipt指向ART/F-composable-phase各episode及matched manifest。F01來源ad44a973；F02來源9caa8422；F03來源3745c144。Best aggregation曾漏掉verified parent的proof欄，影響v2/v4/F01的as-run best回報；原state不改，衍生corrected_best_readouts已另存。修正不進模型prompt/parentpool，因此不改已有模型軌跡、proof、PPA與全局incumbent。

## F04–F06：控制器成本與後期結構對照

F04第一步native STAR270得D2.432234/J.929590069不可行；第二API請求ReadTimeout150s，usage未知、模型call照計、沒有送route。原completed候選與state保留，剩餘1route釋放。可檢查的同輸入prompt比較：原F4 step02有3parents/15prior/1recent、523084bytes；compact重建87275bytes（少83.32%），所有action/power/tradeoff/STA及診斷內容保留，hash/path等audit資料留磁碟。先前漏child的65024-byte比較已取代。

F05用新source17eaa6d1，真Flash請求為55438 input tokens/39.684s；這是不同輸入的運行觀測，**不是controlled latency ablation**。模型選bbf的pair302/303，真Ray全proof/fresh3E得 **60e350de D2.389404/A2427/J.9304365426214756**；三E2.530565253/1.906410325/.3750214091。它更省能但比bbf慢，保留bbf較大餘裕。

F06是root提出的固定no-fold counterfactual，native只選RUN/STOP；不是模型發明六個stars。從exactb00重用311/258/266/271/274/330（4+2純kernel展開、18targets），新完整cellmap與bbf只差7個fold相關instance；兩邊layout/history與freshroute仍屬各自實驗，不把整體差額歸成一顆INV的孤立效應。Flash第一次RUN帶額外action.phases，未送EDA；格式修復原始trace保留後第二次回exactschema。Source8bb55602的真Ray結果：**67c95564 D2.399661/A2416/J.9301115551726122**，三E **2.524363517/1.910615392/.3747224036**，wholeproof/fixedplacement/freshRCX/3E均有效。

67c是目前同goal最低可行J，面積較folded少11，但僅**0.339ps**餘裕，不宣稱multi-seed robustness或signoff；保留60e（10.596ps餘裕）及bbf（37.465ps）。相較60e，uniform E略高，其餘兩E及J低；不可拼各欄最佳值。

F最終 **8/8 route submissions、10/24 native model calls**封口，含timeout與格式修復。原E187mapped/104route/18extraprofiles不變；G32獨立context已封口。H另立2route研究較廣phase assignment，不延长F。
