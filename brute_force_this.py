import pickle
import copy
import random
from common import find_all_branches, KEYWORDS, dictionary, Set

# global vars are ALLSETS and dist_2_pinks
#
# ALLSETS is a dictionnary that contains all the possible SETS
# a SET have one or several words in them, a SET is either PINK (it is part of the solution)
# or GREY (it might or might not be part of the solution)
# it has .links (connexions to other SETs)
#
# dist_2_pinks is a dictionary, 
# it gives the distance from every SET (key) to every PINK SETS (value)

def load(x:str):
    """
    Load a .pickle file into a variable
    """
    "load file x into variable x"
    with open(x+".pickle", 'rb') as handle:
        globals()[f"{x}"] = pickle.load(handle)

def save(x:str, *args):
    """
    Save a variable into a .pickle file
    """
    "save variable x into file x"
    with open(x+".pickle", 'wb') as handle:
        try:
            pickle.dump(eval(x), handle, protocol=pickle.HIGHEST_PROTOCOL)
        except:
            pickle.dump(args[0], handle, protocol=pickle.HIGHEST_PROTOCOL)

def log(x:str):
    "write into the log.txt"
    print(x)
    with open("log.txt", 'a') as file:
        file.write(x)
        file.write("\n")


def ALLSETS_del(word, doPrint=True):
    "method to delete a SET from ALLSETS"
    global ALLSETS
    global dist_2_pinks
    words = ALLSETS[word].words
    del ALLSETS[word]

    if word in dist_2_pinks:
        del dist_2_pinks[word]
        if doPrint:
            log(f"  removed {word} from dist_2_pinks")

    for word in words:
        for key, SET in ALLSETS.items():
            if word in SET.links:
                if doPrint:
                    print(f"removed {word} from {SET}'s links")
                SET.links.remove(word)


def ALLSETS_find(word:str):
    "find the SET that contains word"
    global ALLSETS
    for key, SET in ALLSETS.items():
        if word in SET.words:
            return SET
    return None

def ALLSETS_check_if_all_IDs_are_correct():
    "check if every SET in ALLSETS have the correct ID"
    for key, SET in ALLSETS.items():
        if key != SET.id():
            print(f"ERROR key: {key}, id:{SET.id()} for {SET}")

def ALLSETS_get_pinks(isKey:bool=True):
    "true return PINKS, false returns GREYS"

    global ALLSET
    PINKS = {}
    for key, SET in ALLSETS.items():
        if SET.isKey == isKey:
            PINKS[key] = SET
    return PINKS

def ALLSETS_is_winnable(doPrint=True):
    "check if the game is still winnable from the current state of ALLSETS"
    global ALLSETS

    set_of_words = set()
    for PINK in ALLSETS_get_pinks().values():
        if len(PINK.links) == 0 and len(ALLSETS_get_pinks())>1:
            print(f"can't reach {PINK}")
            return False
        set_of_words.update( PINK.words )
    
    if all(x in set_of_words for x in KEYWORDS): 
        return True
    else:
        log(f"some Keywords are missing")
        return False

def ALLSETS_get_words():
    "return the set of words in ALLSETS"
    global ALLSETS
    result = set()
    for key,SET in ALLSETS.items():
        for word in SET.words:
            result.add(word)
    return result

def ALLSETS_to_txt():
    "write a file with the list of words in ALLSETS"
    result = "\n".join(ALLSETS_get_words())
    with open("KEYWORDS-"+ str(len(result.split("\n"))) +".txt", 'w') as file:
        file.write(result)

def ALLSETS_get_cost():
    "get the cost of all PINK SETS"
    global ALLSETS
    value = sum(x.cost() for x in ALLSETS_get_pinks().values())
    SETS_OF_LINKS = [links.words for links in ALLSETS_get_pinks().values()]
    words = set()
    for SET in SETS_OF_LINKS:
        words.update(SET)

    return (words, value)


