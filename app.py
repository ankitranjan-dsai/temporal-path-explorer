# Credit: A (Streamlit UI and module wiring).
# Integrated from: data_provider (B), data_adj, algorithm_C/D/E, visualizer_plotly, visualizer_F (F); entrypoint app.py.
# Role: Temporal Path Explorer — Data / Explore / What-if / Advanced (paths, bottlenecks, etc.).

from __future__ import annotations

import io
from typing import Any, List, Optional, Set, Tuple

import pandas as pd
import streamlit as st

from algorithm_C import earliest_path
from algorithm_D import modify, nodes_set, sensitive
from algorithm_E import find_menger_bottlenecks
from data_adj import dataframe_to_adj
from data_provider import (
    clean_temporal_data,
    demo_source_label,
    load_example_canonical_cleaned,
    load_temporal_upload,
)
from visualizer_plotly import compute_spring_positions, temporal_network_figure

MAX_EDGE_ROWS_BOTTLENECK = 500
PATH_FLASH_UNREACHABLE = "Unreachable"


@st.dialog("Submission did not succeed")
def _whatif_failure_dialog(message: str) -> None:
    st.markdown(message)
    if st.button("OK", type="primary", use_container_width=True):
        st.rerun()


def _df_fingerprint(df: Optional[pd.DataFrame]) -> Optional[Tuple[int, int, int]]:
    if df is None or len(df) == 0:
        return None
    return (len(df), int(df["Unix"].min()), int(df["Unix"].max()))


def _init_path_defaults(df: pd.DataFrame) -> None:
    nod = sorted(nodes_set(dataframe_to_adj(df)), key=str)
    if not nod:
        return
    st.session_state["path_src"] = nod[0]
    st.session_state["path_tgt"] = nod[-1]
    st.session_state["path_start"] = int(df["Unix"].min())


def _clear_workspace() -> None:
    for k in (
        "work_df",
        "data_label",
        "baseline_r",
        "baseline_l",
        "_baseline_fp",
        "_cached_fp",
        "adv_bn_export",
        "whatif_last",
        "explore_path_sig",
        "explore_path_edge_ids",
        "explore_last_res",
        "explore_path_just_computed",
        "explore_path_flash_info",
        "graph_layout_fp",
        "graph_positions",
        "_p1_failed_sig",
        "phase1_uploader",
    ):
        st.session_state.pop(k, None)
    st.session_state["app_phase"] = 1


def _sidebar_phase2() -> None:
    with st.sidebar:
        st.markdown("##### Details")
        with st.expander("How to use", expanded=False):
            st.markdown(
                """
1. **Data**: Summary, global metrics, preview; to change data use **Back to data selection** at the top.  
2. **Explore**: Move the time slider, query **earliest-arrival paths**.  
3. **Analyze**: **Remove vertices/edges** on top of baseline metrics and see changes.  
4. **Advanced**: **Bottleneck scan**; download full ranked CSV.
                """
            )
        with st.expander("Data format", expanded=False):
            st.markdown(
                """
- **CSV / JSON** supported.  
- Three columns (any one name per role is fine):  
  - Source: `source` / `SRC` / `from`  
  - Target: `target` / `TGT` / `to`  
  - Time: `time` / `Unix` / `timestamp`  
- Time must be **numeric** (built-in sample uses small integers; real data may use Unix seconds).
                """
            )
        with st.expander("Metrics", expanded=False):
            st.markdown(
                """
**Global reachability** and **mean latency** come from `sensitive` on the current temporal network; same numbers as on the Data tab, used as the **What-if baseline**.

**Bottleneck scan**: **temporarily remove** each edge (or each vertex), recompute the same global metrics, rank by **reachability drop / latency increase** to get critical edges/vertices; this is a heuristic inspired by Menger cuts. Many edges mean long runtime.
                """
            )
        with st.expander("About", expanded=False):
            st.markdown(
                """
Temporal Path Explorer — **GROUP 9**, Course 530 project.

**Team:** Yiqing Liu, Ranjan Ankit, Xiaohan Xu, Bowen Li, Zixuan Tang, Ce Wang, Wenbin Zeng
                """
            )


