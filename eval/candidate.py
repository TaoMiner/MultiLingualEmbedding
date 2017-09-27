import codecs
import regex as re
import os

class Candidate:
    "candidate generation"
    def __init__(self):
        self.wiki_dic = {}
        self.wiki_id_dic = {}
        self.mention_dic = {}       # {'mention':set(ent_id,..), ...}

    def loadMentionVocab(self, filename, entities = None):
        mention_set = set()
        miss = 0
        with codecs.open(filename, 'r', encoding='UTF-8') as fin:
            for line in fin:
                items = re.split(r'\t', line.strip())
                if len(items) < 2: continue
                mention_set.add(items[0])
                if not isinstance(entities, type(None)):
                    for ent_id in items[1:]:
                        if ent_id not in entities:
                            miss += 1
        print("lack of {0} entity in embeddings!".format(miss))
        return mention_set

    def loadEntityVocab(self, filename):
        entity_set = set()
        is_first = True
        with codecs.open(filename, 'r', encoding='UTF-8') as fin:
            for line in fin:
                if is_first :
                    is_first = False
                    continue
                items = re.split(r'\t', line.strip())
                entity_set.add(items[0])
        return entity_set

    # entities: id set
    def loadWikiDic(self, filename, entities = None):
        with codecs.open(filename, 'r', encoding='UTF-8') as fin:
            for line in fin:
                items = re.split(r'\t', line.strip())
                if len(items) < 2 : continue
                if not isinstance(entities, type(None)) and items[0] not in entities: continue
                self.wiki_dic[items[1]] = items[0]
                self.wiki_id_dic[items[0]] = items[1]
        print("load {0} wiki dic!".format(len(self.wiki_dic)))

    # for ppr and yago candidates for mention set, mentions are all lowered
    def loadCand(self, filename, mentions = None, entities = None):
        count = 0
        with codecs.open(filename, 'r', encoding='UTF-8') as fin:
            for line in fin:
                items = re.split(r'\t', line.strip())
                ment = items[0].lower()
                if len(items) < 2 : continue
                if not isinstance(mentions, type(None)) and ment not in mentions: continue
                tmp_cand = set() if ment not in self.mention_dic else self.mention_dic[ment]
                if not isinstance(entities, type(None)):
                    for item in items[1:]:
                        if item in entities:
                            tmp_cand.add(item)
                else:
                    tmp_cand |= set(items[1:])
                if len(tmp_cand) > 0:
                    self.mention_dic[ment] = tmp_cand
                    count += len(items)-1
        print("load {0} candidates for {1} mentions from {2}!".format(count, len(self.mention_dic), filename))

    def loadWikiCand(self, anchor_file, redirect_file, mentions = None, entities = None):
        if len(self.wiki_dic) == 0 :
            print("please load wiki dic!")
            return
        count = 0
        with codecs.open(anchor_file, 'r', encoding='UTF-8') as fin:
            for line in fin:
                items = re.split(r'\t', line.strip())
                if len(items) < 3 : continue
                ent_id = items[0]
                if not isinstance(entities, type(None)) and ent_id not in entities: continue
                for item in items[2:]:
                    ment_item = re.split(r'::=', item)
                    ment = ment_item[0].lower()
                    if not isinstance(mentions, type(None)) and ment not in mentions: continue
                    tmp_cand = set() if ment not in self.mention_dic else self.mention_dic[ment]
                    tmp_cand.add(ent_id)
                    self.mention_dic[ment] = tmp_cand
                    count += 1
        print("load {0} candidates for {1} mentions from {2}!".format(count, len(self.mention_dic), anchor_file))
        count = 0
        with codecs.open(redirect_file, 'r', encoding='UTF-8') as fin:
            for line in fin:
                items = re.split(r'\t', line.strip())
                if len(items) < 2 : continue
                wiki_title = items[0]
                ment = items[1].lower()
                if not isinstance(mentions, type(None)) and ment not in mentions: continue
                if wiki_title in self.wiki_dic :
                    ent_id = self.wiki_dic[wiki_title]
                    if not isinstance(entities, type(None)) and ent_id not in entities: continue
                else: return
                tmp_cand = set() if ment not in self.mention_dic else self.mention_dic[ment]
                tmp_cand.add(ent_id)
                self.mention_dic[ment] = tmp_cand
                count += 1
        print("load {0} candidates for {1} mentions from {2}!".format(count, len(self.mention_dic), redirect_file))

    def saveCandidates(self, filename):
        with codecs.open(filename, 'w', encoding='UTF-8') as fout:
            count = 0
            for mention in self.mention_dic:
                if len(self.mention_dic[mention])>0 and len(mention)>1:
                    count += len(self.mention_dic[mention])
                    fout.write("%s\t%s\n" % (mention, '\t'.join(self.mention_dic[mention])))
        print("total {0} candidates for {1} mentions!".format(count, len(self.mention_dic)))


