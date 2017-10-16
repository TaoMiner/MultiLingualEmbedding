import codecs
import regex as re
import Levenshtein
from Entity import Entity
from Word import Word
from Sense import Sense
import numpy as np
from scipy import spatial
import string
import math
from options import Options
from candidate import Candidate
from DataReader import DataReader
from DataReader import Doc
from functools import cmp_to_key

class SenseLinker:
    "given a doc, disambiguate each mention from less ambiguous to more"
    def __init__(self):
        self.cur_lang = ''
        self.window = 5
        self.kb_entity_prior = {}
        self.kb_me_prob = {}
        self.kb_mcount = {}
        self.cur_entity_prior = {}
        self.cur_me_prob = {}
        self.cur_mcount = {}
        self.punc = re.compile('[{0}]'.format(re.escape(string.punctuation)))
        self.log_file = ''
        self.debug_file = ''
        self.total_p = 0
        self.total_tp = 0
        self.doc_actual = 0
        self.mention_actual = 0
        self.total_cand_num = 0
        self.miss_senses = set()
        self.gamma = 0.1        # to smooth the pem
        self.is_local = False
        self.is_global = False
        self.is_prior = False
        self.candidate = None
        self.isFilter = True
        self.total_doc_num = 0
        self.total_cand_num = 0
        self.total_ment_num = 0

    def setGamma(self, gamma):
        self.gamma = gamma

    def setPrior(self):
        self.is_prior = True

    def setLocal(self):
        self.is_local = True

    def setGlobal(self):
        self.is_global = True

    def loadKb(self, id_wiki_dic, word, sense):
        self.kb_idwiki = id_wiki_dic
        self.kb_word = word
        self.kb_sense = sense

    def loadVec(self, id_wiki_dic, word, sense):
        self.cur_idwiki = id_wiki_dic
        self.cur_word = word
        self.cur_sense = sense

    def loadPrior(self, filename):
        me_prob = {}
        entity_prior = {}
        m_count = {}
        with codecs.open(filename, 'r', encoding='UTF-8') as fin:
            total_anchor_num = 0
            for line in fin:
                ent_anchor_num = 0
                items = re.split(r'\t', line.strip())
                if len(items) < 3 : continue
                for mention in items[2:]:
                    tmp_items = re.split(r'::=', mention)
                    if len(tmp_items)!=2: continue
                    tmp_count = int(tmp_items[1])
                    ent_anchor_num += tmp_count
                    tmp_entity_count = me_prob[tmp_items[0]] if tmp_items[0] in me_prob else {}
                    if items[0] in tmp_entity_count:
                        tmp_entity_count[items[0]] += tmp_count
                    else:
                        tmp_entity_count[items[0]] = tmp_count
                    me_prob[tmp_items[0]] = tmp_entity_count
                entity_prior[items[0]] = float(ent_anchor_num)
                total_anchor_num += ent_anchor_num
        for ent in entity_prior:
            entity_prior[ent] /= total_anchor_num
            entity_prior[ent] *= 100
        for m in me_prob:
            m_count[m] = sum([me_prob[m][k] for k in me_prob[m]])
        return me_prob, entity_prior, m_count

    def nearestSenseMu(self, cvec, sense):
        nearest_index = -1
        cloest_sim = -1.0
        if cvec[0] != 0 and cvec[-1] != 0:
            for i in range(sense.size):
                sim = self.cosSim(cvec, sense.mu[i])
                if sim > cloest_sim :
                    cloest_sim = sim
                    nearest_index = i
        return nearest_index

    def cosSim(self, v1, v2):
        res = 0
        len_v1 = math.sqrt(np.dot(v1,v1))
        len_v2 = math.sqrt(np.dot(v2,v2))
        if len_v1 > 0.000001 and len_v2 > 0.000001:
            res = np.dot(v1,v2)/len_v1/len_v2
            res = (res +1)/2
        if math.isnan(res) or math.isinf(res) or res >1 or res <0:
            res = 0
        return res

    def maprule(self, str):
        # possessive case 's
        # tmp_line = re.sub(r' s |\'s', ' ', str)
        # following clean wiki xml, punctuation, numbers, and lower case
        tmp_line = self.punc.sub(' ', str)
        tmp_line = tmp_line.replace('\t', ' ')
        tmp_line = re.sub(r'[\s]+', ' ', tmp_line)
        tmp_line = re.sub(r'(?<=\s)(\d+)(?=($|\s))', 'dddddd', tmp_line)
        tmp_line = re.sub(r'(?<=^)(\d+)(?=($|\s))', 'dddddd', tmp_line).lower().strip()
        return tmp_line

    def getTitle(self, entity_label):
        return re.sub(r'\(.*?\)$', '', entity_label).strip()

    # doc:[w,...,w], mentions:[[doc_pos, m_len, e_id, mention_name],...]
    # senses:[mention_index, e_id]
    def disambiguateDoc(self, doc, isCandLowered=True):
        doc_id = doc.doc_id
        text = doc.text
        mentions = doc.mentions
        senses = {}     #{mention_index:predicted_id}
        m_order = []    #[[mention_index, [cand_id, p(s_en|m_en),p(C_cur(m)|s_en), p(N_en(m)|s_en), p(m_en|m_cur)], [...]], ...]
        # 1. cand_size ==1 or pem > 0.95; p(s_en|m_en)
        for i in range(len(mentions)):
            m_order.append([i])
            tmp_cand_set = []
            ment_name = mentions[i][3].lower() if isCandLowered else mentions[i][3]
            kb_ment_name = self.candidate.getTranslation(ment_name, self.cur_lang)
            kb_entity_label = self.kb_idwiki[mentions[i][2]] if mentions[i][2] in self.kb_idwiki else ''

            has_me_prob = True if kb_ment_name in self.kb_me_prob else False
            kb_cand_set = self.candidate.getCandidates(ment_name, self.cur_lang)

            # filter according to sense embedding
            if self.isFilter and mentions[i][2] not in self.kb_sense.vectors:
                continue

            # filter cand doesnot contain wiki_id
            has_wiki_id = False
            for cand in kb_cand_set:
                if cand[0] == mentions[i][2]:
                    has_wiki_id = True
            if not has_wiki_id: continue

            for cand in kb_cand_set:
                cand_id = cand[0]
                # filter cand without sense embedding
                if self.isFilter and cand_id not in self.kb_sense.vectors:
                    continue
                pem = 0.000001
                if has_me_prob and cand_id in self.kb_me_prob[kb_ment_name]:
                    pem = float(self.kb_me_prob[kb_ment_name][cand_id]) / self.kb_mcount[kb_ment_name]
                if pem > 0.98:
                    del tmp_cand_set[:]
                    tmp_cand_set.append([cand_id, pem, 0.0, 0.0, 0.0])
                    break
                tmp_cand_set.append([cand_id, pem, 0.0, 0.0, 0.0])
            m_order[-1].extend(tmp_cand_set)
        # order for disambiguation
        m_order.sort(key=cmp_to_key(lambda x, y: ((len(x)>len(y))-(len(x)<len(y))) ))
        # m_order = sorted(m_order, cmp=lambda x, y: cmp(len(x), len(y)))
        # unambiguous tls vec in doc
        ge_actual = 0
        ge_vec = np.zeros(self.kb_sense.layer_size)
        for i in range(len(m_order)):   #[[mention_index, [cand_id, pem], [...]], ...]
            m = m_order[i]
            mention_index = m[0]
            if len(m) < 2:
                senses[mention_index] = ''      # no cand, skip
                continue
            self.total_cand_num += len(m) - 1
            if len(m) == 2:
                senses[mention_index] = m[1][0]
                if m[1][0] in self.kb_sense.vectors:
                    ge_vec += self.kb_sense.vectors[m[1][0]]
                    ge_actual +=1
                continue
            # cand:[cand_id, pem] --> [cand_id, p(s_en|m_en),p(C_cur(m)|s_en), p(N_en(m)|s_en), p(m_en|m_cur)]
            for j in range(1,len(m)):
                cand_id = m[j][0]
                # p(C_cur(m)|s_en)
                csim = 0.000001
                c_w_actual = 0
                if cand_id in self.kb_sense.mu:
                    # context vector
                    context_vec = np.zeros(self.cur_word.layer_size)
                    begin_pos = mentions[mention_index][0] - self.window if mentions[mention_index][0] - self.window > 0 else 0
                    end_pos = mentions[mention_index][0] + mentions[mention_index][1]-1 + self.window if mentions[mention_index][0] + mentions[mention_index][1]-1+ self.window < len(text) else len(text) - 1
                    for c in range(begin_pos, end_pos + 1):
                        if c >= mentions[mention_index][0] and c <=mentions[mention_index][0] + mentions[mention_index][1]-1: continue
                        if text[c] in self.cur_word.vectors:
                            context_vec += self.cur_word.vectors[text[c]]
                            c_w_actual += 1
                    if c_w_actual > 0:
                        context_vec /= c_w_actual
                        csim = self.cosSim(context_vec, self.kb_sense.mu[cand_id])
                m_order[i][j][2] = csim
                # p(N_en(m)|s_en)
                gsim = 0.000001
                if ge_actual > 0 and cand_id in self.kb_sense.vectors:
                    gsim = self.cosSim(ge_vec / ge_actual, self.kb_sense.vectors[cand_id])
                m_order[i][j][3] = gsim
                # p(m_en|m_cur)
                tr_sim = 0.000001
                cur_w_vec = np.zeros(self.cur_word.layer_size)
                cur_w_actual = 0
                kb_w_vec = np.zeros(self.kb_word.layer_size)
                kb_w_actual = 0
                ment_name = mentions[mention_index][3].lower()
                kb_ment_name = self.candidate.getTranslation(ment_name, self.cur_lang)
                kb_ment_name = kb_ment_name.lower()
                items = re.split(r' ', ment_name)
                for item in items:
                    if item in self.cur_word.vectors:
                        cur_w_vec += self.cur_word.vectors[item]
                        cur_w_actual += 1
                items = re.split(r' ', kb_ment_name)
                for item in items:
                    if item in self.kb_word.vectors:
                        kb_w_vec += self.kb_word.vectors[item]
                        kb_w_actual += 1
                if cur_w_actual>0 and kb_w_actual>0:
                    tr_sim = self.cosSim(cur_w_vec/cur_w_actual, kb_w_vec/kb_w_actual)
                m_order[i][j][4] = tr_sim
                self.total_cand_num += 1
            tmp_sort = m[1:]
            if self.is_prior:
                tmp_sort.sort(key=lambda x : x[4]*x[1])
            elif self.is_local:
                tmp_sort.sort(key=lambda x : x[4] * x[2] *(x[1]**self.gamma))
            else:
                tmp_sort.sort(key=lambda x : x[4] * x[3] * x[2] * (x[1] ** gamma), reverse = True)
            m_order[i][1:] = tmp_sort
            cand_id = m_order[i][1][0]
            senses[mention_index]=cand_id
            if cand_id in self.kb_sense.vectors:
                ge_vec += self.kb_sense.vectors[cand_id]
                ge_actual += 1

        if len(self.debug_file) > 0:
            self.fout_debug.write('*************************************************\n')
            self.fout_debug.write('doc {0}: has mentions {1}!\n'.format(doc_id, len(mentions)))
            m_order.sort(key=cmp_to_key(lambda x, y: ((x[0] > y[0]) - (x[0] < y[0]))))
            for m in m_order:       #[[mention_index, [cand_id, p(s_en|m_en),p(C_cur(m)|s_en), p(N_en(m)|s_en), p(m_en|m_cur)], [...]], ...]
                ment_name = mentions[m[0]][3]
                wiki_id = mentions[m[0]][2]
                if len(m) < 2:
                    self.fout_debug.write('{0}\t{1}\n'.format(ment_name, wiki_id))
                else:
                    predict = m[1]
                    # ans
                    self.fout_debug.write('{0}\t{1}\t{2}\t{3}\t{4}\t{5}\t{6}\t{7}\n'.format(ment_name, len(m) - 1, wiki_id, predict[0], predict[1], predict[2], predict[3],predict[4]))
                    # truth
                    if predict[0] != wiki_id and len(m)-1 >1:
                        for cand in m[2:]:
                            if cand[0] == wiki_id:
                                self.fout_debug.write('{0}\t{1}\t{2}\t{3}\t{4}\t{5}\t{6}\t{7}\n'.format(ment_name, len(m)-1, wiki_id, cand[0], cand[1], cand[2], cand[3], cand[4]))
            self.fout_debug.write('*************************************************\n')
        return senses

    def evaluate(self, senses, mentions):
        if len(senses) > 0 :
            self.total_doc_num += 1
            self.total_ment_num += len(senses)
            doc_tp = 0
            for i in range(len(mentions)):
                if len(senses[i]) < 1: continue
                if mentions[i][2] == senses[i]:
                    doc_tp += 1
            self.total_p += float(doc_tp)/len(senses)
            self.total_tp += doc_tp
            self.doc_actual += 1
            self.mention_actual += len(senses)

    def disambiguate(self, corpus, dataset_name = ''):
        if not self.is_global and not self.is_local and not self.is_prior:
            self.is_global = True
        if len(self.debug_file) > 0:
            self.fout_debug = codecs.open(self.debug_file, 'w', encoding='UTF-8')
            if len(corpus) > 0:
                for doc in corpus:
                    self.evaluate(self.disambiguateDoc(doc), doc.mentions)
        micro_p = float(self.total_tp) / self.mention_actual
        macro_p = self.total_p / self.doc_actual
        print("micro precision : {0}({1}/{2}/{3}), macro precision : {4}".format(micro_p, self.total_tp, self.mention_actual, self.total_cand_num, macro_p))
        if len(self.log_file) > 0:
            with codecs.open(self.log_file, 'a', encoding='UTF-8') as fout:
                fout.write('*******************************************************************************************\n')
                fout.write("dataset:{0}, {1} docs! {2} mentions! {3} candidates!\n".format(dataset_name, self.total_doc_num, self.total_ment_num, self.total_cand_num))
                fout.write('gamma:{0}, method: is_prior: {1}, is_local: {2}, is_global: {3}\n'.format(self.gamma, self.is_prior, self.is_local, self.is_global))
                fout.write("micro precision : {0}({1}/{2}/{3}), macro precision : {4}\n".format(micro_p, self.total_tp, self.mention_actual, self.total_cand_num, macro_p))
                fout.write("*******************************************************************************************\n")
        if len(self.debug_file) > 0:
            self.fout_debug.write('miss {0} senses!\n{1}\n'.format(len(self.miss_senses), '\n'.join(self.miss_senses)))
            self.fout_debug.close()

