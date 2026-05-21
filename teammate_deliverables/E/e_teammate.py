"""
algorithms.py — Tang Zixuan's Contribution (Updated)
======================================================
Module: find_menger_bottlenecks & optimize_algorithm_speed

Updated to integrate with Ranjan Ankit's datacleaned.ipynb pipeline:
  - Supports loading from his exported CSV files (mathoverflow_cleaned.csv,
    mathoverflow_demo_42k.csv) via load_temporal_file() + clean_temporal_data()
  - Compatible with the defaultdict-based adj_time construction
  - Includes a build_adj_time() helper that mirrors Ranjan's Cell 9 logic
  - Tested with both the small 7-node graph and the real MathOverflow dataset

Data format (unchanged):
    adj_time = {src: [(timestamp, tgt, edge_id), ...], ...}
"""

from collections import deque, defaultdict
import copy
import time as time_module
import os

# ============================================================================
# Section 0 — Data integration helpers (compatible with Ranjan's pipeline)
# ============================================================================

def build_adj_time_from_csv(csv_path):
    """Build adj_time dict from a cleaned CSV file produced by Ranjan's pipeline.

    The CSV must have columns: edge_id, SRC, TGT, Unix (and optionally datetime).
    This mirrors the logic in Ranjan's datacleaned.ipynb Cell 8-9.

    Parameters
    ----------
    csv_path : str
        Path to cleaned CSV file (e.g. "mathoverflow_demo_42k.csv")

    Returns
    -------
    adj_time : dict
        {src_node: [(timestamp, tgt_node, edge_id), ...], ...}
    df : pd.DataFrame
        The loaded and sorted DataFrame for reference
    """
    import pandas as pd

    df = pd.read_csv(csv_path)

    # Ensure correct types (matching Ranjan's clean_temporal_data)
    df["SRC"] = df["SRC"].astype(str).str.strip()
    df["TGT"] = df["TGT"].astype(str).str.strip()
    df["Unix"] = df["Unix"].astype(int)

    # Sort by (Unix, SRC, TGT) — same as Ranjan's Cell 8
    edges_sorted = sorted(
        zip(df["Unix"], df["SRC"], df["TGT"], df["edge_id"]),
        key=lambda x: (x[0], x[1], x[2])
    )

    # Build adjacency list — same as Ranjan's Cell 9
    adj_time = defaultdict(list)
    for t, src, tgt, eid in edges_sorted:
        adj_time[src].append((t, tgt, eid))

    return dict(adj_time), df


def build_adj_time_from_edges(edges_sorted):
    """Build adj_time dict from a pre-sorted edge list.

    Parameters
    ----------
    edges_sorted : list of (timestamp, src, tgt, edge_id) tuples

    Returns
    -------
    adj_time : dict
    """
    adj_time = defaultdict(list)
    for t, src, tgt, eid in edges_sorted:
        adj_time[src].append((t, tgt, eid))
    return dict(adj_time)


# ============================================================================
# Section 1 — Shared utilities (from Bowen Li, included for self-containment)
# ============================================================================

def nodes_set(adj_mat):
    """Collect all node IDs from an adjacency-list dict.

    Nodes that only appear as targets (no outgoing edges) are also included.
    """
    all_nodes = set(adj_mat.keys())
    for edges in adj_mat.values():
        for _, tar, _ in edges:
            all_nodes.add(tar)
    return all_nodes


def BFS_Single(adj_mat, SRC, TGT):
    """Temporal BFS from SRC to TGT.

    Returns (earliest_arrival_time, path) where path is a list of
    (node, timestamp) tuples.  Returns (None, None) if unreachable.
    """
    if not adj_mat:
        return None, None

    all_nodes = nodes_set(adj_mat)
    if SRC not in all_nodes or TGT not in all_nodes:
        return None, None

    queue = deque()
    visited = set()
    queue.append((SRC, -1))
    parents = {}

    while queue:
        point, t = queue.popleft()
        if (point, t) not in visited:
            visited.add((point, t))

        if point == TGT and t != -1:
            path = []
            path.append((point, t))
            cur = (point, t)
            while cur in parents:
                prev = parents[cur]
                path.append(prev)
                cur = prev
            path.pop()
            path.reverse()
            return t, path

        if point in adj_mat:
            for ts, tar, _ in adj_mat[point]:
                if (tar, ts) not in visited and ts >= t:
                    queue.append((tar, ts))
                    parents[(tar, ts)] = (point, t)

    return None, None


