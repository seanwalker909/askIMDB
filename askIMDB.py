import nltk
from gensim.models import Word2Vec
from gensim.models import KeyedVectors
from nltk.corpus import treebank
from nltk.parse import CoreNLPParser
from nltk.tree import *
import pprint
from pycorenlp import StanfordCoreNLP
import sys
import sqlite3
import pytest

debugMode = 0

#function to store queries from input.txt file
def readInputFile():
    queries = []
    with open(sys.argv[1], 'r') as f:
        for line in f:
            line = line.rstrip("\n")
            queries.append([line])
    return queries


class Node:
    def __init__(self, children, word, pos):
        self.children = []
        self.word = word  # empty unless you're a leaf
        self.pos = pos
        self.sem = ""
        self.rule = ""

    def addChild(self, newChild):
        self.children.append(newChild)

rules = {
    "CD->": lambda x : x,
    "IN->by": lambda x : lambda movieName: lambda personName: "FROM Movie JOIN Director ON Director.movie_id = Movie.id join Person on Person.id = Director.director_id WHERE Person.name LIKE '%" + movieName + "%' AND Movie.name LIKE '%" + personName + "%';",
    "IN->in": lambda x: x,
    "IN->with": lambda x : "",
    "IN->for": lambda x : "",
    "NN->director": lambda x: lambda y: "FROM Director, Person WHERE Director.director_id = Person.id AND Person.name LIKE '%" + y + "%';",
    "NN->film": lambda x : "BEST-PICTURE",
    "NN->actress" : lambda x : "BEST-ACTRESS",
    "JJ->French" : lambda x : "France",
    "JJS->best": lambda x : lambda year : lambda oscarType : lambda movieName : "FROM Movie Join Oscar on Oscar.movie_id = Movie.id WHERE Movie.name LIKE '%" + movieName + "%' AND Oscar.type LIKE '%" + year + "%' AND Oscar.year LIKE '%" + oscarType + "%';", #birdman
    "NN->movie": lambda x: "BEST-PICTURE",
    "NP->CD,": lambda x : x, #birdman
    "NP->DT,JJS,NN,": lambda a,b,c : b(c), #birdman
    "NP->DT,JJ,NN,": lambda dt, jj, nn : lambda x : jj,
    "NP->DT,NN,": lambda a, b: b,
    "NP->JJS,NN,": lambda x, y : y,
    "NP->NNP,": lambda a: a,
    "NP->NNP,POS," : lambda a, dummyVar : a,
    "NP->NP,NN," : lambda a, dummyVar : a,
    "NP->NP,PP,": lambda uselessVar, uselessVar2: uselessVar2 if type(uselessVar2) is str else lambda x : uselessVar2(uselessVar), #Did Swank win the oscar in 2000?, is the shining by kuberick
    "NP->VBG," : lambda x : x,
    "PP->IN,NP,": lambda a, b: b if a is "" else a(b), #birdman, Neeson star in Schindler b, movie with Neeson win
    "PP->NP,PP,": lambda fromJoin, year : fromJoin(year), #birdman
    "ROOT->SBARQ," : lambda x : x,
    "S->VP,": lambda x : x,
    "S->S,VP,.,": lambda x,y,z: "SELECT * " + y(x),
    "SBARQ->WHNP,SQ,.," : lambda a, b, periodDummyVar : a + b,
    "SBARQ->WHADVP,SQ,.," : lambda a,b,c : a + b,
    "SQ->VBZ,NP,NP,.,": lambda select, frm, where, z: select + where(frm),
    "SQ->VBD,NP,VP,": lambda a,b,c : a + c(b),
    "SQ->VBD,NP,VP,.,": lambda a, b, c, d: a + c(b), #Neeson star in Schindler, loren
    "SQ->VBD,NP,PP,.,": lambda a, b, c, d : a + c(b), #birdman, loren
    "SQ->VP," : lambda x : x,
    "VB->star" : lambda uselessVar : lambda movieName : lambda personName : "FROM Actor JOIN Movie ON Movie.id = Actor.movie_id JOIN Person on Person.id = Actor.actor_id WHERE Movie.name LIKE '%" + movieName + "%' AND Person.name LIKE '%" + personName + "%';",
    "VB->win" : lambda uselessVar : lambda year : lambda name : "FROM Actor JOIN Movie ON Movie.id = Actor.movie_id JOIN Person on Person.id = Actor.actor_id JOIN Oscar on Oscar.movie_id = Movie.id WHERE Oscar.year LIKE '%" + year + "%' AND Person.name LIKE '%" + name + "%';" if type(name) is str else "FROM Actor JOIN Movie ON Movie.id = Actor.movie_id JOIN Person on Person.id = Actor.actor_id JOIN Oscar on Oscar.movie_id = Movie.id WHERE Oscar.year = '" + year + "' AND Person.pob LIKE '%" + name("") + "%';",
    "VBP->win" : lambda x : lambda oscarType : lambda personName : "FROM Oscar JOIN Movie ON Movie.id = Oscar.movie_id JOIN Actor ON Actor.movie_id = Movie.id JOIN Person ON Person.id = Actor.actor_id WHERE Person.name LIKE '%" + personName + "%' AND Oscar.type LIKE '%" + oscarType + "%';",
    "VBD->Did" : lambda x : "SELECT * ",
    "VBD->Was": lambda x: "SELECT * ",
    "VBD->directed" : lambda dummyVar : lambda movieName : "FROM Person JOIN Director ON Person.id = Director.director_id JOIN Movie ON Movie.id = Director.movie_id WHERE Movie.name LIKE '%" + movieName + "%';",
    "VBD->won" : lambda x, y : "FROM Oscar JOIN Movie ON Movie.id = Oscar.movie_id JOIN Actor ON Actor.movie_id = Movie.id JOIN Person ON Person.id = Actor.actor_id WHERE Oscar.year = '" + x + "' AND Oscar.type LIKE '%" + y + "%' AND Person.id = Oscar.person_id;",
    "VBN->born": lambda uselessVariable: lambda pob: lambda name: "FROM Person WHERE pob LIKE '%" + pob + "%' AND Name LIKE '%" + name + "%';",
    "VBZ->Is": lambda x: "SELECT * ",
    "VBD->did" : lambda x : "",
    "VP->VB,PP," : lambda frm, name: frm(name), #Neeson star in Schindler
    "VP->VB,NP," : lambda x, y : x(y),
    "VP->VBN,PP,": lambda x, y: x(y),
    "VP->VBP,NP,": lambda x, y: x(y),
    "WHNP->WP," : lambda x : x,
    "WHADVP->WRB," : lambda x : x,
    "WRB->When" : lambda x : "SELECT Oscar.year ",
    "ROOT->SQ,": lambda a: a,
    "ROOT->S,": lambda x : x,
    "VP->VBD,NP," : lambda a, b : a(b),
    "VP->VBD,NP,PP," : lambda x,y,z : z,
    "VP->VBD,NP,PP,PP," : lambda a,b,c,d : a(c,d),
    "WP->Who" : lambda x : "SELECT Person.name "
}

