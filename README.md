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
Then this tree is converted into another tree of the same structure, but comprised of the custom nodes class
that stores additional information:

```
class Node:
    def __init__(self, children, word, pos):
        self.children = []
        self.word = word  # empty unless you're a leaf
        self.pos = pos
        self.sem = ""
        self.rule = ""

    def addChild(self, newChild):
        self.children.append(newChild)
```
