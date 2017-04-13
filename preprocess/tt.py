#-*- coding: ISO-8859-1 -*-
import sys
reload(sys)
sys.setdefaultencoding('ISO-8859-1')
import cgi
import HTMLParser
parser = HTMLParser.HTMLParser()

s = 'Ernán_Jiménez_&amp;&quot;Makano&amp;&quot;'
s = s.decode('ISO-8859-1')

print parser.unescape(s)