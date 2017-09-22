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
eleTagRE = re.compile(r'(<[^<>]+?>)([^<>]+?)(</[^<>]+?>)')
propTagRE = re.compile(r'(<[^<>]+?/>)')

ss = 'w<wefjioawe/>wefkp<wefef/>'
for m in propTagRE.finditer(ss):
    print m.span(1)[1]