"""Exact node-weighted Steiner tree solver for the reduced word graph.

The reduced instance (graph_optimal_2283.pickle) is a node-weighted Steiner
tree: 76 PINK Sets are terminals (weight 0, forced in), 2207 GREY Sets are
optional Steiner nodes (weight 1 each -- one non-picture word apiece). We want
the minimum number of GREY nodes that connect all 76 terminals into one
component.  total words = 107 + #greys,  operations = words - 1.

Formulation: directed (bidirected) cut on the node-split graph -- the strong
Steiner relaxation.
  Split each node v into v_in (2v) and v_out (2v+1) with an internal arc
  v_in -> v_out whose capacity/cost is the node weight. Each undirected edge
  {u,w} becomes two link arcs u_out -> w_in and w_out -> u_in (cost 0).
  Root at a terminal r (source r_out). Require, for every other terminal t, a
  directed r_out -> t_in cut of value >= 1:
        sum_{a in delta^+(U)} x_a >= 1   for all U with r_out in U, t_in not in U.
  Objective: min sum over grey node-arcs of x  (== #greys used).

Cuts are separated by max-flow (Dinic). Fractional rounds tighten the LP bound;
then node-arcs are made binary and integer solutions are checked for real
connectivity, adding node-separator cuts until the tree is connected.
"""
import sys
import time
import pickle
from collections import deque

import highspy

import os
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)                                  # sibling exact-solver modules
sys.path.insert(0, os.path.join(_HERE, os.pardir, "src"))  # word_set, utils
from word_set import Set, KEYWORDS  # noqa: E402,F401

INF = highspy.kHighsInf


def load(name):
    with open(name + ".pickle", "rb") as h:
        return pickle.load(h)


# ----------------------------------------------------------------- graph load
def build_graph(name="graph_optimal_2283"):
    g = load(name)
    ids = sorted(g.keys())
    idx = {sid: i for i, sid in enumerate(ids)}
    n = len(ids)
    is_term = [g[sid].isKey for sid in ids]
    adj = [set() for _ in range(n)]
    for sid, s in g.items():
        i = idx[sid]
        for l in s.links:
            if l in idx:
                j = idx[l]
                adj[i].add(j)
                adj[j].add(i)
    adj = [sorted(a) for a in adj]
    edges = [(u, w) for u in range(n) for w in adj[u] if u < w]
    return ids, idx, n, is_term, adj, edges, g