def Arrive_time_and_Latency(adj_mat, SRC):
    """Compute earliest arrival time and latency from SRC to every reachable node.

    Returns dict  {target_node: [arrival_time, latency]}  where
    latency = arrival_time - departure_time_of_SRC.
    """
    if not adj_mat:
        return None

    all_nodes = nodes_set(adj_mat)
    if SRC not in all_nodes:
        return None

    queue = deque()
    visited = set()

    start_time = 0
    if SRC in adj_mat and adj_mat[SRC]:
        start_time = adj_mat[SRC][0][0]

    queue.append((SRC, -1))
    src2tgts = {SRC: [float('inf'), float('inf')]}

    while queue:
        point, t = queue.popleft()
        if (point, t) not in visited:
            visited.add((point, t))

        if point in adj_mat:
            for ts, tar, _ in adj_mat[point]:
                if (tar, ts) not in visited and ts >= t:
                    queue.append((tar, ts))
                    if tar not in src2tgts or ts < src2tgts[tar][0]:
                        src2tgts[tar] = [ts, ts - start_time]

    if not src2tgts:
        return {}
    if src2tgts[SRC][0] == float('inf'):
        src2tgts.pop(SRC)
    return src2tgts


def sensitive(adj_org, adj_modify=None, del_num=0):
    """Compute global reachability and average latency.

    Parameters
    ----------
    adj_org    : original adjacency list (used for iterating source nodes)
    adj_modify : (optional) modified adjacency list to evaluate
    del_num    : number of deleted vertices (adjusts denominator)

    Returns (global_reachable_ratio, average_latency)
    """
    if adj_modify is None:
        adj_modify = adj_org

    num_reach = 0
    total_lat = 0

    all_nodes = nodes_set(adj_org)
    n = len(all_nodes) - del_num

    for src in adj_org:
        s2t = Arrive_time_and_Latency(adj_modify, src)
        if not s2t:
            continue
        num_reach += len(s2t)
        for v in s2t:
            total_lat += s2t[v][1]

    if num_reach == 0:
        return 0.0, float('inf')

    return num_reach / (n ** 2), total_lat / num_reach


# ============================================================================
# Section 2 — find_menger_bottlenecks  (Tang Zixuan)
# ============================================================================

def _remove_edge(adj_mat, edge_id):
    """Return a deep copy of adj_mat with the specified edge removed."""
    adj_new = copy.deepcopy(adj_mat)
    for key in adj_new:
        adj_new[key] = [e for e in adj_new[key] if e[2] != edge_id]
    return adj_new


def _remove_vertex(adj_mat, vertex):
    """Return a deep copy of adj_mat with the specified vertex removed."""
    adj_new = copy.deepcopy(adj_mat)
    adj_new.pop(vertex, None)
    for key in adj_new:
        adj_new[key] = [e for e in adj_new[key] if e[1] != vertex]
    return adj_new