def get_pinkCosts():
    """(the reverse of dist_2_pink)
    from dist_2_pinks, generate pinkCost which is a dict of all PINKS (key)
    and the sum of the costs of all SETS to get to that key (value)
    """
    global dist_2_pinks
    pinkCost = {}
    # variable = input("Regenerate dist_2_pinks? Y/N")
    # if variable == "Y":
    #     ALLSETS_calculate_dist_to_pinks()

    for origin, links in dist_2_pinks.items():
        for destination, linkCost in links.items():
            if destination not in pinkCost:
                pinkCost[destination] = {}
            pinkCost[destination][origin] = linkCost
    return pinkCost

def pinkCost_sort(pinkOnly = False):
    "from pinkCost, get list of PINK SETS ordered by the most expensive on average to get to"
    global ALLSETS
    global dist_2_pinks

    pinkCost = get_pinkCosts()
    my_dict = {}
    for PINK in pinkCost:
        my_dict[PINK] = 0
        population = 0
        for link in pinkCost[PINK]:
            if link not in ALLSETS:
                log(f"  Cant find {link} in SETS, deleting it from dist_2_pinks's dist_2_pinks[{link}][{PINK}]")
                del dist_2_pinks[link][PINK]
            elif not pinkOnly or ALLSETS[link].isKey:
                population += 1
                my_dict[PINK] += pinkCost[PINK][link]
                    
        my_dict[PINK] /= population
    sorted_list = sorted(my_dict.items(), key=lambda item: item[1])
    return sorted_list

    
def initialize():
    "convert words into SETS"
    allWords = {}
    i=0
    for word in dictionary:
        temp = find_all_branches(word)
        temp.remove(word)
        allWords[word] = temp
        i+=1
        if i%500 == 0:
            print(str(i))
    
    ALLSETS = []
    for word in allWords:
        ALLSETS.append(Set({word}, allWords[word]))
    
    temp = {}
    for index,SET in enumerate(ALLSETS):
        temp[SET.id()] = SET
    ALLSETS = temp

##############################################################################

def MERGE_PINK_SETS():
    "if two pink sets are next to each others: merge them together"
    global ALLSETS
    global dist_2_pinks

    somethingHappened = True
    while somethingHappened:
        somethingHappened = False

        for key, SET in ALLSETS.items():
        
            if SET.isKey:
                for link in SET.links:
                    if ALLSETS[link].isKey:
                        log(f"  pink: merged {ALLSETS[link]} with {SET}")
                        first_word = sorted([ALLSETS[link].id(), SET.id()])[0]
                        second_word = sorted([ALLSETS[link].id(), SET.id()])[1]
                        ALLSETS[first_word].update( ALLSETS[second_word], ALLSETS, dist_2_pinks)
                        ALLSETS_del(second_word)
                        somethingHappened = True
                        break
                if somethingHappened:    
                    break
    pass

def clean_ALLSETS():
    "Remove link of words that were moved/deleted, it's just for doublechecking"
    global ALLSETS
    done = set()
    somethingHappened = True
    while somethingHappened:
        somethingHappened = False
        for key, SET in ALLSETS.items():
            if key not in done:
                for word in SET.links:
                    if word not in ALLSETS:
                        log(f"  cleaned {word} from {SET}'s links")
                        SET.links.remove(word)
                        somethingHappened = True
                        break
                if somethingHappened:
                    break

                done.add(key)

def DELETE_EQUIVALENT_GREYS(minimum_connection=1):
    """first, delete sets that have 1 or less connection, they are useless
    then when it finds two SETs with the same links or one with more links only keep that."""
    global ALLSETS
    
    #delete all Greys with one or less connections
    somethingHappened = True
    while somethingHappened:
        somethingHappened = False
        for SET in ALLSETS_get_pinks(False):
            if len(ALLSETS[SET].links) < minimum_connection:
                log("   deleted: "+ALLSETS[SET].id()+" (isolated)")
                ALLSETS_del(SET)

                # if not ALLSETS_is_winnable:
                #     print("UNWINNABLE")
                #     return
                # somethingHappened = True
                # break

    GREYS = ALLSETS_get_pinks(False)
    count = 0
    for key, A in GREYS.items():
        count += 1
        if count%100 == 0:
            print(f"checking {key}")
        for key2, B in GREYS.items():
            if A == B:
                continue
            if key not in ALLSETS:
                continue
            if key2 not in ALLSETS:
                continue

            if (B.links - {A.id}).issubset(A.links - {B.id}): 
                log("   subset deleted: "+B.id()+" is included in "+A.id())
                ALLSETS_del(key2)

