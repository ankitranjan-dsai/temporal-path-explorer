# Temporal Path Explorer — User Guide

---

## 1. First launch

1. In a terminal at the project root: `pip install -r requirements.txt`, then `streamlit run app.py`. To stop the server, press Ctrl+C in that terminal.  
2. After the browser opens, you should see the title **Temporal Path Explorer**.  
3. Choose one way into the app:  
   - **Load sample data**: loads the built-in sample (about 20 nodes, from `demo_data.csv` or embedded data).  
   - Or **upload** CSV / JSON in the middle (column requirements below).  
4. On success you enter the main UI; to switch data use **Back to data selection** at the top.

---

## 2. What the data should look like

The app must be able to recognize three columns (names can be any of the following):

- **Source**: `source` / `SRC` / `from`  
- **Target**: `target` / `TGT` / `to`  
- **Time**: `time` / `Unix` / `timestamp` (numeric; sample uses small integers; real data can be Unix seconds)

More detail is in the sidebar under **Details → Data format** (English).

---

## 3. Sidebar **Details** (recommended first)

- **How to use**: what the four feature areas do.  
- **Data format**: upload format.  
- **Metrics**: what global reachability, mean latency, and bottleneck scan mean (English).  
- **About**: GROUP 9, course 530, team member list.

---

## 4. Tab: **Data**

- See which file is loaded, edge count, vertex count, time range.  
- **Global reachability (baseline)** and **Mean latency (baseline)**: these are the “before” numbers for What-if.  
- The table below is only a **preview** (first 50 rows); computation uses the full table.

---

## 5. Tab: **Explore**

- **Time slider (Time cumulative to t)**: only edges with time ≤ t are drawn; **node positions stay fixed** (layout from the full graph).  
- **Source / Target / Depart ≥**: start, end, and earliest departure lower bound.  
- **Compute and highlight**: computes one **earliest-arrival** path on the **full table** (walking edges by time, not “fewest hops” shortest path).  
  - Success: red bold **Earliest path**; vertices and edges on the path are listed below.  
  - Failure: unreachable message—check source, target, and time.  
- Note: the **slider only changes which edges are drawn**; it does not change the data scope used for path computation.

---

## 6. Tab: **Analyze** (What-if)

- Top table: **global reachability** and **mean latency** before / after change (if nothing submitted yet, “after” may show a dash).  
- Middle chart: still the **full network**; orange edges and enlarged nodes show edges and vertices you **plan to remove** (shown after a successful submit from the last scenario).  
- Form:  
  - **Vertices to remove**: vertex IDs, **space-separated** (e.g. `v3 v5`).  
  - **Edge IDs to remove**: edges to remove, use **`edge_id`** from the table, space-separated.  
  - **Submit scenario and recompute metrics**: submit and recompute metrics.  
  - **Reset**: clear the current hypothetical scenario.  
- Expand **Reference: vertex and edge IDs** to copy IDs and avoid typos.

---

## 7. Tab: **Advanced** (bottlenecks)

- Question: **which edge or vertex, if removed, changes network-wide reachability / latency the most?**  
- **Scan target**: edges only, vertices only, or both.  
- **Top-K**: keep the top K items by impact in each result table.  
- **Run scan**: can be **slow** with many edges; if edge count exceeds **500**, this page **blocks the scan**—use a smaller subset.  
- Results: text summary + table + network graph with **yellow** critical edges/vertices; the time slider again shows edges cumulative up to a moment.  
- **Download full ranking (CSV)**: download the full ranking.

---

## 8. FAQ

| Symptom | Likely cause |
|---------|----------------|
| Bottleneck scan disabled | Edge count > 500—use smaller data or a sample |
| What-if submit fails | Vertex name missing from graph, or `edge_id` must **exactly** match the table (including case) |
| No path found | Truly unreachable under current source, target, and departure lower bound |
| Fewer edges on chart suddenly | English copy may say too many edges—random subset shown; algorithms still use full data |
