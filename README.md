# A CHIA Loop for ECC Optimization with Routed Feedback

This repository contains the paper, code, and data for the CHIA ECC decoder study. Equivalence-checked parity edits are evaluated with routed timing and three-workload energy feedback. This repository includes the measured progression reported in the paper, its source records, and saved-decision CHIA replay for the final 64-bit and 32-bit operations.

Read the [four-page paper](paper/CHIA_ECC_Feedback.pdf) and [expanded evidence supplement](supplement/Expanded_Evidence.pdf). Editable sources are included alongside both PDFs.

## What you can do

- **Inspect the paper's results:** `evidence/expanded_results.csv` has 44 selected observations, including all 20 rows in Table I; `evidence/comparisons_v8.json` declares 17 before/after comparisons. The [evidence guide](evidence/README.md) explains source records and naming.
- **Verify the replay subset offline:** `offline-check` validates the replay-data archive and recomputes 21 selected rows without running CHIA, EDA, or a model.
- **Replay a saved decision:** `replay` checks the exact parent and action, then optionally runs local CHIA, formal equivalence, routing, and fresh activity measurement.
- **Try a model-controlled run:** `model-gate` lets a model choose RUN or STOP for one fixed S02 or V02 action. Network access requires an explicit flag and your own endpoint and credentials.

## Requirements

| Task | Requirements |
| --- | --- |
| Offline evidence check | Conda with Python 3.10.19; the included `data/replay-data.zip` |
| CHIA replay | Linux ARM64, Docker with at least 12 GiB available to the container, the pinned IIC-OSIC image, the environment and Python packages below, and a Git checkout |

CHIA and the Docker image are external dependencies; the image supplies the Sky130A platform files used by the flow. Versions, platform hashes, and image digests are in `public_release/runtime/requirements-public.txt` and `platform/iic-osic-arm64.lock.json`.

## Verify the saved results

Run from the repository root. Keep extracted data and generated runs outside the checkout.

```sh
conda env create -f environment.yml
conda activate familyrtl-replay
unzip data/replay-data.zip -d ../familyrtl-data
python -m public_release.runtime.cli offline-check --data-root ../familyrtl-data/replay-data
```

The command returns `status: PASS`, the paper labels and normalized energy scores for both final examples, and the IDs of 21 checked replay rows. It does not check every one of the 44 display rows or execute a circuit flow. `data/replay-data.zip.sha256` provides the archive checksum.

## Replay the final operations

Install CHIA and Ray in the conda environment, and fetch the pinned ARM64 tool image:

```sh
python -m pip install -r public_release/runtime/requirements-public.txt
docker pull --platform linux/arm64 docker.io/hpretl/iic-osic-tools@sha256:65852976cad4af640c9d848762215137e87ec125111a6d06c850c3ab4e9695fb
```

The paper's **Final mixed-arity assignment** is historical result V2 and CLI example `v02`. Check its saved action and parent before spending time on EDA:

```sh
python -m public_release.runtime.cli replay --example v02 --data-root ../familyrtl-data/replay-data --output-root ../familyrtl-runs/v02-check
```

The expected status is `NOT_RUN` with `preflight: PASS`. To execute the flow, use a **new** output directory and add `--execute`:

```sh
python -m public_release.runtime.cli replay --example v02 --data-root ../familyrtl-data/replay-data --output-root ../familyrtl-runs/v02-run --execute
```

The paper's **Final three-input refinement** is historical result S2 and CLI example `s02`. The run writes `request.json`, `runtime_report.json`, and case artifacts under its output directory. A successful completed run reports `OK` with valid proof, route, and measurement. A failed or incomplete run must be read from its report and is not a measured result.

The replay command binds `source_commit` to the checkout's Git HEAD. If you downloaded a source ZIP, create a local Git commit before replaying; no remote is needed. The offline check works without Git.

## Measured comparison

