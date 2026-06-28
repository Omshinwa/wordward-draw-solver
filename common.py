from itertools import permutations

# keywords
with open("all_picture_words.txt", "r") as file:
    data = file.read()
    i = data.split("\n")
    KEYWORDS = set(i)

# dictionary
with open("dictionary.csv", "r") as file:
    data = file.read()
    dictionary = data.split("\n")

# dictionary
# with open("KEYWORDS-2459.txt", "r") as file:
#     data = file.read()
#     dictionary = data.split("\n")

class Set:
    def __init__(self, set_of_words: set, links):
        self.isKey = False
        for word in set_of_words:
            if word in KEYWORDS:
                self.isKey = True
                break
        
        self.words = set(set_of_words)
        self.links = links
    
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
    def get_pinks_or_greys(ALLSETS:dict, isKey=True):
        "returns all PINKS or GREYS from ALLSETS, true return PINKS "
        PINKS = {}
        for key, SET in ALLSETS.items():
            if SET.isKey == isKey:
                PINKS[key] = SET
        return PINKS
    
    @staticmethod
    def find_set(ALLSETS, word:str):
        for key, SET in ALLSETS.items():
            if word in SET.words:
                return SET
        return None
    
    def update(self, other_set, ALLSETS:dict, dist_2_pinks):
        self.words.update(other_set.words)
        self.links.update(other_set.links)
        discarded_links = set()

        happened = True
        while happened:
            happened = False
            for link in self.links:
                if link in self.words:
                    self.links.remove(link)
                    happened = True
                    discarded_links.add(link)
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
    

class Word:
    "this class is not used in the brute force method"
    def __init__(self, word, parent, children="", links=None):
        self.word = word
        self.parent = parent
        self.children = set(children) # if it has no children, it's an end node
        self.propagated = False
        if links == None:
            self.links = set()
    def isKeyWord(self):
        return self.word in KEYWORDS


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

