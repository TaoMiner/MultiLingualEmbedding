import regex as re
import codecs

testfile = ''

id_set = set()
with codecs.open(testfile, 'r', encoding='UTF-8') as fin:
    for line in fin:
        items = re.split(r'\t', line)
        if len(items) < 5 : continue
        id_set.add(items[4])
print len(id_set)