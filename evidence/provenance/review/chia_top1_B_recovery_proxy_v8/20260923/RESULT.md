# B-recovery-proxy-v8：首個可行 J gain

本獨立 episode **0 mapped／2 route submissions 已用完**，兩筆均為 GCP02 真實 `jobs=1`、2 CPU route，whole-output proof、route 與三 profile measurement 全部 PASS。第一筆 338a/M0/F1-v8 刷新可行 J；第二筆 047c/F1-v8 沒有增益。搜尋 incumbent 338a/M0/F1-v4 的 D=2.372445 ns、A=2434 µm²、J=0.9913747530659007，三能量 2.641682804／2.010296885／0.4120997983 pJ；winner 的固定目標仍是 D≤2.40 ns、相同 b271/F0 分母。

| Attempt | 來源與 flow | D ns | A µm² | J | stress／uniform／low-toggle pJ | 結論 |
| --- | --- | ---: | ---: | ---: | --- | --- |
| `w5-000-2ffde190` | 338a/M0，F1-v8 | **2.397587** | **2424** | **0.9899229945846846** | 2.629275259／2.010854514／0.4121138772 | 可行，新最低 J；相對 incumbent J 降 **0.14644%**、面積減 10 µm²，最終 D margin 僅 **2.413 ps** |
| `w5-001-0c8f03f5` | 047c，F1-v8 | 2.398047 | 2399 | 0.9940157268200335 | 2.606789931／2.001151879／0.422886078 | 可行，與 047c 舊 F1-v4/v5 同 D/A/J/能量/最終 netlist |

兩個 `output.json` 的 `status=OK`、`functional_valid=true`、`route_valid=true`、`measurement_valid=true`、`feasible=true`；proof 方法 `yosys_sat_whole_output_miter`、`status=PASS`。338a 的 final timing 比舊 incumbent 慢 25.142 ps，且離門檻只剩 2.413 ps；這是真實可行結果，也是不應忽略的物理餘裕風險。此結果是 search gain，不聲稱其他 parent 或後續 holdout gain。

模型歸因：四個 qualified mapped parents 338a、047c、e623、93a5 與 v4–v7 歷史量測是 campaign 提供的輸入，非本次模型發明。獨立 W5 Vertex `gemini-3.8-flash` call（HTTP 200、10.216 s）預先選 338a 作 initial、047c 作次筆；它的 `feasible==true` 與 `feasible==false` 兩個 branch **都指向 047c**。真實首筆 feedback 觸發其中一條 branch，但第二個 parent 的選擇並未隨 feedback 改變；不可聲稱 adaptive next-parent gain。模型 plan、完整 prompt/response、state 與兩張 request/output/receipt 都在 raw ART。

F1-v8 是獨立的 GR optimizer proxy context：前段 setup/placement 維持 2.35 ns，後段 recovery clock/max-delay 設 2.575 ns，單次 `recover_power 100`，真實 D≤2.40/J 判準不變。2.575 是根據 338a/M0 舊 GR arrival 2.545790 與 extracted D2.372445 的 0.173345 ns 差距作的**近似先驗**。新 338a OpenROAD raw 在 recovery 前回報 arrival2.545790、required2.575000、positive slack29.210 ps；`post_repair.v→post_power_recovery.v` 實際接受 4 個 downsizes（2 個 `inv_2→inv_1`、2 個 `or3_4→or3_1`），並形成新最終圖。047c proxy slack12.270 ps，只接受 1 個 inverter downsize，最終圖未變。這支持本配置的 proxy 校正有實際硬體效應，不代表校正值可外推所有 parent。

執行 source commit（GCP02 output `source_repo_commit`）為 `83861e81d8bd5658da266b846dc73ba562505d4b`；F1-v8 Tcl SHA256 `99b5db032dc064c496b2e652dfe2e75e5cf356c446d0affcbf15fbda2b140d9a`。兩筆身份如下，完整 hashes／proof／三 profile 位於各自 output 與 raw：

| Parent | Source SV SHA256 | Mapped graph SHA256 | Routed netlist SHA256 | SPEF SHA256 |
| --- | --- | --- | --- | --- |
| 338a | `63ad383d1477316170b2800bcaf0a9b22744c1c5f579c50a35c811e6b6c05b10` | `694baac7b5497db5e4104fc7aaff190e02da7ba99c69de8d728373a8c90e9a16` | `f59eb860ebe91df44cc599272d7da6d83cbf90c6f204162d4776f7fb0737f00e` | `3d0f9e4a1b9dbc94934745e1bc5198ba95af5a94eed0c4633967e56076ec13c2` |
| 047c | `f2e1304419b7cee4f98540739aceb9091a240dfbc38a71b67197ce03d2299181` | `c736b09625d152aaa6f9a0021ee9b3b076a375c80a706ed8689f09adc44d6f94` | `ebcd439446768b9b873c1e378a92db9d935c65724eadb60fe3bd4265ddba62a7` | `4da0ff9c8be6d7212550af3937c4a55aa4e6f525302de387dfd9b4a7e2eba9f4` |

**Raw pointer**：GB10 `/home/thisray/projects/260908_CHIA_Hackathon_artifacts/chia-top1-20260923/recovery-proxy-v8/w5-runtime/`：`run/model_calls/attempt-0/`、`run/state.json`、`run/attempts/w5-000-2ffde190/`、`run/attempts/w5-001-0c8f03f5/`、`raw/w5-000-2ffde190/`、`raw/w5-001-0c8f03f5/`。兩個完整 GCP02 batch tree 各 70 檔，由 GCP 原目錄逐檔 SHA256 核對通過，含 `chia_f1_worker.json`、`openroad.log`、netlist、SPEF/VCD 與三 profile；GCP 原件仍保留在對應 `recovery-proxy-v8/w5-runtime/batches/`。W5 state `route_submitted=2`、`mapped_submitted=0`，global campaign 帳由 root 管理。本 episode 不再提交新路由；e623／93a5 屬另一個待保留的獨立 episode。
