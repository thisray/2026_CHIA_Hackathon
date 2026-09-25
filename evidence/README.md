# Results and source records

`expanded_results.csv` and `expanded_results.json` contain 44 selected measured observations. Twenty appear in Table I of *A CHIA Loop for ECC Optimization with Routed Feedback*. The 17 declared before/after comparisons are in `comparisons_v8.json`. These are selected results, not a complete census of every experiment.

The paper calls the normalized three-workload energy score **E_norm**. Historical code and receipts call the same quantity **J**. Its three energy denominators are fixed separately for the 64-bit and 32-bit decoders; scores across widths are not absolute efficiency comparisons. `measurement_contract.json` records the workload and timing conditions.

`experiment_name_map.csv` maps each paper label to its historical ID, known parent, and source record. `main_table_label` reproduces Table I wording. `supplement_label` preserves the earlier descriptive wording where it differs. Only display labels were aligned; delay, area, workload energies, scores, feasibility, circuit hashes, and historical source records were not changed.

`PUBLIC_SOURCE_INDEX.json` locates the archived source records under `provenance/`. Those files preserve the available historical evidence, including source paths written at execution time. The `receipts/` and `codex_source/` directories contain saved receipt views and decision or proof material. Historical paths and provider details in raw records describe the original execution; they are not setup instructions.

The archived provenance documents are selected snapshots of the private research tree. Relative links inside them may point to companion records that are not included here. Use `PUBLIC_SOURCE_INDEX.json` and the packaged `evidence/receipts/` and `results/receipts/` for records available in this repository. Historical `source_url` fields identify the original private location and may not be publicly accessible.

The portable CLI's `offline-check --data-root` verifies the replay archive and recomputes its **21 selected replay rows**. It does not independently rerun EDA for all 44 display rows. `data/replay-data.zip` at the repository root contains the saved parents and decisions needed for S02 and V02 replay.
