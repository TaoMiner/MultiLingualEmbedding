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
enlabel_re = re.compile(r'\\t\"(.*?)\"@en$')
s = 'sfg    "Heilongjiang"@en'
m = enlabel_re.search(s)
if m!= None:
    print m.group(1)