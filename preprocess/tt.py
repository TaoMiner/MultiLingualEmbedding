#-*- coding: ISO-8859-1 -*-
import sys
reload(sys)
sys.setdefaultencoding('ISO-8859-1')
import cgi
import HTMLParser
parser = HTMLParser.HTMLParser()

s = 'Ern�n_Jim�nez_&amp;&quot;Makano&amp;&quot;'
s = s.decode('ISO-8859-1')

print parser.unescape(s)