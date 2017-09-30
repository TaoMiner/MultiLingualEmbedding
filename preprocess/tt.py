#!/usr/bin/env python
# -*- coding: utf-8 -*-
import codecs
import re
import jieba
import nltk
import pandas as pd
import numpy as np
# from stanfordcorenlp import StanfordCoreNLP

'''
nlp = StanfordCoreNLP(r'/Users/ethan/GitHub/others/py_corenlp/stanford-corenlp_37/')

props={'annotators': 'tokenize,lemma','pipelineLanguage':'en','outputFormat':'text'}
sentence = "We don't live here."
print nlp.annotate(sentence, properties=props)
'''
df = pd.DataFrame({'A' : ['foo', 'bar', 'foo', 'bar',\
                          'foo', 'bar', 'foo', 'foo'],\
                   'B' : ['one', 'one', 'two', 'three',\
                                  'two', 'two', 'one', 'three'],\
                   'C' : np.random.randn(8),\
                   'D' : np.random.randn(8)})

print df

grouped = df.groupby('A')

for name, group in grouped:
    print name
    print group