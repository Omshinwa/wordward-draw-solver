from common import find_all_branches
from a_program_to_beat_cam import write_DICT_to_csv, try_all_greedy_changes
def populate(parent):
    #   populate a single node (*parent*) of the *tree* dictionary using *find_all_branches()*
    for word in find_all_branches(parent):
        if word not in tree:
            tree[word] = {"step":tree[parent]["step"] + 1, "searched":False, "parent":parent}
        elif tree[word]["step"] > tree[parent]["step"] + 1:
            tree[word]["step"] = tree[parent]["step"] + 1
            tree[word]["parent"] = parent

def populate_with_undo(parent):
    #   same as above, but if the parent appears as *chemin[-2 - parent's undo]*:
    #   give the node the parent's undo attribute minus 2
    global chemin
    for word in find_all_branches(parent):
        if word not in tree:
            tree[word] = {"step":tree[parent]["step"] + 1, "searched":False, "parent":parent, "undo":0}
            if len(chemin) > -(tree[parent]["undo"]-1) and chemin[tree[parent]["undo"]-2] == word:
                tree[word]["undo"] = tree[parent]["undo"]-2
                # recently changed from tree[word]["undo"] = tree[parent]["undo"]-1
                # maybe bug
        elif tree[word]["step"] > tree[parent]["step"] + 1:
            tree[word]["step"] = tree[parent]["step"] + 1
            tree[word]["parent"] = parent

def word_with_the_lowest_step_not_searched_yet():
    #   return which node to populate in the *tree* 
    #   this one looks for the closest one (if tied, last in the list)
    min_step = float('inf')
    min_step_key = None

    for key, value in tree.items():
        if not value["searched"] and value["step"] < min_step:
            min_step = value["step"]
            min_step_key = key

    # Check if there is a key with "searched" equal to True
    if min_step_key is not None:
        return min_step_key
    else:
        print("tree size: " + str(len(tree)))
        raise ValueError ("Searched the whole available tree.")

def word_with_the_lowest_step_not_searched_yet_with_undo():
    #   return which node to populate in the *tree* 
    #   this one looks for the closest one TAKING UNDOS in account
    min_step = float('inf')
    min_step_key = None

    for key, value in tree.items():
        if not value["searched"] and value["step"]+value["undo"] < min_step:
            min_step = value["step"] + value["undo"]
            min_step_key = key

    if min_step_key is not None:
        return min_step_key
    else:
        print("tree size: " + str(len(tree)))
        raise ValueError ("Searched the whole available tree.")

def find_shortest_path(start, end):
    #   return the shortest path between two words
    #   could be optimized, rn it only expands from the start node until it finds the end node, but it would be faster to expands from both sides imo
    #   doesnt use UNDOs
    global tree
    tree = {}
    tree[start] = {"step":0, "searched":False}
    step = 0
    while (end not in tree): # or step < 500
        word = word_with_the_lowest_step_not_searched_yet()

        populate(word)
        tree[word]["searched"] = True
        step += 1

    #when it has found a path:
    word = end
    path = []
    while word != start:
        path.append(word)
        word = tree[word]["parent"]

    # path = path
    return list(reversed(path))

def find_shortest_path2(start, list_of_words):
    #   find the shortest path between two words, and returns the result in the global var chemin
    #   use UNDOs
    #   could be optimized
    #   idk it's doing some weird recursive shit, needs some debugging
    global chemin
    global tree
    tree = {}
    
    if len(list_of_words) == 0:
        write_final_path(chemin)
        return

    todo = list_of_words.copy()
    tree[start] = {"step":0, "searched":False, "undo":0}
    step = 0

    while (len(todo) > 0): # or step < 500

        if len(tree) == 0:
            # print(todo)
            break

        word = word_with_the_lowest_step_not_searched_yet_with_undo()

        populate_with_undo(word)
        tree[word]["searched"] = True
        step += 1

        for index,current_word in enumerate(todo):
            
            if len(todo) == 0:
                break

            if current_word in tree:
                todo.pop(index)
                path = []
                wordz = current_word
                while wordz != start:
                    path.append(wordz)
                    wordz = tree[wordz]["parent"]
                # path.append(start)
                chemin = chemin + list(reversed(path))
                # chemin = chemin + find_shortest_path2(current_word, todo)
                find_shortest_path2(current_word, todo)

    write_final_path(chemin)

