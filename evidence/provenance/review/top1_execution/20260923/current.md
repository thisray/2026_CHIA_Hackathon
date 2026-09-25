# CHIA Top-1｜M4 Astra 使用者要求收尾

更新：2026-09-24 12:42 TST。使用者已明確授權接手恢復；唯一 controller 為 M4 task `01a0cb8d-a471-7000-927b-2aca9de6a67b`，舊 M1 主控未恢復。M4 整合 WT `/Users/vegapunk/Vega/Code/260908_CHIA_Hackathon_workers/chia-astra-resume-20260923`。最新 source 以 `origin/main` 為準，歷史暫停文件不再限制本次已授權研究。

ART＝GB10 `/home/thisray/projects/260908_CHIA_Hackathon_artifacts/chia-top1-20260923`。唯一 live 帳本 `ART/campaign.json`，本次Git快照[在此](campaign_latest.json)：本 checkpoint **原187 mapped／104 route submissions／18 extra profiles封口；F8route／10calls、G32 2／4、H2／3、I2／3、K2／3、M3／4均封口；L native STOP 0route／1call；J2／2、N2／2、O32 2／2亦封口；P亦2submissions／1API封口：首ECO實作失敗、第二筆完整但時序不可行；Q修正事實後native STOP：0route／2API封口；R2submissions／1API封口；S2submissions／3API封口；T1route／3API封口；U3route／3API、W2／2封口；V2route／2API已量得新best（cap3／6）、X1API／0route source接線中（cap3／6）**。各follow-on campaign獨立宣告，不延長已封公平cohort；實際狀態以live ledger及各state為準。

## 本輪已停止新增派工

使用者要求準備結束並備份。V03／X01 均未啟動，0 EDA；原生 RUN、已提交程式與純檢查保存為可恢復 checkpoint，不列量測成果。全套收尾與資源停止狀態以[最新收尾紀錄](../20260924_closeout/CLOSEOUT.md)為準；下方歷史「正在」「待下一步」不再授權自動續跑。

## 最新執行增量

