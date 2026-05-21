# Temporal Path Explorer — Acceptance Checklist

---

## 1. Environment and run

| Check | Expected |
|--------|----------|
| Python | 3.10+ recommended (compatible with pandas/streamlit is enough) |
| Dependencies | From project root, `pip install -r requirements.txt` completes without errors |
| Launch | `streamlit run app.py` opens the app in the browser |
| Data privacy | Data tab footer shows wording like “session only, not persisted” |

---

## 2. Data and baseline

| Check | Expected |
|--------|----------|
| Sample data | **Load sample data** enters the workspace (reads `demo_data.csv` or embedded sample) |
| Upload | CSV/JSON supported; columns can be mapped to `SRC` / `TGT` / `Unix` (see sidebar **Details → Data format**) |
| Cleaned schema | Includes `SRC`, `TGT`, `Unix`, `edge_id`, `datetime` (from `data_provider.clean_temporal_data`) |
| Baseline metrics | Data tab shows **Global reachability (baseline)** and **Mean latency (baseline)**, consistent with What-if baseline |

---

## 3. Acceptance by tab

### 3.1 Data

- Shows loaded dataset name, edge count, vertex count, time range.
- Table preview (e.g. first 50 rows) is scrollable; full data is used for downstream computation.

### 3.2 Explore

- **Network graph**: Plotly; **cumulative time** slider controls edges with time ≤ t; layout is full-graph spring layout (node positions do not change with t).
- **Compute and highlight**: Computes **earliest-arrival path** on the **full table** (times along edges non-decreasing, not unweighted shortest path); on success legend **Earliest path** is highlighted; on failure shows unreachable message.
- Sidebar **Details** includes usage, data format, metric notes, About (GROUP 9, member list).

### 3.3 Analyze (What-if)

- Comparison table: **Before (baseline) / After / Change** (global reachability, mean latency).
- Chart: **full network** + slider for cumulative visible edges; after successful submit **What-if remove** and **large orange nodes** mark edges/vertices slated for removal.
- Form: removable vertices (space-separated), removable edge IDs (`edge_id`); **Reset** clears scenario; errors in dialog (e.g. empty fields, ID mismatch).

### 3.4 Advanced (bottlenecks)

- **Bottleneck scan**: ranks edges or vertices by “temporarily remove then recompute global metrics”; optional **Edges only / Vertices only / Edges and vertices**; **Top-K** table + network graph with **yellow** critical edges/vertices.
- **Edge cap**: current implementation **500** edges (constant `MAX_EDGE_ROWS_BOTTLENECK`); above that shows message and skips scan—use a subset.
- **Download full ranking (CSV)** downloads the full ranking.

---

## 4. Roles and code mapping (traceability)

| Module | Main contribution | Root file(s) |
|--------|-------------------|--------------|
| B | Load and clean | `data_provider.py` |
| C | Earliest-arrival path | `algorithm_C.py` |
| D | Sensitivity, What-if `modify` | `algorithm_D.py` |
| E | Bottleneck scan, etc. | `algorithm_E.py` |
| F | Matplotlib snapshots (archived) | `teammate_deliverables/F/t2.py` etc.; root `visualizer_F.py` is an excerpt. |
| A | Streamlit UI, main Plotly graph | `app.py`, `visualizer_plotly.py`, `data_adj.py` |

Finer integration notes: **`docs/INTEGRATION_LOG.md`**; teammate originals under **`teammate_deliverables/`** (do not treat as run entry points for edits).
