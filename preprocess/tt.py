#-*- coding: ISO-8859-1 -*-
import sys
reload(sys)
sys.setdefaultencoding('ISO-8859-1')
import jieba
import re
import string

s = 'awf, swer sefw. sdf'
punc = re.compile('[%s]' % re.escape(string.punctuation))
s1 = punc.sub('', s)

print s
print s1