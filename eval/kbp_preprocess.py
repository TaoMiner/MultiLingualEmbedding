import regex as re
import codecs
import os
import gzip


kbp_eval_path = '/home/caoyx/data/kbp/LDC2017E03_TAC_KBP_Entity_Discovery_and_Linking_Comprehensive_Training_and_Evaluation_Data_2014-2016/data/'
testfile16 = kbp_eval_path + '2016/eval/tac_kbp_2016_edl_evaluation_gold_standard_entity_mentions.tab'
testfile15 = kbp_eval_path + '2015/eval/tac_kbp_2015_tedl_evaluation_gold_standard_entity_mentions.tab'
trainfile15 = kbp_eval_path + '2015/training/tac_kbp_2015_tedl_training_gold_standard_entity_mentions.tab'

ids_file = '/home/caoyx/data/kbp/eval_ids'
title_file = '/home/caoyx/data/kbp/id_title'
output_file = '/home/caoyx/data/kbp/id.key'

freebase_file = '/home/caoyx/data/kbp/freebase_links_en.ttl'
ref_kb_path = '/home/caoyx/data/kbp/LDC2015E42_TAC_KBP_Knowledge_Base_II-BaseKB/data/'

def extractIds(file, id_set):
    with codecs.open(file, 'r', encoding='UTF-8') as fin:
        for line in fin:
            items = re.split(r'\t', line)
            if len(items) < 5: continue
            if items[4].startswith('NIL') : continue
            id_set.add(items[4])
    print len(id_set)

headTitleRe = re.compile(r'<http://dbpedia.org/resource/(.*?)>')
tailIdRe = re.compile(r'<http://rdf.freebase.com/ns/(.*?)>')
def extractTitle(file, id_set, id_map, wiki_dic):
    with codecs.open(file, 'r', encoding='UTF-8') as fin:
        for line in fin:
            items = re.split(r' ', line.strip())
            if len(items) < 3: continue
            headM = headTitleRe.match(items[0])
            tailM = tailIdRe.match(items[2])
            if headM != None and tailM != None :
                title = headM.group(1)
                id = tailM.group(1)
                if id not in id_set or len(title) < 1 or title not in wiki_dic: continue
                id_map[id] = wiki_dic[title]

kbid_re = re.compile(r'<http://rdf.basekb.com/ns/(.*?)>')
enlabel_re = re.compile(r'^"(.*?)"@en$')
wiki_link_re = re.compile(r'<http://(en|es|zh).wikipedia.org/(.*?)>')

def extractTitleFromRefkb(path, id_set, id_map, wiki_dic):
    if os.path.isdir(path):
        for root, dirs, list in os.walk(path):
            for l in list:
                if l.startswith('.') or (not l.startswith('label-m-') and not l.startswith('webpages-m-')): continue
                print "processing file: %s ..." % l
                with gzip.open(os.path.join(ref_kb_path, l), 'r') as fin:
                    for line in fin:
                        line = line.decode('utf8')
                        items = re.split(r'\t', line.strip())
                        if len(items) < 3: continue
                        m = kbid_re.match(items[0])
                        if m != None:
                            kbid = m.group(1)
                            if kbid not in id_set: continue
                            wikis = re.split(r'\t',items[2])
                            for wiki in wikis:
                                label_m = enlabel_re.match(wiki)
                                if label_m!= None:
                                    wiki_label = label_m.group(1)
                                    if wiki_label in wiki_dic:
                                        id_map[kbid] = wiki_dic[wiki_label]

def loadWikiDic(filename):
    wiki_dic = {}
    with codecs.open(filename, 'r', encoding='UTF-8') as fin:
        for line in fin:
            items = re.split(r'\t', line.strip())
            if len(items) < 2: continue
            wiki_dic[items[1]] = items[0]
    print("load {0} wiki dic!".format(len(wiki_dic)))
    return wiki_dic


id_set = set()
id_map = {}
extractIds(testfile15, id_set)
extractIds(testfile16, id_set)
extractIds(trainfile15, id_set)
print "extracted %d different entities!" % len(id_set)
with codecs.open(ids_file, 'w', encoding='UTF-8') as fout:
    for id in id_set:
        fout.write("%s\n" % id)
wiki_id_file = '/home/caoyx/data/dump20170401/enwiki_cl/vocab_entity.dat'
wiki_dic = loadWikiDic(wiki_id_file)
extractTitleFromRefkb(ref_kb_path, id_set, id_map, wiki_dic)
print "extracted enwiki ids for %d entities!" % len(id_map)
extractTitle(freebase_file, id_set, id_map, wiki_dic)
print "extracted enwiki ids for %d entities!" % len(id_map)
with codecs.open(output_file, 'w', encoding='UTF-8') as fout:
    for id in id_map:
        fout.write("%s\t%s\n" % (id, id_map[id]))
