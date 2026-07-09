"""A node-weighted Steiner-tree heuristic (shortest-path heuristic + pruning).

Gives a good *feasible* solution fast: a connected set of Sets containing every
terminal, whose grey count is an upper bound on the optimum. Used both as a
standalone answer and to warm-start the exact SCIP solve.

  operations = 106 + (grey Sets used).
"""
import sys
import heapq
import random
from collections import deque

import os
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)                                  # sibling exact-solver modules
sys.path.insert(0, os.path.join(_HERE, os.pardir, "src"))  # word_set, utils
from exact_solver import build_graph  # noqa: E402


def node_weight(v, is_term):
    return 0 if is_term[v] else 1


def grow_tree(n, is_term, adj, terms, start, weight=None):
    """Shortest-path heuristic. Grow a tree from `start`, each step attaching the
    nearest not-yet-connected terminal by a min-cost path. Returns the set of
    nodes in the tree. `weight[v]` is the Dijkstra cost of entering v (defaults
    to 0 for terminals, 1 for greys); pass LP-derived weights to bias routing."""
    if weight is None:
        weight = [node_weight(v, is_term) for v in range(n)]
    in_tree = bytearray(n)
    in_tree[start] = 1
    need = set(terms)
    need.discard(start)

    while need:
        # multi-source Dijkstra from the whole tree; cost = grey nodes entered
        dist = [None] * n
        prev = [-1] * n
        pq = []
        for v in range(n):
            if in_tree[v]:
                dist[v] = 0
                heapq.heappush(pq, (0, v))
        target = -1
        while pq:
            d, v = heapq.heappop(pq)
            if d > dist[v]:
                continue
            if v in need:
                target = v
                break
            for w in adj[v]:
                nd = d + weight[w]
                if dist[w] is None or nd < dist[w]:
                    dist[w] = nd
                    prev[w] = v
                    heapq.heappush(pq, (nd, w))
        if target == -1:
            raise RuntimeError("graph disconnected: cannot reach a terminal")
        # add the path back to the tree
        v = target
        while v != -1 and not in_tree[v]:
            in_tree[v] = 1
            v = prev[v]
        need.discard(target)
        need = {t for t in need if not in_tree[t]}

    return in_tree


def prune(n, is_term, adj, in_tree):
    """Remove grey leaves (degree <=1 within the tree, non-terminal) until none
    remain -- they can never help connect terminals."""
    deg = [0] * n
    nodes = [v for v in range(n) if in_tree[v]]
    for v in nodes:
        deg[v] = sum(1 for w in adj[v] if in_tree[w])
    q = deque(v for v in nodes if not is_term[v] and deg[v] <= 1)
    while q:
        v = q.popleft()
        if not in_tree[v] or is_term[v]:
            continue
        if deg[v] <= 1:
            in_tree[v] = 0
            for w in adj[v]:
                if in_tree[w]:
                    deg[w] -= 1
                    if not is_term[w] and deg[w] <= 1:
                        q.append(w)
    return in_tree


def greys_of(n, is_term, in_tree):
    return [v for v in range(n) if in_tree[v] and not is_term[v]]


def _voronoi(n, is_term, adj, terms, weight):
    "Multi-source Dijkstra from all terminals: base terminal, distance, predecessor."
    dist = [None] * n
    base = [-1] * n
    prev = [-1] * n
    pq = []
    for t in terms:
        dist[t] = 0
        base[t] = t
        heapq.heappush(pq, (0, t))
    while pq:
        d, v = heapq.heappop(pq)
        if d > dist[v]:
            continue
        for w in adj[v]:
            nd = d + weight[w]
            if dist[w] is None or nd < dist[w]:
                dist[w] = nd
                base[w] = base[v]
                prev[w] = v
                heapq.heappush(pq, (nd, w))
    return dist, base, prev