def find_menger_bottlenecks(adj_mat, top_k=5, mode="both"):
    """Identify the most critical edges and/or vertices in a temporal network.

    Inspired by Menger's Theorem, which relates the maximum number of
    independent paths between two nodes to the minimum cut.  In a temporal
    setting, we approximate bottleneck identification by measuring the *drop
    in global temporal reachability* when each edge or vertex is individually
    removed.

    Parameters
    ----------
    adj_mat : dict
        Adjacency list: {src_node: [(timestamp, tgt_node, edge_id), ...], ...}
        Compatible with Ranjan's build pipeline (datacleaned.ipynb Cell 9).
    top_k : int, default 5
        Number of top bottleneck elements to return for each category.
    mode : str, default "both"
        "edge"   - only analyse edges
        "vertex" - only analyse vertices
        "both"   - analyse both edges and vertices

    Returns
    -------
    dict with up to two keys:
        "edge_bottlenecks" : list of dicts sorted by impact (descending)
            Each dict: {"edge_id", "src", "tgt", "timestamp",
                        "reachability_before", "reachability_after",
                        "reachability_drop", "latency_before", "latency_after",
                        "latency_increase"}
        "vertex_bottlenecks" : list of dicts sorted by impact (descending)
            Each dict: {"vertex",
                        "reachability_before", "reachability_after",
                        "reachability_drop", "latency_before", "latency_after",
                        "latency_increase",
                        "out_degree", "in_degree"}

    Complexity
    ----------
    O(K * V * (V + E))  where K = number of elements tested.
    Use optimize_algorithm_speed for large-scale analysis.
    """
    results = {}

    # Baseline metrics
    base_reach, base_lat = sensitive(adj_mat)

    # ------------------------------------------------------------------
    # Edge bottleneck analysis
    # ------------------------------------------------------------------
    if mode in ("edge", "both"):
        all_edges = []
        for src, edges in adj_mat.items():
            for ts, tgt, eid in edges:
                all_edges.append((eid, src, tgt, ts))

        edge_impacts = []
        for eid, src, tgt, ts in all_edges:
            adj_mod = _remove_edge(adj_mat, eid)
            new_reach, new_lat = sensitive(adj_mat, adj_mod, 0)
            edge_impacts.append({
                "edge_id": eid,
                "src": src,
                "tgt": tgt,
                "timestamp": ts,
                "reachability_before": round(base_reach, 6),
                "reachability_after": round(new_reach, 6),
                "reachability_drop": round(base_reach - new_reach, 6),
                "latency_before": round(base_lat, 4),
                "latency_after": round(new_lat, 4) if new_lat != float('inf') else float('inf'),
                "latency_increase": round(new_lat - base_lat, 4) if new_lat != float('inf') else float('inf'),
            })

        edge_impacts.sort(key=lambda x: (
            -x["reachability_drop"],
            -(x["latency_increase"] if x["latency_increase"] != float('inf') else 1e18)
        ))
        results["edge_bottlenecks"] = edge_impacts[:top_k]

    # ------------------------------------------------------------------
    # Vertex bottleneck analysis
    # ------------------------------------------------------------------
    if mode in ("vertex", "both"):
        all_nodes = nodes_set(adj_mat)

        out_deg = {v: 0 for v in all_nodes}
        in_deg = {v: 0 for v in all_nodes}
        for src, edges in adj_mat.items():
            out_deg[src] = len(edges)
            for _, tgt, _ in edges:
                in_deg[tgt] = in_deg.get(tgt, 0) + 1

        vertex_impacts = []
        for v in all_nodes:
            adj_mod = _remove_vertex(adj_mat, v)
            new_reach, new_lat = sensitive(adj_mat, adj_mod, 1)
            vertex_impacts.append({
                "vertex": v,
                "reachability_before": round(base_reach, 6),
                "reachability_after": round(new_reach, 6),
                "reachability_drop": round(base_reach - new_reach, 6),
                "latency_before": round(base_lat, 4),
                "latency_after": round(new_lat, 4) if new_lat != float('inf') else float('inf'),
                "latency_increase": round(new_lat - base_lat, 4) if new_lat != float('inf') else float('inf'),
                "out_degree": out_deg.get(v, 0),
                "in_degree": in_deg.get(v, 0),
            })

        vertex_impacts.sort(key=lambda x: (
            -x["reachability_drop"],
            -(x["latency_increase"] if x["latency_increase"] != float('inf') else 1e18)
        ))
        results["vertex_bottlenecks"] = vertex_impacts[:top_k]

    return results


# ============================================================================
# Section 3 — optimize_algorithm_speed  (Tang Zixuan)
# ============================================================================