- **W32新最佳V02 2a287349**：mixed arity phase閉包41→56vars，native讀singleton真profile取捨後選global組合，取得 **D2.081588／A1296／J.7955110409**，三E1.275677205／.8836139023／.2662638326，相對原c6所有D/A/3E全改善。105case hashes與3VCD核對；V01較快0.636ps但J稍差，保留完整列。[V證據](../../chia_V_w32_mixed/20260924/VERDICT.md)
- **最低已量測可行物理row：U02 eefeb2af／SPEF af07e89e**，D2.375888／A2425／J.8948591221，三E2.468786261／1.853478461／.3517407458。這是native撤銷pair後恢復S同網表／同placement再route，不能算新phase／Boolean gain；S本身快1.8ps。U三筆255 case hashes有效、全scope291檔已SSD/NAS保存；波形bytes依旧runner預設刪除，只有原hash/logs，明示保存限制。[U證據](../../chia_U_incumbent_feedback/20260924/VERDICT.md)
- **新的XOR3硬體增量：eefeb2af（S02）**。Native選N02雙XOR3→XNOR3縮寬，真CHIA全proof/freshroute3E取得 **D2.374088／A2425／J.8951799620**，三E2.470198669／1.854111761／.3517976802；相對N02全部改善，J降0.177028%。96 case hashes與三VCD有效，原ECO成功但report缺檔控制錯誤已精確reuse續接。S2submissions／3API封口；後繼模型建議保留，但不同parent的S/T不是matched因果比較。[S證據](../../chia_S_folded_xor3/20260924/VERDICT.md)
- **前一最低可行J：320970ab**，N加權plan後native配對299/300，D2.375917／A2427／J.8967674921；三E2.472119231／1.854768634／.3532727351。原N053c D2.369255／J.897155984／同A，delay與low E更好，保留完整取捨。[N證據](../../chia_N_weighted_phase/20260924/VERDICT.md)
- **W32前一可行最佳c6c10558**：O32同count11 power選樣，D2.098243／A1299／J.7976462300，三E1.279070711／.8860687376／.2669597961。較快O01 f8 D2.069854／J.7995528633保留。相對原ff6，兩筆皆三E更低、D更快、area不變；W32獨立分母。[O32證據](../../chia_O32_global_phase/20260924/VERDICT.md)
- **前一全域J最佳8e038f9f**：J timing-frontier protected，D2.376334／A2427／J.8993419995，三E2.476976952／1.859090553／.3547985398，23.666ps餘裕。全proof／fresh3E、86case hashes有效；原bbf上37XNOR／33改動，保護H2全部fail/near＋H1/舊critical集合。[J證據](../../chia_J_timing_frontier/20260924/VERDICT.md)
- **互補能力I已成立**：H2 global phase單獨D2.452134／J.885781不可行，標準repair後39bb D2.398176／A2447／J.903709可行；同工具bbf control NOP、J.932320。保留新recipe的明確優化target與原量測context區分。[I證據](../../chia_I_phase_timing_repair/20260924/VERDICT.md)
- **真feedback K／M已完成**：K先270超時，再依回饋選原39bb pair309/310得bd7 D2.389367／A2447／J.901963984；M再選bd7 pair346/347得977 D2.395378／A2447／J.901387752。全proof/fresh3E，各自170／255檔核對；它們stress／uniform E低於J，但J有較低low E／J／D／A。[K](../../chia_K_phase_feedback/20260924/VERDICT.md)／[M](../../chia_M_phase_feedback/20260924/VERDICT.md)
- **正在推進**：P no-fold×N01首筆ECO因舊script只支援單向轉換失敗（無proof/route/3E）；source bdbc改用已驗generic雙向TSV/recipe，第二次reuse原native決策，完成D2.437572／A2416／J.895448086、三E有效但不可行；P已封口。Q input-cap proxy是program-derived settled logic（原VCD bytes缺失）；native經一次事實更正後仍STOP，0route／2API，未獲PPA。只放鬆在該配置下已實測可行_043_／_300_的N02 warmstart探索22秒回同圖，dedup不追加EDA。R已完成：e07e2ce0 D2.425037／A2416／J.8947643094，三E2.466217848／1.856532035／.3514162017；相對P快12.535ps仍不可行，不能取代N02。2submissions／1API封口；首次marker錯誤後重用成功ECO，取得新proof/route3E。[R證據](../../chia_R_xor3_critical/20260924/VERDICT.md)。S已取得上方新best。T完成1route／3API後native STOP：R02經318單cell upsize變2525e560，D2.370334／A2424／J.8966336020，三E2.470196341／1.862394856／.3519423262；比S更快更小但J較高。86 case files／三VCD有效，107檔已SSD/NAS保存。[T證據](../../chia_T_arity_repair/20260924/VERDICT.md)。U新3route／6API tranche已接S parent回真feedback：三筆完成，U02撤銷前一步得到同S網表／同placement、不同SPEF的物理row，J.8948591221／D2.375888，只記物理取捨、不稱新邏輯gain；loop已新增已知graph回退提示（完整cellmap／ports／assign context），25 tests與真U02一次性識別通過；尚未將此提示效果冒稱新PPA或模型優勢。V已取得上方真mixed-arity結果，仍餘1route待回饋選擇。W已知graph提示真loop另2route／2API完成，無新best；X W64 mixed29改動/保護currentpath已native RUN，source接線中，尚無X PPA。
- **其他有效取捨**：小面積67c D2.399661／A2416／J.930111555僅.339psmargin；較快bbf D2.362535／A2427／J.932080374。W32原ff6f D2.110139／A1299／J.839637150已由O32改善，仍保存lineage，不跨width比較J。[F](../../chia_F_composable_phase/20260924/VERDICT.md)／[G32](../../chia_G32_phase_transfer/20260924/VERDICT.md)
- **Runtime問題已局部修正**：K首call誤用compact catalog陣列，被schema拒絕0EDA；prompt只明確化response object，原raw保存，剩K額度內重開episode。M第三call Flash MAX_TOKENS（77,552 input tokens）後Pro成功，成本照計。J後繼採LOW，不稱受控模型速度比較。Baseline aggregation／compact／有界fallback與成功EDA不重送保持。
- **持久保存**：S155檔／19,671,005bytes已SSD/NAS核對（[checkpoint](../../chia_S_folded_xor3/20260924/archive-checkpoint.json)）；R/cross-arity/VCD scopes297檔／23,502,255bytes及dedup Liberty指向已核對（[checkpoint](xor3-critical-phase-cross-arity-archive.json)）；Q亦已保存。FGH 628檔、I01 100檔、I02+models 102檔均GB10→SSD→NAS逐SHA核對，三份checkpoint已收Git；不與舊重疊scope相加。KMJHL 622檔／65,288,577bytes已三端核對，H manifest摘要重複列項另有correction（unique7 manifests／530 case hashes）；Jfeedback+diagnosis另103檔已保存。N86/85 case與weighted prototype已增量保存：227檔／21,935,721bytes、source manifest SHA dca38a1733…；動態power-delta另存，不與既有重疊scope相加。O32+W32prototype亦289檔／19,429,247bytes三端核對，source manifest3e296822…，含三份wave。
- **資源**：funded project仍`a3-chia-hack26ath-7736`，到期Sep24 14:59 TST。11:20TST API再次確認GCP02／03 RUNNING，region T2A240／300包含其他owner；不用這個數推論Vertex剩餘容量。本task僅GCP02 `34.177.89.85`／`chia-arm64-eda-02`、GCP03 `136.110.23.198`／`chia-arm64-eda-03`；每次mutation前hostname guard。GCP01／`34.87.98.58`屬其他owner，不使用；P舊IP事件無其他owner EDA，setup嘗試／缺失exit／未見指定paths留存皆記incident。GB10模型、GCP CPU EDA、M4輕量指揮分層；native deadline **2026-09-24T06:30Z＝14:30TST**，不是台灣06:30。沒有新增VM／付費project。

## 接手後已取得的可用增量

