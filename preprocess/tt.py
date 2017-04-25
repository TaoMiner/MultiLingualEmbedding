#-*- coding: utf8 -*-
import sys
reload(sys)
sys.setdefaultencoding('utf8')
import re


a = ['','a','']
s = "%s\n" % '\t'.join(a)
print s.strip('\n')
items = re.split(r'\t', s.strip('\n'))
print len(items)