def kmb(n, is_term, adj, terms, weight=None):
    """Mehlhorn's distance-network Steiner heuristic (node-weighted). Returns the
    tree node set."""
    if weight is None:
        weight = [node_weight(v, is_term) for v in range(n)]
    dist, base, prev = _voronoi(n, is_term, adj, terms, weight)

    # best boundary edge between each pair of Voronoi regions (terminals)
    best = {}          # (ta,tb) -> (cost, u, w)
    for u in range(n):
        if dist[u] is None:
            continue
        for w in adj[u]:
            if dist[w] is None or base[u] == base[w]:
                continue
            a, b = base[u], base[w]
            key = (a, b) if a < b else (b, a)
            cost = dist[u] + dist[w]
            cur = best.get(key)
            if cur is None or cost < cur[0]:
                best[key] = (cost, u, w)

    # Prim MST over the terminal distance graph
    tindex = {t: i for i, t in enumerate(terms)}
    adjT = {t: [] for t in terms}
    for (a, b), (cost, u, w) in best.items():
        adjT[a].append((cost, b, u, w))
        adjT[b].append((cost, a, w, u))
    in_mst = {t: False for t in terms}
    start = terms[0]
    in_mst[start] = True
    pq = [(c, start, tb, uu, ww) for (c, tb, uu, ww) in adjT[start]]
    heapq.heapify(pq)
    mst_edges = []
    count = 1
    while pq and count < len(terms):
        c, ta, tb, u, w = heapq.heappop(pq)
        if in_mst[tb]:
            continue
        in_mst[tb] = True
        count += 1
        mst_edges.append((u, w))
        for (cc, tc, uu, ww) in adjT[tb]:
            if not in_mst[tc]:
                heapq.heappush(pq, (cc, tb, tc, uu, ww))

    # expand each MST boundary edge to its actual node path
    in_tree = bytearray(n)
    for t in terms:
        in_tree[t] = 1
    for (u, w) in mst_edges:
        for endp in (u, w):
            v = endp
            while v != -1:
                in_tree[v] = 1
                v = prev[v]
    return in_tree


def eliminate(n, is_term, adj, terms, in_tree):
    """Local search: try removing each grey and reconnecting cheaply; keep the
    move if it does not increase the grey count. Repeats until stable."""
    import heapq as _hq
    changed = True
    while changed:
        changed = False
        greys = [v for v in range(n) if in_tree[v] and not is_term[v]]
        for g in greys:
            if not in_tree[g]:
                continue
            in_tree[g] = 0
            # is the tree still connected across all terminals?
            if _connected(n, is_term, adj, terms, in_tree):
                changed = True          # g was redundant
            else:
                in_tree[g] = 1          # keep it
        prune(n, is_term, adj, in_tree)
    return in_tree


def _connected(n, is_term, adj, terms, in_tree):
    root = terms[0]
    seen = bytearray(n)
    seen[root] = 1
    q = deque([root])
    while q:
        v = q.popleft()
        for w in adj[v]:
            if in_tree[w] and not seen[w]:
                seen[w] = 1
                q.append(w)
    return all(seen[t] for t in terms)


def best_heuristic(name="graph_optimal_2283", tries=40, seed=0, verbose=True,
                   do_eliminate=True):
    ids, idx, n, is_term, adj, edges, g = build_graph(name)
    terms = [i for i in range(n) if is_term[i]]
    rng = random.Random(seed)

    best_tree = None
    best_greys = 10 ** 9

    def consider(tree, tag):
        nonlocal best_tree, best_greys
        prune(n, is_term, adj, tree)
        if do_eliminate:
            eliminate(n, is_term, adj, terms, tree)
        gc = len(greys_of(n, is_term, tree))
        if gc < best_greys:
            best_greys = gc
            best_tree = bytearray(tree)
            if verbose:
                print(f"  {tag}: {gc} greys -> {106 + gc} operations")
        return gc

    consider(kmb(n, is_term, adj, terms), "KMB")

    starts = list(terms)
    rng.shuffle(starts)
    for i in range(min(tries, len(starts))):
        consider(grow_tree(n, is_term, adj, terms, starts[i]), f"SPH<{ids[starts[i]]}>")

    if verbose:
        print(f"\nheuristic best: {best_greys} greys -> operations = {106 + best_greys}")
    chosen = [v for v in range(n) if best_tree[v]]
    return [ids[v] for v in chosen], best_greys, 106 + best_greys, best_tree


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "graph_optimal_2283"
    tries = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    best_heuristic(name, tries)