#select count(*) from Director join Person on Person.id = Director.director_id where Person.name like "%Kubrick%";
#SELECT COUNT(*) FROM Person WHERE pob LIKE '%Italy%' AND Name LIKE '%Loren%';

#function to get just the tag or word from the an NLTK tree node


def getRootString(tree):
    treeString = str(tree).split(" ")
    root = str(treeString[0])
    root = root.replace('(', '')
    root = root.replace(' ', '')
    root = root.replace(')', '')
    root = root.replace(',', '')
    root = root.replace('\n', '')
    root.strip()
    return root


def checkIfLeaf(node):
    if len(node.children) is 1 and len(node.children[0].children) is 0:
        return True
    else:
        return False


def isNLTKTreeLeaf(tree):
    isLeaf = False
    x = 0
    for subtree in tree:
        if type(subtree) == str:
            isLeaf = True
        x = x + 1
    return isLeaf and (x is 1)

def _buildSemanticTree(tree, curr):
    ruleKey = getRootString(tree) + "->"
    if isNLTKTreeLeaf(tree):
        ruleKey = ruleKey + str(tree).split(" ")[2].replace('(', '').replace(')', '').replace(' ', '')
        child = Node([], getRootString(tree[0]), "")
        curr.addChild(child)
        # print("printing ruleKey in if: ", ruleKey)
    else:
        for subtree in tree:  # get all of curr's children's pos tags to form the rule 
            ruleKey = ruleKey + getRootString(subtree) + ", "
            child = Node([], "", getRootString(subtree))
            curr.addChild(child)
    curr.rule = ruleKey.replace(" ", "")
    if debugMode:
        print("ruleKey:", curr.rule)

    i = 0  # for indexing the child list in the Node class
    for subtree in tree:
        if not isNLTKTreeLeaf(subtree):
            _buildSemanticTree(subtree, curr.children[i])
        else:
            word = str(subtree).split(" ")[1].replace('(', '').replace(')', '')
            curr.children[i].word = word
            curr.children[i].rule = getRootString(subtree) + "->" + word
            # print("ruleKey: ", curr.children[i].rule)
        i = i + 1

