# Credit: A (integration layer); adj contract aligned with E’s original design.
# Integrated from: contract per teammate_deliverables/E/e_teammate.py; this module is integration-only.
# Role: Turn B-cleaned DataFrame into adj shared by C/D/E.

from collections import defaultdict
from typing import Any, Dict, List, Tuple

import pandas as pd

AdjList = Dict[str, List[Tuple[int, str, str]]]


def dataframe_to_adj(df: pd.DataFrame) -> AdjList:
    """
    Convert a DataFrame with SRC, TGT, Unix into an adjacency dict.

    Rows are sorted by (Unix, SRC, TGT) before building, same as teammate E's
    ``build_adj_time_from_csv``. Prefer ``clean_temporal_data`` output so each
    row keeps a stable ``edge_id``; if ``edge_id`` is absent, this function
    assigns ``e0000001``, ... in that sorted order.
    """
    required = {"SRC", "TGT", "Unix"}
    cols = {str(c).strip() for c in df.columns}
    missing = required - cols
    if missing:
        raise ValueError(
            f"dataframe_to_adj requires columns SRC, TGT, Unix; missing: {sorted(missing)}"
        )

    full = df.copy()
    full["SRC"] = full["SRC"].astype(str).str.strip()
    full["TGT"] = full["TGT"].astype(str).str.strip()
    full["Unix"] = pd.to_numeric(full["Unix"], errors="coerce")
    if full["Unix"].isna().any():
        raise ValueError("Unix must be numeric for all rows.")
    full["Unix"] = full["Unix"].astype(int)

    full = full.sort_values(by=["Unix", "SRC", "TGT"]).reset_index(drop=True)

    if "edge_id" in full.columns:
        eids = full["edge_id"].astype(str)
    else:
        eids = [f"e{str(i).zfill(7)}" for i in range(1, len(full) + 1)]

    adj: defaultdict[str, List[Tuple[int, str, str]]] = defaultdict(list)
    for t, src, tgt, eid in zip(full["Unix"], full["SRC"], full["TGT"], eids):
        adj[src].append((int(t), str(tgt), str(eid)))

    return dict(adj)


def build_adj_time_from_edges(
    edges_sorted: List[Tuple[int, Any, Any, Any]],
) -> AdjList:
    """
    Build ``adj`` from a list of ``(Unix, SRC, TGT, edge_id)`` tuples
    (global sort optional; outgoing lists follow input order per source).
    Same contract as teammate E's helper.
    """
    adj: defaultdict[str, List[Tuple[int, str, str]]] = defaultdict(list)
    for t, src, tgt, eid in edges_sorted:
        adj[str(src).strip()].append((int(t), str(tgt).strip(), str(eid)))
    return dict(adj)
