#!/usr/bin/env python
# -*- coding: utf-8 -*-
import codecs
import re
import string
from nltk.corpus import stopwords
# from stanfordcorenlp import StanfordCoreNLP

'''
nlp = StanfordCoreNLP(r'/Users/ethan/GitHub/others/py_corenlp/stanford-corenlp_37/')

props={'annotators': 'tokenize,lemma','pipelineLanguage':'en','outputFormat':'text'}
sentence = "We don't live here."
print nlp.annotate(sentence, properties=props)
'''
stop = set(stopwords.words('spanish'))
filename = '/Users/ethan/Downloads/es_stop_words'
with codecs.open(filename, 'w') as fout:
    for w in stop:
        w = w.encode('utf-8', 'ignore')
        fout.write("{0}\n".format(w))