def MERGE_GREYS():
    """if two greys are connected to each others, you can merge them if they only have
    one other connection each"""
    global ALLSETS
    done = set()
    somethingHappened = True
    while somethingHappened:
        somethingHappened = False
        
        GREYS = Set.filter_sets(ALLSETS, False)

        for key,A in GREYS.items():
            # print(f"finding merges for {key}")
            if key not in done:
                if len(A.links) == 2:
                    for B in A.links:
                        if not ALLSETS[B].isKey and len(ALLSETS[B].links)==2:
                            log(f"  grey: merged {A} with {B}")
                            A.update( ALLSETS[B], ALLSETS, dist_2_pinks)
                            ALLSETS_del(B)
                            somethingHappened = True
                            break
                    if somethingHappened:    
                        break
                done.add(key)

def optimize_greys():
    global ALLSETS
    log("   - OPTIMIZING GREYS -")
    log("       - MERGING GREYS-")
    MERGE_GREYS()   #deletable
    log("       - DELETING EQUI-")
    DELETE_EQUIVALENT_GREYS() #deletable
    log("       - CLEANING (optional) -")
    clean_ALLSETS() #deletable

def optimize_all():
    "try to optimize ALLSETS"
    global ALLSETS

    current = 0
    while current != len(ALLSETS):
        current = len(ALLSETS)

        log(f"  Currently {current} sets.")
        
        if not ALLSETS_is_winnable():
            log(f"not winnable anymore")
            input("rip")
            print("nooo")
            save("ALLSETS")
            return
        
        log("   - MERGING PINKS-")
        MERGE_PINK_SETS()
        
        log("   - FIND_NECESSARY_SETS -")
        FIND_NECESSARY_SETS()

        optimize_greys() #deletable

        if current == len(ALLSETS):
            log("   - DELETE_EQUI_GREYS_dist_2_pinks-")
            DELETE_EQUI_GREYS_dist_2_pinks()
            log("   - DELETE_HARD_GREYS -")
            DELETE_HARD_GREYS()

def find_shortest_pathS(start_set, end_set, getWords=True):
    """Return a list of all Sets included in the shortest paths between the inputs
    is used in the DELETE_HARD_GREYS function"""
    
    if start_set == end_set:
        return set()
    
    tree = {}
    tree[start_set] = {"step":0, "searched":False}
    step = 0

    while (end_set not in tree and step<100):
        step += 1
        to_add = {}
        for SET_id in tree:
            if not tree[SET_id]["searched"]:
                for link in ALLSETS[SET_id].links:
                    if link not in tree and link not in to_add:
                        to_add[link] = {"step":step, "searched":False, "parents":{SET_id}}
                    elif link in to_add:
                        if to_add[link]["step"] == step:
                            to_add[link]["parents"].add(SET_id)
                    elif link in tree:
                        if tree[link]["step"] == step:
                            tree[link]["parents"].add(SET_id)
        tree.update(to_add)
        tree[SET_id]["searched"] = True

    if step==100:
        raise TimeoutError("no path found")
    
    #when it has found a path:

    if getWords:
        set_of_words = {end_set}
        next = {end_set}
        while start_set not in set_of_words:
            buffer = set()
            for parent in next:
                set_of_words.update(tree[parent]["parents"])
                buffer.update(tree[parent]["parents"])
            next = buffer

        return set_of_words
    else:
        #get path
        SET = end_set
        path = []
        while SET != start_set:
            path.append(SET)
            SET = tree[SET]["parent"][0]

        return list(reversed(path))