- **前一incumbent：437加shared star318，圖b00ff2fa**。真CHIA **D2.398144ns、A2416µm²、J0.9489461919489333**，三E **2.570336219／1.956616616／0.3816443132pJ**。全proof/fresh三E有效；J再降0.695%，但僅1.856ps時序餘裕，保留437較快parent。[證據](../../chia_star_phase/20260923/run-02.json)。
- **前一incumbent：最後兩組phase，圖437fa753**。真CHIA **D2.371359ns、A2416µm²、J0.9555916600526079**，三E **2.577746927／1.964015246／0.3871342778pJ**。全proof/fixedplacement/fresh三E有效，energy再降但D慢9.739ps；餘裕28.641ps。Phase batch3/3正式完成，[第三筆證據](../../chia_phase_batch/20260923/run-03.json)。
- **前一incumbent：43a79加兩組timing-informed phase pair，圖9c9a0b3f**。模型先要求八個STA查詢，讀回後選347/348與264/265；真CHIA **D2.361620ns、A2416µm²、J0.9595785280178226**，三E **2.588101197／1.974260085／0.3884057514pJ**。全proof/新RCX/activity有效，J再降0.513%，比parent略快。[第二筆證據](../../chia_phase_batch/20260923/run-02.json)。
- **前一incumbent：51652加四組phase pair，圖43a79f8c**。真CHIA/Ray **D2.362417ns、A2416µm²、J0.9645218444604474**，三E **2.598359133／1.984607952／0.3908337021pJ**。全proof/固定位置/fresh三E有效，J比51652再降約2.08%，全三E下降；仍有37.583ps餘裕。[結果](../../chia_phase_batch/20260923/VERDICT.md)。
- **前一incumbent：e5e加305/307局部phase pairing，圖51652d64**。真CHIA/Ray **D2.359302ns、A2416µm²、J0.9850206152250747**，三E **2.619733568／2.005280985／0.4086328772pJ**。全pre/finalproof與fresh三E有效，J相對e5e降0.263%，三E均降，D慢0.449ps；固定位置且實際同尺寸。Source08a1fa4與90-file matched raw見[結果](../../chia_e5e_local_phase/20260923/VERDICT.md)。
- **前一incumbent：在f441上組合327_A rotation，圖e5e837de**。真CHIA/Ray得 **D2.358853ns、A2416µm²、J0.9876137311390889**，三E **2.625896304／2.008363954／0.410271241pJ**；全pre/final proof、cell/master/placement守衛、新RCX與三profile皆PASS。相對f441，J降約0.0801%、D快15.057ps、area相同；uniform E略增，不稱各profile全勝。NativeFlash先選COMPOSE，原單獨327_A超時的經驗不被當成此組合的PPA預測。Source`ead8529`與90-file GCP/GB10/M4 matched raw見[結果](../../chia_top1_E_f441_rotation_complement/20260923/VERDICT.md)／[receipt](../../chia_top1_E_f441_rotation_complement/20260923/receipt.json)。
- **前一incumbent：338a/v8 → 兩次pin ECO → `_318_` selective downsize，圖f44102a9**。D **2.373910ns**、J **0.9884059071531012**、A **2416µm²**；三E **2.626159403／2.006511349／0.4115977572pJ**。相對原f59/v8，J降約0.153%、D快23.677ps、area少8，時序餘裕26.09ps。模型根據舊圖唯讀through-path資料選縮小單一XNOR2；真CHIA/Ray、parent→pre/final全輸出proof、新RCX/三profile PASS。這支持在b441上補足endpoint-worst-path工具漏選的價值，沒有證明pin ECO是必要前提。Source `5b9032e`、terminal `94feb8d`；GB10/M4完整88檔SHA相同，原f59保留。[結果](../../chia_top1_B_b441_selective_downsize/20260923/VERDICT.md)／[完整receipt](../../chia_top1_B_b441_selective_downsize/20260923/receipt.json)。
- **前一incumbent：W64 `338a/M0/F1-v8`**，D2.397587ns、J0.9899229945846846、A2424；三E為2.629275259／2.010854514／0.4121138772pJ。全輸出proof與同context三profile量測PASS；相對原v4 J改善0.14644%、面積少10，但只剩2.413ps時序餘裕，原v4保留較快取捨。收益主要來自stress profile；其餘兩E略高，不能稱各指標全勝。Source83861e8、newrouted f59eb860...；[證據](../../chia_top1_B_recovery_proxy_v8/20260923/RESULT.md)。
- 原待整合的 B-047c／B-batched、path-guided 工具已在main；packed v2 bridge、原4筆proof-only及b271一次獨立retry已在main。原4筆為2PASS／2UNKNOWN，b271 retry真CHIA PASS（wall0.839008s），338a缺exact frontend未送retry，原UNKNOWN保留。有效proof新能力沒有被這個局部缺檔阻塞。[證據](../../chia_linear_cut_bitset/20260923/chia_v2_closeout.md)
- RTL power complement完成0mapped／4submitted：1筆artifact-root前置失敗、3筆真EDA。047c由外層Flash選；後兩筆由內生W5 Flash事前plan選93a5、真J回饋觸發e623。三候選v5均與各自v4相同PPA，沒有新收益；有downsizing不等於有新收益。[結果](../../chia_top1_B_rtl_power_complement/20260923/RESULT.md)
- F1-v7真runtime先選338a，收結果後再選e623；2route皆全proof／3profiles PASS，均未改進同候選PPA。recovery target由2.35放到2.40後，GR proxy slack仍為−0.145790／−0.051511ns；不是所有physical方法飽和。[結果](../../chia_recovery_slack_v7/20260923/README.md)
- Dual whole decoder：runtime選rank2→真mapped→模型stop，1mapped／0route。功能PASS但D4.447206ns；public syndrome[5]/status負載重組出現fanout36。新57..63窗口episode降至D2.526625ns、A2478.6272、critical-path最大fanout8，仍慢於047c parent2.137598ns。data19原source未改但mapper改成OR4關鍵級，說明影響跨越窗口。[whole](../../chia_top1_dual_selector/20260923/whole_decoder_verdict.json)／[window](../../chia_top1_dual_selector/20260923/window_57_63_mapped.json)
- v8模型在初始plan兩個分支都預選047c，所以第二parent不是因量測改變；只宣稱真model預排與實測硬體增益，不冒稱adaptive後繼。其後獨立B-v8-newparents依真feedback重新決策：Flash選93a5（D2.402124超限），Flash兩次429後同prompt Pro選續跑e623（D2.391748、J0.996973502，可行但非global best）；2route額度完整封口。
- 窗口三mapped已全部完成：57..63／60..63／63的D為2.526625／2.495062／2.838134ns，皆proof PASS但劣於047c parent。模型最後STOP，0route；Flash429/500、Pro一次選window63、最後Flash stop完整保留。[完整結果](../../chia_top1_dual_selector/20260923/window_final_verdict.json)
- 上述兩筆dual原q_E錯用routed b271分母，已保留as_run並標**INVALID_REFERENCE**；raw E/D/A/proof有效，過去模型prompt未使用錯ratio，不重EDA。後續request從exact047c mapped receipt讀三E，明示parent-relative mapped reference，不能當routed J。

## 最近完成的下一波

