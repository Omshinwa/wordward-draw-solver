"""
Render a solved graph pickle into a human-readable view of the solution.

A solution is a *connected* set of 4-letter words. Because `undo` is free, we
can walk a spanning tree of that set in (size - 1) real operations: every word
is reached exactly once by a forward move, and backtracking to a branch point
costs nothing. The walk starts from the game's forced opening WORM -> WORD ->
WARD -> DRAW.

Two output formats, both built from that same spanning tree:

  path (default)  the playable, annotated move list (the format of results/result_playable.txt):
      WORD n      forward move; n = running operation count. UPPERCASE = picture word.
      >word n     an undo (free). One '>' per undo step; n stays the same.

  csv (--csv, or an output filename ending in .csv)  the tree as a spreadsheet
  (the format of results/result_csv_view.csv):
      word;isKeyWord;parent;children

Usage:
    python3 src/render_solution.py                                   # default pickle -> stdout (path)
    python3 src/render_solution.py "graph_173.pickle"          # -> stdout (path)
    python3 src/render_solution.py "graph_173.pickle" out.txt  # -> file (path)
    python3 src/render_solution.py "graph_173.pickle" out.csv  # -> file (csv, inferred)
    python3 src/render_solution.py "graph_173.pickle" --csv    # -> stdout (csv)
"""
import sys
import pickle
from word_set import KEYWORDS, Set  # Set is needed to unpickle the graph
from utils import find_all_branches

# The game's forced opening.
OPENING_ROOT = "worm"
FORCED_NEXT = {"worm": "word", "word": "ward", "ward": "draw"}


def solution_words(graph):
    """The solution is the union of the words in every PINK (committed) set."""
    words = set()
    for s in graph.values():
        if s.isKey:
            words |= s.words
    return words


def build_adjacency(words):
    """Undirected graph over `words`: an edge means the two words are one game move
    apart (differ by a single letter, or are anagrams)."""
    words = set(words)
    return {w: sorted(b for b in find_all_branches(w) if b in words) for w in words}


def walk(words):
    """Depth-first walk of a spanning tree of the solution, from the WORM -> WORD ->
    WARD -> DRAW opening.

    Returns (path_lines, operations, parent, children):
      path_lines  the annotated move list (forward moves + '>' undos)
      operations  total forward moves == len(words) - 1
      parent      {word: parent word} for the spanning tree (root -> None)
      children    {word: [child words in visit order]}
    """
    words = set(words)
    adj = build_adjacency(words)

    missing = KEYWORDS - words
    if missing:
        raise SystemExit(f"not a valid solution: {len(missing)} picture words are absent "
                         f"(e.g. {sorted(missing)[:8]})")
    if OPENING_ROOT not in words:
        raise SystemExit(f"opening word '{OPENING_ROOT}' is not in the solution set")

    label = lambda w: w.upper() if w in KEYWORDS else w
    lines = [f"{label(OPENING_ROOT)} 0"]
    parent = {OPENING_ROOT: None}
    children = {w: [] for w in words}
    visited = {OPENING_ROOT}
    stack = [OPENING_ROOT]
    op = 0

    def ordered_children(node):
        kids = [c for c in adj[node] if c not in visited]
        nxt = FORCED_NEXT.get(node)
        if nxt in kids:                # honour the forced opening moves
            kids.remove(nxt)
            kids.insert(0, nxt)
        return kids

    sys.setrecursionlimit(10 * len(words) + 1000)

    def dfs(node):
        nonlocal op
        node_depth = len(stack) - 1    # `node` sits here for the whole call
        for child in ordered_children(node):
            if child in visited:       # became visited via another branch (a cycle edge)
                continue
            # backtrack (free undos) from wherever we are down to `node`
            k = 0
            while len(stack) - 1 > node_depth:
                stack.pop()
                k += 1
                lines.append(f"{'>' * k}{label(stack[-1])} {op}")
            # forward move to the new word (+1 operation)
            op += 1
            lines.append(f"{label(child)} {op}")
            parent[child] = node
            children[node].append(child)
            visited.add(child)
            stack.append(child)
            dfs(child)

    dfs(OPENING_ROOT)

    if len(visited) != len(words):
        unreached = sorted(words - visited)
        raise SystemExit(f"solution set is not connected: {len(unreached)} words are unreachable "
                         f"from '{OPENING_ROOT}' (e.g. {unreached[:8]})")
    return lines, op, parent, children


def to_path(lines):
    "The annotated move list (result.txt format)."
    return "\n".join(lines) + "\n"


def to_csv(parent, children):
    "The spanning tree as a spreadsheet (smallestSET.csv format), rows sorted by word."
    rows = ["word;isKeyWord;parent;children"]
    for word in sorted(parent):
        is_key = "1" if word in KEYWORDS else "0"
        par = parent[word] or ""
        kids = ",".join(children[word])
        rows.append(f"{word};{is_key};{par};{kids}")
    return "\n".join(rows) + "\n"


if __name__ == "__main__":
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    positional = [a for a in sys.argv[1:] if not a.startswith("--")]

    src = positional[0] if positional else "graph_173.pickle"
    out = positional[1] if len(positional) > 1 else None

    # format: explicit flag wins, else infer from the output extension, else path
    if "--csv" in flags:
        fmt = "csv"
    elif "--path" in flags:
        fmt = "path"
    elif out and out.lower().endswith(".csv"):
        fmt = "csv"
    else:
        fmt = "path"

    with open(src, "rb") as handle:
        graph = pickle.load(handle)

    lines, ops, parent, children = walk(solution_words(graph))
    text = to_csv(parent, children) if fmt == "csv" else to_path(lines)

    if out:
        with open(out, "w") as f:
            f.write(text)
        print(f"wrote {out}: {len(parent)} words, {ops} operations ({fmt} format)")
    else:
        sys.stdout.write(text)