'''
    def findPPRCand(self, path):
        if not os.path.isdir(path):
            return
        for root, dirs, list in os.walk(path):
            for dir in dirs:
                self.findPPRCand(os.path.join(root, dir))
            for l in list:
                if not l.startswith('.'):
                    with codecs.open(os.path.join(root, l), 'r', encoding='UTF-8') as fin:
                        mention_name = ''
                        for line in fin:
                            line = line.strip()
                            if line.startswith('ENTITY'):
                                mention_name = re.search(r'(?<=text:).*?(?=\t)', line).group()
                                if mention_name not in self.candidate:
                                    self.candidate[mention_name] = set()
                            if line.startswith('CANDIDATE') and mention_name != '':
                                id = re.search(r'(?<=id:).*?(?=\t)', line).group()
                                if id in self.ids:
                                    self.candidate[mention_name].add(id)

    def findYagoCand(self, filename):
        with codecs.open(filename, 'r', encoding='UTF-8') as fin:
            for line in fin:
                items = re.split(r'\t',line.strip().lower().decode('unicode_escape'))
                items[1] = items[1].replace('_',' ')
                if items[1] in self.wiki_id:
                    tmp_id = self.wiki_id[items[1]]
                    tmp_m = re.search(r'(?<=").*?(?=")', items[0]).group()
                    if tmp_m in self.candidate:
                        cand = self.candidate[tmp_m]
                    else:
                        cand = set()
                    cand.add(tmp_id)
                    self.candidate[tmp_m] = cand

    def findWikiCand(self, anchor_file, redirect_file, wiki_file):
        with codecs.open(anchor_file, 'r', encoding='UTF-8') as fin:
            for line in fin:
                items = re.split(r'\t', line.strip().lower())
                if len(items) <= 2: continue
                for m in items[2:]:
                    m_text = m.replace('=[\d]+$', '')
                    tmp_cand = self.candidate[m_text] if m_text in self.candidate else set()
                    tmp_cand.add(items[0])
                    self.candidate[m_text] = tmp_cand
            print("load %d mention from anchors!" % len(self.candidate))
        if len(self.wiki_id) < 1:
            self.loadWikiId(wiki_file)
        with codecs.open(redirect_file, 'r', encoding='UTF-8') as fin:
            for line in fin:
                items = re.split(r'\t\t', line.strip().lower())
                if len(items)<2:continue
                tmp_cand = self.candidate[items[0]] if items[0] in self.candidate else set()
                if items[1] not in self.wiki_id:
                    items[1] = items[1].replace('_', ' ')
                    if items[1] not in self.wiki_id: continue
                tmp_cand.add(self.wiki_id[items[1]])
                self.candidate[items[0]] = tmp_cand
            print("load %d mention from redirect pages!" % len(self.candidate))
        with codecs.open(wiki_file, 'r', encoding='UTF-8') as fin:
            for line in fin:
                items = re.split(r'\t\t', line.strip().lower())
                tmp_cand = self.candidate[items[0]] if items[0] in self.candidate else set()
                tmp_cand.add(items[1])
                self.candidate[items[0]] = tmp_cand
            print("load %d mention from wiki pages!" % len(self.candidate))

'''

if __name__ == '__main__':
    enwiki_id_file = '/home/caoyx/data/dump20170401/enwiki_cl/vocab_entity.dat'
    eswiki_id_file = '/home/caoyx/data/dump20170401/eswiki_cl/vocab_entity.dat'
    zhwiki_id_file = '/home/caoyx/data/dump20170401/zhwiki_cl/vocab_entity.dat'
    ppr_candidate_file = '/home/caoyx/data/conll/ppr_candidate'
    yago_candidate_file = '/home/caoyx/JTextKgForEL/data/conll/yago_candidates'
    enmention_count_file = '/home/caoyx/data/dump20170401/enwiki_cl/entity_prior'
    enredirect_file = '/home/caoyx/data/dump20170401/enwiki_cl/redirect_article_title'
    enmention_vocab_file = '/home/caoyx/data/eval_mention_dic.en'
    enentity_vocab_file = '/home/caoyx/data/etc/exp8/envec/vocab1_entity.txt'
    en_candidate_file = '/home/caoyx/data/candidates.en'

    en_cand = Candidate()
    entity_vocab = en_cand.loadEntityVocab(enentity_vocab_file)
    mention_vocab = en_cand.loadMentionVocab(enmention_vocab_file, entities=entity_vocab)
    en_cand.loadWikiDic(enwiki_id_file)
    en_cand.loadCand(ppr_candidate_file)
    en_cand.loadCand(yago_candidate_file)
    en_cand.loadWikiCand(enmention_count_file,enredirect_file)
    en_cand.saveCandidates(en_candidate_file)




