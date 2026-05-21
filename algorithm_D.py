# Credit: D (arrival/latency, sensitivity, modify); A (verbose flag, typing, Streamlit alignment).
# Integrated from: teammate_deliverables/D/Modify_and_Sensitive_clean_update.py → algorithm_D.py
# Role: Metrics on adj shared with B/data_adj/C/E; What-if vertex/edge removal.

from __future__ import annotations

import copy
from collections import deque
from typing import Any, Dict, List, Optional, Tuple, Union

Adj = Dict[str, List[Tuple[int, str, str]]]

ModifyResult = List[Any]


def nodes_set(adj_mat: Adj) -> set:
    """All nodes: keys plus any target appearing only as TGT."""
    all_nodes = set(adj_mat.keys())
    for edges in adj_mat.values():
        for _, tar, _ in edges:
            all_nodes.add(tar)
    return all_nodes


def Arrive_time_and_Latency(adj_mat: Adj, SRC: str, verbose: bool = True) -> Optional[Dict[str, List[float]]]:
    if not adj_mat:
        if verbose:
            print("Error:Please input the adj matrix to process")
            print("-" * 20)
        return None

    all_nodes = nodes_set(adj_mat)

    if SRC not in all_nodes:
        if verbose:
            print("Error:The source node not doesn't exist!!!")
            print("-" * 20)
        return None

    prior_queue = deque()
    visit_points = set()
    start_time = 0
    if SRC in adj_mat and adj_mat[SRC]:
        start_time = adj_mat[SRC][0][0]
    prior_queue.append((SRC, -1))

    src2tgts: Dict[str, List[float]] = {SRC: [float("inf"), float("inf")]}

    while prior_queue:
        point, time = prior_queue.popleft()

        if (point, time) not in visit_points:
            visit_points.add((point, time))

        if point in adj_mat:
            for time_stamp, tar, _ in adj_mat[point]:
                if (tar, time_stamp) not in visit_points and time_stamp >= time:
                    prior_queue.append((tar, time_stamp))

                    if tar not in src2tgts or time_stamp < src2tgts[tar][0]:
                        src2tgts[tar] = [float(time_stamp), float(time_stamp - start_time)]

    if not src2tgts:
        return {}

    if src2tgts[SRC][0] == float("inf"):
        src2tgts.pop(SRC)
    return src2tgts


def sensitive(
    adj_org: Adj,
    adj_modify: Optional[Adj] = None,
    del_num: int = 0,
    verbose: bool = True,
) -> Tuple[float, float]:
    if adj_modify is None:
        adj_modify = adj_org

    num_reach_path = 0
    total_latency = 0.0

    all_nodes = nodes_set(adj_org)
    num_node = len(all_nodes) - del_num

    for SRC in adj_org.keys():
        src2tgts = Arrive_time_and_Latency(adj_modify, SRC, verbose=verbose)
        if not src2tgts:
            continue
        num_reach_path += len(src2tgts)
        for v in src2tgts.keys():
            total_latency += src2tgts[v][1]

    if verbose:
        print("num_reach_path:", num_reach_path)
        print("num_node:", num_node)
        print("total_latency:", total_latency)
        print("-" * 20)

    if num_reach_path == 0 or num_node == 0:
        return 0.0, 0.0

    global_reachable = num_reach_path / (num_node**2)
    avg_latency = total_latency / num_reach_path
    return global_reachable, avg_latency


def modify(
    adj_mat: Adj,
    Vertexes: Union[None, List[str], str] = None,
    Edges: Union[None, List[str], str] = None,
    verbose: bool = True,
) -> Optional[ModifyResult]:
    if not adj_mat:
        if verbose:
            print("Error:Please input the adj matrix to process")
            print("-" * 20)
        return None

    all_nodes = nodes_set(adj_mat)

    if isinstance(Vertexes, str):
        Vertexes = Vertexes.split()
    elif Vertexes is None:
        Vertexes = []

    if isinstance(Edges, str):
        Edges = Edges.split()
    elif Edges is None:
        Edges = []

    init_reachable_rate, init_avg_latency = sensitive(adj_mat, verbose=verbose)

    adj_modify = copy.deepcopy(adj_mat)

    if Vertexes:
        for v in Vertexes:
            if v not in all_nodes:
                if verbose:
                    print(f"Error:The vertex {v} to be deleted doesn't exist!!!")
                    print("-" * 20)
                return None

    for v in Vertexes:
        if v in adj_modify:
            adj_modify.pop(v)
        for key in adj_modify.keys():
            for i in range(len(adj_modify[key]) - 1, -1, -1):
                if adj_modify[key][i][1] == v:
                    adj_modify[key].pop(i)

    if Edges:
        for e in Edges:
            found = False
            for key in adj_modify.keys():
                for i in range(len(adj_modify[key]) - 1, -1, -1):
                    if adj_modify[key][i][2] == e:
                        adj_modify[key].pop(i)
                        found = True
            if not found:
                if verbose:
                    print(f"Error: The edge {e} to be deleted doesn't exist!!!")
                    print("-" * 20)
                return None

    after_reachable_rate, after_avg_latency = sensitive(
        adj_org=adj_mat, adj_modify=adj_modify, del_num=len(Vertexes), verbose=verbose
    )

    return [
        (init_reachable_rate, init_avg_latency),
        (after_reachable_rate, after_avg_latency),
        adj_modify,
    ]


__all__ = [
    "Adj",
    "Arrive_time_and_Latency",
    "ModifyResult",
    "modify",
    "nodes_set",
    "sensitive",
]
