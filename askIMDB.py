#Project Members:
#Sohum Mehrotra smehro2 661149644
#Sean Walker swalke30
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

#function to store queries from input.txt file
def readInputFile():
    queries = []
    print("Reading in input.txt file...")
    with open(sys.argv[1], 'r') as f:
        for line in f:
            line = line.rstrip("\n")
            queries.append([line])
    print("input.txt queries read...")
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
    #Is Kubrick a director?
    "ROOT->SQ,": lambda a: a,
    "SQ->VBZ,NP,NP,.,": lambda select, frm, where, z: select + where(frm),
    "VBZ->Is": lambda x: "SELECT * " + x,
    "NP->NNP,": lambda a: a,
    "NP->DT,NN,": lambda a, b: b,
    "NN->director": lambda x: lambda y: "FROM Director, Person WHERE Director.director_id = Person.id AND Person.name LIKE '%" + y + "%';",
    "NNP->*": lambda x: x,

    #Was Loren born in Italy?
    "SQ->VBD,NP,VP,.,": lambda a, b, c, d: a + c(b),
    "VBN->born": lambda uselessVariable: lambda pob: lambda name: "FROM Person WHERE pob LIKE '%" + pob + "%' AND Name LIKE '%" + name + "%';",
    "NNP->": lambda x: x,
    "PP->IN,NP,": lambda a, b: b if a is "" else a,
    "IN->in": lambda x: x,
    "VP->VBN,PP,": lambda x, y: x(y),
    "VBD->Was": lambda x: "SELECT COUNT(*) ",

    #Is Mighty Aphrodite by Allen?
    # select * from Actor join Person on Person.id = Actor.actor_id join Director on Director.director_id = Actor.actor_id where Director.director_id = Person.id and Person.name like '%Allen%';
    # SELECT * FROM Movie JOIN Director ON Director.movie_id = Movie.id join Person on Person.id = Director.director_id WHERE Person.name LIKE '%Allen%' AND Movie.name LIKE '%Mighty%' AND Movie.name LIKE '%Aphrodite%';
    #               ROOT
    #                |
    #                SQ
    #   _____________|____________________
    #  |    |               NP            |
    #  |    |         ______|___          |
    #  |    |        |          PP        |
    #  |    |        |       ___|____     |
    #  |    NP       NP     |        NP   |
    #  |    |        |      |        |    |
    # VBZ  NNP      NNP     IN      NNP   .
    #  |    |        |      |        |    |
    #  Is Mighty Aphrodite  by     Allen  ?
    "IN->by": lambda firstPartOfName : lambda secondPartOfName : "FROM Movie JOIN Director ON Director.movie_id = Movie.id join Person on Person.id = Director.director_id WHERE Person.name LIKE '%" + firstPartOfName + "%' AND Movie.name LIKE '%Mighty%' AND Movie.name LIKE '%" + secondPartOfName + "%';",
    "NP->NP,PP,": lambda uselessVar, uselessVar2 : lambda x : uselessVar2(uselessVar)
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
        ruleKey = getRootString(tree) + "->" + str(tree).split(" ")[2].replace('(', '').replace(')', '')
        child = Node([], getRootString(tree[0]), "")
        curr.addChild(child)
        print("printing ruleKey in if: ", ruleKey)
    else:
        for subtree in tree:  # traverse to generate grammar rules
            ruleKey = ruleKey + getRootString(subtree) + ", "
            child = Node([], "", getRootString(subtree))
            curr.addChild(child)
    curr.rule = ruleKey.replace(" ", "")
    print("ruleKey: ", ruleKey)

    i = 0  # for indexing the child list in the Node class
    for subtree in tree:
        if not isNLTKTreeLeaf(subtree):
            _buildSemanticTree(subtree, curr.children[i])
        else:
            word = str(subtree).split(" ")[1].replace('(', '').replace(')', '')
            curr.children[i].word = word
            curr.children[i].rule = getRootString(subtree) + "->" + word
            print("ruleKey: ", curr.children[i].rule)
        i = i + 1


def buildSemanticTree(tree):
    root = Node([], "", getRootString(tree))
    _buildSemanticTree(tree, root)
    return root


def traverse_custom_tree(node):
    for child in node.children:
        traverse_custom_tree(child)
    if node.rule in rules.keys():
        print(node.rule)
        lambdaFunction = rules[node.rule]
        args = []
        for child in node.children:
            args.append(child.sem)
        if len(args) is 0:
            args.append("")
        node.sem = lambdaFunction(*args)
        print("node.sem: ", node.sem)
    elif "NNP->" in node.rule:
        node.sem = node.word
    else:
        node.sem = node.word
        print(node.word)


def answerQuestion(questions, DBconnection, parser):
    for q in questions:
        print(q[0])

        text = q[0]

        output = parser.annotate(text, properties={
            'annotators': 'tokenize,ssplit,pos,depparse,parse',
            'outputFormat': 'json'
        })

        a = [s['parse'] for s in output['sentences']]
        print("printing a[0]")
        print(a[0])
        print("***********traverse_tree***********")
        Tree.fromstring(a[0]).pretty_print()
        print("**********rules from tree***********")
        customTreeRoot = buildSemanticTree(Tree.fromstring(a[0]))
        print("*********custom tree traversal**********")
        traverse_custom_tree(customTreeRoot)
        print("***********sql string***********")
        SQLQuery = customTreeRoot.sem
        print(SQLQuery)
        DBconnection.execute(SQLQuery)
        all_rows = DBconnection.fetchall()
        for row in all_rows:
            print(row)


def main():
    print("Project Initializing...")

    #questions = readInputFile()
    questions = [["Is Kubrick a director?"], ["Was Loren born in Italy?"], ["Is Mighty Aphrodite by Allen?"]]
    parser = StanfordCoreNLP('http://localhost:9000')

    conn = sqlite3.connect("oscar-movie_imdb.sqlite")
    c = conn.cursor()

    answerQuestion(questions, c, parser)

    conn.close()


if __name__ == "__main__":
    main()