# ----------------------------------------------------------------- max-flow (Dinic)
class Dinic:
    """Directed max-flow on the split graph. Each LP/MIP variable maps to one
    forward arc; reverse (residual) arcs carry no variable. cap_base is the
    fresh residual graph for the current arc values; maxflow() copies it so
    per-terminal calls start clean."""

    def __init__(self, n, edges, node_var, link_var):
        self.N = 2 * n
        self.n = n
        self.graph = [[] for _ in range(self.N)]
        self.to = []
        self.frm = []
        self.evar = []            # forward arc -> LP var index, reverse arc -> -1
        self.cap_base = []
        self.node_edge = [0] * n  # forward-edge index of node v's internal arc
        for v in range(n):
            self.node_edge[v] = self._add(2 * v, 2 * v + 1, node_var[v])
        for k, (u, w) in enumerate(edges):
            a, b = link_var[k]
            self._add(2 * u + 1, 2 * w, a)      # u_out -> w_in
            self._add(2 * w + 1, 2 * u, b)      # w_out -> u_in
        self.cap = list(self.cap_base)

    def _add(self, a, b, var):
        e = len(self.to)
        self.graph[a].append(e); self.to.append(b); self.frm.append(a)
        self.evar.append(var);   self.cap_base.append(0.0)
        self.graph[b].append(e + 1); self.to.append(a); self.frm.append(b)
        self.evar.append(-1);    self.cap_base.append(0.0)
        return e

    def set_caps(self, xvals):
        "Load forward-arc capacities from the current solution vector xvals."
        cb = self.cap_base
        for e in range(0, len(self.to), 2):     # forward arcs are the even indices
            cb[e] = max(0.0, xvals[self.evar[e]])

    def _bfs(self, s, t):
        self.level = [-1] * self.N
        self.level[s] = 0
        q = deque([s])
        while q:
            v = q.popleft()
            for e in self.graph[v]:
                if self.cap[e] > 1e-12 and self.level[self.to[e]] < 0:
                    self.level[self.to[e]] = self.level[v] + 1
                    q.append(self.to[e])
        return self.level[t] >= 0

    def _dfs(self, v, t, f):
        if v == t:
            return f
        g = self.graph
        while self.it[v] < len(g[v]):
            e = g[v][self.it[v]]
            w = self.to[e]
            if self.cap[e] > 1e-12 and self.level[w] == self.level[v] + 1:
                d = self._dfs(w, t, f if f < self.cap[e] else self.cap[e])
                if d > 1e-12:
                    self.cap[e] -= d
                    self.cap[e ^ 1] += d
                    return d
            self.it[v] += 1
        return 0.0

    def maxflow(self, s, t, cutoff=1.0):
        self.cap = list(self.cap_base)
        flow = 0.0
        while flow < cutoff and self._bfs(s, t):
            self.it = [0] * self.N
            while True:
                f = self._dfs(s, t, INF)
                if f <= 1e-12:
                    break
                flow += f
                if flow >= cutoff:
                    break
        return flow

    def _reach_from(self, s):
        vis = bytearray(self.N)
        vis[s] = 1
        q = deque([s])
        while q:
            v = q.popleft()
            for e in self.graph[v]:
                if self.cap[e] > 1e-12 and not vis[self.to[e]]:
                    vis[self.to[e]] = 1
                    q.append(self.to[e])
        return vis

    def _reach_to(self, t):
        "Vertices that can reach t in the residual graph (reverse BFS)."
        vis = bytearray(self.N)
        vis[t] = 1
        q = deque([t])
        while q:
            v = q.popleft()
            for e in self.graph[v]:          # e: v -> to[e]; reverse e^1: to[e] -> v
                pred = self.to[e]
                if self.cap[e ^ 1] > 1e-12 and not vis[pred]:
                    vis[pred] = 1
                    q.append(pred)
        return vis

    def cut_vars(self, side_in):
        """Variables of every forward arc crossing from the source side to the
        sink side. side_in is the source-side bytearray; an arc (x->y) crosses
        when x is on the source side and y is not. ALL such arcs must be
        included (even ones currently at 0) or the cut is stronger than valid
        and can exclude the true optimum."""
        out = []
        frm, to, evar = self.frm, self.to, self.evar
        for e in range(0, len(to), 2):          # forward arcs are the even indices
            if side_in[frm[e]] and not side_in[to[e]]:
                out.append(evar[e])
        return out