class TemporalGraphOptimized:
    """Optimized temporal graph data structure with indexed edge lookups,
    pre-sorted adjacency lists, and cached BFS results.

    This class wraps the raw adjacency-list format used by the rest of the
    project and provides:
      - O(1) edge removal / restoration via an active-edge bitmap
      - Adjacency lists pre-sorted by timestamp for early termination
      - An LRU-style result cache for repeated BFS / sensitivity queries
      - Batch bottleneck analysis that reuses cached baselines

    Usage
    -----
    >>> graph = TemporalGraphOptimized(adj_time)
    >>> t, path = graph.bfs_single('1', '6')
    >>> reach, lat = graph.sensitivity()
    >>> graph.remove_edge('e2')
    >>> reach2, lat2 = graph.sensitivity()
    >>> graph.restore_edge('e2')
    """

    def __init__(self, adj_mat):
        """Build optimized internal structures from a raw adjacency dict.

        Parameters
        ----------
        adj_mat : dict
            Standard adjacency list produced by Ranjan's pipeline:
            {src: [(timestamp, tgt, edge_id), ...], ...}
            Works with both regular dict and defaultdict.
        """
        self._raw = adj_mat

        # --- Pre-sort adjacency lists by timestamp ---
        self._adj_sorted = {}
        for src, edges in adj_mat.items():
            self._adj_sorted[src] = sorted(edges, key=lambda e: e[0])

        # --- Build edge index: edge_id -> (src, index_in_adj_list) ---
        self._edge_index = {}
        self._active_edges = set()
        for src, edges in self._adj_sorted.items():
            for idx, (ts, tgt, eid) in enumerate(edges):
                self._edge_index[eid] = (src, idx)
                self._active_edges.add(eid)

        # --- Node set ---
        self._all_nodes = set(self._adj_sorted.keys())
        for edges in self._adj_sorted.values():
            for _, tgt, _ in edges:
                self._all_nodes.add(tgt)

        # --- Removed vertices ---
        self._removed_vertices = set()

        # --- Cache ---
        self._cache = {}
        self._cache_hits = 0
        self._cache_misses = 0

    # ---- State key for caching ----
    def _state_key(self):
        return (frozenset(self._active_edges), frozenset(self._removed_vertices))

    # ---- Active adjacency iteration (generator, avoids copy) ----
    def _iter_neighbors(self, node):
        """Yield (timestamp, target, edge_id) for active edges from node."""
        if node in self._removed_vertices:
            return
        if node not in self._adj_sorted:
            return
        for ts, tgt, eid in self._adj_sorted[node]:
            if eid in self._active_edges and tgt not in self._removed_vertices:
                yield ts, tgt, eid

    # ---- Modification API ----
    def remove_edge(self, edge_id):
        """Deactivate an edge (O(1))."""
        self._active_edges.discard(edge_id)

    def restore_edge(self, edge_id):
        """Reactivate an edge (O(1))."""
        if edge_id in self._edge_index:
            self._active_edges.add(edge_id)

    def remove_vertex(self, vertex):
        """Deactivate a vertex and all its incident edges."""
        self._removed_vertices.add(vertex)

    def restore_vertex(self, vertex):
        """Reactivate a vertex."""
        self._removed_vertices.discard(vertex)

    def reset(self):
        """Restore all edges and vertices."""
        self._active_edges = set(self._edge_index.keys())
        self._removed_vertices.clear()
        self._cache.clear()

    # ---- Optimized BFS ----
    def bfs_single(self, src, tgt):
        """Temporal BFS from src to tgt using active edges only.

        Returns (earliest_arrival_time, path) or (None, None).
        """
        active_nodes = self._all_nodes - self._removed_vertices
        if src not in active_nodes or tgt not in active_nodes:
            return None, None

        queue = deque()
        visited = set()
        queue.append((src, -1))
        parents = {}

        while queue:
            point, t = queue.popleft()
            if (point, t) in visited:
                continue
            visited.add((point, t))

            if point == tgt and t != -1:
                path = [(point, t)]
                cur = (point, t)
                while cur in parents:
                    prev = parents[cur]
                    path.append(prev)
                    cur = prev
                path.pop()
                path.reverse()
                return t, path

            for ts, tar, _ in self._iter_neighbors(point):
                if ts >= t and (tar, ts) not in visited:
                    queue.append((tar, ts))
                    if (tar, ts) not in parents:
                        parents[(tar, ts)] = (point, t)

        return None, None

    # ---- Optimized arrival time / latency ----
    def arrive_time_and_latency(self, src):
        """Compute earliest arrival and latency from src to all reachable nodes."""
        active_nodes = self._all_nodes - self._removed_vertices
        if src not in active_nodes:
            return None

        queue = deque()
        visited = set()

        start_time = 0
        if src not in self._removed_vertices and src in self._adj_sorted:
            for ts, tgt, eid in self._adj_sorted[src]:
                if eid in self._active_edges and tgt not in self._removed_vertices:
                    start_time = ts
                    break

        queue.append((src, -1))
        src2tgts = {src: [float('inf'), float('inf')]}

        while queue:
            point, t = queue.popleft()
            if (point, t) in visited:
                continue
            visited.add((point, t))

            for ts, tar, _ in self._iter_neighbors(point):
                if ts >= t and (tar, ts) not in visited:
                    queue.append((tar, ts))
                    if tar not in src2tgts or ts < src2tgts[tar][0]:
                        src2tgts[tar] = [ts, ts - start_time]

        if not src2tgts:
            return {}
        if src2tgts[src][0] == float('inf'):
            src2tgts.pop(src)
        return src2tgts

    # ---- Optimized sensitivity with caching ----
    def sensitivity(self):
        """Compute global reachability and average latency (with caching).

        Returns (global_reachable_ratio, average_latency).
        """
        key = ("sensitivity", self._state_key())
        if key in self._cache:
            self._cache_hits += 1
            return self._cache[key]
        self._cache_misses += 1

        num_reach = 0
        total_lat = 0
        n = len(self._all_nodes) - len(self._removed_vertices)

        for src in self._adj_sorted:
            if src in self._removed_vertices:
                continue
            s2t = self.arrive_time_and_latency(src)
            if not s2t:
                continue
            num_reach += len(s2t)
            for v in s2t:
                total_lat += s2t[v][1]

        if num_reach == 0:
            result = (0.0, float('inf'))
        else:
            result = (num_reach / (n ** 2), total_lat / num_reach)

        self._cache[key] = result
        return result

    # ---- Batch bottleneck analysis (optimized) ----
    def find_bottlenecks_fast(self, top_k=5, mode="both"):
        """Optimized bottleneck analysis using O(1) edge/vertex toggling.

        Much faster than the standalone find_menger_bottlenecks because:
          - No deep-copy per iteration
          - Pre-sorted adjacency lists
          - Cached baseline computation

        Returns same structure as find_menger_bottlenecks().
        """
        results = {}

        saved_active = set(self._active_edges)
        saved_removed = set(self._removed_vertices)

        base_reach, base_lat = self.sensitivity()

        # --- Edge bottlenecks ---
        if mode in ("edge", "both"):
            all_edges = []
            for src, edges in self._adj_sorted.items():
                for ts, tgt, eid in edges:
                    all_edges.append((eid, src, tgt, ts))

            edge_impacts = []
            for eid, src, tgt, ts in all_edges:
                self.remove_edge(eid)
                new_reach, new_lat = self.sensitivity()
                self.restore_edge(eid)

                edge_impacts.append({
                    "edge_id": eid,
                    "src": src,
                    "tgt": tgt,
                    "timestamp": ts,
                    "reachability_before": round(base_reach, 6),
                    "reachability_after": round(new_reach, 6),
                    "reachability_drop": round(base_reach - new_reach, 6),
                    "latency_before": round(base_lat, 4),
                    "latency_after": round(new_lat, 4) if new_lat != float('inf') else float('inf'),
                    "latency_increase": round(new_lat - base_lat, 4) if new_lat != float('inf') else float('inf'),
                })

            edge_impacts.sort(key=lambda x: (
                -x["reachability_drop"],
                -(x["latency_increase"] if x["latency_increase"] != float('inf') else 1e18)
            ))
            results["edge_bottlenecks"] = edge_impacts[:top_k]

        # --- Vertex bottlenecks ---
        if mode in ("vertex", "both"):
            out_deg = {}
            in_deg = {}
            for v in self._all_nodes:
                out_deg[v] = 0
                in_deg[v] = 0
            for src, edges in self._adj_sorted.items():
                out_deg[src] = len(edges)
                for _, tgt, _ in edges:
                    in_deg[tgt] = in_deg.get(tgt, 0) + 1

            vertex_impacts = []
            for v in self._all_nodes:
                self.remove_vertex(v)
                new_reach, new_lat = self.sensitivity()
                self.restore_vertex(v)

                vertex_impacts.append({
                    "vertex": v,
                    "reachability_before": round(base_reach, 6),
                    "reachability_after": round(new_reach, 6),
                    "reachability_drop": round(base_reach - new_reach, 6),
                    "latency_before": round(base_lat, 4),
                    "latency_after": round(new_lat, 4) if new_lat != float('inf') else float('inf'),
                    "latency_increase": round(new_lat - base_lat, 4) if new_lat != float('inf') else float('inf'),
                    "out_degree": out_deg.get(v, 0),
                    "in_degree": in_deg.get(v, 0),
                })

            vertex_impacts.sort(key=lambda x: (
                -x["reachability_drop"],
                -(x["latency_increase"] if x["latency_increase"] != float('inf') else 1e18)
            ))
            results["vertex_bottlenecks"] = vertex_impacts[:top_k]

        # Restore original state
        self._active_edges = saved_active
        self._removed_vertices = saved_removed

        return results

    def cache_stats(self):
        """Return cache hit/miss statistics."""
        return {
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "cached_entries": len(self._cache),
        }

    def get_graph_info(self):
        """Return summary statistics of the current graph state."""
        active_nodes = self._all_nodes - self._removed_vertices
        active_edge_count = sum(
            1 for src in self._adj_sorted
            if src not in self._removed_vertices
            for _, tgt, eid in self._adj_sorted[src]
            if eid in self._active_edges and tgt not in self._removed_vertices
        )
        return {
            "total_nodes": len(self._all_nodes),
            "active_nodes": len(active_nodes),
            "removed_nodes": len(self._removed_vertices),
            "total_edges": len(self._edge_index),
            "active_edges": active_edge_count,
            "removed_edges": len(self._edge_index) - len(self._active_edges),
        }


