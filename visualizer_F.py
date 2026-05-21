# Credit: F (excerpt below); A (no Streamlit dep, Agg backend, empty graph / binary JSON fixes).
# Integrated from: teammate_deliverables/F/t2.py → visualizer_F.py (not imported by main app; archive/reference).
# Role: u,v,t from JSON; Matplotlib + NetworkX snapshot by time t.

from __future__ import annotations

import json
import os
from typing import Any, BinaryIO, Optional, Union

os.environ.setdefault("MPLBACKEND", "Agg")
import matplotlib

matplotlib.use(os.environ.get("MPLBACKEND", "Agg"))
import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd

JsonSource = Union[str, bytes, BinaryIO, Any]


def load_json_data(uploaded_file: JsonSource) -> Optional[pd.DataFrame]:
    """
    Parse JSON array into columns u, v, t (same idea as t2).
    Accepts str, bytes, or objects with read() (e.g. Streamlit UploadedFile).
    """
    try:
        if isinstance(uploaded_file, str):
            data = json.loads(uploaded_file)
        elif isinstance(uploaded_file, (bytes, bytearray)):
            data = json.loads(uploaded_file.decode("utf-8"))
        else:
            raw = uploaded_file.read()
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            data = json.loads(raw)
        if not isinstance(data, list):
            return None
        df = pd.DataFrame(data)
        if df.empty:
            return None
        cols = {str(c).strip().lower(): c for c in df.columns}
        if not {"u", "v", "t"}.issubset(cols.keys()):
            return None
        out = df[[cols["u"], cols["v"], cols["t"]]].copy()
        out.columns = ["u", "v", "t"]
        return out
    except (json.JSONDecodeError, TypeError, ValueError, UnicodeDecodeError, AttributeError):
        return None


class TemporalVisualizer:
    """Same idea as t2: spring layout on full graph; filter edges with t <= current_time."""

    def __init__(self, df: pd.DataFrame):
        self.df = df[["u", "v", "t"]].copy()
        self.G = nx.DiGraph()
        for _, row in self.df.iterrows():
            self.G.add_edge(row["u"], row["v"])
        self.pos = self.compute_static_layout()

    def compute_static_layout(self):
        if self.G.number_of_nodes() == 0:
            return {}
        return nx.spring_layout(self.G, seed=42)

    def render_snapshot_frame(self, current_time=None):
        """If current_time is None, draw full graph; else subgraph with t <= current_time."""
        fig, ax = plt.subplots(figsize=(10, 7))

        if current_time is not None:
            display_df = self.df[self.df["t"] <= current_time]
            edges = list(zip(display_df["u"], display_df["v"]))
            active_nodes = list(set(display_df["u"]).union(set(display_df["v"])))
        else:
            edges = list(self.G.edges())
            active_nodes = list(self.G.nodes())

        if not active_nodes:
            ax.set_title("No nodes")
            ax.axis("off")
            return fig

        nx.draw_networkx_nodes(
            self.G,
            self.pos,
            nodelist=active_nodes,
            node_color="skyblue",
            node_size=500,
            ax=ax,
        )
        nx.draw_networkx_labels(self.G, self.pos, font_size=10, ax=ax)
        nx.draw_networkx_edges(
            self.G,
            self.pos,
            edgelist=edges,
            edge_color="gray",
            arrows=True,
            ax=ax,
        )

        title = "Full Static Network" if current_time is None else f"Temporal Snapshot at t={current_time}"
        ax.set_title(title)
        return fig


__all__ = ["TemporalVisualizer", "load_json_data"]
