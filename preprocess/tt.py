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
headerRE = re.compile(r'<doc id="(.*?)".*>')
s = '<doc id="12" url="https://en.wikipedia.org/wiki?curid=12" title="Anarchism">'

m = headerRE.match(s)
if m:
    print m.group(1)