def FINAL_PATH(start):

    #   finds the shortest path to finish the game, no cache
    #   
    #   input: word to start
    #   KEYWORDS = shorter_list.txt

    global chemin
    my_file = open("shorter_list.txt", "r")
    data = my_file.read()
    KEYWORDS = data.split("\n")
    my_file.close()

    print(KEYWORDS)
    find_shortest_path2(start, KEYWORDS)
    write_final_path(chemin)

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

#from here on out, we use cached results

def CALCULATE_ALL_COMBINAISONS(start, numberOfWordsToDo = 1):

    # calculate shortest path between pairs of picture words
    # cache the file in tableur.csv
    
    shortest_path_for_pairs = {}

    my_file = open("list_combinaison.txt", "r")
    data = my_file.read()
    liste_de_mots = data.split("\n")
    my_file.close()

    result = "sep=,\n"
    result += " ,"
    for word in liste_de_mots:
        result += word + ","
    result += "\n"

    numberOfWords = 0
    for index, word in enumerate(liste_de_mots):
        if word<start:
            continue
        if numberOfWords>=numberOfWordsToDo:
            break
        print( "---- " + word + " ----")
        numberOfWords+=1

        result += word + ","

        for index2, word2 in enumerate(liste_de_mots):
            print( "index " + str(index2) + " " + word2)
            # if frozenset({word, word2}) in shortest_path_for_pairs:
            #     pass
            if index>=index2:
                result += ""
            else:
                shortest_path_for_pairs[frozenset({word, word2})] = find_shortest_path(word, word2)
                distance = shortest_path_for_pairs[frozenset({word, word2})]
                result += str(len(distance)) + " : " + "-".join(distance)
            result += ","
        
        result += "\n"

        if numberOfWords%5 == 4:
            with open('tableur.csv', 'w') as file:
                file.write(result)
        # Open the file in write mode (this will overwrite the file)
    with open('tableur.csv', 'w') as file:
        file.write(result)

def debug_are_all_words_in_dictionary():
    # check if all the words in shorter_list.txt are in the dictionary
    my_file = open("shorter_list.txt", "r")
    data = my_file.read()
    KEYWORDS = data.split("\n")
    my_file.close()
    for word in KEYWORDS:
        if word in dictionary:
            pass
        else:
            print("cant find " + word)
    return print("done!")

def clean_csv():

    # take tableur.csv, generate tableur_clean.csv which only keeps the numbers and mirror the results

    my_file = open("tableur_archive.csv", "r")
    csv_data = my_file.read()

    import re

    # Function to extract numbers from a cell
    def extract_numbers(cell):
        if len(cell)>0 and cell[0].isdigit():
            cell = [int(number) for number in re.findall(r'\b\d+\b', cell)]
            if len(cell) == 1:
                return cell[0]
        else:
            return cell

    csv_rows = csv_data.split('\n')

    for index, row in enumerate(csv_rows):
        csv_rows[index] = row.split(';')

    print(csv_rows[0])

    for index, row in enumerate(csv_rows):

        if len(row) > 1:
            row[1:] = [extract_numbers(cell) for cell in row[1:]]
        
        for index2, cell in enumerate(row):
            if index>index2 and index2>0:
                if len(csv_rows[index2])>index:
                    row[index2] = csv_rows[index2][index]
                    # row[index2] = str(index) + " : " + str(index2)

    output_csv = "\n".join([";".join(map(str, row)) for row in csv_rows])

    # print(output_csv)
    with open('tableur_clean.csv', 'w') as file:
        file.write(output_csv)


# KEYWORDS from shorter_list.txt
with open("v0.5/all_picture_words_minus_two.txt", "r") as file:
    data = file.read()
    KEYWORDS = data.split("\n")

# read data from tableur_clean.csv with pairs_data[ligne][colonne]
with open("v0.5/path_between_keywords.csv", "r") as file:
    data = file.read()
    pairs_data = data.split("\n")

    for index, row in enumerate(pairs_data):
        pairs_data[index] = row.split(';')

