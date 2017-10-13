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
m = [[1],[2,3],[4]]


m.sort(key=cmp_to_key(lambda x, y: ((len(x) > len(y)) - (len(x) < len(y)))))


print m