def DELETE_HARD_GREYS():
    """
    For every pair of PINK, find shortest pathS
    between the two. Remember all the SETs mentionned
    At the end, delete every grey SETS not mentionned.
    slow to run
    """
    PINKS = Set.filter_sets(ALLSETS)
    necessary_sets = set()
    done = [set()]
    for A in PINKS:
        for B in PINKS:
            if A==B: continue
            if {A,B} in done:
                continue
            done.append( {A,B} )
            if len(done)%100 == 0:
                print(f"searching for {A} and {B}, currently {len(necessary_sets)} words")
            necessary_sets.update( find_shortest_pathS(A,B) )

    # load("necessary_sets")
    GREYS = Set.filter_sets(ALLSETS, False)
    for GREY in GREYS:
        if GREY not in necessary_sets:
            log(f"  the set of {GREY} is unecessary")
            ALLSETS_del(GREY)

def FIND_NECESSARY_SETS():
    """
    for every GREY:
    try to delete it, is the game still winnable?
    if it's not winnable anymore, it means the GREY was necessary
    make the GREY a PINK set.
    slow
    """
    global ALLSETS
    global dist_2_pinks

    # if there is pinks with only 1 connection:

    PINKS = ALLSETS_get_pinks()
    for key, pink in PINKS.items():
        if len(pink.links) == 1:
            ALLSETS[list(pink.links)[0]].isKey = True
            MERGE_PINK_SETS()

    GREYS = ALLSETS_get_pinks(False)
    
    ALLSETS_BACKUP = copy.deepcopy(ALLSETS)
    dist_2_pinks_BACK = copy.deepcopy(dist_2_pinks)
    
    cutInThePast = False

    # for key, SET in GREYS.items():
    i = 0
    while i < len(GREYS)-1:
        key = list(sorted(GREYS))[i]
        SET = GREYS[key]
        # if key<"gaby":
        #     continue
        ALLSETS_del(key, False)
        # i think an easier way is just to check if all PINKs still have at least 1 connection
        if ALLSETS_is_winnable():
            if i%100 == 0:
                print(f"No info on {SET}.")
            cutInThePast = True
            i+=1
            
        else:
            if cutInThePast:
                print(f"    maybe must keep {SET}")
                ALLSETS = copy.deepcopy(ALLSETS_BACKUP)
                dist_2_pinks = copy.deepcopy(dist_2_pinks_BACK)
                cutInThePast = False
            else:
                log(f"  MUST KEEP {SET}")
                ALLSETS = copy.deepcopy(ALLSETS_BACKUP)
                dist_2_pinks = copy.deepcopy(dist_2_pinks_BACK)
                ALLSETS[key].isKey = True

                MERGE_PINK_SETS()
                return
    log(f"      no necessary set found.")
    ALLSETS = copy.deepcopy(ALLSETS_BACKUP)
    dist_2_pinks = copy.deepcopy(dist_2_pinks_BACK)
    return