- F1-v9將完整mapped SHA與1ps recovery target接進所有implementation/measurement/cache/pending keys；內生Flash選338a alpha0.5→2.560ns，真CHIA得到與v8相同f59e圖與PPA，讀回饋後STOP，實際1route而非用滿2。[receipt](../../chia_f1_v9_calibrated/20260923/receipt.json)
- Root指定的W32/v8一次固定工具轉移：功能、同W32 MASKED分母三profile皆PASS，與原W32 F0同D/J/A/E/graph；proxy slack+446ps仍0resize，只否證此W32 parent設定。[receipt](../../chia_top1_B_w32_v8_transfer/20260923/RESULT.md)
- 047c正相clone由內生Flash選v4，真route D2.362788/A2415/J1.001212，比parent快35.259ps但能量較差；模型再選v8也同圖同PPA。Negative NOR3+3NAND3版本由模型先選probe、讀真proof/STA後選v8，D2.393446/A2404/J1.004111，面積省但能量更差。全域phase版本由root選mapped診斷，再由Flash選v8，D2.413222超限13.222ps/J.998072。三條線全功能與測量均有效，沒有新energy winner；import/CLI/LEF前置失敗全留帳。[positive](../../chia_mapped_load_split_route/20260923/README.md)／[complement](../../chia_mapped_load_split_v8/20260923/README.md)／[negative](../../chia_mapped_load_split_polarity/20260923/README.md)／[global](../../chia_top1_B_global_phase_route/20260923/RESULT.md)
- Recovery threshold kernel已真跑10次診斷（3權限FAIL+7有效），0新detailedroute/RCX/power，診斷Docker wall合計19.945s、API成本另列。獨立clean prefix在2.525/2.540得到兩inv類、2.550/2.560/2.575/2.700得到四move類；2.700第二pass無新move。只有已測[2.540,2.550]兩端不同，未細測中間、不得宣稱連續區間或普遍cost優勢。模型提名兩inv圖，但root核出其為歷史v7 exact4b8圖；功能proof匹配可引用，target不同不借finalPPA，也不浪費route重新找舊成果。[final](../../chia_recovery_threshold/20260923/final_verdict.json)／[歷史比對](../../chia_recovery_threshold/20260923/historical_match.json)

## 最新物理互補結果

- 第一筆 pin ECO 由 native Flash 選 `_328_` XNOR3 的 B↔C，**直接 Python→Docker EDA 原型，未經 CHIA Ray**。完整 proof 與 fresh route/RCX/三 profile PASS，D2.365314、A2424、J0.990335610936；三E為2.630400704／2.012901823／0.4120333688pJ。比最低J方案快32.273ps，能量稍高。[結果](../../chia_top1_B_postroute_pin_eco/20260923/RESULT.md)
- 第二筆從第一筆真量測的新critical path選 `_384_` OR3 B↔C，native Flash 決策後**真 CHIA/Ray**執行。兩階段全輸出proof/fresh三E PASS，D2.359425、A2424、J0.990428573670；三E為2.631109965／2.013202902／0.4119766891pJ。再快5.889ps但J稍升，保留較大時序餘裕取捨；當時最低J為338a/v8；目前已由selective downsize再改善。[結果](../../chia_top1_B_postroute_pin_eco_02/20260923/VERDICT.md)
- 第一pin-ECO後的extracted-RC power recovery：首submission hash前置失敗、0EDA；獨立修正retry接受0move，netlist/ODB byte-identical，不重route或profile、不稱新收益。兩筆皆計提交額度。[結果](../../chia_top1_B_pin_eco_power/20260923/VERDICT.md)
- F1-v10 timing-driven placement在338a保留19個buf4，D2.368223、A2517、J1.014394300；v11只將GPL resize改成virtual，mapped/pre logical cells288→288，D2.365689、A2431、J0.997526545。兩者均有完整mapped→placement→final proof與fresh三E；各模型episode測首筆後STOP，未自動用完第二route。v11改善v10的buffer代價但未胜最低J。[v10](../../chia_top1_B_timing_driven_placement/20260923/VERDICT.md)／[v11](../../chia_top1_B_virtual_timing_placement/20260923/VERDICT.md)
- 另開root固定選擇的28b/v11診斷，不改上述模型STOP：真CHIA、兩階段proof與fresh三E PASS，D2.440104仍超限40.104ps、A2479、J1.014623464；三E2.66195013／2.048502356／0.430237269pJ。相對28b/v2省面積/能量但延遲略差，只否證此配置。[結果](../../chia_top1_B_28b_virtual_probe/20260923/VERDICT.md)

## 最新結構診斷與活躍工作

- 兩級arity episode已完成：內生Flash先選XNOR2→XOR2，讀慢110.436ps的真回饋後選XOR2→XNOR2，再读慢81.105ps後STOP。全74輸出miter皆PASS；同context ideal D為2.294354／2.265023ns，parent2.183918。最差路由data29換成data61，末級slew倍增，下級inverter慢約50–57ps。**兩筆是直接pinned Docker EDA，不是CHIA/Ray**；worker早期訊息曾誤稱，live ledger已更正，未重跑補歸因。此前positive/negative load-split mapped probe同樣direct，其後route才是CHIA/Ray。這些是執行方式更正，不變更已驗證功能或實測值。[結果](../../chia_late_arity_split/20260923/README.md)
- 兩級末級drive2會令cell總面積超過原XNOR3，未立即再開矩陣；另開單級XNOR3_2針對output slew的不同機制。既有兩級episode的STOP與未使用route額度保留。
- Flash提供的新decoder minterm grouping已被現有參數涵蓋，第二次model REJECT，0EDA。其首回原模型raw被後續worker誤覆蓋且尚無副本，不能再宣稱raw可核；第二回raw與prompt保留，正式更正由owner收口。這只影響0EDA假說判別的第一回model trace，不涉及硬體量測。[記錄](../../chia_338a_energy_hypothesis/20260923/README.md)