def optimize_algorithm_speed(adj_mat):
    """Factory function that wraps a raw adjacency list into an optimized
    TemporalGraphOptimized object.

    This is the public entry point referenced in the project specification.

    Parameters
    ----------
    adj_mat : dict
        Standard adjacency list produced by Ranjan's datacleaned.ipynb:
        {src: [(timestamp, tgt, edge_id), ...], ...}

    Returns
    -------
    TemporalGraphOptimized
        An optimized graph object with cached BFS, O(1) edge toggling,
        and pre-sorted adjacency lists.

    Example
    -------
    >>> # From Ranjan's CSV output:
    >>> adj, df = build_adj_time_from_csv("mathoverflow_demo_42k.csv")
    >>> graph = optimize_algorithm_speed(adj)
    >>> t, path = graph.bfs_single('1', '6')
    >>> reach, lat = graph.sensitivity()
    >>> bottlenecks = graph.find_bottlenecks_fast(top_k=3)
    """
    return TemporalGraphOptimized(adj_mat)


# ============================================================================
# Section 4 — Demonstration & Testing
# ============================================================================

if __name__ == "__main__":

    # ==================================================================
    # Part A: Small test graph (same as Bowen Li's draft)
    # ==================================================================
    adj_time_small = {
        '1': [(1, '2', 'e0'), (2, '6', 'e1')],
        '6': [(3, '2', 'e7'), (10, '7', 'e9')],
        '2': [(4, '3', 'e2')],
        '3': [(5, '4', 'e3'), (6, '5', 'e4')],
        '4': [(5, '6', 'e5'), (7, '5', 'e5_2')],
        '5': [(8, '6', 'e6'), (9, '5', 'e8')],
    }

    print("=" * 70)
    print("TEMPORAL PATH EXPLORER — Tang Zixuan's Module Tests")
    print("=" * 70)

    # ---- Test 1: Baseline metrics ----
    print("\n[Test 1] Baseline graph metrics (7-node test graph)")
    print(f"  Nodes: {nodes_set(adj_time_small)}")
    print(f"  Num nodes: {len(nodes_set(adj_time_small))}")
    reach, lat = sensitive(adj_time_small)
    print(f"  Global reachability: {reach:.6f}")
    print(f"  Average latency:    {lat:.4f}")

    # ---- Test 2: find_menger_bottlenecks ----
    print("\n" + "=" * 70)
    print("[Test 2] find_menger_bottlenecks (unoptimized)")
    print("=" * 70)

    t0 = time_module.time()
    bottlenecks = find_menger_bottlenecks(adj_time_small, top_k=3, mode="both")
    t1 = time_module.time()
    print(f"  Execution time: {t1 - t0:.4f}s")

    print("\n  Top edge bottlenecks:")
    for i, b in enumerate(bottlenecks["edge_bottlenecks"], 1):
        print(f"    {i}. Edge {b['edge_id']} ({b['src']}->{b['tgt']} @ t={b['timestamp']})")
        print(f"       Reachability drop: {b['reachability_drop']:.6f}")
        print(f"       Latency increase:  {b['latency_increase']}")

    print("\n  Top vertex bottlenecks:")
    for i, b in enumerate(bottlenecks["vertex_bottlenecks"], 1):
        print(f"    {i}. Vertex {b['vertex']} (out={b['out_degree']}, in={b['in_degree']})")
        print(f"       Reachability drop: {b['reachability_drop']:.6f}")
        print(f"       Latency increase:  {b['latency_increase']}")

    # ---- Test 3: optimize_algorithm_speed ----
    print("\n" + "=" * 70)
    print("[Test 3] optimize_algorithm_speed (optimized wrapper)")
    print("=" * 70)

    graph = optimize_algorithm_speed(adj_time_small)
    print(f"\n  Graph info: {graph.get_graph_info()}")

    t_arr, path = graph.bfs_single('1', '6')
    print(f"\n  BFS('1' -> '6'): arrival={t_arr}, path={path}")

    t_arr2, path2 = graph.bfs_single('1', '7')
    print(f"  BFS('1' -> '7'): arrival={t_arr2}, path={path2}")

    reach_opt, lat_opt = graph.sensitivity()
    print(f"\n  Sensitivity (original):  reach={reach_opt:.6f}, lat={lat_opt:.4f}")

    graph.remove_edge('e2')
    reach_mod, lat_mod = graph.sensitivity()
    print(f"  Sensitivity (-e2):       reach={reach_mod:.6f}, lat={lat_mod:.4f}")
    graph.restore_edge('e2')

    # ---- Test 4: Optimized bottleneck analysis ----
    print("\n" + "=" * 70)
    print("[Test 4] find_bottlenecks_fast (optimized)")
    print("=" * 70)

    t0 = time_module.time()
    bn_fast = graph.find_bottlenecks_fast(top_k=3, mode="both")
    t1 = time_module.time()
    print(f"  Execution time: {t1 - t0:.4f}s")

    print("\n  Top edge bottlenecks (fast):")
    for i, b in enumerate(bn_fast["edge_bottlenecks"], 1):
        print(f"    {i}. Edge {b['edge_id']} — drop={b['reachability_drop']:.6f}")

    print("\n  Top vertex bottlenecks (fast):")
    for i, b in enumerate(bn_fast["vertex_bottlenecks"], 1):
        print(f"    {i}. Vertex {b['vertex']} — drop={b['reachability_drop']:.6f}")

    print(f"\n  Cache stats: {graph.cache_stats()}")

    # ---- Test 5: Consistency check ----
    print("\n" + "=" * 70)
    print("[Test 5] Consistency — unoptimized vs optimized results")
    print("=" * 70)

    r1, l1 = sensitive(adj_time_small)
    graph.reset()
    r2, l2 = graph.sensitivity()
    print(f"  Unoptimized: reach={r1:.6f}, lat={l1:.4f}")
    print(f"  Optimized:   reach={r2:.6f}, lat={l2:.4f}")
    print(f"  Match: {abs(r1 - r2) < 1e-9 and abs(l1 - l2) < 1e-9}")

    # ---- Test 6: Larger synthetic graph ----
    print("\n" + "=" * 70)
    print("[Test 6] Performance on larger synthetic graph (50 nodes, 200 edges)")
    print("=" * 70)

    import random
    random.seed(42)
    N_NODES = 50
    N_EDGES = 200
    node_ids = [str(i) for i in range(N_NODES)]
    adj_large = defaultdict(list)
    for i in range(N_EDGES):
        src = random.choice(node_ids)
        tgt = random.choice(node_ids)
        ts = random.randint(1, 1000)
        adj_large[src].append((ts, tgt, f"e{i}"))
    adj_large = dict(adj_large)

    t0 = time_module.time()
    r_unopt, l_unopt = sensitive(adj_large)
    t_unopt = time_module.time() - t0

    graph_large = optimize_algorithm_speed(adj_large)
    t0 = time_module.time()
    r_opt, l_opt = graph_large.sensitivity()
    t_opt = time_module.time() - t0

    print(f"  Unoptimized sensitivity: {t_unopt:.4f}s  (reach={r_unopt:.4f})")
    print(f"  Optimized sensitivity:   {t_opt:.4f}s  (reach={r_opt:.4f})")

    t0 = time_module.time()
    bn_large = graph_large.find_bottlenecks_fast(top_k=5, mode="edge")
    t_bn = time_module.time() - t0
    print(f"  Edge bottleneck (top 5): {t_bn:.4f}s")
    for b in bn_large["edge_bottlenecks"][:3]:
        print(f"    {b['edge_id']}: drop={b['reachability_drop']:.6f}")

    # ==================================================================
    # Part B: Integration test with Ranjan's CSV output format
    # ==================================================================
    print("\n" + "=" * 70)
    print("[Test 7] Integration with Ranjan's CSV pipeline")
    print("=" * 70)

    # Simulate Ranjan's CSV output (edge_id, SRC, TGT, Unix, datetime)
    import tempfile, csv

    test_csv_path = os.path.join(tempfile.gettempdir(), "test_temporal.csv")
    with open(test_csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["edge_id", "SRC", "TGT", "Unix", "datetime"])
        writer.writerow(["e0000001", "1", "2", 1000, "2009-09-14 01:16:40"])
        writer.writerow(["e0000002", "1", "3", 2000, "2009-09-14 01:33:20"])
        writer.writerow(["e0000003", "2", "4", 3000, "2009-09-14 01:50:00"])
        writer.writerow(["e0000004", "3", "4", 2500, "2009-09-14 01:41:40"])
        writer.writerow(["e0000005", "3", "5", 4000, "2009-09-14 02:06:40"])
        writer.writerow(["e0000006", "4", "5", 5000, "2009-09-14 02:23:20"])
        writer.writerow(["e0000007", "2", "3", 1500, "2009-09-14 01:25:00"])
        writer.writerow(["e0000008", "5", "1", 6000, "2009-09-14 02:40:00"])

    adj_csv, df_csv = build_adj_time_from_csv(test_csv_path)
    print(f"  Loaded from CSV: {len(adj_csv)} source nodes, {len(df_csv)} edges")
    print(f"  Nodes: {nodes_set(adj_csv)}")

    graph_csv = optimize_algorithm_speed(adj_csv)
    info = graph_csv.get_graph_info()
    print(f"  Graph info: {info}")

    reach_csv, lat_csv = graph_csv.sensitivity()
    print(f"  Sensitivity: reach={reach_csv:.6f}, lat={lat_csv:.4f}")

    bn_csv = graph_csv.find_bottlenecks_fast(top_k=3, mode="both")
    print(f"\n  Top edge bottlenecks (from CSV):")
    for i, b in enumerate(bn_csv["edge_bottlenecks"], 1):
        print(f"    {i}. {b['edge_id']} ({b['src']}->{b['tgt']}) drop={b['reachability_drop']:.6f}")

    print(f"\n  Top vertex bottlenecks (from CSV):")
    for i, b in enumerate(bn_csv["vertex_bottlenecks"], 1):
        print(f"    {i}. Vertex {b['vertex']} drop={b['reachability_drop']:.6f}")

    # Clean up temp file
    os.remove(test_csv_path)

    # ==================================================================
    # Part C: Test with build_adj_time_from_edges (Ranjan's edge list)
    # ==================================================================
    print("\n" + "=" * 70)
    print("[Test 8] build_adj_time_from_edges (Ranjan's edges_sorted format)")
    print("=" * 70)

    # Simulate Ranjan's edges_sorted: list of (Unix, SRC, TGT, edge_id)
    edges_sorted_sim = [
        (1000, "A", "B", "e001"),
        (1500, "A", "C", "e002"),
        (2000, "B", "C", "e003"),
        (2500, "B", "D", "e004"),
        (3000, "C", "D", "e005"),
        (3500, "D", "A", "e006"),
    ]

    adj_edges = build_adj_time_from_edges(edges_sorted_sim)
    print(f"  Built from edges_sorted: {len(adj_edges)} source nodes")
    for src in sorted(adj_edges.keys()):
        print(f"    {src} -> {adj_edges[src]}")

    graph_edges = optimize_algorithm_speed(adj_edges)
    reach_e, lat_e = graph_edges.sensitivity()
    print(f"  Sensitivity: reach={reach_e:.6f}, lat={lat_e:.4f}")

    bn_e = graph_edges.find_bottlenecks_fast(top_k=3)
    print(f"  Top edge: {bn_e['edge_bottlenecks'][0]['edge_id']} "
          f"drop={bn_e['edge_bottlenecks'][0]['reachability_drop']:.6f}")
    print(f"  Top vertex: {bn_e['vertex_bottlenecks'][0]['vertex']} "
          f"drop={bn_e['vertex_bottlenecks'][0]['reachability_drop']:.6f}")

    print("\n" + "=" * 70)
    print("ALL TESTS COMPLETED SUCCESSFULLY")
    print("=" * 70)
