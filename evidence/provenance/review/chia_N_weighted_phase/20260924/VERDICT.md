# N｜實測 power 重要度導引的 phase 指派

N 已封口：2route／2次native Flash LOW，原J、K、M預算不變。下表每一列屬同一候選，固定W64三profile／原分母／D≤2.40ns。

| 候選 | D ns | A µm² | stress／uniform／low E pJ | J |
|---|---:|---:|---|---:|
| J：8e038f9f | 2.376334 | 2427 | 2.476976952／1.859090553／.3547985398 | .8993419995 |
| N01：053c7242 | 2.369255 | 2427 | 2.474159992／1.856979507／.3530194954 | .8971559836 |
| N02：320970ab | 2.375917 | 2427 | 2.472119231／1.854768634／.3532727351 | .8967674921 |

三列皆有完整功能proof與新route／RCX／三activity量測。N01對J：面積相同、D快7.079ps、三E全降，J相對改善0.2431%；N02對N01：J再降，但D慢6.662ps、low-toggle E增加，故保留N01的30.745ps餘裕與較低low E。N02餘裕24.083ps，是目前最低可行J，並非所有欄位都最好。

N01與J同為37XNOR、同34個frozen phase nets／33個受保護gate。搜尋目標改為原bbf三profile的每gate `internal_w / whole-design total_w` 平均重要度；一次22s有界GF(2)求解產生不同位置的41個改動。權重是重要度代理，沒有XOR/XNOR反事實能耗、glitch模型或精準PPA預測。代理值由.091994降至.085038（−7.56%），不可寫成實際J改善7.56%。這是單一exploit候選比較，未證明加權方法具有統計上的普遍優勢；同count卻不同實測結果說明count不足以替候選排序。

外層Flash／Sol提供權重與程式，native Flash在讀J/H/I回饋後[選擇量測](n01-model.json)。source `2d0a5f4265e496cd5e8e7d2722c247e9afed6fbe` 已main；prototype首次外層Flash呼叫遇本地unpack錯誤，已計呼叫，HTTP／usage／raw遺失明列UNKNOWN/MISSING，第二次完整保留，未捏造原始證據。這不影響N的正式native proposal與完整EDA證據。

N02用現有source6a67a polarity loop，提供真J02 STAR270失敗receipt及hash-bound `_316_` arc增77.766ps診斷。舊J並未作selectable parent，歷史仍獨立通過receipt／proof／三檔hash／native decision驗證；全部legal actions保留，原保護集合不是新增硬gate。Flash讀回後[選原N親本的pair299/300](n02-decision.json)，取得新320970ab。這是含歷史物理回饋的實際後繼，不把不同parent的舊arc差當新圖必然結果。

N01新pre wholeproof PASS1.097s、N02 PASS1.158s；各自pre/final網表bytes相同，final只重用本次新proof及完整相同context。86／85個case檔案逐SHA核對；GB10 source/raw/native logs在 `.../chia-top1-20260923/N-weighted-phase-assignment/`，SSD／NAS已逐SHA驗證227檔／21,935,721bytes（N全campaign與weighted prototype），動態power-delta診斷另存未納此scope。[N01 receipt](n01-receipt.json)／[診斷](n01-diagnosis.json)、[N02 receipt](n02-receipt.json)／[診斷](n02-diagnosis.json)、[proxy與provenance](prototype-summary.json)。

接續兩個獨立未知：在既有W32約290ps timing餘裕下轉移global phase方法；將新phase映到已驗no-fold結構，檢查面積／energy與timing代價。兩者先純proposal/identity核對，尚無新PPA；不為延續N而擴充已封2route額度。
