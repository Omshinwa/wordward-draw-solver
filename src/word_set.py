def _load_lines(path):
    with open(path) as f:
        return f.read().split("\n")

# module globals
KEYWORDS = set(_load_lines("all_picture_words.txt"))
dictionary = _load_lines("dictionary.txt")          # list: preserves file/build order
DICTIONARY_WORDS = frozenset(dictionary)            # set: O(1) membership for branch-finding

class Set:
    def __init__(self, words: set[str], links: set[str]):
        self.words = set(words)
        self.links = links  # connections to other sets
        # PINK (part of the solution) if it holds at least one picture word
        self.isKey = any(word in KEYWORDS for word in self.words)

    def cost(self):
        """
        number of non keywords in it
        higher = the most costly is the solution
        """
        return len(self.words - KEYWORDS)
    
    def id(self):
        return sorted(self.words)[0]
    
    def __repr__(self) -> str:
        return f"{self.id()} ({len(self.words)})"
    
    def __lt__(self,other):
        return len(self.words) > len(other.words)
    
    def update(self, other_set: "Set", sets: dict[str, "Set"], dist_to_pinks: dict[str, dict[str, int]]):
        """Merge (contract) other_set into self: absorb its words/links, rewire
        neighbors to point at self.id(), and fold other_set's dist_to_pinks entries
        into self's (keeping the min distance).

        NOTE: this does NOT remove other_set from the graph or dist_to_pinks. The
        caller is responsible for that via WordGraph.remove(other_set.id()) right after
        calling update() (see reductions.py).
        """
        self.words.update(other_set.words)
        self.links.update(other_set.links)
        self.links -= self.words   # a Set never links to its own words

        for link in self.links:
            # update the links in other Sets
            sets[link].links -= self.words
            sets[link].links.add( self.id() )

        self.isKey = self.isKey or other_set.isKey

        #UPDATE THE DIST_TO_PINK
        # delete the longest distance before the merge
        for key in dist_to_pinks:
            if other_set.id() in dist_to_pinks[key]:
                if self.id() in dist_to_pinks[key]:
                    dist_to_pinks[key][self.id()] = min( dist_to_pinks[key][self.id()], dist_to_pinks[key][other_set.id()] )
                else:
                    dist_to_pinks[key][self.id()] = dist_to_pinks[key][other_set.id()]
                del dist_to_pinks[key][other_set.id()]

        for link in dist_to_pinks[other_set.id()]:
            if link not in dist_to_pinks[self.id()]:
                dist_to_pinks[self.id()][link] = dist_to_pinks[other_set.id()][link]
            else:
                dist_to_pinks[self.id()][link] = min( dist_to_pinks[self.id()][link], dist_to_pinks[other_set.id()][link])
        # del dist_to_pinks[other_set.id()]

        if other_set.id() in dist_to_pinks[self.id()]:
            del dist_to_pinks[self.id()][other_set.id()]

        return
    

# class Word:
#     "this class is not used in the brute force method"
#     def __init__(self, word, parent, children="", links=None):
#         self.word = word
#         self.parent = parent
#         self.children = set(children) # if it has no children, it's an end node
#         self.propagated = False
#         if links == None:
#             self.links = set()
#     def isKeyWord(self):
#         return self.word in KEYWORDS