| Owner／模型／執行 | 現況與有界額度 | 下一步 |
|---|---|---|
| Root／native Vertex／GCP02 | Auto pin-swap完成：D2.373509/A2416/J.988116465 | 新route/RCX/全proof/三E有效，改善自身f441 parent但未勝e5e；exact prefix reuse避免重做成功步驟。[結果](../../chia_top1_E_auto_pin_swap/20260923/VERDICT.md) |
| Root／native Vertex／GCP02 | f441＋327_A真route已完成新best | 兩次Pro本機Ray前置失敗（0EDA）與局部1次超額如實入帳；root修正實作後獨立GCPretry成功，舊tmp最後snapshot與兩次trace保存。 |
| GB10 native Flash／root／GCP03 | cancellation SLP20個abstract設定完成，0mapped/route | 17個係數有效、3個depth-limit拒絕；未比radix2更少XOR2且0retained cancellation。轉置樹3mapped/1route已完成，功能有效但不具物理收益；模型STOP。[結果](../../chia_transposed_tree/20260923/VERDICT.md) |
| GB10 Flash/Pro／GCP03 | 局部樹2mapped/1route完成，模型STOP | 新RTL D2.36636/A2427/J.999282533可行但未勝；保留工具與負結果。[結果](../../chia_local_tree/20260923/VERDICT.md) |
| GB10 Flash/Pro／GCP02 | Phase batch3/3完成得437fa753 | 原額度不延長；兩次READ_TIMING均有實際query/feedback，第三筆先澄清model操作語義再執行。 |
| GB10 Flash／GCP02 | W32 phase1/1完成，獨立W32 best18644d78 | D2.061026/A1299/J.867296083，對自身強parent再改善1.938%，不與W64比較。[證據](../../chia_w32_phase_transfer/20260923/VERDICT.md) |
| Root／Flash／GCP03 | W64 frontier pin已完成，D2.427235不可行 | 兩個換腳使cell arc慢37.284/17.891ps；保留437，原1前置failure加1retry全記。[診斷](../../chia_frontier_pin/20260923/VERDICT.md) |
| GB10 Flash/Pro／GCP03 | Shared star2/2完成，b00ff2fa新最低J | 308失敗；318成功但timing預測錯，critical已換支線。[證據](../../chia_star_phase/20260923/VERDICT.md) |
| GPT-6 Luna／Sol／GB10 | kernel／executor／episode已main，修真pilot接線失敗 | 新parent不再要改硬編碼source；先只接已實測same-footprint pair/star，2route pilot，不建通用平台。 |
| GB10 Flash/Pro／GCP03 | Mixed phase1/1完成 | 對自身parent微幅J改善，但未勝437；保留取捨與完整173檔。 |
| M4 Astra | main整合、完整帳目、持久保存與研究接續 | 先前Codex協調子agent曾quota耗盡；2026-09-24 fresh查詢ordinaryUsageAllowed=true，GPT6 Luna/Sol已實際恢復；3個Flash coding各35步無source，兩個Pro生成骨架後root修正實際接線。已授權Vertex/GCP仍可用，沒有改個人付費project。 |

B-f59 transfer已真Ray完成：全proof/3E有效，D2.416267超限、A2416、J.9884829196，未勝f441；首次模型STOP與一次局部/全局slack事實澄清後TRANSFER完整保留，不把J反事實算術當預測。[結果](../../chia_top1_B_f59_selective_transfer/20260923/VERDICT.md)
B旋轉先選327_A/B，兩筆fullproof PASS、ideal差異僅0.003/0.005ps，未收到完整counterexample path。模型選327_A route後D2.408977超限、A2424、J.9890255963；兩條input改接確實存活，其餘cell masters與原f59完全相同。[結果](../../chia_mapped_xor_rotation_runtime/20260923/README.md)
新E-criticalpath提供parent/child完整top3 path後，模型選326_A→B→C→STOP，3真Ray mapped proof均PASS，idealD2.201935/2.183923/2.183921，0route。A將critical換到data68、B/C未移走原critical；這是模型實際使用反例的trace，沒有新的硬體gain或普遍模型優勢主張。原429/截斷0EDA嘗試保留。[結果](../../chia_criticalpath_rotation/20260923/README.md)
單級XNOR3 drive2真Ray mapped改善21.549ps，但v8將其縮回1且改變其他masters；final D2.423043超限/A2429/J.9915380331，不是wholegraph NOP。[結果](../../chia_xnor3_drive2/20260923/README.md)
可選cell power首次f59 run產生完整JSON後因NULL Liberty object中止TSV；原3E有效，原錯誤保留。三JSON各554unique cells、加總與原report最大差2.77e-11W，另以exactnetlist解析獨立mapping才作功率歸因：其餘XOR/XNOR在stress/uniform/low佔61.78%/67.76%/95.11%，僅屬該超時f59圖。NULL修版唯讀metadata smoke899行通過；其後e5e與auto-pin兩筆必要新量測皆完整JSON/TSV成功，沒有重跑舊power；原量測接線15項測試PASS。[歸因與限制](../../chia_f59_instance_power/20260923/README.md)

新的source修正包含安全UUID／fail-closed artifact目錄、讀原始mapped proof receipt、不重建PASS envelope；v7 driver追加持久submit-intent以免SSH中斷後換UUID重送同index，既有兩筆結果不重跑。

## 資源、驗證與保存

- 最新recovery／轉置樹／cancellation三組735個regular files已SSD/NAS逐檔SHA匹配，兩端manifest `m4_recovery_transposed_nas_verified.json`；範圍不與舊checkpoint相加。原生Vertex新增opt-in reasoning level，default request不變，直接10項測試PASS；Flash LOW已完成實際分析與工具source輸出。[說明](../../chia_vertex_thinking/20260923/README.md)

