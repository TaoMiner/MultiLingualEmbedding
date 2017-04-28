#-*- coding: utf8 -*-
import sys
reload(sys)
sys.setdefaultencoding('utf8')
import re


a = [['a',0.01], ['b',0.1],['c',0.2]]

b = sorted(a, key=lambda x: x[1] )

print b