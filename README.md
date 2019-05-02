# askIMDB
askIMDB uses Natural Language Processing theory and the Stanford CoreNLP to provide a question answer interface 
for questions that can be answered by retrieving data from the IMDB sqlite database.

# Supported Types of Questions:
Is insert name here a director?
Was insert name here born in <insert place of birth here>?

The Algorithm uses Stanford CoreNLP in Python to produce a parse tree that taggs the input sentance, for example:
```
ROOT                 
             |                    
             SQ                  
  ___________|_________________   
 |     NP         NP           | 
 |     |      ____|_____       |  
VBZ   NNP    DT         NN     . 
 |     |     |          |      |  
 Is Kubrick  a       director  ?
```
Then this tree is converted into another tree of the same structure, but comprised of the nodes of custom class, Node, which stores additional information:

```
class Node:
    def __init__(self, children, word, pos):
        self.children = []
        self.word = word  # empty unless you're a leaf
        self.pos = pos #POS = Part of Speach 
        self.sem = "" #semantic meaning - either a SQL string or a Python lambda function
        self.rule = "" #The grammar rule of the form pos->[*children POS]

    def addChild(self, newChild):
        self.children.append(newChild)
```

The rule variables in the node class when traversitng this tree in order will be:
```
ruleKey:  ROOT->SQ, 
ruleKey:  SQ->VBZ, NP, NP, ., 
ruleKey:  VBZ->Is
ruleKey:  NP->NNP, 
ruleKey:  NNP->Kubrick
ruleKey:  NP->DT, NN, 
ruleKey:  DT->a
ruleKey:  NN->director
ruleKey:  .->?
```
