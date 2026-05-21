from collections import deque
import copy

###########################################################################
#Collect all nodes from the adjacency matrix
#Extra handling is needed because nodes with no outgoing edges may not appear in the adjacency matrix
def nodes_set(adj_mat):
    all_nodes = set(adj_mat.keys())
    for edges in adj_mat.values():
        for _, tar, _ in edges:
            all_nodes.add(tar)

    return all_nodes


###########################################################################
#BFS from a single SRC node to a single TGT node
def BFS_Single(adj_mat,SRC,TGT):
    if not adj_mat:
        print("Error:Please input the adj matrix to process")
        print("-"*20)
        return None,None

    all_nodes = nodes_set(adj_mat)

    if SRC not in all_nodes or TGT not in all_nodes:
        print("Point don't Exist!!!")
        return None,None

    prior_queue = deque()
    visit_points = set()
    #Add a dummy node so that we can check if a node can reach itself
    prior_queue.append((SRC,-1))
    parents = {}

    #Keep running while the priority queue is not empty
    while prior_queue:

        point,time = prior_queue.popleft()

        #If the current node has not been visited, add it to the visit_points set
        if (point,time) not in visit_points:
            visit_points.add((point, time))

        #If the target node is reached, output the path and arrival time
        if point == TGT and time != -1:
            path = []
            path.append((point,time))
            current = (point,time)
            while current in parents:
                prev_points,prev_time = parents[current]
                path.append((prev_points,prev_time))
                current = (prev_points,prev_time)
            path.pop()
            path.reverse()
            return time,path

        #Traverse the adjacency list of the current node and add its neighbors to the priority queue
        if point in adj_mat.keys():#Check if the current node has no outgoing edges
            for time_stamp,tar,_ in adj_mat[point]:
                if (tar,time_stamp) not in visit_points and time_stamp >= time:
                    prior_queue.append((tar, time_stamp))
                    parents[(tar,time_stamp)] = (point,time)

    #If no path is found, return None
    return None,None


###########################################################################
#BFS from a single SRC node to all other nodes (including itself)
def Arrive_time_and_Latency(adj_mat,SRC):
    if not adj_mat:
        print("Error:Please input the adj matrix to process")
        print("-"*20)
        return None

    all_nodes = nodes_set(adj_mat)

    if SRC not in all_nodes:
        print("Error:The source node not doesn't exist!!!")
        print("-"*20)
        return None

    prior_queue = deque()
    visit_points = set()
    start_time = 0
    if adj_mat[SRC]:#Check if this vertex still has outgoing edges (to see if SRC still has out-degree after node deletions)
        start_time = adj_mat[SRC][0][0]
    prior_queue.append((SRC,-1))

    src2tgts = {SRC:[float('inf'),float('inf')]}

    while prior_queue:

        point,time = prior_queue.popleft()

        if (point,time) not in visit_points:
            visit_points.add((point,time))

        if point in adj_mat.keys():#Check if the original point exists in the adjacency matrix (to see if it had outgoing edges before any deletions)
            for time_stamp,tar,_ in adj_mat[point]:
                if (tar,time_stamp) not in visit_points and time_stamp >= time:
                    prior_queue.append((tar, time_stamp))

                    if tar not in src2tgts or time_stamp < src2tgts[tar][0]:
                        src2tgts[tar] = [time_stamp,time_stamp-start_time]

    if not src2tgts:
        return {}

    if src2tgts[SRC][0] == float('inf'):
        src2tgts.pop(SRC)
    return src2tgts


###########################################################################
def sensitive(adj_org,adj_modify = None,del_num = 0):
    if adj_modify == None:
        adj_modify = adj_org

    #Total number of paths
    num_reach_path = 0
    #Total latency
    total_latency = 0

    #Count the number of nodes in the graph
    all_nodes = nodes_set(adj_org)

    num_node = len(all_nodes) - del_num

    #Reduce: accumulate total reachable paths and total latency from all source nodes
    for SRC in adj_org.keys():
        src2tgts = Arrive_time_and_Latency(adj_modify,SRC)
        if not src2tgts:
            continue
        num_reach_path += len(src2tgts)
        for v in src2tgts.keys():
            total_latency += src2tgts[v][1]

    #Debug output
    print("num_reach_path:",num_reach_path)
    print("num_node:",num_node)
    print("total_latency:",total_latency)
    print("-"*20)

    global_reachable = num_reach_path / (num_node**2)
    avg_latency = total_latency / num_reach_path
    return global_reachable,avg_latency


###########################################################################
def modify(adj_mat,SRC=None,TGT=None,Vertexes=None,Edges=None):
    if not adj_mat:
        print("Error:Please input the adj matrix to process")
        print("-"*20)
        return None

    all_nodes = nodes_set(adj_mat)

    if SRC not in all_nodes or TGT not in all_nodes :
        print("Error:The source or target node doesn't exist!!!")
        print("-"*20)
        return None

    #If input is a string, split it by spaces
    if isinstance(Vertexes,str):
        Vertexes = Vertexes.split()
    elif Vertexes is None:
        Vertexes = []

    if isinstance(Edges,str):
        Edges = Edges.split()
    elif Edges is None:
        Edges = []

    #Arrival time and path before deleting a node or edge
    init_time,init_path = BFS_Single(adj_mat,SRC,TGT)
    #Global reachability and average latency before deleting a node or edge
    init_reachable_rate,init_avg_latency = sensitive(adj_mat)

    adj_modify = copy.deepcopy(adj_mat)

    if Vertexes:
        for v in Vertexes:
            if v not in all_nodes:
                print(f"Error:The vertex {v} to be deleted doesn't exist!!!")
                print("-"*20)
                return None

    #Delete Vertexes
    for v in Vertexes:
        if v in adj_modify.keys():
            adj_modify.pop(v)
        #Delete all edges pointing to the node
        for key in adj_modify.keys():
            for i in range(len(adj_modify[key])-1,-1,-1):
                if adj_modify[key][i][1] == v:
                    adj_modify[key].pop(i)

    #Delete edges
    if Edges:
        for e in Edges:
            found = False
            for key in adj_modify.keys():
                for i in range(len(adj_modify[key])-1,-1,-1):
                    if adj_modify[key][i][2] == e:
                        adj_modify[key].pop(i)
                        found = True
            if not found:
                print(f"Error: The edge {e} to be deleted doesn't exist!!!")
                print("-" * 20)
                return None


    #Arrival time and path after deleting a node or edge
    after_time, after_path = BFS_Single(adj_modify, SRC, TGT)
    #Global reachability and average latency after deleting a node or edge
    after_reachable_rate,after_avg_latency = sensitive(adj_mat,adj_modify,len(Vertexes))

    return [(init_time, init_path),(after_time, after_path),(init_reachable_rate, init_avg_latency),(after_reachable_rate, after_avg_latency)]









