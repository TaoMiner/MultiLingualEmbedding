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
lang = 'es'
lang1_file = '/Users/ethan/Downloads/kbp15/eval_mention_dic.'+lang
lang2_file = '/Users/ethan/Downloads/kbp15/'+lang+'-en'
output_file = '/Users/ethan/Downloads/kbp15/'+lang+'-en2'

lines1 = []
lines2 = []
fin1 = codecs.open(lang1_file, 'r', encoding='UTF-8')
lines1 = fin1.readlines()
fin2 = codecs.open(lang2_file, 'r', encoding='UTF-8')
lines2 = fin2.readlines()
if len(lines1) != len(lines2): print("error")
with codecs.open(output_file, 'w', encoding='UTF-8') as fout:
    for i in range(len(lines2)):
        items = re.split(r'\t', lines1[i].strip())
        cand = items[0].strip()
        trans_cand = lines2[i].strip()
        fout.write("{0}\t{1}\n".format(cand, trans_cand))