# list_combinaison from list_combinaison.txt, list_combinaison includes "draw" contrary to KEYWORDS
with open("v0.5/list_combinaison.txt", "r") as file:
    data = file.read()
    word_to_id = {}
    for index, line in enumerate(data.split('\n')):
        word_to_id[line] = index

    list_combinaison = data.split('\n')
      
def read_path_between(word1, word2):
    # using cached results, give us the length of the shortest pass (without undos)  
    string = pairs_data[word_to_id[word1]+1][word_to_id[word2]+1]
    if string == '':
        return 0
    else:
        return int(string)

def variance_of_static(word):
    # calculate the variance of a picture word using cached results
    return float(pairs_data[106][word_to_id[word]+1].replace('"', '').replace(',', '.'))

def variance_of(word, mean, todo=list_combinaison):
    # recalculate the variance of a picture word by removing words already passed through from the list
    sum = 0
    population = 0
    for i in range(105):
        if i>0:
            key = pairs_data[0][i]
            value = get_path_from_to(key, word)[0]

            if key in todo and value != '':
                sum += (int(value) - mean)**2
                population += 1
                pass

    if population == 0:
        return 0
    return sum/population

def average_of_static(word):
    # calculate the average of a picture word using cached results
    return float(pairs_data[107][word_to_id[word]+1].replace('"', '').replace(',', '.'))

def average_of(word, todo=list_combinaison):
    # recalculate the average of a picture word by removing words already passed through from the list
    sum = 0
    population = 0
    for i in range(105):
        if i>0:
            key = pairs_data[0][i]
            value = get_path_from_to(key, word)[0]
            if key in todo and value != '':
                sum += int(value)
                population += 1
                pass

    # print("sum: " + str(sum))
    # print("pop: " + str(population))

    if population == 0:
        return 0
    return sum/population

def correct_my_csv():
    # correct previos errors that was in my csv
    with open("tableur_archive.csv", "r") as file:
        data = file.read()
        tableau_archive = data.split("\n")

    for index, row in enumerate(tableau_archive):
        tableau_archive[index] = row.split(';')

    for index, cell in enumerate(tableau_archive):
        for index2, value in enumerate(cell):
            if len(value)>0 and index>0 and index2>0:
                # if int(value[0])<=1:
                #     if value[4:] == tableau_archive[0][index2] or value[4:] == cell[0]:
                #         continue
                # tableau_archive[index][index2] += "-" + tableau_archive[0][index]
                tableau_archive[index][index2] = tableau_archive[index][index2][:-4]
                tableau_archive[index][index2] += tableau_archive[0][index2]

    output_csv = "\n".join([";".join(map(str, row)) for row in tableau_archive])

    # print(output_csv)

    # Open the file in write mode (this will overwrite the file)
    with open('tableur_cleaner.csv', 'w') as file:
        file.write(output_csv)

def check_all_duplicates_in_result():
    # check if theres duplicate words (opportunities to UNDO missed)
    with open("result.txt", "r") as file:
        data = file.read()
        result = data.split("\n")

    for i, line in enumerate(result):
        result[i] = result[i].split(" ")[0]
    
    for word in result:
        compteur = result.count(word)
        if compteur > 1:
            print(word)
            for i, j in enumerate(result):
                if j == word:
                    print(i)

def CALCULATE_ALL_BRANCHES(start, end_branch = 1, numberOfWords_ToDo = 5):

    # calculate all posibilities words up to N for every word, ordered by steps
    # cache the file in tableur_branches.csv
    
    shortest_path_for_pairs = {}

    my_file = open("list_combinaison.txt", "r")
    data = my_file.read()
    liste_de_mots = data.split("\n")
    my_file.close()

    result = ""
    for index,word in enumerate(liste_de_mots):
        result += str(index) + ";"
    result += "\n"

    numberOfWords_Done = 0
    for index, word in enumerate(liste_de_mots):

        print(word)

        if word<start:
            continue

        if numberOfWords_Done>=numberOfWords_ToDo:
            break
        numberOfWords_Done+=1

        #words = [[0 step word], [1 step words], [2 step words], [3 step words], [4 step words]]
        WORDS_TO_ADD = [[word]]
        for i in range(end_branch):

            if i>0:
                WORDS_TO_ADD.append( [] )
                for current_word in WORDS_TO_ADD[i-1]:
                    temp_words_to_add = find_all_branches(current_word)

                    for temp_word in temp_words_to_add:
                        recursion = 1
                        already_exist = False
                        while i-recursion>=0:
                            if temp_word in WORDS_TO_ADD[i-recursion]:
                                already_exist = True
                                break
                            recursion += 1
                        if not already_exist:
                            if temp_word not in WORDS_TO_ADD[i]:
                                WORDS_TO_ADD[i].append(temp_word)

            # print(WORDS_TO_ADD)
        
            result += ",".join(WORDS_TO_ADD[i]) + ";"
        result += "\n"

        if index%5 == 4:
            with open('words_from_keywords.csv', 'w') as file:
                file.write(result)

    with open('words_from_keywords.csv', 'w') as file:
        file.write(result)

