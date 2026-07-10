# Exact / near-exact solver for the wordward-draw Steiner instance

This folder holds an experiment (built by Claude) to solve the reduced word graph
**exactly** with real optimization solvers, instead of the hand-tuned heuristic in
`src/solver.py`. It reframes the puzzle as a classic optimization problem, throws
LP/MIP machinery at it, and lands a solution **one better than the 173 record**.

> **All scripts are run from the repo root** (`python3 src_exact_solver/<x>.py`).
> They read the checkpoints (`graph_optimal_2283.pickle`) and text inputs
> (`all_picture_words.txt`, `dictionary.txt`) relative to the working directory,
> exactly like the original `src/` code.

## The reframing (important — read this first)

The reduced instance `graph_optimal_2283.pickle` is a **node-weighted Steiner
tree in a graph**:

* **Terminals (76 PINK Sets, weight 0):** must all be in the answer. The opening
  `WORM → WORD → WARD → DRAW` is *not* an extra cost — all four words live inside a
  single 7-word PINK terminal set (`card`), so they're already forced in.
* **Steiner candidates (2207 GREY Sets, weight 1 each):** optional stepping-stones,
  one non-picture word apiece.
* **Goal:** the minimum number of GREY Sets that connect all 76 terminals into one
  component.

Because every PINK set together holds 107 words:

```
total words = 107 + (#greys used)
operations  = total words - 1 = 106 + (#greys used)
```

So the record **173 operations = 67 greys**, and every result below is quoted in
both units.

## Results

| | greys | operations | how |
|---|---|---|---|
| Previous record (`src/solver.py`) | 67 | 173 | hand-tuned heuristic |
| **Best found here** | **66** | **172** | randomized SPH + Steiner-node elimination |
| Lower bound (proven) | ≥ 44 | ≥ 150 | SCIP root directed-cut bound 43.5 (session 2) |

**The true optimum is bracketed in `[150, 172]` operations.** We have a concrete,
better-than-record solution (saved as `best_solution.pickle`), and a valid proof
that you can't do better than 150.

### Session 2 (2026-07-09): optimality push + full-dictionary check

Four parallel ~80–105 min runs, all warm-started at/around the 66-grey record:

* **Global bound (SCIP, full 2283 graph, 105 min):** root bound reached 43.5
  greys before the time limit → **proven ≥ 44 greys / ≥ 150 operations** (up
  from 149). Still all root separation, no branching — unchanged diagnosis.
* **Bigger pool matheuristic** (360-grey pool from ~7.2k randomized runs,
  91 min MIP): nothing below 66; within-pool dual only reached 43.
* **Incumbent-neighborhood exact solve** (terminals + record greys + all 446
  greys with ≥2 attachments to the record tree = 588 nodes, 80 min): **no
  65-grey solution found** near the record (timelimit at ~13% of the tree, so
  not a full local-optimality proof; within-neighborhood dual 42).
* **Full dictionary, no reductions** (`graph_full_3915.pickle`: 3915 singleton
  Sets, 107 pink terminals, 22 916 edges — built because `delete_hard_greys` /
  `delete_equi_greys_dist_to_pinks` in `src/reductions.py` are *not* provably
  optimality-preserving for Steiner trees): ~9k randomized heuristics + pool
  MIP give **exactly 66 greys / 172 operations again**, and the best solution
  found uses **zero** of the 1601 words the reduction dropped. Empirically the
  reduction lost nothing.

Net: 66/172 survived ~16k randomized restarts and three independent exact
subproblem searches on two graphs. Optimum still open in `[150, 172]`, with 172
looking ever more likely to be it.

### Why it isn't closed to optimality

This is a **dense** Steiner instance (median GREY degree ≈ 10, max 31) — unlike the
sparse road-network graphs that PACE/SCIP-Jack close in seconds. Two consequences:

* The directed-cut **LP relaxation is strong but degenerate**: its bound tails off
  around 40–43 greys and each cut round re-solves a big, dense LP. SCIP spends all
  its time separating at the root and barely branches.
