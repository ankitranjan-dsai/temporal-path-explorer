# Integration log — Temporal Path Explorer

Progress and attribution for wiring teammate modules into the main Streamlit app.  
Original teammate code lives under `teammate_deliverables/` and is **not modified**; integration code lives in the repo root (or indicated paths below) with inline credits.

---

## 0. Conventions

| Item | Choice | Notes |
|------|--------|--------|
| **Canonical edge table (after B)** | `SRC`, `TGT`, `Unix`, `edge_id` (+ optional `datetime`) | From `teammate_deliverables/B/b_new_pipeline.ipynb` — `load_temporal_file`, `clean_temporal_data`. |
| **Canonical graph for C / D / E** | `adj: dict` — `{src: [(unix, tgt, edge_id), ...], ...}` per outgoing edge sorted by `unix` | Matches C, D (`Modify_and_Sensitive_clean_update.py`), E (`e_teammate.py`). |
| **Path & earliest arrival (UI)** | Group uses **C** — `calculate_earlist_arrival` / `extract_path_sequence` (rename to `earliest` in integration if desired). | Notebook: `teammate_deliverables/C/c_earliest_path.ipynb`. |
| **What-if & sensitivity** | **D** — `modify`, `sensitive`, etc. from `teammate_deliverables/D/Modify_and_Sensitive_clean_update.py`. | |
| **Bottlenecks & fast analysis** | **E** — `find_menger_bottlenecks`, `optimize_algorithm_speed`, `TemporalGraphOptimized.find_bottlenecks_fast`. File: `teammate_deliverables/E/e_teammate.py`. |
| **Visualization** | **Plotly** — `visualizer_plotly.py`: main network (Explore / Analyze / Advanced). **F** — `visualizer_F.py`: Matplotlib snapshot excerpt (`teammate_deliverables/F/t2.py`, `t3.py`, `t5.py`, etc.). | |
| **Streamlit upload** | Use in-memory `UploadedFile` → `pd.read_csv` / `pd.read_json` — **not** only disk paths; bridge to `adj` via `DataFrame` + helper (see Step 2). | |

---

## 1. Steps checklist

| Step | Goal | Source (teammate) | Target in repo | Status |
|------|------|-------------------|----------------|--------|
| **1** | B: load + clean edge table | `b_new_pipeline.ipynb` — `load_temporal_file`, `clean_temporal_data` | `data_provider.py` — `load_temporal_file`, `load_temporal_upload`, `clean_temporal_data`; `clean_temporal_data(..., verbose=False)` for Streamlit | `done` |
| **2** | `DataFrame` → `adj` (+ upload path) | `e_teammate.py` — `build_adj_time_from_csv` sort contract | `data_adj.py` — `dataframe_to_adj` | `done` |
| **3** | C: earliest arrival + path | `c_earliest_path.ipynb` — `first_edge_idx`, `calculate_earlist_arrival`, `extract_path_sequence` | `algorithm_C.py` — includes `earliest_path` | `done` |
| **4** | D: modify + sensitive | `Modify_and_Sensitive_clean_update.py` | `algorithm_D.py` — `nodes_set`, `Arrive_time_and_Latency`, `sensitive`, `modify`; `verbose=False` for Streamlit | `done` |
| **5** | E: bottlenecks | `e_teammate.py` — §0–3 (no `__main__`) | `algorithm_E.py` — imports `algorithm_D` + `data_adj`; does not depend on B directly | `done` |
| **6** | F: Matplotlib snapshots | `F/t2.py`, `t3.py`, `t5.py`, etc. | `visualizer_F.py` (t2 excerpt; not imported by main UI; Plotly is primary) | `done` |
| **7** | UI wiring | — | `app.py` — B upload/example, C/D/E, Plotly graphs | `done` |
| **8** | G: path highlight / compare | (pending delivery) | `visualizer_G.py` (reserved filename) | `pending` |

Update **Status** to `in_progress` / `done` and add a short note under **Change log** when each step lands.

---

## 2. Change log (newest first)

| Date | Step | What changed | Files |
|------|------|----------------|-------|
| 2026-04-06 | Docs | Removed `docs/integration_snippets/` (redundant B paste; canonical code in `data_provider.py` and `b_new_pipeline.ipynb`); fixed Step 5 / conventions / open decisions wording. | `docs/` |
| 2026-04-05 | Repo layout | Teammate deliverables moved to `teammate_deliverables/` (English filenames); root modules use unified three-line headers (Credit / Integrated from / Role). | `teammate_deliverables/`, `*.py`, `docs/` |
| 2026-04-02 | UI | `app.py` tabs (Data/Explore/Analyze/Advanced); snapshot cumulative/discrete options; D/E mostly button-driven; Advanced E `bfs_single` and bottleneck mode. | `app.py`, `visualizer_F.py` |
| 2026-03-30 | Step 7 | `app.py` wired to B→`clean_temporal_data`, C/D/E, F sample path; `load_example_canonical_cleaned`. | `app.py`, `data_provider.py` |
| 2026-03-27 | Step 6 | Teammate F — Matplotlib `TemporalVisualizer` + UVT helpers (`dataframe_uvt_from_canonical` for B columns; later simplified). | `visualizer_F.py`, `requirements.txt` |
| 2026-03-27 | Step 5c | `algorithm_E` dropped `build_adj_time_from_csv`, `BFS_Single`, long section dividers; graph build via `data_adj` / `data_provider`. | `algorithm_E.py` |
| 2026-03-27 | Step 5b | Deduped E: `nodes_set` / `Arrive_time_and_Latency` / `sensitive` → `algorithm_D`; `build_adj_time_from_edges` → `data_adj`. | `algorithm_E.py`, `data_adj.py` |
| 2026-03-27 | Step 5 | E — `find_menger_bottlenecks`, `optimize_algorithm_speed`, `TemporalGraphOptimized`, etc.; truncated `__main__` test block. | `algorithm_E.py` |
| 2026-03-27 | Step 4 | D — what-if / sensitivity: `modify`, `sensitive`, etc. in `algorithm_D.py`; optional `verbose`. | `algorithm_D.py` |
| 2026-03-27 | Step 3 | C integrated in `algorithm_C.py` (incl. `earliest_path`); removed old `algorithms.py` / `c_paths.py`. | `algorithm_C.py` |
| 2026-03-27 | Step 1 / Prep | B pipeline merged into `data_provider.py`; added `load_temporal_upload` for Streamlit. | `data_provider.py` |

---

## 3. Module header convention

At the top of each root module, use three lines (same pattern as in code):

```python
# Credit: <B/C/D…>; A: <adaptations>
# Integrated from: teammate_deliverables/<path> → <module>.py
# Role: <one line>.
```

---

## 4. Open decisions

- [ ] **G** (path highlight / multi-scenario compare): reserved `visualizer_G.py`, pending delivery.

---

*Last updated: English pass + docs cleanup.*
