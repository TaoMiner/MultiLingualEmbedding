#!/usr/bin/env python
# -*- coding: utf-8 -*-
import codecs
import re
import jieba
import nltk
# from stanfordcorenlp import StanfordCoreNLP

'''
nlp = StanfordCoreNLP(r'/Users/ethan/GitHub/others/py_corenlp/stanford-corenlp_37/')

props={'annotators': 'tokenize,lemma','pipelineLanguage':'en','outputFormat':'text'}
sentence = "We don't live here."
print nlp.annotate(sentence, properties=props)
'''
ss = [0,1,2,3,4]
ss.insert(6,5)
print ss