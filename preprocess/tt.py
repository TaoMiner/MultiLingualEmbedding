#-*- coding: ISO-8859-1 -*-
import sys
reload(sys)
sys.setdefaultencoding('ISO-8859-1')
import jieba
import re

s = 'fwef\twef wef\t\t wefo   wef'

numRE = re.compile(r'(?<=\s)[\d\s]+(?=($|\s))')

s1 = re.sub(r'[\s]+', ' ', s)
print s1
print re.split(r'\t', s1)