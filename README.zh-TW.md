# A CHIA Loop for ECC Optimization with Routed Feedback

本儲存庫收錄 CHIA ECC 解碼器研究的 paper、程式與資料。經等價證明的 parity 編輯以佈線後時序和三種工作負載的能量回饋評估。本儲存庫收錄 paper 所報告的量測進程、來源紀錄，以及最終 64 位元與 32 位元操作的 CHIA 保存決策重放。

可先閱讀[四頁主稿](paper/CHIA_ECC_Feedback.pdf)與[擴充證據補充](supplement/Expanded_Evidence.pdf)；兩份 PDF 旁均有可編輯來源。

## 可以做什麼

- **查看 paper 結果：**`evidence/expanded_results.csv` 收錄 44 筆選定觀察，包含 Table I 的全部 20 列；`evidence/comparisons_v8.json` 列出 17 組明確比較。[證據導覽](evidence/README.md)說明來源紀錄與命名。
- **離線核對重放子集：**`offline-check` 驗證資料包並重算其中 21 筆選定列，不執行 CHIA、EDA 或模型。
- **重放保存的決策：**`replay` 核對指定 parent 與 action，並可選擇執行本地 CHIA、形式等價證明、佈線及新活動量測。
- **試用模型控制：**`model-gate` 讓模型對一個固定的 S02 或 V02 action 選擇 RUN 或 STOP。連網必須明確啟用，並使用讀者自己的端點與憑證。

## 執行需求

| 工作 | 需求 |
| --- | --- |
| 離線證據核對 | Conda 與 Python 3.10.19；隨附的 `data/replay-data.zip` |
| CHIA 重放 | Linux ARM64、可供容器使用至少 12 GiB 記憶體的 Docker、指定版本的 IIC-OSIC 映像、下述環境與 Python 套件，以及 Git checkout |

CHIA 與 Docker 映像需另外取得；該映像提供流程使用的 Sky130A 平台檔案。版本、平台檔案雜湊與映像摘要記錄於 `public_release/runtime/requirements-public.txt` 和 `platform/iic-osic-arm64.lock.json`。

## 核對保存結果

在儲存庫根目錄執行；請將解壓資料與新執行結果放在儲存庫外。

```sh
conda env create -f environment.yml
conda activate familyrtl-replay
unzip data/replay-data.zip -d ../familyrtl-data
python -m public_release.runtime.cli offline-check --data-root ../familyrtl-data/replay-data
```

資料包與分數一致時，輸出包含 `status: PASS`、兩個最終範例的 paper 名稱與正規化能量分數，以及 21 筆已核對重放列的 ID。它不會檢查全部 44 筆展示列，也不會執行電路流程。資料包摘要另見 `data/replay-data.zip.sha256`。

## 重放最終操作

先在 conda 環境安裝 CHIA 與 Ray，並取得指定的 ARM64 工具映像：

```sh
python -m pip install -r public_release/runtime/requirements-public.txt
docker pull --platform linux/arm64 docker.io/hpretl/iic-osic-tools@sha256:65852976cad4af640c9d848762215137e87ec125111a6d06c850c3ab4e9695fb
```

Paper 的 **Final mixed-arity assignment** 對應歷史結果 V2 與 CLI 範例 `v02`。先核對保存的 action 與 parent，不執行 EDA：

```sh
python -m public_release.runtime.cli replay --example v02 --data-root ../familyrtl-data/replay-data --output-root ../familyrtl-runs/v02-check
```

預期狀態為 `NOT_RUN`，且 `preflight: PASS`。要執行流程，請使用**新的**輸出目錄並加上 `--execute`：

```sh
python -m public_release.runtime.cli replay --example v02 --data-root ../familyrtl-data/replay-data --output-root ../familyrtl-runs/v02-run --execute
```

Paper 的 **Final three-input refinement** 對應歷史結果 S2 與 CLI 範例 `s02`。執行結果會在輸出目錄寫入 `request.json`、`runtime_report.json` 與 case artifacts。完整成功的執行狀態為 `OK`，且 proof、route 和 measurement 均有效；失敗或未完成的執行須依 report 判讀，不能當作量測結果。

`replay` 會將 `source_commit` 綁定到 checkout 真正的 Git HEAD。如果使用下載的原始碼 ZIP，執行重放前須先建立本地 Git commit；不需要 remote。離線核對不需要 Git。

## 實測比較

