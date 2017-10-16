#!/usr/bin/env python
# -*- coding: utf-8 -*-
import codecs
import re
import string
from nltk.corpus import stopwords
from functools import cmp_to_key
# from stanfordcorenlp import StanfordCoreNLP

'''
nlp = StanfordCoreNLP(r'/Users/ethan/GitHub/others/py_corenlp/stanford-corenlp_37/')

props={'annotators': 'tokenize,lemma','pipelineLanguage':'en','outputFormat':'text'}
sentence = "We don't live here."
print nlp.annotate(sentence, properties=props)
'''

gamma = 0.1

b = [['25204117', 0.14814814814814814, 0.88074702722472553, 0.83709255326725329, 0.54181770782883032], ['189322', 0.37037037037037035, 0.88771092816823971, 0.88144302702310784, 0.54181770782883032], ['46765776', 0.25925925925925924, 0.89317344691872291, 0.88763913819752971, 0.54181770782883032]]

b.sort(key=lambda x : x[4] * x[3] * x[2] * (x[1] ** gamma), reverse = True)

print b