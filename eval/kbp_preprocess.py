import regex as re
import codecs
import os

testfile = '/home/caoyx/data/kbp/tac_kbp_2015_tedl_evaluation_gold_standard_entity_mentions.tab'
ref_kb_path = '/home/caoyx/data/kbp/LDC2015E42_TAC_KBP_Knowledge_Base_II-BaseKB/data/'

id_set = set()
with codecs.open(testfile, 'r', encoding='UTF-8') as fin:
    for line in fin:
        items = re.split(r'\t', line)
        if len(items) < 5 : continue
        id_set.add(items[4])
print len(id_set)

output_file = '/home/caoyx/data/kbp/LDC2015E42_TAC_KBP_Knowledge_Base_II-BaseKB/id.key'
label_re = re.compile(r'<http://rdf.basekb.com/ns/(.*?)>')
with codecs.open(output_file, 'w', encoding='UTF-8') as fout:
    if os.path.isdir(ref_kb_path):
        for list in os.walk(ref_kb_path):
            for l in list:
                if l.startswith('.') or not l.startswith('label-m-') or not l.startswith('webpages-m-') : continue
                with codecs.open(os.path.join(ref_kb_path, l), 'r', encoding='UTF-8') as fin:
                    for line in fin:
                        items = re.split(r'\t', line.strip())
                        if len(items) != 3 : continue
                        m = label_re.match(items[0])
                        if m != None:
                            kbid = m.group(1)
                            fout.write("%s\t%s\n" % (kbid,items[2]))