def buildSemanticTree(tree):
    root = Node([], "", getRootString(tree))
    _buildSemanticTree(tree, root)
    return root

def build_SQL_query(node):
    for child in node.children:
        build_SQL_query(child)
    if node.rule in rules.keys():
        if debugMode:
            print(node.rule)
        lambdaFunction = rules[node.rule]
        args = []
        for child in node.children:
            args.append(child.sem)
        if len(args) is 0:
            args.append("")
        node.sem = lambdaFunction(*args)
        if debugMode:
            print("node.sem if in dictionary: ", node.sem)
    elif "NNP->" or "CD->" or "VBG->" in node.rule:
        node.sem = node.word
    # else:#no rule in dictionary just return the sem of the child through a lambda function
    #     print("no rule in dictionary")
    #     lambdaFunction = lambda x : x
    #     args = []
    #     for child in node.children:
    #         args.append(child.sem)
    #     if len(args) is 0:
    #         args.append("")
    #     node.sem = lambdaFunction(*args)

correctQueries = {
    "Was Loren born in Italy?": "SELECT * FROM Person WHERE pob LIKE '%Italy%' AND Name LIKE '%Loren%';",
    "Is Kubrick a director?" : "SELECT * FROM Director, Person WHERE Director.director_id = Person.id AND Person.name LIKE '%Kubrick%';",
    "Is Mighty Aphrodite by Allen?" : "SELECT * FROM Movie JOIN Director ON Director.movie_id = Movie.id join Person on Person.id = Director.director_id WHERE Person.name LIKE '%Allen%' AND Movie.name LIKE '%Aphrodite%';",
    "Who directed Schindler’s List?" : "SELECT Person.name FROM Person JOIN Director ON Person.id = Director.director_id JOIN Movie ON Movie.id = Director.movie_id WHERE Movie.name LIKE '%Schindler%';",
    "Was Birdman the best movie in 2015?" : "SELECT * FROM Movie Join Oscar on Oscar.movie_id = Movie.id WHERE Movie.name LIKE '%Birdman%' AND Oscar.type LIKE '%BEST-PICTURE%' AND Oscar.year LIKE '%2015%';",
    "Did Neeson star in Schindler’s List?" : "SELECT * FROM Actor JOIN Movie ON Movie.id = Actor.movie_id JOIN Person on Person.id = Actor.actor_id WHERE Movie.name LIKE '%Schindler%' AND Person.name LIKE '%Neeson%';",
    "Did Swank win the oscar in 2000?" : "SELECT * FROM Actor JOIN Movie ON Movie.id = Actor.movie_id JOIN Person on Person.id = Actor.actor_id JOIN Oscar on Oscar.movie_id = Movie.id WHERE Oscar.year LIKE '%2000%' AND Person.name LIKE '%Swank%';",
    "Is the Shining by Kubrik?" : "SELECT * FROM Movie JOIN Director ON Director.movie_id = Movie.id join Person on Person.id = Director.director_id WHERE Person.name LIKE '%Kubrik%' AND Movie.name LIKE '%Shining%';",
    "Did a French actor win the oscar in 2012?" : "SELECT * FROM Actor JOIN Movie ON Movie.id = Actor.movie_id JOIN Person on Person.id = Actor.actor_id JOIN Oscar on Oscar.movie_id = Movie.id WHERE Oscar.year = '2012' AND Person.pob LIKE '%France%';",
    "Did a movie with Neeson win the oscar for best film?" : "SELECT * FROM Oscar JOIN Movie ON Movie.id = Oscar.movie_id JOIN Actor ON Actor.movie_id = Movie.id JOIN Person ON Person.id = Actor.actor_id WHERE Person.name LIKE '%Neeson%' AND Oscar.type LIKE '%BEST-PICTURE%';",
    "Who won the oscar for best actor in 2005?" : "SELECT Person.name FROM Oscar JOIN Movie ON Movie.id = Oscar.movie_id JOIN Actor ON Actor.movie_id = Movie.id JOIN Person ON Person.id = Actor.actor_id WHERE Oscar.year = '2005' AND Oscar.type LIKE '%BEST-ACTOR%' AND Person.id = Oscar.person_id;",
    "Who directed Hugo?" : "SELECT Person.name FROM Person JOIN Director ON Person.id = Director.director_id JOIN Movie ON Movie.id = Director.movie_id WHERE Movie.name LIKE '%Hugo%';",
    "When did Blanchett win an oscar for best actress?" : "SELECT * from Oscar JOIN Person ON Person.id = Oscar.person_id JOIN Movie ON Movie.id = Oscar.movie_id JOIN Actor on Actor.actor_id = Person.id WHERE Person.name LIKE '%Blanchett%' AND Oscar.type = 'BEST-ACTRESS' AND Actor.movie_id = Oscar.movie_id;"
}