- GCP02／03 fresh核實各48vCPU；01及其他project保持原owner。接手時T2A使用240／300vCPU；配額不是保證stock。GB10 coding明確Flash3.8，內生runtime另有原生Vertex call與實際CHIA/Ray worker identity。外層OpenCode model-turn400與原生429/500均保留；已使用mini-vertex替代，不反覆原樣重試。
- 同funded project `a3-chia-hack26ath-7736`；期限仍**2026-09-24 14:59 TST**，未切個人付費project。M4只輕量工作，Python全conda。
- 原核心suite一次為915PASS／219skip，另1個既有release allowlist缺`ecc_masked_direct_xor`，非本次研究回歸，不阻塞實驗。後續只檢查改動：F1接線23PASS、proof/power整合45PASS、dual接線29PASS、v7原focused8PASS、v9合併後50PASS；最新v10/v11/Vertex整合的59個相關測試通過（58項首跑，移除過時hint文字assert後單項重試行為測試通過）；SSH中斷重送修正另2個直接測試PASS。不為static receipt增加永久測試。
- M4持久mirror：`/Volumes/SKC3000D2048G/VegaExternal/Projects/260908_CHIA_Hackathon/Artifacts/chia-top1-20260923/`。B-047c/B-batched/path-guided/portfolio324檔已GB10→M4→NAS逐檔SHA核對，manifest `m4_takeover_20260923.sha256`；power-complement320檔、v7完成版166檔及packed raw亦已M4驗證。
- NAS selected root `/Volumes/BerryHead/projects/260908_CHIA_Hackathon/Artifacts/chia-top1-20260923/` 已建立；dual兩線raw亦由owner保存SSD/NAS。只對已驗證checkpoint主張有副本，不假設GCP disk/bucket到期後可靠。RayOpsRegistry已同步owner/workspace/NAS入口。另10組1393個manifest entries與pin/placement相關8組2306個regular files已M4/NAS逐檔SHA核對；兩份checkpoint範圍可重疊，不相加作unique檔數。

以下保留前一輪完整incumbent、取捨與歷史實驗摘要；舊「正在執行」與137／41計數已由上面及live ledger取代。不要依歷史快照重新提交。

## 最強可用方案與新取捨

W64目標 `routed3_w64_d240_b271F0_v1`：所有輸出D≤2.40ns；J是三profile相對固定b271/F0能量比的幾何平均。三能量欄順序為stress_encoded／valid_uniform／valid_low_toggle，單位pJ；各1024 vectors、10000ps間隔、0.05ns slew、0.005pF load、tt025C1v80。Mapped q_E不與routed J混比。

| 候選／mapping／flow | D ns | J | Area µm² | 三能量 pJ | 狀態 |
|---|---:|---:|---:|---|---|
| b271／M0／F0 | 2.526346 | 1 | 2392 | 2.541007707／2.027927403／0.4358843944 | 不可行，參考分母 |
| **eefeb2af／U02同graph新route** | **2.375888** | **.8948591221** | **2425** | **2.468786261／1.853478461／.3517407458** | **最低已量測可行J，非新Boolean gain** |
| eefeb2af／S02雙XOR3相位縮寬 | 2.374088 | .8951799620 | 2425 | 2.470198669／1.854111761／.3517976802 | 快1.8ps，margin25.912ps |
| 67c95564／b00六phase no-fold replay | 2.399661 | .9301115552 | 2416 | 2.524363517／1.910615392／.3747224036 | 保留小面積取捨，margin0.339ps |
| 60e350de／bbf＋pair302/303 | 2.389404 | .9304365426 | 2427 | 2.530565253／1.906410325／.3750214091 | 保留10.596psmargin |
| **bbf15474／244＋batch274/330** | **2.362535** | **.9320803737** | **2427** | **2.534645901／1.911262370／.3754500722** | 保留37.465psmargin |
| 244543a8／234再加STAR271 | 2.362283 | .9379139528 | 2427 | 2.550519130／1.926686964／.3771194679 | 略快取捨 |
| **234c2a9a／1b再加STAR266** | **2.364892** | **.9406441092** | **2427** | **2.559028508／1.934800093／.3775674122** | 前一最低J |
| **1b904211／fold2＋STAR311＋STAR258** | **2.373085** | **.9444228398** | **2427** | **2.569547214／1.944607502／.3786522939** | 前一最低J，保留較小A的fc |
| **fc806b8a／star318＋star320＋star311** | **2.373917** | **.9476580854** | **2416** | **2.565100149／1.951085724／.3819478297** | 較小面積取捨，margin26.083ps |
| eeaba1f3／fc再加STAR304 | 2.365660 | .9503381869 | 2416 | 見v3-result同一候選三E | 更快、J較差取捨 |
| 5b007892／b00 syndrome2折INV | 2.363135 | .9514660681 | 2427 | 2.583332825／1.958906068／.3823099905 | 新結構時序餘裕parent |
| **338a／v8＋pin ECO×2＋downsize＋327_A＋phase305/307＋phase4+2+2＋star318** | **2.398144** | **0.9489461919** | **2416** | **2.570336219／1.956616616／0.3816443132** | 前一最低J，low-toggle E略低於fc；餘裕1.856ps |
| 338a／v8＋pin ECO×2＋downsize＋327_A＋phase305/307＋phase4+2+2 | 2.371359 | 0.9555916601 | 2416 | 2.577746927／1.964015246／0.3871342778 | 保留較大餘裕parent437 |
| 338a／v8＋pin ECO×2＋downsize＋327_A＋phase305/307＋phase4+2 | 2.361620 | 0.9595785280 | 2416 | 2.588101197／1.974260085／0.3884057514 | 前一9c9a，較快取捨 |
| 338a／v8＋pin ECO×2＋downsize＋327_A＋phase305/307＋四組phase | 2.362417 | 0.9645218445 | 2416 | 2.598359133／1.984607952／0.3908337021 | 前一43a79，逐列保留 |
| 338a／v8＋pin ECO×2＋downsize＋327_A＋phase305/307 | 2.359302 | 0.9850206152 | 2416 | 2.619733568／2.005280985／0.4086328772 | 前一51652，略快取捨 |
| 338a／v8＋pin ECO×2＋selective downsize＋327_A | 2.358853 | 0.9876137311 | 2416 | 2.625896304／2.008363954／0.4102712410 | 前一e5e，略快取捨 |
| 338a／v8＋pin ECO×2＋selective downsize | 2.373910 | 0.9884059072 | 2416 | 2.626159403／2.006511349／0.4115977572 | 前一f441，保留uniform較低取捨 |
| 338a／M0／F1-v8 | 2.397587 | 0.9899229946 | 2424 | 2.629275259／2.010854514／0.4121138772 | 前一incumbent，保留原圖f59 |
| 338a／M0／F1-v4 | 2.372445 | 0.9913747531 | 2434 | 2.641682804／2.010296885／0.4120997983 | 保留較快、較大餘裕取捨 |
| **047c／M0／F1-v4** | **2.398047** | **0.9940157268** | **2399** | **2.606789931／2.001151879／0.422886078** | 新低面積取捨，非J winner |
| **e623／M0／F1-v4** | **2.345434** | **1.002362742** | **2436** | **2.661167237／2.029861935／0.418760574** | 新較快取捨，非J winner |
| 338a／M2_D2000／F1-v5 | 2.365369 | 1.0038091327 | 2480 | 2.677490993／2.035439684／0.4168663872 | 被e623在J/D/A上支配，但其low-toggle E略低 |