def _render_phase1_landing() -> None:
    top_l, _ = st.columns([1, 6])
    with top_l:
        demo = st.button(
            "Load sample data",
            type="primary",
            help="Reads demo_data.csv from the app folder (~20 nodes); you can also download and upload that file.",
        )

    _, title_col, _ = st.columns([1, 3, 1])
    with title_col:
        st.markdown(
            "<h1 style='text-align:center;font-size:3.15rem;font-weight:700;"
            "margin:min(18vh,200px) 0 1.75rem;line-height:1.15;'>Temporal Path Explorer</h1>",
            unsafe_allow_html=True,
        )

    err = st.session_state.get("phase1_error")
    if err:
        st.error(err)

    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        uploaded = st.file_uploader(
            " ",
            type=["csv", "json"],
            help="CSV or JSON. After entering the app, see sidebar → Details → Data format.",
            label_visibility="collapsed",
            key="phase1_uploader",
        )

    if uploaded is None:
        st.session_state.pop("_p1_failed_sig", None)

    if demo:
        st.session_state.pop("phase1_error", None)
        st.session_state.pop("_p1_failed_sig", None)
        try:
            with st.spinner("Loading data and computing global metrics…"):
                df = load_example_canonical_cleaned()
                if df is None or len(df) == 0:
                    st.session_state["phase1_error"] = "Sample data is empty."
                else:
                    adj = dataframe_to_adj(df)
                    r0, l0 = sensitive(adj, verbose=False)
                    st.session_state["work_df"] = df
                    st.session_state["data_label"] = demo_source_label()
                    st.session_state["baseline_r"] = float(r0)
                    st.session_state["baseline_l"] = float(l0)
                    st.session_state["_baseline_fp"] = _df_fingerprint(df)
                    st.session_state["app_phase"] = 2
                    _init_path_defaults(df)
        except Exception as e:  # noqa: BLE001
            st.session_state["phase1_error"] = str(e)
        st.rerun()

    if uploaded is not None:
        sig = (getattr(uploaded, "name", "") or "", int(getattr(uploaded, "size", 0)))
        if st.session_state.get("_p1_failed_sig") != sig:
            try:
                with st.spinner("Loading data and computing global metrics…"):
                    raw = load_temporal_upload(uploaded)
                    df = clean_temporal_data(raw, verbose=False)
                    if len(df) == 0:
                        st.session_state["phase1_error"] = (
                            "No valid edges in file (or time is not numeric). Try another file or clear and re-select."
                        )
                        st.session_state["_p1_failed_sig"] = sig
                    else:
                        st.session_state.pop("phase1_error", None)
                        adj = dataframe_to_adj(df)
                        r0, l0 = sensitive(adj, verbose=False)
                        st.session_state["work_df"] = df
                        st.session_state["data_label"] = getattr(uploaded, "name", "Uploaded file") or "Uploaded file"
                        st.session_state["baseline_r"] = float(r0)
                        st.session_state["baseline_l"] = float(l0)
                        st.session_state["_baseline_fp"] = _df_fingerprint(df)
                        st.session_state["app_phase"] = 2
                        st.session_state.pop("_p1_failed_sig", None)
                        _init_path_defaults(df)
            except Exception as e:  # noqa: BLE001
                st.session_state["phase1_error"] = str(e)
                st.session_state["_p1_failed_sig"] = sig
            st.rerun()


def _format_path_result(res: dict) -> None:
    nodes = res.get("path_node") or []
    edges = res.get("path_edge") or []
    if nodes:
        st.markdown("**Vertices visited (in order)**")
        st.markdown(" → ".join(f"`{n}`" for n in nodes))
    if edges:
        st.markdown("**Edges visited**")
        rows = []
        for e in edges:
            rows.append(
                {
                    "From": e.get("src"),
                    "To": e.get("tgt"),
                    "Edge ID": e.get("edge_id"),
                    "Time": e.get("depart_t"),
                }
            )
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    with st.expander("Raw result (JSON, easy to copy)"):
        st.json(
            {
                "path_node": res.get("path_node"),
                "path_edge": res.get("path_edge"),
                "final_arrival_t": res.get("final_arrival_t"),
            }
        )


