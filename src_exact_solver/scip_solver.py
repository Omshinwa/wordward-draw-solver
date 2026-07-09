"""Exact solve of the reduced word graph with SCIP branch-and-cut.

Same node-weighted Steiner instance and directed (bidirected) cut formulation
as exact_solver.py, but instead of re-solving a HiGHS MIP once per lazy cut,
SCIP does a single branch-and-cut tree and we feed it cuts through a constraint
handler:

  * conssepalp  -- fractional rounds: max-flow directed-cut separation on the
                   LP point, adding violated directed cuts (strong bound).
  * consenfolp/ops, conscheck -- correctness: an integer node selection is
                   feasible iff it connects the root to every terminal; if not,
                   add the node-separator cut around the root's component.

Variables: one per split-graph arc.  node arcs 0..n-1 (grey = binary cost 1,
terminal = fixed to 1, cost 0); link arcs continuous in [0,1], cost 0.
operations = 106 + (#grey node arcs = 1).
"""
import sys
import time
import pickle
from collections import deque

from pyscipopt import Model, Conshdlr, SCIP_RESULT, quicksum

import os
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)                                  # sibling exact-solver modules
sys.path.insert(0, os.path.join(_HERE, os.pardir, "src"))  # word_set, utils
from exact_solver import build_graph, Dinic  # noqa: E402
from heuristic import grow_tree, prune, best_heuristic  # noqa: E402


class SteinerConshdlr(Conshdlr):
    """Directed-cut separation + integer connectivity enforcement."""

    def setup(self, model, V, dinic, n, is_term, adj, root, others, node_var):
        self.M = model
        self.V = V                 # nvars SCIP variable objects, indexed by var id
        self.d = dinic
        self.n = n
        self.is_term = is_term
        self.adj = adj
        self.root = root
        self.others = others
        self.node_var = node_var
        self.src = 2 * root + 1
        self.added = set()
        self.ncuts = 0
        self.frac_calls = 0

    # ---- helpers
    def _xvals(self, sol):
        gv = self.M.getSolVal
        V = self.V
        return [gv(sol, V[i]) for i in range(len(V))]

    def _add(self, varidx):
        if not varidx:
            return False
        key = frozenset(varidx)
        if key in self.added:
            return False
        self.added.add(key)
        self.M.addCons(quicksum(self.V[j] for j in varidx) >= 1)
        self.ncuts += 1
        return True

    def _separate_fractional(self, sol):
        d = self.d
        d.set_caps(self._xvals(sol))
        cuts = 0
        for t in self.others:
            if d.maxflow(self.src, 2 * t, cutoff=1.0) < 1.0 - 1e-6:
                cuts += self._add(d.cut_vars(d._reach_from(self.src)))
                back = d._reach_to(2 * t)
                cuts += self._add(d.cut_vars(bytearray(1 - b for b in back)))
        return cuts

    def _connectivity_cut(self, sol):
        "None if the selected node set connects root to all terminals, else a cut."
        gv = self.M.getSolVal
        V = self.V
        sel = [self.is_term[v] or gv(sol, V[v]) > 0.5 for v in range(self.n)]
        seen = bytearray(self.n)
        seen[self.root] = 1
        q = deque([self.root])
        while q:
            v = q.popleft()
            for w in self.adj[v]:
                if sel[w] and not seen[w]:
                    seen[w] = 1
                    q.append(w)
        if all(seen[t] for t in self.others):
            return None
        border = set()
        for v in range(self.n):
            if seen[v]:
                for w in self.adj[v]:
                    if not seen[w] and not self.is_term[w]:
                        border.add(w)
        return [self.node_var[v] for v in border]

    # ---- SCIP callbacks
    def conssepalp(self, constraints, nusefulconss):
        self.frac_calls += 1
        # separate fractional directed cuts mostly near the top of the tree
        if self.M.getDepth() > 0 and self.frac_calls % 4 != 0:
            return {"result": SCIP_RESULT.DIDNOTRUN}
        return {"result": SCIP_RESULT.CONSADDED if self._separate_fractional(None)
                else SCIP_RESULT.DIDNOTFIND}

    def consenfolp(self, constraints, nusefulconss, solinfeasible):
        cut = self._connectivity_cut(None)
        if cut is not None:
            self._add(cut)
            return {"result": SCIP_RESULT.CONSADDED}
        # node set connects; also make sure directed cuts hold (bound integrity)
        if self._separate_fractional(None):
            return {"result": SCIP_RESULT.CONSADDED}
        return {"result": SCIP_RESULT.FEASIBLE}

    def consenfops(self, constraints, nusefulconss, solinfeasible, objinfeasible):
        cut = self._connectivity_cut(None)
        if cut is not None:
            self._add(cut)
            return {"result": SCIP_RESULT.CONSADDED}
        return {"result": SCIP_RESULT.FEASIBLE}

    def conscheck(self, constraints, solution, checkintegrality, checklprows,
                  printreason, completely):
        if self._connectivity_cut(solution) is not None:
            return {"result": SCIP_RESULT.INFEASIBLE}
        return {"result": SCIP_RESULT.FEASIBLE}

    def conslock(self, constraint, locktype, nlockspos, nlocksneg):
        pass


