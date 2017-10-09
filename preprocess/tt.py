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
punc = re.compile('^[{0}]+$'.format(re.escape(string.punctuation)))
print '[{0}]+'.format(re.escape(string.punctuation))

s = "'s"

m = punc.match(s)

if m:
    print "match!"
