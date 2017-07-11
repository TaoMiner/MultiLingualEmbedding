import codecs
import re
from preprocess import cleaner

file = '/home/caoyx/data/paradata/cross_links_labels.en_zh_chs'
output_file = '/home/caoyx/data/paradata/cross_links_labels.en_zh'

with codecs.open(file, 'r', 'utf8') as fin:
    with codecs.open(output_file, 'w', 'utf8') as fout:
        for line in fin:
            items = re.split(r'\t', line.strip())
            if len(items) < 2: continue
            en_str = cleaner.regularize(items[0], 'en')
            zh_str = cleaner.regularize(items[1], 'zh')
            fout.write("%s\t%s\n" % (en_str, zh_str))