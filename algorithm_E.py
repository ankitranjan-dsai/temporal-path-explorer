# Credit: E (bottlenecks, TemporalGraphOptimized, etc.); A (truncate __main__, dedupe imports from D/data_adj).
# Integrated from: teammate_deliverables/E/e_teammate.py → algorithm_E.py
# Role: Menger-style bottleneck heuristics on temporal graphs; uses adj from algorithm_D and data_adj.

from collections import deque
import copy

from algorithm_D import Arrive_time_and_Latency, nodes_set, sensitive
from data_adj import build_adj_time_from_edges


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


def find_menger_bottlenecks(adj_mat, top_k=5, mode="both", return_full_ranked: bool = False):
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
    return_full_ranked : bool, default False
        If True, also include ``edge_bottlenecks_full`` / ``vertex_bottlenecks_full``
        with the full sorted lists (for CSV export). Can be large for big graphs.

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

    # Baseline metrics (quiet: ``algorithm_D.sensitive`` can print debug lines)
    base_reach, base_lat = sensitive(adj_mat, verbose=False)

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
            new_reach, new_lat = sensitive(adj_mat, adj_mod, 0, verbose=False)
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
        if return_full_ranked:
            results["edge_bottlenecks_full"] = list(edge_impacts)

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
            new_reach, new_lat = sensitive(adj_mat, adj_mod, 1, verbose=False)
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
        if return_full_ranked:
            results["vertex_bottlenecks_full"] = list(vertex_impacts)

    return results


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
    >>> # adj from data_adj.dataframe_to_adj(cleaned DataFrame)
    >>> graph = optimize_algorithm_speed(adj)
    >>> t, path = graph.bfs_single('1', '6')
    >>> reach, lat = graph.sensitivity()
    >>> bottlenecks = graph.find_bottlenecks_fast(top_k=3)
    """
    return TemporalGraphOptimized(adj_mat)


__all__ = [
    "Arrive_time_and_Latency",
    "TemporalGraphOptimized",
    "build_adj_time_from_edges",
    "find_menger_bottlenecks",
    "nodes_set",
    "optimize_algorithm_speed",
    "sensitive",
]
