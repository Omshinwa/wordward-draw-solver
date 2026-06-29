from itertools import permutations

# keywords
with open("all_picture_words.txt", "r") as file:
    data = file.read()
    i = data.split("\n")
    KEYWORDS = set(i)

# dictionary
with open("dictionary.txt", "r") as file:
    data = file.read()
    dictionary = data.split("\n")

class Set:
    def __init__(self, words: set[str], links: set[str]):
        # links: ids of connected Sets (each is a key into ALLSETS)
        self.isKey = False  # is the set part of the solution?
        self.words = set(words)
        self.links = links # connections to other sets
        
        for word in words:
            if word in KEYWORDS:
                self.isKey = True
                break
    
    def cost(self):
        i = 0
        for word in self.words:
            if word not in KEYWORDS:
                i+=1
        return i
    
    def id(self):
        return sorted(self.words)[0]
    
    def __repr__(self) -> str:
        return f"{self.id()} ({len(self.words)})"
    
    def __lt__(self,other):
        return len(self.words) > len(other.words)
    
    @staticmethod
    def filter_sets(ALLSETS: dict[str, "Set"], pink=True):
        """
        returns all PINKS (pink=True) or GREYS (pink=False) Sets from ALLSETS.
        """
        PINKS = {}
        for key, SET in ALLSETS.items():
            if SET.isKey == pink:
                PINKS[key] = SET
        return PINKS
    
    @staticmethod
    def find_set(ALLSETS: dict[str, "Set"], word: str):
        """
        Find the Set containing the WORD.
        """
        for key, SET in ALLSETS.items():
            if word in SET.words:
                return SET
        return None
    
    def update(self, other_set: "Set", ALLSETS: dict[str, "Set"], dist_2_pinks: dict[str, dict[str, int]]):
        """Merge (contract) other_set into self: absorb its words/links, rewire
        neighbors to point at self.id(), and fold other_set's dist_2_pinks entries
        into self's (keeping the min distance).

        NOTE: this does NOT remove other_set from ALLSETS or dist_2_pinks. The
        caller is responsible for that via ALLSETS_del(other_set.id()) right after
        calling update() (see brute_force_this.py merge_pinks / optimize_greys).
        """
        self.words.update(other_set.words)
        self.links.update(other_set.links)

        happened = True
        while happened:
            happened = False
            for link in self.links:
                if link in self.words:
                    self.links.remove(link)
                    happened = True
                    break
        

        for link in self.links:
            # update the links in other Sets
            ALLSETS[link].links -= self.words
            ALLSETS[link].links.add( self.id() )

        self.isKey = self.isKey or other_set.isKey

        #UPDATE THE DIST_TO_PINK
        # delete the longest distance before the merge
        for key in dist_2_pinks:
            if other_set.id() in dist_2_pinks[key]:
                if self.id() in dist_2_pinks[key]:
                    dist_2_pinks[key][self.id()] = min( dist_2_pinks[key][self.id()], dist_2_pinks[key][other_set.id()] )
                else:
                    dist_2_pinks[key][self.id()] = dist_2_pinks[key][other_set.id()]
                del dist_2_pinks[key][other_set.id()]

        for link in dist_2_pinks[other_set.id()]:
            if link not in dist_2_pinks[self.id()]:
                dist_2_pinks[self.id()][link] = dist_2_pinks[other_set.id()][link]
            else:
                dist_2_pinks[self.id()][link] = min( dist_2_pinks[self.id()][link], dist_2_pinks[other_set.id()][link])
        # del dist_2_pinks[other_set.id()]

        if other_set.id() in dist_2_pinks[self.id()]:
            del dist_2_pinks[self.id()][other_set.id()]

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


def find_all_permutation(word):
    valid_permutation = set()
    list_permutation = set([''.join(p) for p in permutations(word)])
    for permutation in list_permutation:
        if permutation in dictionary:
            valid_permutation.add(permutation)
    return valid_permutation

def find_all_substitution(word):
    valid_sub = set()
    alphabet = "abcdefghijklmnopqrstuvwxyz"
    for index in range(len(word)):
        for letter in alphabet:
            substitution = word[:index] + letter + word[index+1:] 
            if substitution in dictionary:
                valid_sub.add(substitution)
    
    return valid_sub

def find_all_branches(word):
    set1 = find_all_substitution(word)
    set2 = find_all_permutation(word)
    return set1.union(set2)

