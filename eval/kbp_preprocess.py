import regex as re
import codecs
import os
import gzip


kbp_eval_path = '/home/caoyx/data/kbp/LDC2017E03_TAC_KBP_Entity_Discovery_and_Linking_Comprehensive_Training_and_Evaluation_Data_2014-2016/data/'
testfile16 = kbp_eval_path + '2016/eval/tac_kbp_2016_edl_evaluation_gold_standard_entity_mentions.tab'
testfile15 = kbp_eval_path + '2015/eval/tac_kbp_2015_tedl_evaluation_gold_standard_entity_mentions.tab'
testfile14 = kbp_eval_path + '2014/eval/tac_kbp_2014_english_EDL_evaluation_KB_links.tab'

ids_file = '/home/caoyx/data/kbp/eval_ids'
title_file = '/home/caoyx/data/kbp/id_title'

ref_kb_file = '/home/caoyx/data/kbp/freebase_links_en.ttl'

def extractIds(file, id_set):
    with codecs.open(file, 'r', encoding='UTF-8') as fin:
        for line in fin:
            items = re.split(r'\t', line)
            if len(items) < 5: continue
            id_set.add(items[4])
    print len(id_set)

headTitleRe = re.compile(r'<http://dbpedia.org/resource/(.*?)>')
tailIdRe = re.compile(r'<http://rdf.freebase.com/ns/(.*?)>')
def extractTitle(file, id_set, id_map):
    with codecs.open(file, 'r', encoding='UTF-8') as fin:
        for line in fin:
            items = re.split(r' ', line.strip())
            if len(items) < 3: continue
            headM = headTitleRe.match(items[0])
            tailM = tailIdRe.match(items[2])
            if headM != None and tailM != None :
                title = headM.group(1)
                id = tailM.group(1)
                if id not in id_set or len(title) < 1: continue
                tmp_list = [] if id not in id_map else id_map[id]
                isRepeated = False
                for l in tmp_list:
                    if l == title :
                        isRepeated = True
                        break
                if not isRepeated :
                    tmp_list.append(title)
                    id_map[id] = tmp_list

id_set = set()
id_map = {}
extractIds(testfile15, id_set)
extractIds(testfile16, id_set)
print "extracted %d different entities!" % len(id_set)
with codecs.open(ids_file, 'w', encoding='UTF-8') as fout:
    for id in id_set:
        fout.write("%s\n" % id)
extractTitle(ref_kb_file, id_set, id_map)
print "extracted titles for %d entities!" % len(id_map)
with codecs.open(title_file, 'w', encoding='UTF-8') as fout:
    for id in id_map:
        fout.write("%s\t%s\n" % (id, '\t'.join(id_map[id])))
'''
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
                        id_map[kbid] = tmp_list
print "extracted %d ids!" % len(id_map)
with codecs.open(output_file, 'w', encoding='UTF-8') as fout:
    for id in id_map:
        fout.write("%s\t%s\n" % (id.encode('utf8'), '\t'.join(id_map[id]).encode('utf8')))
'''