def _bfs_tree(n, adj, in_tree, root):
    "Spanning tree of the selected nodes rooted at root: {child: parent}."
    parent = {}
    seen = bytearray(n)
    seen[root] = 1
    q = deque([root])
    while q:
        v = q.popleft()
        for w in adj[v]:
            if in_tree[w] and not seen[w]:
                seen[w] = 1
                parent[w] = v
                q.append(w)
    return parent


def solve_core(n, is_term, adj, edges, warm_tree=None, time_limit=0,
               root_sep_full=True, verbose=True):
    """Exact node-weighted Steiner solve on the given graph via SCIP branch-and-cut.
    Returns (chosen_indices, n_greys, dual_bound, status). `warm_tree` is an
    optional bytearray of selected nodes (a feasible tree) used as a warm start."""
    sys.setrecursionlimit(50000)
    terms = [i for i in range(n) if is_term[i]]
    root = terms[0]
    others = terms[1:]
    m = len(edges)

    node_var = list(range(n))
    link_var = [(n + 2 * k, n + 2 * k + 1) for k in range(m)]
    nvars = n + 2 * m
    dinic = Dinic(n, edges, node_var, link_var)
    edge_id = {(u, w): k for k, (u, w) in enumerate(edges)}

    model = Model("wordward-steiner")
    if not verbose:
        model.hideOutput()
    V = [None] * nvars
    for v in range(n):
        if is_term[v]:
            V[v] = model.addVar(f"t{v}", vtype="B", lb=1, ub=1, obj=0)
        else:
            V[v] = model.addVar(f"y{v}", vtype="B", lb=0, ub=1, obj=1)
    for k in range(m):
        a, b = link_var[k]
        V[a] = model.addVar(f"a{k}", vtype="C", lb=0, ub=1, obj=0)
        V[b] = model.addVar(f"b{k}", vtype="C", lb=0, ub=1, obj=0)
    model.setMinimize()

    ch = SteinerConshdlr()
    ch.setup(model, V, dinic, n, is_term, adj, root, others, node_var)
    model.includeConshdlr(
        ch, "steiner", "directed-cut Steiner connectivity",
        sepapriority=1, enfopriority=-1, chckpriority=-1,
        sepafreq=1, propfreq=-1, eagerfreq=-1, maxprerounds=0,
        delaysepa=False, delayprop=False, needscons=False,
    )
    # Constraints live only in the conshdlr (added lazily) so they are invisible
    # to presolve: stop it deleting the "unused" vars and dual-fixing them.
    model.setParam("presolving/maxrounds", 0)
    model.setParam("misc/allowstrongdualreds", False)
    model.setParam("misc/allowweakdualreds", False)
    model.setParam("separating/maxroundsroot", -1 if root_sep_full else 40)
    model.setParam("separating/maxstallroundsroot", -1 if root_sep_full else 12)
    model.setParam("separating/maxrounds", 8)
    if time_limit:
        model.setParam("limits/time", time_limit)

    if warm_tree is not None:
        parent = _bfs_tree(n, adj, warm_tree, root)
        sol = model.createSol()
        for v in range(n):
            model.setSolVal(sol, V[v], 1.0 if (warm_tree[v] or is_term[v]) else 0.0)
        for c, p in parent.items():          # orient each tree edge parent->child
            k = edge_id[(p, c)] if p < c else edge_id[(c, p)]
            a, b = link_var[k]
            model.setSolVal(sol, V[a if p < c else b], 1.0)
        model.addSol(sol)

    model.optimize()
    status = model.getStatus()
    lb = model.getDualbound()
    if model.getNSols() == 0:
        return None, None, lb, status
    chosen = [i for i in range(n) if is_term[i] or model.getVal(V[i]) > 0.5]
    greys = [i for i in chosen if not is_term[i]]
    return chosen, len(greys), lb, status


def solve(name="graph_optimal_2283", time_limit=0):
    ids, idx, n, is_term, adj, edges, g = build_graph(name)
    print(f"{n} nodes, {sum(is_term)} terminals, {len(edges)} edges")
    _, hgreys, _, tree = best_heuristic(name, tries=76, verbose=False)
    print(f"warm-start heuristic: {hgreys} greys -> operations = {106 + hgreys}")

    t0 = time.time()
    chosen, greys, lb, status = solve_core(
        n, is_term, adj, edges, warm_tree=bytearray(tree), time_limit=time_limit)
    print(f"\nstatus={status}  time={time.time()-t0:.1f}s")
    print(f"dual bound (greys) >= {lb:.4f}  ->  operations >= {106 + lb:.4f}")
    if chosen is None:
        print("no feasible solution found")
        return None
    words = 107 + greys
    print(f"best: {greys} grey Steiner nodes  ->  operations = {words - 1}")
    if status == "optimal":
        print("PROVEN OPTIMAL")
    return [ids[i] for i in chosen], greys, words - 1


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "graph_optimal_2283"
    tl = float(sys.argv[2]) if len(sys.argv) > 2 else 0
    out = solve(name, time_limit=tl)
    if out:
        chosen_ids, ngrey, ops = out
        with open("exact_solution_ids.pickle", "wb") as fh:
            pickle.dump(chosen_ids, fh)
        print(f"saved {len(chosen_ids)} set ids to exact_solution_ids.pickle")
