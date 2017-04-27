#-*- coding: utf8 -*-
import sys
reload(sys)
sys.setdefaultencoding('utf8')
import re


a = 'he (wef) llo (disambiguate)'

titlRE = re.compile(r' \([^\(]*?\)$')

s = titlRE.sub('', a)
print s