# ----------------------------------------------------------------- solver
def solve(name="graph_optimal_2283", verbose=True, lp_time_budget=150.0):
    sys.setrecursionlimit(50000)   # Dinic DFS recurses along augmenting paths
    ids, idx, n, is_term, adj, edges, g = build_graph(name)
    terms = [i for i in range(n) if is_term[i]]
    root = terms[0]
    others = terms[1:]
    m = len(edges)
    print(f"{n} nodes, {len(terms)} terminals, {m} edges")

    # ---- variable layout: 0..n-1 node arcs, then 2 link arcs per edge
    node_var = list(range(n))
    link_var = [(n + 2 * k, n + 2 * k + 1) for k in range(m)]
    nvars = n + 2 * m
    dinic = Dinic(n, edges, node_var, link_var)

    # ---- HiGHS model (all arcs continuous for the LP phase)
    h = highspy.Highs()
    h.setOptionValue("output_flag", False)
    h.setOptionValue("threads", 0)
    for v in range(n):
        cost = 0.0 if is_term[v] else 1.0
        h.addCol(cost, 0.0, 1.0, 0, [], [])
    for _ in range(2 * m):
        h.addCol(0.0, 0.0, 1.0, 0, [], [])

    added = set()

    def add_cut(varlist):
        if not varlist:
            return False
        key = frozenset(varlist)
        if key in added:
            return False
        added.add(key)
        h.addRow(1.0, INF, len(varlist), list(varlist), [1.0] * len(varlist))
        return True

    src = 2 * root + 1

    def separate_fractional(x):
        dinic.set_caps(x)
        cuts = 0
        for t in others:
            if dinic.maxflow(src, 2 * t, cutoff=1.0) < 1.0 - 1e-6:
                s_side = dinic._reach_from(src)         # source-side min cut
                cuts += add_cut(dinic.cut_vars(s_side))
                t_side = dinic._reach_to(2 * t)         # back cut (sink side)
                comp = bytearray(1 - b for b in t_side)  # V \ W  (source side)
                cuts += add_cut(dinic.cut_vars(comp))
        return cuts

    def separate_integer(x):
        "Exact check on a rounded node selection: connect r to every terminal."
        sel = [x[v] > 0.5 or is_term[v] for v in range(n)]
        seen = [False] * n
        seen[root] = True
        q = deque([root])
        while q:
            v = q.popleft()
            for w in adj[v]:
                if sel[w] and not seen[w]:
                    seen[w] = True
                    q.append(w)
        cuts = 0
        for t in others:
            if not seen[t]:
                # separator = grey neighbours of the reached component
                R = [v for v in range(n) if seen[v]]
                border = set()
                for v in R:
                    for w in adj[v]:
                        if not seen[w] and not is_term[w]:
                            border.add(w)
                cuts += add_cut([node_var[v] for v in border])
                break  # one cut per round is enough; re-solve
        return cuts

    t0 = time.time()

    # ---- Phase A: fractional directed-cut generation (strong LP bound).
    # Stop when no cut is violated (true LP bound), or the bound tails off, or
    # the budget is hit -- Phase B keeps separating so an early stop is safe.
    rnd = 0
    prev = -1.0
    stall = 0
    while True:
        h.run()
        x = h.getSolution().col_value
        lb = h.getObjectiveValue()
        c = separate_fractional(x)
        rnd += 1
        if verbose and (rnd % 10 == 0 or c == 0):
            print(f"  [LP {rnd}] bound={lb:.3f} greys  cuts+={c} "
                  f"total={len(added)}  ({time.time()-t0:.1f}s)")
        if c == 0:
            print(f"  [LP] converged at bound {lb:.4f}")
            break
        stall = stall + 1 if lb <= prev + 1e-4 else 0
        prev = lb
        if stall >= 20:
            print(f"  [LP] bound tailing off at {lb:.3f}; handing to MIP")
            break
        if time.time() - t0 > lp_time_budget:
            print(f"  [LP] time budget hit at bound {lb:.3f}")
            break
    print(f"LP root bound: {h.getObjectiveValue():.4f} greys "
          f"-> operations >= {106 + h.getObjectiveValue():.4f}")

    # ---- Phase B: node arcs integer. Keep separating directed cuts on the
    # full (node+link) arc solution: once none is violated, a unit flow reaches
    # every terminal through selected nodes only, so the node set is provably
    # connected and the solution is optimal. Integer BFS is the final check.
    for v in range(n):
        h.changeColIntegrality(v, highspy.HighsVarType.kInteger)
    best = None
    mrnd = 0
    while True:
        h.run()
        x = h.getSolution().col_value
        obj = h.getObjectiveValue()
        c = separate_fractional(x)          # strong directed cuts
        ic = separate_integer(x)            # exact connectivity of node set
        mrnd += 1
        if verbose and (mrnd % 10 == 0 or (c == 0 and ic == 0)):
            print(f"  [MIP {mrnd}] greys={round(obj)}  cuts+={c}  intcuts+={ic}"
                  f"  ({time.time()-t0:.1f}s)")
        if c == 0 and ic == 0:
            best = x
            break

    chosen = [i for i in range(n) if best[i] > 0.5]
    greys = [i for i in chosen if not is_term[i]]
    words = 107 + len(greys)
    print(f"\nOPTIMAL: {len(greys)} grey Steiner nodes")
    print(f"total words = {words}  ->  operations = {words - 1}")
    return [ids[i] for i in chosen], len(greys), words - 1


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "graph_optimal_2283"
    chosen_ids, ngrey, ops = solve(name)
    with open("exact_solution_ids.pickle", "wb") as fh:
        pickle.dump(chosen_ids, fh)
    print(f"saved {len(chosen_ids)} set ids to exact_solution_ids.pickle")
