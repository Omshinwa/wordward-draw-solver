import pickle
import copy
from common import find_all_branches, KEYWORDS, Word

def load(x:type("s")):
    with open(x+".pickle", 'rb') as handle:
        globals()[f"{x}"] = pickle.load(handle)

def save(x:type("s")):
    with open(x+".pickle", 'wb') as handle:
        pickle.dump(eval(x), handle, protocol=pickle.HIGHEST_PROTOCOL)

    def __repr__(self) -> str:
        return self.word
    
    def __lt__(self,other): #this makes operation with '<' possible, and so sorting cards are by names.
        return self.word<other.word

    def isKeyWord(self):
        return self.word in KEYWORDS

def find_big_SET():

    step = 0
    TODO = KEYWORDS.copy()
    SET = { Word("worm", ""), Word("word", ""), Word("ward", ""), Word("draw", "") }

    #remove all starting words from the list of words to search
    for CURRENTWORD in SET:
        if CURRENTWORD.isKeyWord():
            TODO.discard(CURRENTWORD.word)

    while len(TODO)>0:
        print( "[" + str(len(SET)) + "]" )
        # print( "[" + str(len(SET)) + "] : " + ", ".join(sorted(list([item.word for item in SET]))))

        for CURRENTWORD in SET:

            smallSet = set()
            
            if not CURRENTWORD.propagated:
                list_of_words = find_all_branches(CURRENTWORD.word)
                for word in list_of_words:
                    if word not in [item.word for item in SET]: #SET.union(smallSet)]:
                        smallSet.add(Word(word, CURRENTWORD))
                        CURRENTWORD.children.add(word)
                        if word in KEYWORDS:
                            TODO.discard(word)
                             
            CURRENTWORD.propagated = True
            SET = SET.union(smallSet)
        # SET = newSET.copy()
        step += 1

    ######
    # WE HAVE THE LIST OF SET, NOW WE CUT UNNEEDED BRANCHES
    return SET

def shave_off_branches_dict(DICT):
    # remove end branches that arent keys
    somethingHappened = True
    while somethingHappened: 
        somethingHappened = False

        for word in DICT:
            newDICT = DICT.copy()

            if len(DICT[word].children) == 0 and not DICT[word].isKeyWord(): # end node
                
                for word2 in newDICT:
                    if word in DICT[word2].children:
                        DICT[word2].children.remove(word)

                del newDICT[word]
                somethingHappened = True

            DICT = newDICT.copy()
    return DICT

def write_DICT_to_csv(DICT, filename = "smallestSET"):
    
    result = "word;isKeyWord;parent;children"
    for word in sorted(DICT):
        Word = DICT[word]
        result += "\n"
        if Word.parent != "":
            result += Word.word +";"+ str(int(Word.isKeyWord())) +";"+ Word.parent +";"+ ",".join(sorted(Word.children))
        else:
            result += Word.word +";1;;"+ ",".join(sorted(Word.children))

    with open(filename+'.csv', 'w') as file:
        file.write(result)

def import_csv_to_DICT(filename = "smallestSET"):
    with open(filename+'.csv', 'r') as file:
        data = file.read()
        data = data.split("\n")
        DICT = {}
        for index,array in enumerate(data):
            if array != '':
                array = array.split(";")
                word = array[0]
                parent = array[2]
                children = set()
                for child in array[3].replace('"','').split(","):
                    children.add(child)
                if index == 0:
                    continue
                DICT[word] = Word(word,parent,children)

    return DICT

# randomly switch between two possible connection and see if it can cut off branches from that
def try_all_greedy_changes(DICT):
    def try_optimize(DICT):
        print(len(DICT))
        already_tried_connexions = set()
        for word in DICT:
            for newParent in find_all_branches(word):
                if newParent == word:
                    continue
                # si c'est la connexion de base:
                if DICT[word].parent == newParent:
                    continue

                if newParent in DICT[word].children:
                    continue

                if newParent in list(DICT):
                    if (newParent, word) not in already_tried_connexions:
                        # we try changing the connexion:
                        already_tried_connexions.add((newParent, word))
                        
                        newDICT = copy.deepcopy(DICT)

                        oldParent = newDICT[word].parent

                        if oldParent == '' or newDICT[oldParent].parent == word:
                            continue

                        oldParent = newDICT[oldParent]
                        
                        oldParent.children.remove(word)
                        newDICT[word].parent = newParent
                        if newDICT[newParent].children == {""}:
                            newDICT[newParent].children = {word}
                        else:
                            newDICT[newParent].children.add(word)

                        newDICT = copy.deepcopy( shave_off_branches_dict(newDICT) )
                        
                        if len(DICT)>len(newDICT):
                            
                            #if everything is connected:
                            test = {list(newDICT)[0]}
                            temptest = set()
                            past_length = len(temptest)
                            done = set()
                            while len(test) != past_length:
                                past_length = len(test)

                                temptest = copy.deepcopy(test)
                                for element in temptest:
                                    if element in done:
                                        continue
                                    if newDICT[element].parent != "":
                                        test.add(newDICT[element].parent)
                                    for child in newDICT[element].children:
                                        if child != "":
                                            test.add(child)
                                    done.add(element)


                            if len(test) != len(newDICT):
                                continue

                            if all(x in newDICT for x in KEYWORDS):
                                DICT = copy.deepcopy( newDICT )
                                print("went as far as: " + word)
                                return [False, DICT]
                        
        return [True, DICT]

    while True:
        newDICT = try_optimize(DICT)
        if newDICT[0]:
            break
        else:
            DICT = copy.deepcopy(newDICT[1])

    return DICT