* **Heuristics plateau hard at 66–67.** SPH, KMB, elimination, ~6600 randomized
  restarts, and even an exact solve over a 185-grey candidate pool all stop at 66.
  That's decent (unproven) evidence 66 is at or near the true optimum.

## Files

| file | what it is |
|---|---|
| `heuristic.py` | Node-weighted Steiner heuristics: shortest-path heuristic (`grow_tree`), Mehlhorn distance-network (`kmb`), leaf `prune`, Steiner-node `eliminate` local search, and `best_heuristic` driver. **Fast, gives a real solution.** |
| `exact_solver.py` | The shared graph loader `build_graph` and the split-graph max-flow `Dinic` used for directed-cut separation. Also a standalone HiGHS cut-loop solver (superseded by `scip_solver.py`). |
| `scip_solver.py` | SCIP branch-and-cut. A `Conshdlr` lazily separates directed (bidirected) cuts on fractional LP points and enforces integer connectivity. `solve_core(...)` runs it on *any* graph (used by `pool_solve.py`). |
| `lp_primal.py` | Directed-cut LP relaxation → the **lower bound** (43 greys / 149 ops) + LP-guided rounding. |
| `pool_solve.py` | **Matheuristic:** gather a pool of "useful" greys from many heuristic runs, then solve Steiner *exactly* on the small induced subgraph. Best way to squeeze the primal. |
| `best_solution.pickle` | The 66-grey / 172-operation answer: a `pickle`d `list` of 142 Set ids (76 terminals + 66 greys) from `graph_optimal_2283.pickle`. |

## How to run

```bash
# fast: a real solution + operation count (seconds)
python3 src_exact_solver/heuristic.py graph_optimal_2283 76

# the proven lower bound + LP-rounded primal (a few minutes)
python3 src_exact_solver/lp_primal.py

# matheuristic: pool + exact subgraph solve (args: pool_seconds mip_seconds)
python3 src_exact_solver/pool_solve.py graph_optimal_2283 90 600

# full exact branch-and-cut (args: name time_limit_seconds) — will NOT close, dense
python3 src_exact_solver/scip_solver.py graph_optimal_2283 600
```

### Dependencies (pip-installed into `~/.local` this session)

```bash
pip install highspy pyscipopt networkx
```

`highspy` = HiGHS LP/MIP, `pyscipopt` = SCIP 10 (branch-and-cut with constraint
handlers), `networkx` was a sanity-check baseline. The original `src/` code still
needs nothing beyond the standard library — these are only for this folder.

## Next steps you could ask Claude to do (new session)

1. **Render the 66-grey solution into a playable move list.** `best_solution.pickle`
   is a list of Set ids, but `src/render_solution.py` expects a *graph* pickle whose
   PINK Sets are the answer. Write a small adapter: load `graph_optimal_2283.pickle`,
   mark those 142 Sets `isKey=True`, keep only them, `pickle` it, and run
   `render_solution.py` on it to get the annotated `WORM 0 / WORD 1 / …` path and
   confirm it really plays in 172 moves. *(This is the most valuable follow-up — it
   turns the number into a verified, playable result.)*

2. **Push the primal below 66 with a stronger local search.** The current elimination
   move can't escape the 66–67 plateau. Implement **key-path exchange** (replace each
   path between two branch/terminal vertices with a cheaper reconnection) or a
   **local-branching** loop in SCIP around the incumbent. Target the low 60s.

3. **Tighten the lower bound.** Let `pool_solve.py` run the tight-pool branch-and-cut
   to completion (it was at gap ~28%, within-pool dual 51.5 greys, when paused) to get
   the *within-pool* optimum, and/or let full-graph SCIP branch longer for a global
   dual bound above 43. If a bound meets a primal, the optimum is proven.

4. **Try graph reductions for node-weighted Steiner.** Standard Steiner reductions
   (bottleneck/least-cost tests, long-edge removal) could thin the dense graph enough
   for SCIP to actually branch. This is what real solvers rely on and we skipped it.

5. **Fold the winner back into the repo.** If a solution beats 173 and is verified
   playable, update `README.md` (the "173 operations" / "not possible to find optimal"
   claims) and regenerate `results/`.