| Table I design | Historical ID | Width | Delay (ns) | Area (µm²) | E_norm |
| --- | --- | ---: | ---: | ---: | ---: |
| RTL + physical tuning (start) | tuned64 | 64 | 2.372445 | 2434 | 0.991375 |
| Final three-input refinement | S2 | 64 | 2.374088 | 2425 | 0.895180 |
| Projected searched RTL (start) | projected32 | 32 | 2.049337 | 1299 | 0.884433 |
| Final mixed-arity assignment | V2 | 32 | 2.081588 | 1296 | 0.795511 |

Relative to these **already optimized, feasible starts**, E_norm falls by **9.70%** for 64 bits and **10.05%** for 32 bits; both final designs meet the 2.40 ns delay limit. The 3.96% and 5.26% figures elsewhere in the paper describe later extensions from the feedback-recovered local and four-star designs, respectively. These comparisons have different starts and are not additive.

E_norm is the geometric mean of energy ratios over the three fixed workloads. Historical code and records call this same value `J`; the CLI reports both `e_norm` and `j_score`. Each width has its own reference energies, so cross-width scores are not absolute efficiency comparisons. Energy is estimated from simulated activity and routed parasitics at one library corner, not measured silicon power or signoff.

The original S02 run reused a verified S01 ECO. The supplied S02 replay applies the same saved action to its N02 parent as a new ECO, so it does not reproduce that historical reuse step. The archive retains the original receipts and artifacts for inspection.

The historical CHIA loop also used catalog action selection, timing reports, and outer development of new operators. This portable CLI implements the two saved final-operation replays and a fixed-plan RUN/STOP gate; it does not reproduce every earlier research episode.

## Optional model gate

The gate accepts only RUN or STOP for one fixed action. It allows at most two model calls and one routed execution; the optional second call can only assess feedback and STOP. There is no default paid or network call.

To check the gate without a provider or EDA run, use the included STOP response:

```sh
python -m public_release.runtime.cli model-gate --example v02 --data-root ../familyrtl-data/replay-data --output-root ../familyrtl-runs/v02-mock --execute --timeout-s 30 --max-output-tokens 512 --mock-responses examples/mock-stop-v02.json
```

The expected status is `STOP` with `route_count: 0`. For a live model call, configure your own provider settings and run:

```sh
python -m public_release.runtime.cli model-gate --example v02 --data-root ../familyrtl-data/replay-data --output-root ../familyrtl-runs/v02-gated --execute --timeout-s 60 --max-output-tokens 1024 --enable-network-model --assess-feedback --endpoint "$CHIA_MODEL_ENDPOINT" --model "$CHIA_MODEL_ID" --auth-env CHIA_MODEL_TOKEN
```

Set `CHIA_MODEL_ENDPOINT`, `CHIA_MODEL_ID`, and the `CHIA_MODEL_TOKEN` environment variable for your provider. A mock RUN with `--execute` can still start EDA; use STOP for a no-route check.

## Repository guide

| Path | Contents |
| --- | --- |
| `public_release/runtime/` | CLI, model gate, and pinned Python requirements |
| `research/ecc_perf_bench/`, `chia_adapter/`, `eda/` | Transformations, CHIA nodes, formal and physical-design recipes |
| `evidence/` | 44 selected observations, Table I name map, declared comparisons, and archived source records |
| `results/` | 21-row replay subset and receipt views |
| `review/` | Original S02/V02 receipts and model decisions read by the replay CLI; historical machine paths are provenance, not setup instructions |
| `data/replay-data.zip` | Saved parents, decisions, and raw replay evidence |
| `examples/` | Offline STOP fixture for the model gate |
| `paper/`, `supplement/`, `build-paper.sh` | Manuscript, expanded evidence, and document build entry |
| `MANIFEST.json` | SHA-256 and size of each payload file |
| `LICENSE`, `NOTICE.md`, `LICENSES/` | Project and upstream license information |

For supported commands and flags, run `python -m public_release.runtime.cli --help`. The replay examples are fixed ECC cases; the CLI is not a general circuit optimizer.
