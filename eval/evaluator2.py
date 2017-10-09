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

class SenseLinker:
    "given a doc, disambiguate each mention from less ambiguous to more"
    def __init__(self):
        self.window = 5
        self.kb_entity_prior = {}
        self.kb_me_prob = {}
        self.mention_cand = {}
        self.kb_mcount = {}
        self.cur_entity_prior = {}
        self.cur_me_prob = {}
        self.cur_mcount = {}
        self.punc = re.compile('[%s]' % re.escape(string.punctuation))
        self.log_file = ''
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


    def savePrior(self, file):
        with codecs.open(file, 'w', encoding='UTF-8') as fout:
            for ent in self.entity_prior:
                fout.write('%s\t%f\n' % (ent,self.entity_prior[ent]))

    def loadCand(self, filename):
        with codecs.open(filename, 'r', encoding='UTF-8') as fin:
            can_sum = 0
            skip_candidate = 0
            for line in fin:
                items = re.split(r'\t', line.strip())
                tmp_set = set()
                if len(items) > 1:
                    for i in items[1:]:
                        if i not in self.id_wiki or self.id_wiki[i] not in self.tr_title.ent_vectors:
                            skip_candidate += 1
                            continue
                        tmp_set.add(i)
                if len(tmp_set) > 0:
                    self.mention_cand[items[0]] = tmp_set
                    can_sum += len(tmp_set)
        print("load %d mentions with %d candidates!" % (len(self.mention_cand),can_sum))

    def nearestSenseMu(self, cvec, sense):
        nearest_index = -1
        cloest_sim = -1.0
        if cvec[0] != 0 and cvec[-1] != 0:
            for i in xrange(sense.size):
                sim = self.cosSim(cvec, sense.mu[i])
                if sim > cloest_sim :
                    cloest_sim = sim
                    nearest_index = i
        return nearest_index

    def cosSim(self, v1, v2):
        res = spatial.distance.cosine(v1,v2)
        if math.isnan(res) or math.isinf(res) or res >1 or res <-1:
            res = 1
        return 1-res

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

    # doc:[w,...,w], mentions:[[doc_pos, mention_name, e_id],...]
    # senses:[mention_index, e_id]
    def disambiguateDoc(self, doc_id, doc, mentions):
        senses = {}     #{mention_index:predicted_id}
        m_order = []    #[[mention_index, [cand_id, pem], [...]], ...]
        # 1. cand_size ==1 or pem > 0.95;
        for i in xrange(len(mentions)):
            m_order.append([i])
            tmp_cand_set = []
            ment_name = mentions[i][1]
            tmp_w = doc[mentions[i][0]]
            has_m_prob = True if tmp_w in self.me_prob else False
            if not has_m_prob and len(self.log_file) > 0:
                self.fout_log.write('miss norm mention: %s, for %s, in anchors!\n' % (tmp_w, ment_name))
            for cand_id in self.mention_cand[ment_name]:
                pem = 0.000001
                if has_m_prob and cand_id not in self.me_prob[tmp_w]:
                    if len(self.log_file) > 0:
                        self.fout_log.write('miss entity: %s, for norm mention: %s!\n' % (cand_id, tmp_w))
                elif has_m_prob:
                    pem = float(self.me_prob[tmp_w][cand_id]) / self.m_count[tmp_w]
                if pem > 0.98:
                    del tmp_cand_set[:]
                    tmp_cand_set.append([cand_id, pem, 0.0, 0.0])
                    break
                tmp_cand_set.append([cand_id, pem, 0.0, 0.0])
            m_order[-1].extend(tmp_cand_set)
        # order for disambiguation
        m_order = sorted(m_order, cmp=lambda x, y: cmp(len(x), len(y)))
        # unambiguous tls vec in doc
        ge_actual = 0
        ge_vec = np.zeros(self.tr_title.layer_size)
        for i in xrange(len(m_order)):   #[[mention_index, [cand_id, pem], [...]], ...]
            m = m_order[i]
            mention_index = m[0]
            if len(m) == 2:
                senses[mention_index] = m[1][0]
                if self.id_wiki[m[1][0]] in self.tr_title.ent_vectors:
                    ge_vec += self.tr_title.ent_vectors[self.id_wiki[m[1][0]]]
                    ge_actual +=1
                continue
            # cand:[cand_id, pem] --> [cand_id, p(tls|m), p(tls|context), p(tls|tls(umambiguous))]
            for j in xrange(1,len(m)):
                cand_id = m[j][0]
                entity_label = self.id_wiki[cand_id]
                # p(tls|context)
                csim = 0.000001
                c_w_actual = 0
                if entity_label in self.tr_title.ent_mu:
                    # context vector
                    context_vec = np.zeros(self.tr_word.layer_size)
                    begin_pos = mentions[mention_index][0] - self.window if mentions[mention_index][0] - self.window > 0 else 0
                    end_pos = mentions[mention_index][0] + self.window if mentions[mention_index][0] + self.window < len(doc) else len(doc) - 1
                    for c in xrange(begin_pos, end_pos + 1):
                        if c == mentions[m[0]][0]: continue
                        if doc[c] in self.tr_word.vectors:
                            context_vec += self.tr_word.vectors[doc[c]]
                            c_w_actual += 1
                    if c_w_actual > 0:
                        context_vec /= c_w_actual
                        csim = self.cosSim(context_vec, self.tr_title.ent_mu[entity_label])
                m_order[i][j][2] = csim
                # p(tls|tls(umambiguous))
                gsim = 0.000001
                if ge_actual > 0 and entity_label in self.tr_title.ent_vectors:
                    gsim = self.cosSim(ge_vec / ge_actual, self.tr_title.ent_vectors[entity_label])
                m_order[i][j][3] = gsim
                self.total_cand_num += 1
            if self.is_prior:
                m_order[i][1:] = sorted(m[1:], cmp=lambda x, y: cmp(y[1],x[1]))
            elif self.is_local:
                m_order[i][1:] = sorted(m[1:], cmp=lambda x, y: cmp(y[2]*(y[1]**self.gamma), x[2]*(x[1]**self.gamma)))
            else:
                m_order[i][1:] = sorted(m[1:], cmp=lambda x, y: cmp(y[2]*y[3]*(y[1]**self.gamma), x[2]*x[3]*(x[1]**self.gamma)))

            cand_id = m_order[i][1][0]
            senses[mention_index]=cand_id
            if self.id_wiki[cand_id] in self.tr_title.ent_vectors:
                ge_vec += self.tr_title.ent_vectors[self.id_wiki[cand_id]]
                ge_actual += 1

        if len(self.log_file) > 0:
            self.fout_log.write('*************************************************\n')
            self.fout_log.write('doc %d: has mentions %d!\n' % (doc_id, len(mentions)))
            m_order = sorted(m_order, cmp=lambda x, y: cmp(x[0], y[0]))
            for m in m_order:       #[[mention_index, [cand_id, pem], [...]], ...]
                ment_name = mentions[m[0]][1]
                wiki_id = mentions[m[0]][2]
                predict = m[1]
                # ans
                self.fout_log.write('%s\t%d\t%s\t%s\t%f\t%f\t%f\n' % (ment_name, len(m) - 1, wiki_id, predict[0], predict[1], predict[2], predict[3]))
                # truth
                if predict[0] != wiki_id:
                    for cand in m[2:]:
                        if cand[0] == wiki_id:
                            self.fout_log.write('%s\t%d\t%s\t%s\t%f\t%f\t%f\n' % (ment_name, len(m)-1, wiki_id, cand[0], cand[1], cand[2], cand[3]))
                if predict[0] == wiki_id:
                    for cand in m[2:]:
                        if cand[1] > 0.9:
                            self.fout_log.write('%s\t%d\t%s\t%s\t%f\t%f\t%f\n' % (ment_name, len(m)-1, wiki_id, cand[0], cand[1], cand[2], cand[3]))
            self.fout_log.write('*************************************************\n')
        return senses

    def evaluate(self, senses, mentions):
        if len(senses) > 0 :
            doc_tp = 0
            for i in xrange(len(mentions)):
                if mentions[i][2] == senses[i]:
                    doc_tp += 1
            self.total_p += float(doc_tp)/len(senses)
            self.total_tp += doc_tp
            self.doc_actual += 1
            self.mention_actual += len(senses)

    def disambiguate(self, doc_file, output_file):
        if not self.is_global and not self.is_local and not self.is_prior:
            self.is_global = True
        if len(self.log_file) > 0:
            self.fout_log = codecs.open(self.log_file, 'w', encoding='UTF-8')
        with codecs.open(doc_file, 'r', encoding='UTF-8') as fin:
            doc_id = 0
            doc = []
            mentions = []
            is_mention = False
            for line in fin:
                line = line.strip()
                if line.startswith('-DOCSTART-'):
                    if doc_id >= 1163 and len(mentions) > 0:
                        self.evaluate(self.disambiguateDoc(doc_id, doc, mentions), mentions)
                    doc_id += 1
                    del doc[:]
                    del mentions[:]
                    is_mention = False
                    continue
                elif len(line)<1:
                    is_mention = False
                    continue
                else:
                    items = re.split(r'\t', line)
                    if len(items)>4 and items[1] == 'B' and items[2] in self.mention_cand and items[5] in self.mention_cand[items[2]]:
                        mentions.append([len(doc), items[2], items[5]])
                        doc.append(self.maprule(items[2]))
                        is_mention = True
                    elif is_mention and len(items)> 2 and items[1] == 'I':
                        continue
                    else:
                        tmp_w = self.maprule(items[0])
                        if tmp_w in self.tr_word.vectors:
                            doc.append(tmp_w)
                        is_mention = False
                        continue
            if len(doc) > 0:
                self.evaluate(self.disambiguateDoc(doc_id, doc, mentions), mentions)
        micro_p = float(self.total_tp) / self.mention_actual
        macro_p = self.total_p / self.doc_actual
        print("micro precision : %f(%d/%d/%d), macro precision : %f" % (micro_p, self.total_tp, self.mention_actual, self.total_cand_num, macro_p))
        with codecs.open(output_file, 'a', encoding='UTF-8') as fout:
            fout.write('*******************************************************************************************\n')
            fout.write('input: %s, gamma:%f, method: is_prior: %r, is_local: %r, is_global: %r\n' % (self.input_path, self.gamma, self.is_prior, self.is_local, self.is_global))
            fout.write("micro precision : %f(%d/%d/%d), macro precision : %f\n" % (micro_p, self.total_tp, self.mention_actual, self.total_cand_num, macro_p))
            fout.write("*******************************************************************************************\n")
        if len(self.log_file) > 0:
            self.fout_log.write('miss %d senses!\n%s\n' % (len(self.miss_senses), '\n'.join(self.miss_senses)))
            self.fout_log.close()

if __name__ == '__main__':

    # 1:prior, 2:local, 3:global
    method = 3
    gamma = 0.1
    exp = 'exp2'
    it = 5
    cur_lang = Options.en
    corpus_year = 2015
    doc_type = Options.doc_type[0]

    sense_linker = SenseLinker()
    sense_linker.log_file = Options.getLogFile('eval2.log')
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

    sense_linker.disambiguate(aida_file, output_file)
