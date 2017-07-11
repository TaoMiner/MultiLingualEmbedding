import codecs
import re
from preprocess import cleaner
import jieba
jieba.set_dictionary('/home/caoyx/data/dict.txt.big')

file = '/home/caoyx/data/paradata/cross_links_labels.en_zh_chs'
output_file = '/home/caoyx/data/paradata/cross_links_labels.en_zh'

with codecs.open(file, 'r', 'utf8') as fin:
    with codecs.open(output_file, 'w', 'utf8') as fout:
        for line in fin:
            items = re.split(r'\t', line.strip())
            if len(items) < 2: continue
            en_str = cleaner.regularize(items[0], 'en')
            seg_list = jieba.cut(items[1], cut_all=False)
            # some chinese entities contain whitespace
            seg_line = " ".join(seg_list)
            zh_str = cleaner.regularize(seg_line, 'zh')
            fout.write("%s\t%s\n" % (en_str, zh_str))