047c完整ID `ecc-047c53d8c62ecf2c`，source SHA `f2e1304419b7cee4f98540739aceb9091a240dfbc38a71b67197ce03d2299181`、mapped SHA `c736b09625d152aaa6f9a0021ee9b3b076a375c80a706ed8689f09adc44d6f94`。Action為radix2、bit_order `6,5,3,4,2,1,0`、tree a2/b3/AC、decoder_perm `0,1,2,4,3,5,6`。相對338a/v4兩個高活動profile能量與area較低，但low-toggle與delay較差，不宣稱全archive新frontier。索引見 `review/chia_top1_surrogate_exploit/20260923/parent-047c.json`。

F1-v4在v2後接受兩個inverter縮小。Matched control只移除recovery、保留相同incremental DPL/route，完全重現v2，支持這次縮小加配套佈線的7.453ps與J約0.074%收益。v5擴大端點到100：M0與v4同點，M2多四個cell變更而改善J/area。v6最多三輪，M2第二輪0moves、前後Verilog相同，最終指標同v5；不外推成所有物理方法飽和。見 `review/chia_power_endpoint100/20260923/` 與 `review/chia_power_multipass/20260923/`。

W32固定轉移已完成：独立goal `routed3_w32_d240_maskedF0_v1`、分母 `ecc_masked_reduction::F0::routed3_w32_v1`。

| W32／F0 | D ns | J | Area µm² | 三能量 pJ |
|---|---:|---:|---:|---|
| MASKED | 2.248806 | 1 | 1836 | 1.595184585／1.140097229／0.3278113945 |
| **投影b271＋三組phase** | **2.061026** | **0.8672960832** | **1299** | **1.363066986／0.9591930575／0.2974786548** |
| 投影b271 parent | 2.049337 | 0.8844328925 | 1299 | 1.379291207／0.9746563592／0.3068061415 |
| selector33/p5 child | 2.435600 | 0.9777794640 | 1373 | 1.500555227／1.084425239／0.3424900933 |

Parent全功能／mapped／routed確認PASS；delay−8.87%、J−11.56%、area−29.25%。這是固定規則跨寬度重用，不是模型自主發明或selector收益。Child不可行。原parent mapped q_E錯用routed分母，保留原值並標INVALID_REFERENCE，不主張mapped增益。可用source在 `candidates/ecc_top1_w32_projected_b271/`，證據在 `review/chia_top1_w32_transfer/20260923/`。

## 真runtime決策與已完成實驗

- 首late-select pair的人指定候選／順序與模型predicate分開記錄。其後free-choice的三次route中，Flash依b271/ad71失敗回饋選338a取得首可行解。見 `review/chia_top1_freechoice/20260923/`；模型latency/retry與EDA時間分列，沒有普遍成本優勢主張。
- B adaptive RTL：12mapped／4route、7次Flash呼叫、真kernel展開與回饋後繼；10個全proof PASS、2個UNKNOWN未獲route資格。四route都不可行。見 `review/chia_top1_B_adaptive/20260923/`。
- C公平比較：共享12fresh mapped，兩臂各12logical mapped／4logical route；6actual route與2opaque cache hit。共同incumbent未改進而平手；只看新query，fixed最佳J1.034309優於Flash1.046497。不比較cache造成的walltime，不追加C。見 `review/chia_top1_C_policy_compare/20260923/`。
- B surrogate：上限32/8，實際16mapped／8route。Flash先選parent/mode，controller才呼叫ridge kernel生成未seen candidates，並使用真mapped/routed回饋；047c是可用成果。Root於checkpoint提供047c新parent，但模型未選，原trace保留。沒有普遍優於盲採樣的主張。見 `review/chia_top1_surrogate_exploit/20260923/`；raw `ART/surrogate-exploit/`。
- B-047c stepping-stone：root明示以runtime已找到的047c為起點，實際8mapped／4route。先energy工具四候選，三route未勝；Flash接著選外層新建的path-guided工具四候選（未經外層EDA預篩），最後route e623。e623 mapped D反而較差86.624ps，但routed改善52.613ps：syndrome4下游由OR3高負載改為NOR2_2加AND4。收益是時序取捨，J/area比047c差。外層path-guided reservation实际0，計帳全歸此runtime，未重跑。