with open("v0.5/words_from_keywords.csv", "r") as file:
    data = file.read()
    cached_branches = data.split('\n')

    for index, row in enumerate(cached_branches):
        cached_branches[index] = row.split(';')
        
        for i, cell in enumerate(cached_branches[index]):
            cached_branches[index][i] = cell.replace('"', '').split(',')
      
def get_path_from_to(word1, word2):
    # using cached results, give us the length of the shortest pass (without undos)  
    string = pairs_data[word_to_id[word1]+1][word_to_id[word2]+1]
    
    if string == '':
        return (0, [])
    else:
        key = string.split(" : ")
        value = int(key[0]) # length of the path
        value_path_set = key[1].split("-") # the path in list format
        return (value, value_path_set)

def FINAL_PATH_ULTRA_MAX(start):
    # does its best
    global chemin
    global chemin_live

    def find_shortest_path3(start, list_of_words):
        global chemin
        global chemin_live
        tree = {}
        if len(list_of_words) == 0 :
            return []
        
        todo = list_of_words.copy()

        while (len(todo) > 0):

            target = word_with_highest_profit(chemin[-1], todo)

            if target[1] == None: # if there is no shortcut:
                end = target[0]

                path = find_shortest_path(chemin[-1], end)
                

            else: #there is a shortcut through target[1]
                end = target[0]
                shortcut = target[1]

                current_index = len(chemin_live)-2

                while chemin[-1] != shortcut:
                    chemin.append(chemin_live[current_index])
                    chemin_count.append(chemin_count[-1])
                    current_index-=1
                while chemin_live[-1] != shortcut:
                    chemin_live.pop(-1)

                path = find_shortest_path(shortcut, end)

            chemin += path
            for wordzz in path:
                if wordzz in chemin_live:
                    chemin_live.pop(-1)
                    chemin_count.append(chemin_count[-1])
                else:
                    chemin_live.append(wordzz)
                    chemin_count.append(chemin_count[-1]+1)

            for index, worz in enumerate(todo):
                    if worz == end:
                        todo.pop(index)
                        

    def cached_find_all_branches_from(endGoal, distance):
        # gives the list of words at X distance from *endGoal*
        return cached_branches[word_to_id[endGoal]+1][distance]


    def getLastTime(chemin_live, element_to_find):
        # return how long ago did an element appear from a history list
        my_list = chemin_live
        try:
            last_occurrence_index = len(my_list) - list(reversed(my_list)).index(element_to_find) - 1
            return len(my_list) -1 - last_occurrence_index
        except ValueError:
            print(f"{element_to_find} is not found in the list.")

    def word_with_highest_profit(start, todo=KEYWORDS):

        max_var = -999
        min_step_key = []

        for index, key in enumerate(todo):
            numberOfUndos = 0
            CHEMIN = get_path_from_to(start, key)
            value = CHEMIN[0]
            path = CHEMIN[1]

            isUndo = None
            for i in range(1, value):

                if isUndo != None:
                    break

                for minusStep,word in enumerate(path):
                    if i>minusStep:
                        if word in cached_find_all_branches_from(key, i-minusStep) and word in chemin_live:
                            isUndo = word
                            value = i
                            numberOfUndos = getLastTime(chemin_live,word)
                            break


            mean = average_of(key, todo)

            # profit = mean - float(value) - (variance_of(key, mean, todo)) + numberOfUndos/10
            
            # euristic #
            profit = mean - float(value) - (variance_of(key, mean, todo)) #193
            

            if profit > max_var:
                max_var = profit
                min_step_key= [ (key,isUndo) ]
            elif profit == max_var:
                min_step_key.append( (key,isUndo) )

        # in the scenario of a tie for the eval function:
        
        if len(min_step_key)==1:
            return min_step_key[0]
        elif len(min_step_key)>1:
            max_var = -999
            max_var_key = None

            for keys in min_step_key:
                key = keys[0]
                profit = - float(value)
                if profit >= max_var:
                    max_var = profit
                    max_var_key = (key,isUndo)
            return max_var_key

        else:
            raise ValueError ("No key found")

    
    find_shortest_path3(start, KEYWORDS)

    write_DICT_to_csv(try_all_greedy_changes(createDICT_from_chemin(chemin)))

    write_final_path2(chemin)

