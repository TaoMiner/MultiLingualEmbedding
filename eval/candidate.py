import codecs
import regex as re
from options import Options

nonEngRE = re.compile(r'[\W]+')
class Candidate:
    "candidate generation"
    def __init__(self):
        self.wiki_dic = {}
        self.wiki_id_dic = {}
        self.en_cand_dic = {}
        self.es_cand_dic = {}
        self.zh_cand_dic = {}
        self.en_zh_dic = {}
        self.en_es_dic = {}
        self.zh_to_en = {}
        self.es_to_en = {}

    def loadTranslations(self, isLowered = True):
        self.zh_to_en = self.loadTranslateMention(Options.getTransFile(Options.zh), isLowered)
        self.es_to_en = self.loadTranslateMention(Options.getTransFile(Options.es), isLowered)

    def getTranslation(self, ment_name, lang):
        tr_ment_name = ''
        if lang == Options.es:
            tr_ment_name = self.es_to_en[ment_name] if ment_name in self.es_to_en else ''
        if lang == Options.zh:
            tr_ment_name = self.zh_to_en[ment_name] if ment_name in self.zh_to_en else ''
        if lang == Options.en:
            tr_ment_name = ment_name
        return tr_ment_name

    def getCandidates(self, ment_name, lang):
        en_cand = set()
        cand = []
        if ment_name in self.en_cand_dic:
            en_cand.update(self.en_cand_dic[ment_name])
        if ment_name in self.zh_cand_dic:
            en_cand.update(self.zh_cand_dic[ment_name])
        if ment_name in self.es_cand_dic:
            en_cand.update(self.es_cand_dic[ment_name])
        has_crosslinks = True
        if lang == Options.en:
            has_crosslinks = False
        else:
            tmp_dic = self.en_zh_dic if lang == Options.zh else self.en_es_dic
        for ent_id in en_cand:
            if has_crosslinks and ent_id in tmp_dic:
                cand.append([ent_id, tmp_dic[ent_id]])
            else:
                cand.append([ent_id, ''])
        return cand

    def loadCrossLinks(self, filename):
        line_count = 0
        with codecs.open(filename, 'r', encoding='UTF-8') as fin:
            for line in fin:
                line_count += 1
                if line_count <= 2 : continue
                items = re.split(r'\t', line.strip())
                if len(items) < 3 or len(items[0]) < 1: continue
                if len(items[1]) > 0:
                    self.en_zh_dic[items[0]] = items[1]
                if len(items[2]) > 0:
                    self.en_es_dic[items[0]] = items[2]

    def loadMentionVocab(self, filename, isLowered):
        mention_vocab = {}
        with codecs.open(filename, 'r', encoding='UTF-8') as fin:
            for line in fin:
                items = re.split(r'\t', line.strip())
                if len(items) < 2: continue
                ment_name = items[0].lower() if isLowered else items[0]
                tmp_ent_set = mention_vocab[ment_name] if ment_name in mention_vocab else set()
                tmp_ent_set.update(items[1:])
                mention_vocab[ment_name] = tmp_ent_set
        return mention_vocab

    def loadTranslateMention(self, filename, isLowered):
        mentions = {}
        with codecs.open(filename, 'r', encoding='UTF-8') as fin:
            for line in fin:
                if isLowered:
                    line = line.lower()
                items = re.split(r'\t', line.strip())
                if len(items) != 2 : continue
                mentions[items[0]] = items[1]
        print("totally {0} translated mentions".format(len(mentions)))
        return mentions

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
    def loadWikiDic(self, mention_dic, filename, isLowered, mentions = None, entities = None):
        with codecs.open(filename, 'r', encoding='UTF-8') as fin:
            for line in fin:
                items = re.split(r'\t', line.strip())
                if len(items) < 2 : continue
                if not isinstance(entities, type(None)) and items[0] not in entities: continue
                self.wiki_dic[items[1]] = items[0]
                self.wiki_id_dic[items[0]] = items[1]
                lower_title = items[1].lower() if isLowered else items[1]
                if not isinstance(mentions, type(None)) and lower_title not in mentions: continue
                tmp = set() if lower_title not in mention_dic else mention_dic[lower_title]
                tmp.add(items[0])
                mention_dic[lower_title] = tmp
        print("load {0} wiki dic!{1} mentions!".format(len(self.wiki_dic), len(mention_dic)))

    # for ppr and yago candidates for mention set, mentions are all lowered
    def loadCand(self, mention_dic, filename, isLowered, mentions = None, entities = None):
        with codecs.open(filename, 'r', encoding='UTF-8') as fin:
            for line in fin:
                items = re.split(r'\t', line.strip())
                ment_name = items[0].lower() if isLowered else items[0]
                if len(items) < 2 : continue
                if not isinstance(mentions, type(None)) and ment_name not in mentions: continue
                tmp_cand = set() if ment_name not in mention_dic else mention_dic[ment_name]
                if not isinstance(entities, type(None)):
                    for item in items[1:]:
                        if item in entities:
                            tmp_cand.add(item)
                else:
                    tmp_cand |= set(items[1:])
                if len(tmp_cand) > 0:
                    mention_dic[ment_name] = tmp_cand

        cand_sum = 0
        for ment in mention_dic:
            cand_sum += len(mention_dic[ment])
        print("load {0} candidates for {1} mentions from {2}!".format(cand_sum, len(mention_dic), filename))

    def loadWikiCand(self, mention_dic, anchor_file, redirect_file, isLowered, mentions = None, entities = None):
        if len(self.wiki_dic) == 0 :
            print("please load wiki dic!")
            return
        with codecs.open(anchor_file, 'r', encoding='UTF-8') as fin:
            for line in fin:
                items = re.split(r'\t', line.strip())
                if len(items) < 3 : continue
                ent_id = items[0]
                if not isinstance(entities, type(None)) and ent_id not in entities: continue
                for item in items[2:]:
                    ment_item = re.split(r'::=', item)
                    ment_name = ment_item[0].lower() if isLowered else ment_item[0]
                    if not isinstance(mentions, type(None)) and ment_name not in mentions: continue
                    tmp_cand = set() if ment_name not in mention_dic else mention_dic[ment_name]
                    tmp_cand.add(ent_id)
                    mention_dic[ment_name] = tmp_cand
        cand_sum = 0
        for ment in mention_dic:
            cand_sum += len(mention_dic[ment])
        print("load {0} candidates for {1} mentions from {2}!".format(cand_sum, len(mention_dic), anchor_file))
        with codecs.open(redirect_file, 'r', encoding='UTF-8') as fin:
            for line in fin:
                items = re.split(r'\t', line.strip())
                if len(items) < 2 : continue
                wiki_title = items[0]
                ment_name = items[1].lower() if isLowered else items[1]
                if not isinstance(mentions, type(None)) and ment_name not in mentions: continue
                if wiki_title in self.wiki_dic :
                    ent_id = self.wiki_dic[wiki_title]
                    if not isinstance(entities, type(None)) and ent_id not in entities: continue
                else: return
                tmp_cand = set() if ment_name not in mention_dic else mention_dic[ment_name]
                tmp_cand.add(ent_id)
                mention_dic[ment_name] = tmp_cand
        cand_sum = 0
        for ment in mention_dic:
            cand_sum += len(mention_dic[ment])
        print("load {0} candidates for {1} mentions from {2}!".format(cand_sum, len(mention_dic), redirect_file))

    def saveCandidates(self, filename, mention_dic):
        with codecs.open(filename, 'w', encoding='UTF-8') as fout:
            count = 0
            for mention in mention_dic:
                if len(mention_dic[mention])>0 and len(mention)>1:
                    count += len(mention_dic[mention])
                    fout.write("%s\t%s\n" % (mention, '\t'.join(mention_dic[mention])))
        print("total {0} candidates for {1} mentions!".format(count, len(mention_dic)))

    def loadCandidates(self):
        self.loadEnCandidates(Options.getEvalCandidatesFile(Options.en))
        self.loadEsCandidates(Options.getEvalCandidatesFile(Options.es))
        self.loadZhCandidates(Options.getEvalCandidatesFile(Options.zh))

    def loadEnCandidates(self, filename):
        count = 0
        with codecs.open(filename, 'r', encoding='UTF-8') as fin:
            for line in fin:
                items = re.split(r'\t', line.strip())
                self.en_cand_dic[items[0]] = items[1:]
                count += len(items[1:])
        print("load {0} mentions with {1} candidates!".format(len(self.en_cand_dic), count))

    def loadEsCandidates(self, filename):
        count = 0
        with codecs.open(filename, 'r', encoding='UTF-8') as fin:
            for line in fin:
                items = re.split(r'\t', line.strip())
                self.es_cand_dic[items[0]] = items[1:]
                count += len(items[1:])
        print("load {0} mentions with {1} candidates!".format(len(self.es_cand_dic), count))

    def loadZhCandidates(self, filename):
        count = 0
        with codecs.open(filename, 'r', encoding='UTF-8') as fin:
            for line in fin:
                items = re.split(r'\t', line.strip())
                self.zh_cand_dic[items[0]] = items[1:]
                count += len(items[1:])
        print("load {0} mentions with {1} candidates!".format(len(self.zh_cand_dic), count))

    def buildCandidates(self, isLowered = True):
        enmention_dic = self.loadMentionVocab(Options.getEvalMentionVocabFile(Options.en), isLowered)
        zh_en_dic = self.loadTranslateMention(Options.getTransFile(Options.zh), isLowered)
        es_en_dic = self.loadTranslateMention(Options.getTransFile(Options.es), isLowered)

        en_mention_vocab = set(enmention_dic.keys())
        en_mention_vocab.update(set(zh_en_dic.values()))
        en_mention_vocab.update(set(es_en_dic.values()))

        esmention_dic = self.loadMentionVocab(Options.getEvalMentionVocabFile(Options.es), isLowered)
        zhmention_dic = self.loadMentionVocab(Options.getEvalMentionVocabFile(Options.zh), isLowered)
        es_mention_vocab = set(esmention_dic.keys())
        zh_mention_vocab = set(zhmention_dic.keys())

        mention_vocab = en_mention_vocab | es_mention_vocab | zh_mention_vocab

        # eng candidate file
        en_cand_dic = {}
        self.loadWikiDic(en_cand_dic, Options.getEntityIdFile(Options.en),isLowered, mentions=mention_vocab)
        self.loadCand(en_cand_dic, Options.ppr_candidate_file, isLowered, mentions=mention_vocab)
        self.loadCand(en_cand_dic, Options.yago_candidate_file, isLowered, mentions=mention_vocab)
        self.loadWikiCand(en_cand_dic, Options.getMentionCountFile(Options.en), Options.getRedirectFile(Options.en), isLowered, mentions=mention_vocab)
        self.saveCandidates(en_cand_dic, Options.getEvalCandidatesFile(Options.en))

        # es candidate file
        es_cand_dic = {}
        self.loadWikiDic(es_cand_dic, Options.getEntityIdFile(Options.es),isLowered, mentions=mention_vocab)
        self.loadWikiCand(es_cand_dic, Options.getMentionCountFile(Options.es), Options.getRedirectFile(Options.es), isLowered, mentions=mention_vocab)
        self.saveCandidates(es_cand_dic, Options.getEvalCandidatesFile(Options.es))

        # zh candidate file
        zh_cand_dic = {}
        self.loadWikiDic(zh_cand_dic, Options.getEntityIdFile(Options.zh),isLowered, mentions=mention_vocab)
        self.loadWikiCand(zh_cand_dic, Options.getMentionCountFile(Options.zh), Options.getRedirectFile(Options.zh), isLowered, mentions=mention_vocab)
        self.saveCandidates(zh_cand_dic, Options.getEvalCandidatesFile(Options.zh))

if __name__ == '__main__':
    cand = Candidate()
    cand.buildCandidates()
    '''
    cand.loadCandidates()
    cand.loadCrossLinks(Options.cross_links_file)
    cand.loadTranslations()
    '''