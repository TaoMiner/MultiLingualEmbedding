#-*- coding: utf8 -*-
import sys
reload(sys)
sys.setdefaultencoding('utf8')
import re
import codecs

input_file1 = '/data/m1/cyx/MultiMPME/data/paradata/europarl-v7.es-en.en'
input_file2 = '/data/m1/cyx/MultiMPME/data/paradata/europarl-v7.es-en.es'
output_file = '/data/m1/cyx/MultiMPME/data/paradata/para_data.es-en'

with codecs.open(input_file1, 'rb', 'utf-8') as fin1, codecs.open(input_file2, 'rb', 'utf-8') as fin2:
    with codecs.open(output_file, 'w', 'utf-8') as fout:
        for line1 in fin1:
            line2 = fin2.readline()
            fout.write("%s\t%s\n" % (line1, line2))