def write_csv_of_DICT(DICT, filename = "smallestSET"):
    
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

class Word:
    def __init__(self, word, parent, children=""):
        self.word = word
        self.parent = parent
        self.children = set(children) # if it has no children, it's an end node
        self.propagated = False

    def __repr__(self) -> str:
        return self.word
    
    def __lt__(self,other): #this makes operation with '<' possible, and so sorting cards are by names.
        return self.word<other.word

    def isKeyWord(self):
        return self.word in KEYWORDS
    
def createDICT_from_chemin(chemin):
    DICT = {}
    for index, i in enumerate(chemin):
        if i.lower() not in DICT:
            if index>0:
                DICT[i.lower()] = Word(i.lower(), chemin[index-1].lower())
                DICT[chemin[index-1].lower()].children.add(i.lower())
            else:
                DICT[i.lower()] = Word(i.lower(), "")

    return DICT


def clean_csv2():

    # take tableur.csv, generate tableur_clean.csv which only keeps the numbers and mirror the results

    my_file = open("tableur_archive.csv", "r")
    csv_data = my_file.read()

    import re

    # Function to extract numbers from a cell
    def extract_numbers(cell):
        return cell

    csv_rows = csv_data.split('\n')

    for index, row in enumerate(csv_rows):
        csv_rows[index] = row.split(';')

    print(csv_rows[0])

    for index, row in enumerate(csv_rows):

        if len(row) > 1:
            row[1:] = [extract_numbers(cell) for cell in row[1:]]
        
        for index2, cell in enumerate(row):
            if index>index2 and index2>0:
                if len(csv_rows[index2])>index:
                    row[index2] = csv_rows[index2][index]

                    nStep = csv_rows[index2][index][:4]
                    path = csv_rows[index2][index][4:]
                    pathList = path.split("-")
                    pathList.pop(-1)
                    pathList.reverse()
                    pathList.append( csv_rows[0][index2] )

                    row[index2] = nStep + '-'.join(pathList)

    output_csv = "\n".join([";".join(map(str, row)) for row in csv_rows])

    # print(output_csv)
    with open('tableur_clean.csv', 'w') as file:
        file.write(output_csv)

def write_final_path2(chemin):

    #   write the full path to result.txt
    #   recalculate the UNDOs itself

    with open('result.txt', 'w') as file:
        backtrack = 0
        for index, item in enumerate(chemin):
            
            

            if index>1:
                if chemin_count[index] == chemin_count[index-1]:
                    backtrack += 1
                else:
                    backtrack = 0

            if backtrack>0:
                cache = backtrack
                while cache>0:
                    file.write(">")
                    cache -= 1
            if item in KEYWORDS:
                file.write(item.upper())
            else:
                file.write(item)

            file.write(" " + str(chemin_count[index]))
            file.write("\n")

import time
start_time = time.time()

tree = {}
chemin = ["WORM","WORD","WARD","draw"]
chemin_count = [0,1,2,3] # keep the step count
chemin_live = chemin.copy()

# find_shortest_path2("draw", list_of_words=KEYWORDS)

# average_of("acid")

# print( find_shortest_path("boll", "goat") )
# check_all_duplicates_in_result()

# CALCULATE_ALL_BRANCHES("chat", end_branch = 8, numberOfWords_ToDo = 100)

print(FINAL_PATH_ULTRA_MAX("draw"))

print("--- %s seconds ---" % (time.time() - start_time))


# print(find_all_branches("crew"))

# print(chemin)