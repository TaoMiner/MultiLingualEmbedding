import regex as re
import codecs
import os
import gzip

testfile = '/home/caoyx/data/kbp/tac_kbp_2015_tedl_evaluation_gold_standard_entity_mentions.tab'
ref_kb_path = '/home/caoyx/data/kbp/LDC2015E42_TAC_KBP_Knowledge_Base_II-BaseKB/data/'

id_set = set()
with codecs.open(testfile, 'r', encoding='UTF-8') as fin:
    for line in fin:
        items = re.split(r'\t', line)
        if len(items) < 5 : continue
        id_set.add(items[4])
print len(id_set)

id_map = {}
output_file = '/home/caoyx/data/kbp/LDC2015E42_TAC_KBP_Knowledge_Base_II-BaseKB/id.key'
label_re = re.compile(r'<http://rdf.basekb.com/ns/(.*?)>')
count = 0
if os.path.isdir(ref_kb_path):
    for root, dirs, list in os.walk(ref_kb_path):
        for l in list:
            if l.startswith('.') or (not l.startswith('label-m-') and not l.startswith('webpages-m-')) : continue
            count += 1
            print "processing file: %s ..." % l
            with gzip.open(os.path.join(ref_kb_path, l), 'r') as fin:
                for line in fin:
                    line = line.decode('utf8')
                    items = re.split(r'\t', line.strip())
                    if len(items) < 3 : continue
                    m = label_re.match(items[0])
                    if m != None:
                        kbid = m.group(1)
                        if kbid not in id_set: continue
                        tmp_list = [] if kbid not in id_map else id_map[kbid]
                        tmp_list.append(items[2])
print "extracted %d ids!" % len(id_map)
with codecs.open(output_file, 'w', encoding='UTF-8') as fout:
    for id in id_map:
        fout.write("%s\t%s\n" % (id.encode('utf8'), '\t'.join(id_map[id]).encode('utf8')))