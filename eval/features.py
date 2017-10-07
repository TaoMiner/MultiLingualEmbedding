import codecs
import regex as re
import Levenshtein
from Entity import Entity
from Word import Word
from Sense import Sense
import numpy as np
from scipy import spatial
import os
import pandas as pd
import string
import math
from candidate import Candidate
from DataReader import DataReader
from options import Options

class Features:
    "construct (mention, entity) pair's feature vectors, including base feature, \
    contextual feature and string feature"
    def __init__(self):
        self.window = 5
        self.kb_entity_prior = {}
        self.kb_me_prob = {}
        self.kb_mcount = {}
        self.cur_entity_prior = {}
        self.cur_me_prob = {}
        self.cur_mcount = {}
        self.res1 = {}
        self.skip = 0
        self.punc = re.compile('[{0}]'.format(re.escape(string.punctuation)))
        self.log_file = ''
        self.has_cur_sense = False
        self.has_kb_sense = False
        self.candidate = None

    def setCurLang(self, lang):
        self.lang = lang

    def loadKb(self, id_wiki_dic, word, entity, sense=None):
        self.kb_idwiki = id_wiki_dic
        self.kb_word = word
        self.kb_entity = entity
        if not isinstance(sense, type(None)):
            self.kb_sense = sense
            self.has_kb_sense = True

    def loadCurVec(self, id_wiki_dic, word, entity, sense=None):
        self.cur_idwiki = id_wiki_dic
        self.cur_word = word
        self.cur_entity = entity
        if not isinstance(sense, type(None)):
            self.has_cur_sense = True
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

    # load the predicted entity in the first step, or return None
    def loadResult(self, filename):
        count = 0
        if os.path.isfile(filename):
            with codecs.open(filename, 'r', encoding='UTF-8') as fin:
                for line in fin:
                    items = re.split(r',', line.strip())
                    if len(items) < 6 : continue
                    tmp_ans = self.res1[items[2]] if items[2] in self.res1 else set()
                    if items[5] in self.kb_idwiki:
                        tmp_ans.add(self.kb_idwiki[items[5]])
                        self.res1[items[2]] = tmp_ans

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

    #doc=[w,..,w], mentions = [[doc_pos, ment_name, wiki_id],...], c_entities = [wiki_id, ...]
    # default, mention candidate dict depends on isCandLowered, embedding vocab is lowered
    def getFVec(self, doc, isCandLowered, c_entities = []):
        self.fout_log.write("doc:{0}\nmentions:{1}".format(doc.text, doc.mentions))
        vec = []
        largest_kb_pe = -1.0
        largest_cur_pe = -1.0
        mention_index = -1
        skip_mentions = {}
        isFirstStep = True if len(c_entities) < 1 else False
        for m in doc.mentions:      # m [doc_index, sentence_index, wiki_id]     # [doc_index, ment_len, wiki_id, ment_str]
            mention_index += 1
            ment_length = int(m[1])
            # sense embedding starts with '\s+'
            ment_name = m[3].lower() if isCandLowered else m[3]
            lower_ment_name = m[3].lower()
            tr_ment_name = self.candidate.getTranslation(m[3], self.lang)
            if isCandLowered:
                tr_ment_name = tr_ment_name.lower()
            lower_tr_ment_name = tr_ment_name.lower()
            cand_set = self.candidate.getCandidates(ment_name, self.lang)
            cand_size = len(cand_set)

            if cand_size < 1:
                self.skip += 1
                if ment_name not in skip_mentions:
                    skip_mentions[m[3]] = m[2]
                continue

            for cand in cand_set:        #cand_id: m's candidates wiki id
                kb_cand_id = cand[0]
                cur_cand_id = cand[1]
                # can fliter out the cand entity that doesnot has the entity vec
                if kb_cand_id not in self.kb_idwiki : continue
                kb_entity_label = self.kb_idwiki[kb_cand_id]
                cur_entity_label = self.cur_idwiki[cur_cand_id] if cur_cand_id in self.cur_idwiki else ''

                tmp_mc_vec = [doc.doc_id]
                tmp_mc_vec.extend([mention_index, m[2], kb_cand_id, cand_size])

                #get kb base features
                kb_pem = 0.0
                if lower_tr_ment_name in self.kb_me_prob and kb_cand_id in self.kb_me_prob[lower_tr_ment_name]:
                    kb_pem = float(self.kb_me_prob[lower_tr_ment_name][kb_cand_id])/self.kb_mcount[lower_tr_ment_name]
                kb_pe = 0.0
                if kb_cand_id in self.kb_entity_prior:
                    kb_pe = self.kb_entity_prior[kb_cand_id]
                largest_kb_pe = kb_pe if largest_kb_pe < kb_pe else largest_kb_pe
                tmp_mc_vec.extend([kb_pem, kb_pe, 0])

                # cur lang cand entity p
                cur_pem = 0.0
                cur_pe = 0.0
                if len(cur_cand_id) > 0:
                    if lower_ment_name in self.cur_me_prob and cur_cand_id in self.cur_me_prob[lower_ment_name]:
                        cur_pem = float(self.cur_me_prob[lower_ment_name][cur_cand_id]) / self.cur_mcount[lower_ment_name]
                    if cur_cand_id in self.cur_entity_prior:
                        cur_pe = self.cur_entity_prior[cur_cand_id]
                largest_cur_pe = cur_pe if largest_cur_pe < cur_pe else largest_cur_pe
                tmp_mc_vec.extend([cur_pem, cur_pe, 0])

                #get kb string features
                str_sim1 = str_sim2 = str_sim3 = str_sim4 = str_sim5 = 0
                if len(tr_ment_name) > 0:
                    lower_kb_entity_label = kb_entity_label.lower()
                    str_sim1 = Levenshtein.distance(lower_tr_ment_name, lower_kb_entity_label)
                    str_sim2 = 1 if lower_tr_ment_name == lower_kb_entity_label else 0
                    str_sim3 = 1 if lower_kb_entity_label.find(lower_tr_ment_name) else 0
                    str_sim4 = 1 if lower_kb_entity_label.startswith(lower_tr_ment_name) else 0
                    str_sim5 = 1 if lower_kb_entity_label.endswith(lower_tr_ment_name) else 0
                tmp_mc_vec.extend([str_sim1, str_sim2, str_sim3, str_sim4, str_sim5])

                # get cur string features
                str_sim1 = str_sim2 = str_sim3 = str_sim4 = str_sim5 = 0
                if len(cur_entity_label) > 0:
                    lower_cur_entity_label = cur_entity_label.lower()
                    str_sim1 = Levenshtein.distance(lower_ment_name, lower_cur_entity_label)
                    str_sim2 = 1 if lower_ment_name == lower_cur_entity_label else 0
                    str_sim3 = 1 if lower_cur_entity_label.find(lower_ment_name) else 0
                    str_sim4 = 1 if lower_cur_entity_label.startswith(lower_ment_name) else 0
                    str_sim5 = 1 if lower_cur_entity_label.endswith(lower_ment_name) else 0
                tmp_mc_vec.extend([str_sim1, str_sim2, str_sim3, str_sim4, str_sim5])

                # embedding features
                kb_w_actual = 0
                items = re.split(r' ', lower_tr_ment_name)
                kbw_vec = np.zeros(self.kb_word.layer_size, dtype=float)
                for item in items:
                    if item in self.kb_word.vectors:
                        kbw_vec += self.kb_word.vectors[item]
                        kb_w_actual += 1
                if kb_w_actual>0:
                    kbw_vec /= kb_w_actual

                cur_w_actual = 0
                curw_vec = np.zeros(self.cur_word.layer_size, dtype=float)
                if self.lang != Options.en:
                    items = re.split(r' ', lower_ment_name)
                    for item in items:
                        if item in self.cur_word.vectors:
                            curw_vec += self.cur_word.vectors[item]
                            cur_w_actual += 1
                    if cur_w_actual > 0:
                        curw_vec /= cur_w_actual

                has_kb_sense = True if self.has_kb_sense and kb_cand_id in self.kb_sense.vectors else False
                has_cur_sense = True if self.lang != Options.en and self.has_cur_sense and cur_cand_id in self.cur_sense.vectors else False
                self.fout_log.write("ment_label:{0},kb_s:{1},kb_w_actual:{2},cur_s:{3},cur_w_actual{4}\n".format(ment_name, has_kb_sense,kb_w_actual, has_cur_sense,cur_w_actual))
                # 3 embedding similarity: esim1:(kbw,kbsense), esim2:(curw,cursense), esim3:(curw,kbw), esim4:(curw, kbsense)
                esim1 = 0
                erank1 = 0
                if kb_w_actual > 0 and has_kb_sense:
                    esim1 = self.cosSim(kbw_vec,self.kb_sense.vectors[kb_cand_id])

                esim2 = 0
                erank2 = 0
                if self.lang != Options.en and has_cur_sense and cur_w_actual>0:
                    esim2 = self.cosSim(curw_vec, self.cur_sense.vectors[cur_cand_id])

                esim3 = 0
                erank3 = 0
                if self.lang != Options.en and cur_w_actual>0 and kb_w_actual > 0:
                    esim3 = self.cosSim(curw_vec, kbw_vec)

                esim4 = 0
                erank4 = 0
                if self.lang != Options.en and cur_w_actual > 0 and has_kb_sense:
                    esim4 = self.cosSim(curw_vec, self.kb_sense.vectors[kb_cand_id])

                # 4 contexual similarities for align: csim1:(c(w),kb_mu), csim2:(N(kb_e),kb_e), csim3:(c(w), cur_mu)
                # context vec
                c_w_actual = 0
                context_vec = np.zeros(self.cur_word.layer_size, dtype=float)
                begin_pos = m[0] - self.window if m[0] - self.window > 0 else 0
                end_pos = m[0] + self.window + ment_length - 1 if m[0] + self.window + ment_length - 1 < len(doc.text) else len(doc.text) - 1
                for i in range(begin_pos, end_pos + 1):
                    if i >= m[0] and i <= m[0] + ment_length - 1: continue
                    if doc.text[i] in self.cur_word.vectors:
                        context_vec += self.cur_word.vectors[doc.text[i]]
                        c_w_actual += 1
                if c_w_actual > 0:
                    context_vec /= c_w_actual
                csim1 = 0
                crank1 = 0
                if c_w_actual>0 and has_kb_sense:
                    csim1 = self.cosSim(context_vec, self.kb_sense.mu[kb_cand_id])

                csim2 = 0
                crank2 = 0

                # similarity between entity's mu and mention's context vec
                csim3 = 0
                crank3 = 0
                if c_w_actual > 0 and self.lang != Options.en and has_cur_sense:
                    csim3 = self.cosSim(context_vec, self.cur_sense.mu[cur_cand_id])

                tmp_mc_vec.extend([esim1, erank1, esim2, erank2, esim3, erank3, esim4, erank4, csim1, crank1, csim2, crank2, csim3, crank3])
                self.fout_log.write("esim1:{0},esim2:{1},esim3:{2},esim4:{3},csim1:{4},csim2:{5},csim3:{6},\n".format(esim1,esim2,esim3,esim4,csim1,csim2,csim3))
                vec.append(tmp_mc_vec)
                # add entities without ambiguous as truth
                if isFirstStep and kb_pem > 0.95 :
                    c_entities.append(kb_cand_id)
        df_vec = pd.DataFrame(vec, columns = ['doc_id', 'mention_id', 'wiki_id', 'kb_cand_id',\
                                              'kb_cand_size', 'kb_pem', 'kb_pe','kb_largest_pe', \
                                              'cur_pem', 'cur_pe', 'cur_largest_pe', \
                                              'trans_str_sim1', 'trans_str_sim2','trans_str_sim3','trans_str_sim4','trans_str_sim5', \
                                                'cur_str_sim1', 'cur_str_sim2', 'cur_str_sim3','cur_str_sim4', 'cur_str_sim5', \
                                                'esim1', 'erank1', 'esim2', 'erank2','esim3', 'erank3', 'esim4', 'erank4',\
                                                'csim1', 'crank1','csim2', 'crank2','csim3', 'crank3'])

        cand_count = 0
        cand_size = 0
        last_mention = -1
        for row in df_vec.itertuples():
            # update feature vector for contextual feature's rank and largest pe
            if last_mention != row[2]:
                last_mention = row[2]
                cand_count = 0
                kb_cand_size = row[5]
            kb_cand_id = row[4]
            cand_count += 1
            #update the largest pe in base features
            df_vec.loc[row[0], 'kb_largest_pe'] = largest_kb_pe
            df_vec.loc[row[0], 'cur_largest_pe'] = largest_cur_pe
            #update context entity features
            if len(c_entities) > 0 and kb_cand_id in self.kb_entity.vectors :
                c_ent_vec = np.zeros(self.kb_entity.layer_size, dtype=float)
                c_ent_num = 0
                for ent in c_entities:
                    if ent in self.kb_entity.vectors:
                        c_ent_vec += self.kb_entity.vectors[ent]
                        c_ent_num += 1
                entity_vec = self.kb_entity.vectors[kb_cand_id]
                if c_ent_num > 0:
                    c_ent_vec /= c_ent_num
                    df_vec.loc[row[0], 'csim2'] = self.cosSim(c_ent_vec, entity_vec)

            if cand_count == cand_size and cand_size > 0:
                #compute last mention's candidate rank
                t = -df_vec.loc[ row[0]-cand_size+1:row[0], 'esim1']
                ranks = t.rank(method = 'min')
                for i in ranks.index:
                    df_vec.loc[i, 'erank1'] = ranks[i]

                t = -df_vec.loc[row[0] - cand_size + 1:row[0], 'esim2']
                ranks = t.rank(method='min')
                for i in ranks.index:
                    df_vec.loc[i, 'erank2'] = ranks[i]

                t = -df_vec.loc[row[0] - cand_size + 1:row[0], 'esim3']
                ranks = t.rank(method='min')
                for i in ranks.index:
                    df_vec.loc[i, 'erank3'] = ranks[i]

                t = -df_vec.loc[row[0] - cand_size + 1:row[0], 'esim4']
                ranks = t.rank(method='min')
                for i in ranks.index:
                    df_vec.loc[i, 'erank4'] = ranks[i]

                t = -df_vec.loc[ row[0]-cand_size+1:row[0], 'csim1']
                ranks = t.rank(method = 'min')
                for i in ranks.index:
                    df_vec.loc[i, 'crank1'] = ranks[i]

                t = -df_vec.loc[ row[0]-cand_size+1:row[0], 'csim2']
                ranks = t.rank(method = 'min')
                for i in ranks.index:
                    df_vec.loc[i, 'crank2'] = ranks[i]

                t = -df_vec.loc[ row[0]-cand_size+1:row[0], 'csim3']
                ranks = t.rank(method = 'min')
                for i in ranks.index:
                    df_vec.loc[i, 'crank3'] = ranks[i]

                cand_size = 0
        return df_vec

    def extFeatures(self, corpus, feature_file, isLowered=True):
        if len(self.log_file) > 0:
            self.fout_log = codecs.open(self.log_file, 'w', encoding='UTF-8')
        for doc in corpus:
            vec = self.getFVec(doc, isLowered)
            vec.to_csv(feature_file, mode='a', header=False, index=False)
        if len(self.log_file) > 0:
            self.fout_log.close()