## 新能力、有效範圍與近期負結果

- Learned proposal kernel：3085筆coherent資料、3002個energy groups，holdout605；ridge q_E MAE0.013948、rho0.686902、top-decile retrieval0.35，略勝RFF。它只提供候選排序；RFF seed disagreement不是校準不確定性。Model/schema/seen hashes、selected-action invocation與輸出SHA保存；新run已materialized／UNKNOWN／FAIL語意都排除重複。
- Timing metadata：只有837筆common-IO（667train/170holdout），2248 legacy值未混訓。固定ridge D-head輸給1NN（MAE0.4489對0.3624ns），不採用弱head，保留有明確context的鄰近資料。常數同分排序的4.76%不是隨機期望，也未主張顯著性。見 `review/chia_common_io_delay_head/20260923/`。
- Exact source proof：strict continuous-assign AST與GF2 quotient使W64每output rank≤9，全部74outputs共35328 quotient states確認；不是抽樣。b271/338a及原兩個120s UNKNOWN來源均PASS。實際CHIA proof-only兩task亦PASS，每case約6.2s；原Yosys UNKNOWN保留。
- Opt-in `source_proof_method="linear-cut-first"` 已接formal/node/batch/W5；width64、pinned bridge、checker/reference/golden hashes、frontend與source bytes綁定。Counterexample FAIL不能fallback，UNKNOWN僅明示fallback；既有artifact不可覆寫。Bridge在 `review/chia_top1_linear_cut_proof/20260923/golden_bridge.json`，SHA `d5c9cbe00621a9ba444c69f667611d910299b5ccea1db72556a474398ad07751`。大批新mapped已實際使用，非只改request標籤。
- M1只加ABC delay target的四次映射回到原圖；M2 explicit driver/load得到真實映射差異但需付能量成本。Depth-aware join抽象深度較小、實測卻變慢。M3排除NOR4後整條path仍變差；M4 classic map及M5 classic dch+map令XOR結構劣化，兩者各兩mapped負結果，沒有route。
- Direct/cofactor/selector/joint舊負結果保留各自scope；兩個joint source UNKNOWN不充作winner。既有q_E紀錄0.663424472257尚未被本輪刷新。已知338a八點鄰域全為歷史已測，於dispatch前取消、0新EDA。

## 現在的研究與分工

| Owner／模型／主機 | 工作 | 已開始或下一個增量 |
|---|---|---|
| planner_worker／GB10 Flash3.8／GCP03為主 | B-batched-frontier，64mapped／4route | 先16一批看回饋，48已提交、0route；完成pool後選4route。父代338a/047c/e623、energy/diversity/改寫family由runtime選 |
| rtl_exec_recovery／Sol協調GB10 Flash3.8 | bounded Yosys-first→quotient portfolio | 易證case先5s Yosys，未知才quotient；四既有source proof-only、0新EDA，量真成本而不假設cut-first永遠快 |
| mapping_exec／Sol協調GB10 Flash3.8 | packed bitset proof prototype | 同quotient classes用bigint平行精確求值；獨立backend，先比較scalar/packed與mutants，不改現有checker/gate |
| M1 Astra root | 研究取捨、main整合、跨worker去重、持久保存 | 小成果即整合；完成的power/classic批次不再原樣重試 |

Batch2初選338a-basis時kernel判定unseen pool為空，0新EDA；錯誤與plan保存，該action排除後再選047c-local。不能把pending或預期dispatch當成actual提交。便宜availability由程式計算，不讓模型重試已知空空間。

## 額度、資源與保存

本checkpoint提交**137 mapped／41 route／18 extra anchor profiles**，含失敗。Route41中power100含1次Docker create前端失敗、v6含1次OpenROAD失敗，重試均另計。C另兩次exact cache query只計logical。B-batched第三批16已submit但未必完成，詳見ART ledger。

基本上限544mapped／72route；條件擴展總800／104不能相加。局部批次不是整場研究上限。GCP02/03各48vCPU，01其他owner保留；大批mapped可用03上32CPU、02上16CPU，仍計入子程序threads/RSS，與其他本task工作協調。

GB10 Vertex與GCP同funded project `a3-chia-hack26ath-7736`，期限2026-09-24 14:59 TST；不轉個人付費project。M1/M4只輕量指揮、Git、檢視與傳輸。GB10 coding model、runtime model、實際GCP EDA各有獨立身分與紀錄。

持久副本：GB10 ART與M4 `/Volumes/SKC3000D2048G/VegaExternal/Projects/260908_CHIA_Hackathon/Artifacts/chia-top1-20260923`。anchors、pilots、W32、B/C、各mapping/repair證據已有雙份；新的surrogate/proof/M5/v6正增量mirror并逐檔核對。GCP disk/bucket不是到期後唯一保存。

承諾切面：新RTL/工具真runtime與後繼、W32重用、公平比較均已執行；source/receipt持續進main。能量最佳解保持，新增低面積與較快中間點；仍在授權期限內持續探索，未宣告Top-1或全局完成。

本次一次性錨點釐清：338a同RTL SHA63ad383d…已由source-proof portfolio對pinned common_cells golden完成74/74等價且拒絕mutant；mapped_exact_miter PASS的694baac7…亦與F1-v8輸入一致。舊packed-v2 UNKNOWN是另一frontend缺bench_meta.json，仍保留UNKNOWN；不構成目前功能錨點缺口，不重跑proof。
