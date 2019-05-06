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

The tree is then traversed post order and these rules are used as keys into the python dictionary called rules on line 39.
The rules dictionary uses rules as keys and lambda functions as values.
The algorithm traverses post order and and gets the lambda function for each corresponding tree, and then evaluates and stores
the result in the sem variable, for example:
```
<QUESTION> Is Kubrick a director?
***********traverse_tree***********
            ROOT                 
             |                    
             SQ                  
  ___________|_________________   
 |     NP         NP           | 
 |     |      ____|_____       |  
VBZ   NNP    DT         NN     . 
 |     |     |          |      |  
 Is Kubrick  a       director  ? 

**********rules from tree***********
ruleKey: ROOT->SQ,
            ROOT                 
             |                    
             SQ                  
  ___________|_________________   
 |     NP         NP           | 
 |     |      ____|_____       |  
VBZ   NNP    DT         NN     . 
 |     |     |          |      |  
 Is Kubrick  a       director  ? 

ruleKey: SQ->VBZ,NP,NP,.,
             SQ                 
  ___________|________________   
 |     NP        NP           | 
 |     |      ___|_____       |  
VBZ   NNP    DT        NN     . 
 |     |     |         |      |  
 Is Kubrick  a      director  ? 

ruleKey: NP->NNP,
   NP  
   |    
  NNP  
   |    
Kubrick

ruleKey: NP->DT,NN,
     NP         
  ___|_____      
 DT        NN   
 |         |     
 a      director

*********custom tree traversal**********
VBZ->Is
node.sem if in dictionary:  SELECT * 
NP->NNP,
node.sem if in dictionary:  Kubrick
NN->director
node.sem if in dictionary:  <function <lambda>.<locals>.<lambda> at 0x120f89f28>
NP->DT,NN,
node.sem if in dictionary:  <function <lambda>.<locals>.<lambda> at 0x120f89f28>
SQ->VBZ,NP,NP,.,
node.sem if in dictionary:  SELECT * FROM Director, Person WHERE Director.director_id = Person.id AND Person.name LIKE '%Kubrick%';
ROOT->SQ,
node.sem if in dictionary:  SELECT * FROM Director, Person WHERE Director.director_id = Person.id AND Person.name LIKE '%Kubrick%';
<QUERY>
SELECT * FROM Director, Person WHERE Director.director_id = Person.id AND Person.name LIKE '%Kubrick%';
<ANSWER> Yes
```

# Requirements:
Java 8 or greater
python 3
pip3

download and install 
the following python modules:
-gensim
-nltk
-pycorenlp  --  install this with the following command: pip3 install pycorenlp
pip install pytest

download the Stanford CoreNLP server:
https://stanfordnlp.github.io/CoreNLP/index.html#download
extract the zip and cd to the folder it creates.
then inside of this new directory start the server with this command:
java -mx4g -cp "*" edu.stanford.nlp.pipeline.StanfordCoreNLPServer -annotators "tokenize,ssplit,pos,lemma,parse,sentiment" -port 9000 -timeout 30000