if __name__ == '__main__':

    # 1:prior, 2:local, 3:global
    method = 3
    gamma = 0.1
    exp = 'exp9'
    it = 5
    cur_lang = Options.zh
    corpus_year = 2015
    doc_type = Options.doc_type[0]

    sense_linker = SenseLinker()
    sense_linker.cur_lang = cur_lang
    sense_linker.log_file = Options.getLogFile('eval2.log')
    sense_linker.debug_file = Options.getLogFile('eval2.debug')
    if method == 1:
        sense_linker.setPrior()
    elif method == 2:
        sense_linker.setLocal()
    else:
        sense_linker.setGlobal()
    sense_linker.setGamma(gamma)

    kb_word = Word()
    kb_word.loadVector(Options.getExpVecFile(exp, Options.en, Options.word_type, it))

    kb_entity = Entity()
    kb_idwiki_dic = kb_entity.loadEntityIdDic(Options.getEntityIdFile(Options.en))

    kb_sense = Sense()
    kb_sense.loadVector(Options.getExpVecFile(exp, Options.en, Options.sense_type, it))
    sense_linker.loadKb(kb_idwiki_dic, kb_word, kb_sense)

    if cur_lang == Options.en:
        cur_word = kb_word
        cur_sense = kb_sense
        cur_idwiki_dic = kb_idwiki_dic
    else:
        cur_word = Word()
        cur_word.loadVector(Options.getExpVecFile(exp, cur_lang, Options.word_type, it))

        cur_entity = Entity()
        cur_idwiki_dic = cur_entity.loadEntityIdDic(Options.getEntityIdFile(cur_lang))

        cur_sense = Sense()
        cur_sense.loadVector(Options.getExpVecFile(exp, cur_lang, Options.sense_type, it))

    sense_linker.loadVec(cur_idwiki_dic, cur_word, cur_sense)

    sense_linker.kb_me_prob, sense_linker.kb_entity_prior, sense_linker.kb_mcount = sense_linker.loadPrior(Options.getMentionCountFile(Options.en))
    print("load kb {0} entities' priors!".format(len(sense_linker.kb_entity_prior)))
    # {m:{e1:1, e2:3, ...}} for calculating p(e|m)
    print("load kb {0} mention names with prob !".format(len(sense_linker.kb_me_prob)))

    if cur_lang == Options.en:
        sense_linker.cur_me_prob = sense_linker.kb_me_prob
        sense_linker.cur_entity_prior = sense_linker.kb_entity_prior
        sense_linker.cur_mcount = sense_linker.kb_mcount
    else:
        sense_linker.cur_me_prob, sense_linker.cur_entity_prior, sense_linker.cur_mcount = sense_linker.loadPrior(Options.getMentionCountFile(cur_lang))
    print("load cur {0} entities' priors!".format(len(sense_linker.cur_entity_prior)))
    # {m:{e1:1, e2:3, ...}} for calculating p(e|m)
    print("load cur {0} mention names with prob !".format(len(sense_linker.cur_me_prob)))

    #mention's candidate entities {apple:{wiki ids}, ...}
    sense_linker.candidate = Candidate()
    sense_linker.candidate.loadCandidates()
    sense_linker.candidate.loadTranslations()
    sense_linker.candidate.loadCrossLinks(Options.cross_links_file)
    #p(e)
    sense_linker.loadPrior(Options.getMentionCountFile(cur_lang))

    dr = DataReader()
    dr.initNlpTool(Options.getNlpToolUrl(cur_lang), cur_lang)
    idmap = dr.loadKbidMap(Options.kbid_map_file)

    mentions15 = dr.loadKbpMentions(Options.getKBPAnsFile(corpus_year, True), id_map=idmap)
    en_eval_corpus = dr.readKbp(corpus_year, True, cur_lang, doc_type, mentions15)
    dataset_name = Options.getFeatureFile(corpus_year, True, cur_lang, doc_type, exp)
    sense_linker.disambiguate(en_eval_corpus, dataset_name)