def _whatif_comparison_table(
    r0: float,
    l0: float,
    r1: Optional[float],
    l1: Optional[float],
) -> None:
    if r1 is None or l1 is None:
        rows = [
            {
                "Metric": "Global reachability (higher is better)",
                "Before (baseline)": f"{r0:.6f}",
                "After": "—",
                "Change": "—",
            },
            {
                "Metric": "Mean latency",
                "Before (baseline)": f"{l0:.6f}",
                "After": "—",
                "Change": "—",
            },
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        rows = [
            {
                "Metric": "Global reachability (higher is better)",
                "Before (baseline)": f"{r0:.6f}",
                "After": f"{r1:.6f}",
                "Change": f"{r1 - r0:+.6f}",
            },
            {
                "Metric": "Mean latency",
                "Before (baseline)": f"{l0:.6f}",
                "After": f"{l1:.6f}",
                "Change": f"{l1 - l0:+.6f}",
            },
        ]
        df_w = pd.DataFrame(rows)
        styled = df_w.style.set_properties(
            subset=pd.IndexSlice[:, ["After", "Change"]],
            **{
                "background-color": "#ffe0b2",
                "color": "#d35400",
                "font-weight": "600",
            },
        )
        st.dataframe(styled, use_container_width=True, hide_index=True)


def _bottleneck_export_csv(bn: dict) -> Tuple[Optional[bytes], str]:
    parts: List[pd.DataFrame] = []
    if bn.get("edge_bottlenecks_full"):
        dfe = pd.DataFrame(bn["edge_bottlenecks_full"])
        dfe.insert(0, "kind", "edge")
        parts.append(dfe)
    if bn.get("vertex_bottlenecks_full"):
        dfv = pd.DataFrame(bn["vertex_bottlenecks_full"])
        dfv.insert(0, "kind", "vertex")
        parts.append(dfv)
    if not parts:
        e = bn.get("edge_bottlenecks")
        v = bn.get("vertex_bottlenecks")
        if e:
            dfe = pd.DataFrame(e)
            dfe.insert(0, "kind", "edge")
            parts.append(dfe)
        if v:
            dfv = pd.DataFrame(v)
            dfv.insert(0, "kind", "vertex")
            parts.append(dfv)
    if not parts:
        return None, ""
    merged = pd.concat(parts, ignore_index=True)
    buf = io.BytesIO()
    merged.to_csv(buf, index=False, encoding="utf-8-sig")
    return buf.getvalue(), "bottleneck_ranked_full.csv"


def _df_reorder_columns(df: pd.DataFrame, priority: List[str]) -> pd.DataFrame:
    if df.empty:
        return df
    rest = [c for c in df.columns if c not in priority]
    cols = [c for c in priority if c in df.columns] + rest
    return df[cols]


def _df_display_sanitize(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for c in out.columns:
        if pd.api.types.is_float_dtype(out[c]):
            out[c] = out[c].replace([float("inf"), float("-inf")], pd.NA)
    return out


def _bottleneck_column_config_edges(df: pd.DataFrame) -> dict:
    cfg: dict = {}
    if "edge_id" in df.columns:
        cfg["edge_id"] = st.column_config.TextColumn("Edge ID", width="medium")
    if "src" in df.columns:
        cfg["src"] = st.column_config.TextColumn("Source", width="small")
    if "tgt" in df.columns:
        cfg["tgt"] = st.column_config.TextColumn("Target", width="small")
    if "timestamp" in df.columns:
        cfg["timestamp"] = st.column_config.NumberColumn("Time", format="%.0f", width="small")
    for key, label in (
        ("reachability_drop", "Reachability ↓"),
        ("reachability_before", "Reach. (before)"),
        ("reachability_after", "Reach. (after)"),
        ("latency_increase", "Latency ↑"),
        ("latency_before", "Lat. (before)"),
        ("latency_after", "Lat. (after)"),
    ):
        if key in df.columns:
            cfg[key] = st.column_config.NumberColumn(label, format="%.4f", width="small")
    return cfg


def _bottleneck_column_config_vertices(df: pd.DataFrame) -> dict:
    cfg: dict = {}
    if "vertex" in df.columns:
        cfg["vertex"] = st.column_config.TextColumn("Vertex", width="small")
    for key, label in (
        ("reachability_drop", "Reachability ↓"),
        ("reachability_before", "Reach. (before)"),
        ("reachability_after", "Reach. (after)"),
        ("latency_increase", "Latency ↑"),
        ("latency_before", "Lat. (before)"),
        ("latency_after", "Lat. (after)"),
    ):
        if key in df.columns:
            cfg[key] = st.column_config.NumberColumn(label, format="%.4f", width="small")
    if "out_degree" in df.columns:
        cfg["out_degree"] = st.column_config.NumberColumn("Out-degree", format="%d", width="small")
    if "in_degree" in df.columns:
        cfg["in_degree"] = st.column_config.NumberColumn("In-degree", format="%d", width="small")
    return cfg


def _render_bottleneck_result_tables(re: List[dict], rv: List[dict]) -> None:
    edge_order = [
        "edge_id",
        "src",
        "tgt",
        "timestamp",
        "reachability_drop",
        "latency_increase",
        "reachability_before",
        "reachability_after",
        "latency_before",
        "latency_after",
    ]
    vert_order = [
        "vertex",
        "reachability_drop",
        "latency_increase",
        "out_degree",
        "in_degree",
        "reachability_before",
        "reachability_after",
        "latency_before",
        "latency_after",
    ]
    max_h = 400
    header_px = 44
    row_px = 35

    def _df_table(df: pd.DataFrame, cfg: dict) -> None:
        n = len(df)
        kwargs: dict = {
            "use_container_width": True,
            "hide_index": True,
            "column_config": cfg,
        }
        # Omit fixed height when few rows to avoid extra blank space below the table
        if n > 12:
            kwargs["height"] = min(max_h, header_px + n * row_px)
        st.dataframe(df, **kwargs)

    if re:
        st.markdown("**Critical edges (Top-K)**")
        dfe = _df_display_sanitize(_df_reorder_columns(pd.DataFrame(re), edge_order))
        _df_table(dfe, _bottleneck_column_config_edges(dfe))
    if rv:
        st.markdown("**Critical vertices (Top-K)**")
        dfv = _df_display_sanitize(_df_reorder_columns(pd.DataFrame(rv), vert_order))
        _df_table(dfv, _bottleneck_column_config_vertices(dfv))


def main() -> None:
    st.set_page_config(page_title="Temporal Path Explorer", layout="wide", initial_sidebar_state="expanded")

    st.session_state.setdefault("app_phase", 1)

    if st.session_state["app_phase"] == 1:
        _render_phase1_landing()
        return

    df: pd.DataFrame = st.session_state.get("work_df")
    if df is None or len(df) == 0:
        _clear_workspace()
        st.rerun()
        return

    _sidebar_phase2()

    label = st.session_state.get("data_label", "Current dataset")
    st.title("Temporal Path Explorer")
    st.caption(f"Current dataset: **{label}**")

    if st.button("Back to data selection", type="secondary"):
        _clear_workspace()
        st.rerun()

    fp = _df_fingerprint(df)
    if fp != st.session_state.get("_cached_fp"):
        for k in (
            "whatif_last",
            "adv_bn_export",
            "explore_path_sig",
            "explore_path_edge_ids",
            "explore_last_res",
            "explore_path_just_computed",
            "explore_path_flash_info",
        ):
            st.session_state.pop(k, None)
        st.session_state["_cached_fp"] = fp
        st.session_state["graph_positions"] = compute_spring_positions(df)
        st.session_state["graph_layout_fp"] = fp
    elif st.session_state.get("graph_layout_fp") != fp:
        st.session_state["graph_positions"] = compute_spring_positions(df)
        st.session_state["graph_layout_fp"] = fp

    pos = st.session_state.get("graph_positions")
    if pos is None:
        st.session_state["graph_positions"] = compute_spring_positions(df)
        st.session_state["graph_layout_fp"] = fp
        pos = st.session_state["graph_positions"]

    tab_data, tab_explore, tab_analysis, tab_advanced = st.tabs(
        ["Data", "Explore", "Analyze", "Advanced"]
    )

    br = st.session_state.get("baseline_r")
    bl = st.session_state.get("baseline_l")
    bfp = st.session_state.get("_baseline_fp")

    with tab_data:
        st.subheader("Data")
        n_nodes = len(nodes_set(dataframe_to_adj(df)))
        t_min, t_max = int(df["Unix"].min()), int(df["Unix"].max())
        st.success(
            f"Loaded **{label}**: **{len(df)}** edges, **{n_nodes}** vertices; "
            f"time range **{t_min}** – **{t_max}**."
        )
        if br is not None and bl is not None and bfp == fp:
            c1, c2 = st.columns(2)
            c1.metric("Global reachability (baseline)", f"{br:.6f}")
            c2.metric("Mean latency (baseline)", f"{bl:.6f}")
        elif bfp != fp:
            st.warning("Baseline does not match the current table; reload from phase 1.")
        st.markdown(
            f"The network has **{n_nodes}** vertices and **{len(df)}** edges; times roughly **{t_min}**–**{t_max}**. "
            "Use **Explore / Analyze / Advanced** for paths, bottlenecks, and What-if."
        )
        st.caption("Preview (first 50 rows); full data is used in all later steps.")
        st.dataframe(df.head(50), use_container_width=True)
        st.markdown(
            "<div style='text-align:center;color:gray;font-size:0.85rem;margin-top:2rem;'>"
            "Your upload is used only in this browser session and is not stored permanently on the server.</div>",
            unsafe_allow_html=True,
        )

    with tab_explore:
        t_lo, t_hi = int(df["Unix"].min()), int(df["Unix"].max())
        _ps0 = st.session_state.get("path_start")
        if _ps0 is None or not (t_lo <= int(_ps0) <= t_hi):
            st.session_state["path_start"] = t_lo
        adj_ex = dataframe_to_adj(df)
        nod_sorted = sorted(nodes_set(adj_ex), key=str)
        def_src = nod_sorted[0] if nod_sorted else "A"
        def_tgt = nod_sorted[-1] if nod_sorted else "B"

        st.subheader("Network view")
        st.caption(
            "**Cumulative mode**: edges with **t′ ≤ current time**. Pan/zoom the plot; hover for vertex names. "
            "After computing a path, **Earliest path** in the legend is red and bold."
        )
        st.caption(
            "The slider only affects **edges drawn**; **Compute and highlight** below still runs earliest path on the **full table**."
        )
        if t_lo == t_hi:
            t_pick = t_lo
            st.caption("All edges share the same timestamp.")
        else:
            t_pick = st.slider("Time (cumulative to t)", min_value=t_lo, max_value=t_hi, value=t_lo)

        st.caption(
            f"**Current view**: edges with time ≤ **{int(t_pick)}** only (fixed layout)."
        )
        src_sv = str(st.session_state.get("path_src", def_src)).strip()
        tgt_sv = str(st.session_state.get("path_tgt", def_tgt)).strip()
        start_u_int = int(st.session_state.get("path_start", t_lo))
        sig = (src_sv, tgt_sv, start_u_int)
        path_edge_ids: set = set()
        if st.session_state.get("explore_path_sig") == sig:
            path_edge_ids = set(st.session_state.get("explore_path_edge_ids") or [])

        try:
            fig_ex, w_ex = temporal_network_figure(
                df,
                int(t_pick),
                pos,
                path_edge_ids=path_edge_ids,
            )
            if w_ex:
                st.caption(w_ex)
            st.plotly_chart(fig_ex, use_container_width=True, key="plot_explore_network")
        except Exception as e:  # noqa: BLE001
            st.error(f"Plot error: {e}")

        if st.session_state.pop("explore_path_just_computed", False):
            lr = st.session_state.get("explore_last_res") or {}
            if lr.get("found"):
                st.success(
                    f"Earliest arrival time: **{lr.get('final_arrival_t')}**, "
                    f"**{lr.get('hop_count')}** hops; red bold edges in the plot are that path."
                )
                _format_path_result(lr)

        st.caption(
            "Walk edges in non-decreasing time to **arrive as early as possible** (not unweighted shortest path). "
            "Change source/target/start time and click the button again to refresh the highlight."
        )
        lr1, lr2, lr3, lr4 = st.columns([1.1, 1.1, 1.2, 1])
        with lr1:
            st.markdown("Source")
        with lr2:
            st.markdown("Target")
        with lr3:
            st.markdown("Depart ≥")
        with lr4:
            st.markdown(" ")  # align with label row above

        ec1, ec2, ec3, ec4 = st.columns([1.1, 1.1, 1.2, 1])
        with ec1:
            src_w = st.text_input("Source", key="path_src", label_visibility="collapsed")
        with ec2:
            tgt_w = st.text_input("Target", key="path_tgt", label_visibility="collapsed")
        with ec3:
            start_u_w = st.number_input(
                "Departure time lower bound",
                min_value=t_lo,
                max_value=t_hi,
                step=1,
                key="path_start",
                label_visibility="collapsed",
                help="Earliest time you may leave the source when walking along edges.",
            )
        with ec4:
            run_path = st.button("Compute and highlight", type="primary")

        if run_path:
            try:
                res = earliest_path(adj_ex, str(src_w).strip(), str(tgt_w).strip(), start_time=int(start_u_w))
                sig_run = (str(src_w).strip(), str(tgt_w).strip(), int(start_u_w))
                if res.get("found"):
                    st.session_state["explore_path_sig"] = sig_run
                    st.session_state["explore_path_edge_ids"] = {
                        str(e["edge_id"]) for e in (res.get("path_edge") or [])
                    }
                    st.session_state["explore_last_res"] = res
                    st.session_state["explore_path_just_computed"] = True
                else:
                    st.session_state.pop("explore_path_sig", None)
                    st.session_state.pop("explore_path_edge_ids", None)
                    st.session_state.pop("explore_last_res", None)
                    st.session_state["explore_path_flash_info"] = PATH_FLASH_UNREACHABLE
                st.rerun()
            except Exception as e:  # noqa: BLE001
                st.error(f"Path error: {e}")

        flash_info = st.session_state.pop("explore_path_flash_info", None)
        if flash_info == PATH_FLASH_UNREACHABLE:
            st.info("Unreachable with current settings; check source, target, and departure time.")

    with tab_analysis:
        _whatif_dlg_msg = st.session_state.pop("_whatif_fail_dialog", None)
        if isinstance(_whatif_dlg_msg, str) and _whatif_dlg_msg.strip():
            _whatif_failure_dialog(_whatif_dlg_msg)

        st.subheader("What-if analysis")
        adj = dataframe_to_adj(df)
        cur_fp = _df_fingerprint(df)

        st.markdown("**Current dataset**")
        st.caption(
            f"{len(df)} edges, {len(nodes_set(adj))} vertices."
        )

        if br is None or bl is None or bfp != cur_fp:
            st.warning("No valid baseline; return to phase 1 and reload data.")
            r_show, l_show = 0.0, 0.0
        else:
            r_show, l_show = float(br), float(bl)

        wl = st.session_state.get("whatif_last")
        if wl and wl.get("fp") == cur_fp:
            r1, l1 = wl.get("r1"), wl.get("l1")
        else:
            r1, l1 = None, None

        _whatif_comparison_table(r_show, l_show, r1, l1)

        mark_v: Set[str] = set()
        mark_e: Set[str] = set()
        if wl and wl.get("fp") == cur_fp:
            mark_v = {str(x).strip() for x in (wl.get("mark_verts") or []) if str(x).strip()}
            mark_e = {str(x).strip() for x in (wl.get("mark_edges") or []) if str(x).strip()}

        _whatif_fig_hint = (
            "Legend **What-if remove** and **large orange nodes** match edges/vertices to remove from the **last successful submit**."
            if (mark_e or mark_v)
            else "After a successful submit, edges and vertices to remove appear as **What-if remove** and **orange** in the legend."
        )
        st.caption(
            "**What-if**: the graph is the **full network**; "
            f"the slider controls edges visible up to time **t**. {_whatif_fig_hint}"
        )
        t_wlo, t_whi = int(df["Unix"].min()), int(df["Unix"].max())
        if t_wlo == t_whi:
            t_wpick = t_wlo
            st.caption(f"All edges share timestamp **{t_wlo}**.")
        else:
            t_wpick = st.slider(
                "Time (cumulative to t)",
                min_value=t_wlo,
                max_value=t_whi,
                value=t_wlo,
                key="whatif_plot_t",
            )
        try:
            fig_w, fw = temporal_network_figure(
                df,
                int(t_wpick),
                pos,
                whatif_edge_ids=mark_e,
                whatif_vertices=mark_v,
            )
            if fw:
                st.caption(fw)
            st.plotly_chart(fig_w, use_container_width=True, key="plot_whatif_network")
        except Exception as e:  # noqa: BLE001
            st.error(f"Plot error: {e}")

        st.caption("Vertex names are as in the plot; edge IDs are `edge_id` from the table. Submit updates **After** in the table above.")
        with st.form("whatif_form"):
            dv = st.text_input(
                "Vertices to remove (space-separated)",
                value="",
                placeholder="e.g. v3 v5",
                key="whatif_del_vertices",
            )
            de = st.text_input(
                "Edge IDs to remove (space-separated)",
                value="",
                placeholder="e.g. e0000001",
                key="whatif_del_edges",
            )
            c_go, c_rst, _ = st.columns([3.5, 1.2, 5.3])
            with c_go:
                go_whatif = st.form_submit_button(
                    "Submit scenario and recompute metrics",
                    type="primary",
                    use_container_width=False,
                )
            with c_rst:
                reset_whatif = st.form_submit_button("Reset", use_container_width=False)
        if reset_whatif:
            st.session_state.pop("whatif_del_vertices", None)
            st.session_state.pop("whatif_del_edges", None)
            st.session_state.pop("whatif_last", None)
            st.rerun()
        elif go_whatif:
            verts = [x.strip() for x in dv.split() if x.strip()]
            edges = [x.strip() for x in de.split() if x.strip()]
            if not verts and not edges:
                st.session_state["_whatif_fail_dialog"] = (
                    "Enter at least **vertices to remove** or **edge IDs to remove** before submitting."
                )
                st.rerun()
            else:
                out = modify(adj, Vertexes=verts or None, Edges=edges or None, verbose=False)
                if out is None:
                    st.session_state["_whatif_fail_dialog"] = (
                        "Computation failed: check vertex names exist and edge IDs **exactly** match `edge_id` in the table."
                    )
                    st.rerun()
                else:
                    (_r0, _l0), (r1b, l1b), _ = out
                    st.session_state["whatif_last"] = {
                        "fp": cur_fp,
                        "r0": float(_r0),
                        "l0": float(_l0),
                        "r1": float(r1b),
                        "l1": float(l1b),
                        "mark_verts": verts,
                        "mark_edges": edges,
                    }
                    st.rerun()

        with st.expander("Reference: vertex and edge IDs (from current data)", expanded=False):
            st.caption(
                "For **vertices**, use the **Vertex** column below, space-separated; for **edges**, use **Edge ID** (`edge_id`), exactly as in the inputs above."
            )
            nod_ref = sorted(nodes_set(adj), key=str)
            st.markdown("**Vertices**")
            st.dataframe(
                pd.DataFrame({"Vertex": nod_ref}),
                use_container_width=True,
                hide_index=True,
                height=min(260, 44 + max(len(nod_ref), 1) * 34),
            )
            st.markdown("**Edges**")
            ref_e = df[["edge_id", "SRC", "TGT", "Unix"]].copy()
            ref_e.columns = ["Edge ID", "Source", "Target", "Time"]
            st.dataframe(
                ref_e,
                use_container_width=True,
                hide_index=True,
                height=min(400, 48 + min(len(ref_e), 30) * 36),
            )

    with tab_advanced:
        st.subheader("Advanced · Bottleneck scan")
        st.caption(
            "Rank edges or vertices by **temporarily deleting** each and recomputing global metrics; slow when there are many edges. "
            "The plot shares layout with **Explore**; tables show Top-K; **yellow** marks critical edges/vertices."
        )
        adj = dataframe_to_adj(df)
        t_lo_a, t_hi_a = int(df["Unix"].min()), int(df["Unix"].max())
        mode_map = {"Edges only": "edge", "Vertices only": "vertex", "Edges and vertices": "both"}

        st.markdown("##### Scan options")
        if len(df) > MAX_EDGE_ROWS_BOTTLENECK:
            st.warning(
                f"**{len(df)}** edges exceed the limit {MAX_EDGE_ROWS_BOTTLENECK}; "
                "bottleneck scan is disabled here. Use a smaller subset."
            )
        else:
            lr1, lr2, lr3 = st.columns([2.2, 1.2, 1])
            with lr1:
                st.markdown("Scan target")
            with lr2:
                st.markdown("Top-K")
            with lr3:
                st.markdown(" ")

            sc1, sc2, sc3 = st.columns([2.2, 1.2, 1])
            with sc1:
                mode_e = st.selectbox(
                    "Scan target",
                    ["Edges only", "Vertices only", "Edges and vertices"],
                    index=0,
                    key="adv_scan_mode",
                    label_visibility="collapsed",
                )
            with sc2:
                ek2 = st.number_input(
                    "Top-K",
                    min_value=1,
                    max_value=25,
                    value=5,
                    key="topk_adv",
                    label_visibility="collapsed",
                    help='Keep top K by impact for edges and vertices separately (with "Edges and vertices", each table has K rows).',
                )
            with sc3:
                start_scan = st.button("Run scan", type="primary", use_container_width=True)

            if start_scan:
                with st.spinner("Scanning…"):
                    try:
                        bn = find_menger_bottlenecks(
                            adj,
                            top_k=int(ek2),
                            mode=mode_map[mode_e],
                            return_full_ranked=True,
                        )
                        st.session_state["adv_bn_export"] = bn
                        st.rerun()
                    except Exception as e:  # noqa: BLE001
                        st.error(str(e))

            bn_store = st.session_state.get("adv_bn_export")
            if bn_store:
                re = bn_store.get("edge_bottlenecks") or []
                rv = bn_store.get("vertex_bottlenecks") or []
                st.markdown("##### Scan results")
                res_lines: List[str] = []
                has_e, has_v = bool(re), bool(rv)
                if has_e and not has_v:
                    top = re[0]
                    res_lines.append(
                        f"Evaluated all **{len(df)}** edges by removal. "
                        f"Largest impact: **`{top.get('edge_id')}`** ({top.get('src')} → {top.get('tgt')}), "
                        f"reachability drop **{top.get('reachability_drop')}**."
                    )
                elif has_v and not has_e:
                    topv = rv[0]
                    res_lines.append(
                        f"Evaluated all **{len(nodes_set(adj))}** vertices by removal. "
                        f"Largest impact: **`{topv.get('vertex')}`**, "
                        f"reachability drop **{topv.get('reachability_drop')}**."
                    )
                elif has_e and has_v:
                    top = re[0]
                    topv = rv[0]
                    res_lines.append(
                        f"**Edges**: among **{len(df)}** edges, largest impact **`{top.get('edge_id')}`** "
                        f"({top.get('src')} → {top.get('tgt')}), reachability drop **{top.get('reachability_drop')}**."
                    )
                    res_lines.append(
                        f"**Vertices**: largest impact **`{topv.get('vertex')}`**, "
                        f"reachability drop **{topv.get('reachability_drop')}**."
                    )
                else:
                    res_lines.append("Scan finished (no Top-K list to show).")
                res_lines.append(
                    "Below: **Top-K tables** (column widths and formats adjusted); "
                    "then a network view with **yellow** critical edges/vertices; slider changes cumulative time. "
                    "Download full ranking as CSV."
                )
                st.markdown("\n\n".join(res_lines))

                _render_bottleneck_result_tables(re, rv)

                stress_e = {str(r["edge_id"]) for r in re}
                stress_v = {str(r["vertex"]) for r in rv}
                st.markdown("##### Network view")
                t_adv = st.slider(
                    "Plot time (cumulative)",
                    min_value=t_lo_a,
                    max_value=t_hi_a,
                    value=t_hi_a,
                    key="adv_plot_t",
                )
                try:
                    st.caption(
                        f"Edges with time ≤ **{int(t_adv)}** only; same layout as **Explore**."
                    )
                    fig_a, w_a = temporal_network_figure(
                        df,
                        int(t_adv),
                        pos,
                        stress_edge_ids=stress_e,
                        stress_vertices=stress_v,
                        figure_height=580,
                    )
                    if w_a:
                        st.caption(w_a)
                    st.plotly_chart(
                        fig_a,
                        use_container_width=True,
                        config={"plotGlPixelRatio": 2},
                        key="plot_advanced_bottleneck",
                    )
                except Exception as e:  # noqa: BLE001
                    st.error(f"Plot error: {e}")

                payload, fname = _bottleneck_export_csv(bn_store)
                if payload:
                    st.download_button(
                        label="Download full ranking (CSV)",
                        data=payload,
                        file_name=fname,
                        mime="text/csv",
                        key="dl_bn_full",
                    )


if __name__ == "__main__":
    main()
