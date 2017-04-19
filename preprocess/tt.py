#-*- coding: utf8 -*-
import sys
reload(sys)
sys.setdefaultencoding('utf8')
import jieba
import re
import string
from itertools import izip, izip_longest

ss = ' wfwef-{zh-tw:域;zh-cn:體}-wefa'

formatRE1 = re.compile(r'-\{.*?(zh-hans|zh-cn):(?P<label>[^;]*?)(;.*?\}|\})-')

formatRE2 = re.compile(r'-\{.*?(zh-hans|zh-cn):(?P<label>[^;]*?)\}-')
ss1 = formatRE1.sub('\g<label>', ss)

print ss1