def ALLSETS_calculate_dist_to_pinks(SAVE=False):
    """
    create dist_2_pinks
    Calculate distance to nearest pinks,
    (nearest pink: from a SET, it propagates in every direction,
    but it becomes an end node if it reaches a pink, that means
    it will not take into account PINKs that use other PINKs to
    get to them, but it will take into account every PINK that
    has an alternative path with only GREY sets)
    slow to run"""
    
    if all( len(x.words)==1 for x in ALLSETS_get_pinks(False).values()):
        mode = "simple" # only counts the steps
    else:
        mode = "hard" # counts the cost()
    
    global dist_2_pinks
    dist_2_pinks = {}
    global ALLSETS
    # GREYS = ALLSETS_get_pinks(False)
    i = 0
    for key,SET in ALLSETS.items():
        i+=1
        if i%100 == 0:
            print(f"setting {SET}'s pink links")
        tree = {}
        tree[key] = False
        Links = {}
        Links[key] = ALLSETS[key].cost()
        step = 0

        somethingHappenned = True
        while somethingHappenned:
            somethingHappenned = False
            
            step+=1
            buffer = {}
            for SET_id in tree:
                if not tree[SET_id]:
                    somethingHappenned = True
                    for link in ALLSETS[SET_id].links:
                        if mode == "hard": # we save the costs of GREYS
                            if link not in Links:
                                Links[link] = Links[SET_id] + ALLSETS[link].cost()
                            else:
                                if Links[link]> Links[SET_id] + ALLSETS[link].cost():
                                    Links[link] = Links[SET_id] + ALLSETS[link].cost()
                            if link not in tree and not ALLSETS[link].isKey:
                                buffer[link] = False
                        else: # we save only the costs of PINKs (grey costs can be guessed)
                            if ALLSETS[link].isKey:
                                if link not in Links:
                                    Links[link] = step + 1
                                else:
                                    if Links[link]> step + 1:
                                        Links[link] = step + 1
                            elif link not in tree:
                                buffer[link] = False
                tree[SET_id] = True
            tree.update(buffer)

        if mode == "hard":
            #remove grey costs
            for link in list(Links):
                if link in tree: #if it's not a key:
                    del Links[link]

        del Links[key]

        dist_2_pinks[key] = Links

    if SAVE:
        save("dist_2_pinks")

def DELETE_EQUI_GREYS_dist_2_pinks():
    """
    if two GREYs have the same distance to PINKs, or one have shorter route, or more
    connections, delete the worse one.
    """
    global ALLSETS
    global dist_2_pinks
    GREYS = ALLSETS_get_pinks(False)

    done = 0
    for keyA in GREYS:
        
        for keyB in GREYS:
            done += 1
            if keyA == keyB:
                continue
            if keyA not in ALLSETS or keyB not in ALLSETS:
                continue

            if done%100000 == 0:
                print(f"{keyA}, {keyB} DELETE_EQUI_GREYS_dist_2_pinks")

            if all(link in dist_2_pinks[keyA] and dist_2_pinks[keyB][link] >= dist_2_pinks[keyA][link] for link in dist_2_pinks[keyB]):
            
                log(f"  set deleted: {keyB} is worse than {keyA}")
                ALLSETS_del(keyB)

def test_time(callback):
    start_time = time.time()
    callback()
    print("--- %s seconds ---" % (time.time() - start_time))

def euristic():
    """
    At some point you have to guess which SET you'll need.
    """
    global ALLSETS
    global dist_2_pinks
    while ALLSETS_is_winnable() and len(ALLSETS_get_pinks())>1 and ALLSETS_get_cost()[1]<90:
        
        log(f"Currently {len(ALLSETS)} sets & {len(ALLSETS_get_words())} words:  {ALLSETS_get_cost()}")

        # optimize_all()

        #  173 words
        # choose the word with the highest average cost, find use the link with the lowest distance
        bestChoice = pinkCost_sort()[-1][0] #the Set with the highest average cost
        link_sums = [(link, sum( [ max(0,7-x)**3 for x in dist_2_pinks[link].values() ] ) - ALLSETS[link].cost()) for link in ALLSETS[bestChoice].links]

        # Sort the list of tuples by the total sum of values
        bestLink = sorted(link_sums, key=lambda x: x[1])[-1]
        log(f"euristic: added {bestLink} as Key")
        ALLSETS[bestLink[0]].isKey = True
        MERGE_PINK_SETS()
        optimize_all()

        save("ALLSETS")

    if not ALLSETS_is_winnable:
        log("CANT WIN ANYMORE")
        variable = input("u suck")
    else:
        log(f"found solution with {ALLSETS_get_cost()} words")
        save("ALLSETS")

import time
start_time = time.time()

load("ALLSETS")
load("dist_2_pinks")

with open("log.txt", 'w') as file:
    file.write("")
    
# variable = input("Regenerate dist_2_pinks? Y/N")
# if variable == "Y":
#     ALLSETS_calculate_dist_to_pinks()
euristic()

# DELETE_EQUI_GREYS_dist_2_pinks()
log("--- %s seconds ---" % (time.time() - start_time))
save("ALLSETS")