def checkIfCorrectQueryWasBuilt(question, query):
    assert correctQueries[question[0]] == query

def answerQuestion(questions, DBconnection, parser):
    for q in questions:
        print("<QUESTION>", q[0])

        text = q[0]

        output = parser.annotate(text, properties={
            'annotators': 'tokenize,ssplit,pos,depparse,parse',
            'outputFormat': 'json'
        })

        a = [s['parse'] for s in output['sentences']]
        
        if debugMode:
            print("***********traverse_tree***********")
            Tree.fromstring(a[0]).pretty_print()
        if debugMode:
            print("**********rules from tree***********")
        customTreeRoot = buildSemanticTree(Tree.fromstring(a[0]))
        if debugMode:
            print("*********custom tree traversal**********")
        build_SQL_query(customTreeRoot)
        print("<QUERY>")
        SQLQuery = customTreeRoot.sem
        print(SQLQuery)

        # checkIfCorrectQueryWasBuilt(q, SQLQuery)
        print("<ANSWER> ", end="")
        DBconnection.execute(SQLQuery)
        all_rows = DBconnection.fetchall()
        if q[0][0:3] == "Is " or q[0][0:3] == "Did" or q[0][0:3] == "Was":
            if(all_rows):
                print("Yes")
            else:
                print("No")
        else:
            for row in all_rows:
                print(str(row).replace("(", "").replace(")", "").replace(",", "").replace("'", ""))



def main():
    questions = readInputFile()

    # , ["Is Kubrick a director?"], ["Was Loren born in Italy?"], ["Is Mighty Aphrodite by Allen?", ["Is the Shining by Kubrik?"]]
    #questions = [["Did Swank win the oscar in 2000?"]]
    parser = StanfordCoreNLP('http://localhost:9000')

    conn = sqlite3.connect("oscar-movie_imdb.sqlite")
    c = conn.cursor()

    answerQuestion(questions, c, parser)

    conn.close()

if __name__ == "__main__":
    main()