| Table I 設計 | 歷史 ID | 位寬 | 延遲（ns） | 面積（µm²） | E_norm |
| --- | --- | ---: | ---: | ---: | ---: |
| RTL + physical tuning (start) | tuned64 | 64 | 2.372445 | 2434 | 0.991375 |
| Final three-input refinement | S2 | 64 | 2.374088 | 2425 | 0.895180 |
| Projected searched RTL (start) | projected32 | 32 | 2.049337 | 1299 | 0.884433 |
| Final mixed-arity assignment | V2 | 32 | 2.081588 | 1296 | 0.795511 |

相對這兩個**已優化且可行的起點**，E_norm 在 64 位元下降 **9.70%**、在 32 位元下降 **10.05%**；兩個最終設計都符合 2.40 ns 延遲上限。Paper 其他位置的 3.96% 與 5.26% 指的是從 feedback-recovered local design 與 four-star trial 出發的後段延伸；起點不同，不能把百分比相加。

E_norm 是三種固定工作負載能量比值的幾何平均。歷史程式與紀錄稱它為 `J`；CLI 同時輸出 `e_norm` 和 `j_score`。每個位寬使用自己的參考能量，因此跨位寬分數不是絕對效率比較。能量依單一 library corner 的模擬活動與佈線寄生參數估計，不是晶片實測功耗或 signoff。

原始 S02 執行重用了經核對的 S01 ECO。此處提供的 S02 重放會對 N02 parent 重新套用相同的保存 action，並不逐步重現當時的 ECO reuse。原始 receipts 與 artifacts 保存在資料包中，供讀者檢查。

歷史 CHIA loop 還包括 catalog action 選擇、時序報告與外層開發者擴充操作。本可攜 CLI 提供兩個最終操作的保存決策重放與固定方案 RUN/STOP gate，不重現所有先前研究 episode。

## 選用的模型 gate

Gate 只接受對單一固定 action 的 RUN 或 STOP。最多兩次模型呼叫、一次佈線執行；選用的第二次呼叫只能評估回饋並停止。預設不會連網或呼叫付費 API。

若要在沒有 provider、也不執行 EDA 的情況下檢查 gate，可使用隨附的 STOP response：

```sh
python -m public_release.runtime.cli model-gate --example v02 --data-root ../familyrtl-data/replay-data --output-root ../familyrtl-runs/v02-mock --execute --timeout-s 30 --max-output-tokens 512 --mock-responses examples/mock-stop-v02.json
```

預期狀態是 `STOP`，且 `route_count: 0`。若要呼叫即時模型，請先設定自己的 provider，再執行：

```sh
python -m public_release.runtime.cli model-gate --example v02 --data-root ../familyrtl-data/replay-data --output-root ../familyrtl-runs/v02-gated --execute --timeout-s 60 --max-output-tokens 1024 --enable-network-model --assess-feedback --endpoint "$CHIA_MODEL_ENDPOINT" --model "$CHIA_MODEL_ID" --auth-env CHIA_MODEL_TOKEN
```

請為所用 provider 設定 `CHIA_MODEL_ENDPOINT`、`CHIA_MODEL_ID` 及 `CHIA_MODEL_TOKEN` 環境變數。Mock RUN 搭配 `--execute` 仍可能啟動 EDA；不執行佈線時請使用 STOP。

## 儲存庫導覽

| 路徑 | 內容 |
| --- | --- |
| `public_release/runtime/` | CLI、模型 gate 與指定版本的 Python 套件 |
| `research/ecc_perf_bench/`、`chia_adapter/`、`eda/` | 結構變換、CHIA 節點、形式驗證與實體設計流程 |
| `evidence/` | 44 筆選定觀察、Table I 命名對照、比較與封存來源紀錄 |
| `results/` | 21 列重放子集及 receipt 摘錄 |
| `review/` | 重放 CLI 讀取的原始 S02／V02 receipt 與模型決策；其中舊機器路徑是來源紀錄，不是安裝指令 |
| `data/replay-data.zip` | 保存的 parent、決策及原始重放證據 |
| `examples/` | 模型 gate 的離線 STOP 範例 |
| `paper/`、`supplement/`、`build-paper.sh` | 主稿、擴充證據與文件建構入口 |
| `MANIFEST.json` | 各個交付檔案的 SHA-256 與大小 |
| `LICENSE`、`NOTICE.md`、`LICENSES/` | 本專案與上游授權資訊 |

可執行 `python -m public_release.runtime.cli --help` 查看支援的命令與參數。重放範例是固定的 ECC case；此 CLI 不是通用電路最佳化器。
