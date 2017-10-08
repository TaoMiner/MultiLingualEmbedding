#!/usr/bin/env python
# -*- coding: utf-8 -*-
import codecs
import re
# from stanfordcorenlp import StanfordCoreNLP

'''
nlp = StanfordCoreNLP(r'/Users/ethan/GitHub/others/py_corenlp/stanford-corenlp_37/')

props={'annotators': 'tokenize,lemma','pipelineLanguage':'en','outputFormat':'text'}
sentence = "We don't live here."
print nlp.annotate(sentence, properties=props)
'''
s = "weofnf.of.wer.wer"

index =  s.find(r'.')
print s[:index]

