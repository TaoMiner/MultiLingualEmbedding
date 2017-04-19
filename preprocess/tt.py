#-*- coding: utf8 -*-
import sys
reload(sys)
sys.setdefaultencoding('utf8')
import jieba
import re
import string
from itertools import izip, izip_longest
import codecs

file = '/Users/ethan/Downloads/zhwiki/raw_chs_vocab_entity.dat'

titles = set()
with codecs.open(file, 'rb', 'utf-8') as fin:
    for line in fin:
        items = re.split(r'\t', line.strip())
        if items[1] in titles:
            print items[1].encode('utf-8')
        else:
            titles.add(items[1])