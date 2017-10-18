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

a = [2,3,1]

a.sort(key=lambda x:x, reverse=True)

print a