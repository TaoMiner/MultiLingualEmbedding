#-*- coding: utf8 -*-
import sys
reload(sys)
sys.setdefaultencoding('utf8')
import jieba
import re
import string
from itertools import izip, izip_longest

ss = 'w_w_w'
a = ss
ss = re.sub(r'_', ' ', ss)
print ss
print a