if __name__ == '__main__':
    # kb lang is always 'eng'
    has_sense = True
    exp = 'exp8'
    it = 5
    cur_lang = Options.en
    doc_type = Options.doc_type[0]
    corpus_year = 2015


    features = Features()
    # set for current lang
    features.setCurLang(cur_lang)

    # load kb entity, sense, and wiki_id
    kb_word = Word()
    kb_word.loadVector(Options.getExpVecFile(exp, Options.en, Options.word_type, it))

    kb_entity = Entity()
    kb_entity.loadVector(Options.getExpVecFile(exp, Options.en, Options.entity_type, it) )
    kb_idwiki_dic = kb_entity.loadEntityIdDic(Options.getEntityIdFile(Options.en))

    kb_sense = None
    if has_sense:
        kb_sense = Sense()
        kb_sense.loadVector(Options.getExpVecFile(exp, Options.en, Options.sense_type, it))

    features.loadKb(kb_idwiki_dic, kb_word, kb_entity, sense=kb_sense)

    # load cur lang word, entity, sense and wiki_id

    if cur_lang == Options.en:
        cur_word = kb_word
        cur_entity = kb_entity
        cur_sense = kb_sense
        cur_idwiki_dic = kb_idwiki_dic
    else:
        cur_word = Word()
        cur_word.loadVector(Options.getExpVecFile(exp, cur_lang, Options.word_type, it))

        cur_entity = Entity()
        cur_entity.loadVector(Options.getExpVecFile(exp, cur_lang, Options.entity_type, it))
        cur_idwiki_dic = cur_entity.loadEntityIdDic(Options.getEntityIdFile(cur_lang))

        cur_sense = None
        if has_sense:
            cur_sense = Sense()
            cur_sense.loadVector(Options.getExpVecFile(exp, cur_lang, Options.sense_type, it))

    features.loadCurVec(cur_idwiki_dic, cur_word, cur_entity, sense=cur_sense)

    features.log_file = Options.getLogFile('log_feature')

    # kb mention's candidate entities {apple:{wiki ids}, ...}
    # p(e)
    features.kb_me_prob, features.kb_entity_prior, features.kb_mcount = features.loadPrior(Options.getMentionCountFile(Options.en))
    print("load {0} entities' priors!".format(len(features.kb_entity_prior)))
    # {m:{e1:1, e2:3, ...}} for calculating p(e|m)
    print("load {0} mention names with prob !".format(len(features.kb_me_prob)))

    # mention's candidate entities {apple:{wiki ids}, ...}
    # p(e)
    if cur_lang == Options.en:
        features.cur_me_prob = features.kb_me_prob
        features.cur_entity_prior = features.kb_entity_prior
        features.cur_mcount = features.kb_mcount
    else:
        features.cur_me_prob, features.cur_entity_prior, features.cur_mcount = features.loadPrior(Options.getMentionCountFile(cur_lang))
    print("load {0} entities' priors!".format(len(features.cur_entity_prior)))
    # {m:{e1:1, e2:3, ...}} for calculating p(e|m)
    print("load {0} mention names with prob !".format(len(features.cur_me_prob)))

    # features.loadResult(res_file)

    # generate mention candidates in eng kb
    features.candidate = Candidate()
    features.candidate.loadCandidates()
    features.candidate.loadTranslations()
    features.candidate.loadCrossLinks(Options.cross_links_file)

    # load doc
    dr = DataReader()
    dr.initNlpTool(Options.getNlpToolUrl(cur_lang), cur_lang)
    idmap = dr.loadKbidMap(Options.kbid_map_file)
    mentions15 = dr.loadKbpMentions(Options.getKBPAnsFile(corpus_year, True), id_map=idmap)
    mentions15_train = dr.loadKbpMentions(Options.getKBPAnsFile(corpus_year, False), id_map=idmap)
    en_train_corpus = dr.readKbp(corpus_year,False,cur_lang, doc_type, mentions15_train)
    en_eval_corpus = dr.readKbp(corpus_year,True,cur_lang, doc_type, mentions15)

    features.extFeatures(en_train_corpus, Options.getFeatureFile(corpus_year,False,cur_lang, doc_type))
    features.extFeatures(en_eval_corpus, Options.getFeatureFile(corpus_year,True,cur_lang, doc_type))