def minimum_optimal_answer():
    SETS = []
    DICT = {}
    for word in KEYWORDS:
        DICT[word] = Word(word, "", "")

    for word in DICT:
        for newParent in find_all_branches(word):
            if newParent in KEYWORDS:
                DICT[word].links.add(newParent)

    for word in sorted(DICT):
        smth_happened = False

        for SET in SETS:
            if any(x in SET for x in DICT[word].links):
                SET.add(word)
                smth_happened = True
                break

        if not smth_happened:
            SETS.append({word})

    while len(SETS) != 1:
        # solve this
        break

def write_final_path(chemin):

    #   write the full path to result.txt
    #   recalculate the UNDOs itself

    with open('result.txt', 'w') as file:
        i = 0
        j = 2
        for index, item in enumerate(chemin):
            
            backtrack = False

            if item == chemin[index-j]:
                i -= 1
                j += 2
                backtrack = True
            else:
                j = 2

            if backtrack:
                cache_j = j
                while cache_j>2:
                    file.write(">")
                    cache_j -= 2
            if item in KEYWORDS:
                file.write(item.upper() + " " + str(i))
            else:
                file.write(item + " " + str(i))
            
            
            file.write("\n")
            i += 1

def csv_to_path(filename = "smallestSET"):
    DICT = import_csv_to_DICT(filename)
    result = "WORM 0 \nWORD 1\nWARD 2 \nDRAW 3\n"

    chemin = ["worm", "word", "ward", "draw"]
    live_chemin = ["worm", "word", "ward", "draw"]
    count = 3

    DICT["worm"].children.discard("word")
    DICT["word"].children.discard("ward")
    DICT["ward"].children.discard("draw")

    while not all(x in chemin for x in KEYWORDS):
        while len(DICT[chemin[-1]].children) > 0 and sorted(DICT[chemin[-1]].children)[0]!="":
            live_chemin.append( sorted(DICT[chemin[-1]].children)[0] ) #GO DEEPER
            chemin.append( sorted(DICT[chemin[-1]].children)[0] ) #GO DEEPER
            count+=1
            if DICT[chemin[-1]].isKeyWord():
                result += chemin[-1].upper() + " " + str(count) + "\n"
            else:
                result += chemin[-1] + " " + str(count) + "\n"

            DICT[chemin[-2]].children.remove(chemin[-1])

        #we reached an impasse
        index = -1
        while len(DICT[live_chemin[-1]].children) == 0 or sorted(DICT[live_chemin[-1]].children)[0]=="":    # DICT[chemin[index-1]].children.remove(chemin[index])
            index -= 2
            live_chemin.pop(-1)
            chemin.append(live_chemin[-1])
            for i in range(-int(index/2)):
                result += ">"
            if DICT[chemin[-1]].isKeyWord():
                result += chemin[-1].upper() + " " + str(count) + "\n"
            else:
                result += chemin[-1] + " " + str(count) + "\n"

    # result = "\n".join(chemin)
    # write_final_path(chemin)
    with open("result.txt", 'w') as file:
        file.write(result)

def import_cam_txt_DICT(filename):
    with open(filename, 'r') as file:
        data = file.read()
        data = data.split("\n")
        DICT = {}
        for index,array in enumerate(data):
            if array != '':
                array = array.split(" ")
                word = array[0].lower()
                if word not in DICT:
                    if len(DICT)<1:
                        DICT[word] = Word(word,"")
                    else:
                        if word not in DICT:
                            DICT[word] = Word(word, data[index-1].split(" ")[0].lower())

                if len(DICT)>1:
                    if "<" not in array[1]:
                        DICT[data[index-1].split(" ")[0].lower()].children.add(word)
    return DICT

# write_csv_of_Words(find_big_SET())

# write_DICT_to_csv(try_all_greedy_changes(import_csv_to_DICT("myOwn_183")))

# write_DICT_to_csv(try_all_greedy_changes(import_txt_DICT("result.txt")))

csv_to_path()
# import_txt_DICT("cam-result-182.txt")

# import_csv_SET()


# CHECK IF ALL WORDS ARE THERE: all(x in DICT for x in KEYWORDS)