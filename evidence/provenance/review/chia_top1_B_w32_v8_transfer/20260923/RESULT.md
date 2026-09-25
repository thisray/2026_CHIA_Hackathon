# B-w32-v8-transfer：固定工具跨寬度重用，真route無增益

Root 直接指定把已在 W64 得到可行 J gain 的 **F1-v8 固定工具**重用到已 qualified 的 W32 projected-b271 parent。這不是模型自主選擇，也沒有新 model call／mapped submission／anchor profile。獨立額度 **0 mapped／1 route（含失敗）已用完**。GCP02 以 `jobs=1`／Ray 2 CPU 執行不可變 source `83861e81d8bd5658da266b846dc73ba562505d4b`、recipe SHA256 `99b5db032dc064c496b2e652dfe2e75e5cf356c446d0affcbf15fbda2b140d9a`。

| W32 `routed3_w32_d240_maskedF0_v1` | D ns | A µm² | J | stress／uniform／low-toggle pJ |
| --- | ---: | ---: | ---: | --- |
| 原 projected-b271/F0 | 2.049337 | 1299 | 0.8844328925383526 | 1.379291207／0.9746563592／0.3068061415 |
| 新 projected-b271/F1-v8 | **2.049337** | **1299** | **0.8844328925383526** | **1.379291207／0.9746563592／0.3068061415** |

新 result `status=OK`、`functional_valid=true`、`route_valid=true`、`measurement_valid=true`、`feasible=true`；Yosys `sat` whole-output miter proof PASS。W32 專用 goal、reference `ecc_masked_reduction::F0::routed3_w32_v1` 與 MASKED/F0 三能量分母 **1.595184585／1.140097229／0.3278113945 pJ** 均由原 W32 request 繼承並見新 output，沒有使用 W64 b271 分母或 W64 source-proof bridge。重新產生的 SPEF/VCD、三 profile 原始量測與 CHIA worker identity 保留；這次新 SPEF hash 與舊 F0 不同，故只主張 D/A/J/三能量與圖 bytes 同點。

OpenROAD 在 recovery 前顯示 GR arrival **2.128669 ns**、proxy required **2.575000 ns**、slack +446.331 ps；`recover_power 100` 的最終 resize 數 **0**。`pre_repair.v`、`post_repair.v`、`post_power_recovery.v`、`routed.v` 四者 bytes 完全相同，SHA256 `f9843a3bad971d180b418ee547a0c3aaf7bd19c942a56b883a99da94707696b0`，也是原 F0 routed graph hash。本筆只證明此 parent／width／固定 F1-v8 recipe 沒有硬體或 J 增益；不能外推整個 W32 family 已無可回收 cell。

原 qualified mapped source SHA256 `3a4f95a3751d487b8010676a74f2929c7fe28995146dd8f163c5c72220dcb295`、mapped graph SHA256 `53ae4ca390bee039894ea177f372f35e4af2bf5ed405878b95905a331b5933e2`，原 mapped exact miter 與 structural mutant proof 均 PASS。原 GCP 絕對路徑已不在，故提交前先從 GB10 durable raw **copy-first** 將原 parent 的58檔／1.6 MB 完整 snapshot 移到新的 GCP task-local `parent_snapshot/`，GCP 依原 relative SHA manifest逐檔驗證通過；只重綁新 request 的 `mapped_result` 路徑，source/proof/hash未變，沒有重做 mapping或舊F0 route。原 W32 mapped `q_E` 曾用 routed denominator，已被標記 `INVALID_REFERENCE`；本次沒有用它判斷增益。

**原始證據**：GB10 `/home/thisray/projects/260908_CHIA_Hackathon_artifacts/chia-top1-20260923/w32-v8-transfer/`。`intent.json`／`request.pre_rebind.json`／`request.json` 保存原來源與路徑重綁；唯一 batch `w32-v8-projected-89bc80a8` 的 request檔SHA256 `4a23c2f6ddd03a0077361c3234eb57e5adb57393d0e508dc2c7b25f7a9f87d01`，原 F0 output檔SHA256 `7f97cf7c6add8e6ed6026bc5df119d5d0c57970b627eeb3ef32f8d93cb09a133`。新 `output.json` SHA256 `d91bd571d07c46890bf3673c82ea99884464e509669c1cc2e7dc7c03db5e2233`，其 execution記錄 normalized request SHA `536a365fb2e3482011c4fbfdaed9e117a69484df94e6f167a0a0e23c303c6818`、GCP source SHA、wall20.608s與 worker PID169291。`raw/w32-v8-projected-89bc80a8/` 含 OpenROAD、proof、netlist、SPEF、三 profile activity／power；GCP 原始 batch tree 的70檔已逐檔SHA256與GB10 copy核對成功，原件仍在GCP。沒有第二筆 route。
