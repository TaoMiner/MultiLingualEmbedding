#!/usr/bin/env python
# -*- coding: utf-8 -*-
import codecs
import re
import string
# from stanfordcorenlp import StanfordCoreNLP

'''
nlp = StanfordCoreNLP(r'/Users/ethan/GitHub/others/py_corenlp/stanford-corenlp_37/')

props={'annotators': 'tokenize,lemma','pipelineLanguage':'en','outputFormat':'text'}
sentence = "We don't live here."
print nlp.annotate(sentence, properties=props)
'''
for i in range(3):
    print i
    if i == 2:
        i = i - 1
