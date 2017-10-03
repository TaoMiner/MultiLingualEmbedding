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

class Features:
    "construct (mention, entity) pair's feature vectors, including base feature, \
    contextual feature and string feature"
    def __init__(self):
        self.window = 5
        self.entity_prior = {}
        self.me_prob = {}
        self.res1 = {}
        self.skip = 0
        self.m_count = {}
        self.punc = re.compile('[{0}]'.format(re.escape(string.punctuation)))
        self.log_file = ''
        self.has_sense = False
        self.candidate = None

    def setCurLang(self, lang):
        self.lang = lang

    def loadKbVec(self, entity, sense=None):
        self.kb_entity = entity
        self.kb_sense = sense

    def loadCurVec(self, word, entity, sense=None):
        self.tr_word = word
        self.tr_entity = entity
        if not isinstance(sense, type(None)):
            self.has_sense = True
            self.tr_sense = sense

    def loadIdWiki(self, id_wiki_file):
        self.id_wiki = Entity.loadEntityIdDic(id_wiki_file)

    def loadPrior(self, filename):
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
                    tmp_entity_count = self.me_prob[tmp_items[0]] if tmp_items[0] in self.me_prob else {}
                    if items[0] in tmp_entity_count:
                        tmp_entity_count[items[0]] += tmp_count
                    else:
                        tmp_entity_count[items[0]] = tmp_count
                    self.me_prob[tmp_items[0]] = tmp_entity_count
                self.entity_prior[items[0]] = float(ent_anchor_num)
                total_anchor_num += ent_anchor_num
        for ent in self.entity_prior:
            self.entity_prior[ent] /= total_anchor_num
            self.entity_prior[ent] *= 100
        for m in self.me_prob:
            self.m_count[m] = sum([self.me_prob[m][k] for k in self.me_prob[m]])

    def savePrior(self, file):
        with codecs.open(file, 'w', encoding='UTF-8') as fout:
            for ent in self.entity_prior:
                fout.write('{0}\t{1}\n'.format(ent,self.entity_prior[ent]))

    # load the predicted entity in the first step, or return None
    def loadResult(self, filename):
        count = 0
        if os.path.isfile(filename):
            with codecs.open(filename, 'r', encoding='UTF-8') as fin:
                for line in fin:
                    items = re.split(r',', line.strip())
                    if len(items) < 6 : continue
                    tmp_ans = self.res1[items[2]] if items[2] in self.res1 else set()
                    if items[5] in self.id_wiki:
                        tmp_ans.add(self.id_wiki[items[5]])
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
    def getFVec(self, doc, candidate_dic, c_entities = []):
        vec = []
        largest_pe = -1.0
        mention_index = -1
        skip_mentions = {}
        isFirstStep = True if len(c_entities) < 1 else False
        for m in doc.mentions:      #m [doc_index, sentence_index, wiki_id]     # [doc_index, ment_len, wiki_id, ment_str]
            mention_index += 1
            ment_name = m[3]
            if ment_name not in candidate_dic:
                self.skip += 1
                if ment_name not in skip_mentions:
                    skip_mentions[m[3]] = m[2]
                continue
            cand_set = candidate_dic[ment_name]
            cand_size = len(cand_set)

            for cand_id in cand_set:        #cand_id: m's candidates wiki id
                if cand_id not in self.id_wiki : continue
                entity_label = self.id_wiki[cand_id]
                tmp_mc_vec = [doc.doc_id]
                #get base features
                pem = 0.0
                if ment_name in self.me_prob and cand_id in self.me_prob[ment_name]:
                    pem = float(self.me_prob[ment_name][cand_id])/self.m_count[ment_name]
                pe = 0.0
                if cand_id in self.entity_prior:
                    pe = self.entity_prior[cand_id]
                largest_pe = pe if largest_pe < pe else largest_pe
                tmp_mc_vec.extend([mention_index, m[2], cand_id, cand_size, pem, pe, 0])

                #get string features
                str_sim1 = Levenshtein.distance(ment_name, entity_label)
                str_sim2 = 1 if ment_name == entity_label else 0
                str_sim3 = 1 if entity_label.find(ment_name) else 0
                str_sim4 = 1 if entity_label.startswith(ment_name) else 0
                str_sim5 = 1 if entity_label.endswith(ment_name) else 0
                tmp_mc_vec.extend([str_sim1, str_sim2, str_sim3, str_sim4, str_sim5])

                has_word = True if ment_name in self.tr_word.vectors else False
                has_entity = True if entity_label in self.tr_entity.vectors else False
                has_sense = True if entity_label in self.tr_sense.vectors else False

                # 3 embedding similarity: esim1:(w,e), esim2:(sense,e), esim3:(w,sense)
                esim1 = 0
                erank1 = 0
                if has_word and has_entity:
                    esim1 = self.cosSim(self.tr_word.vectors[ment_name],self.tr_entity.vectors[entity_label])

                esim2 = 0
                erank2 = 0
                if has_sense and has_entity:
                    esim2 = self.cosSim(self.tr_sense.vectors[entity_label], self.tr_entity.vectors[entity_label])

                esim3 = 0
                erank3 = 0
                if has_sense and has_word:
                    esim3 = self.cosSim(self.tr_word.vectors[ment_name], self.tr_sense.vectors[entity_label])

                # 4 contexual similarities for align, me and mpme: csim1:(c(w),e), csim2:(N(e),e), csim3:(tls,c(w)) [only mpme], csim4:(mu(tls),c(w)) [only mpme], csim5:(N(tls),tls)
                # context vec
                c_w_actual = 0
                if has_sense or has_entity:
                    context_vec = np.zeros(self.tr_word.layer_size)
                    begin_pos = m[0] - self.window if m[0] - self.window > 0 else 0
                    end_pos = m[0] + self.window if m[0] + self.window < len(doc) else len(doc) - 1
                    for i in xrange(begin_pos, end_pos + 1):
                        if i == m[0]: continue
                        if doc[i] in self.tr_word.vectors:
                            context_vec += self.tr_word.vectors[doc[i]]
                            c_w_actual += 1
                    if c_w_actual > 0:
                        context_vec /= c_w_actual
                csim1 = 0
                crank1 = 0
                if c_w_actual>0 and has_entity:
                    csim1 = self.cosSim(context_vec,
                                                  self.tr_entity.vectors[entity_label])

                csim2 = 0
                crank2 = 0

                # similarity between entity's mu and mention's context vec
                csim3 = 0
                crank3 = 0
                if c_w_actual > 0 and has_sense:
                    csim3 = self.cosSim(context_vec, self.tr_sense.vectors[entity_label])

                csim4 = 0
                crank4 = 0
                if has_sense and c_w_actual>0:
                    csim4 = self.cosSim(context_vec, self.tr_sense.mu[entity_label])

                csim5 = 0
                crank5 = 0

                tmp_mc_vec.extend([esim1, erank1, esim2, erank2, esim3, erank3, csim1, crank1, csim2, crank2, csim3, crank3, csim4, crank4, csim5, crank5])
                vec.append(tmp_mc_vec)
                # add entities without ambiguous as truth
                if isFirstStep and pem > 0.95 :
                    c_entities.append(entity_label)
        df_vec = pd.DataFrame(vec, columns = ['doc_id', 'mention_id', 'wiki_id', 'cand_id',\
                                              'cand_size', 'pem', 'pe','largest_pe',\
                                                'str_sim1', 'str_sim2','str_sim3','str_sim4','str_sim5',\
                                                'esim1', 'erank1', 'esim2', 'erank2','esim3', 'erank3',\
                                                'csim1', 'crank1','csim2', 'crank2','csim3', 'crank3','csim4', 'crank4', 'csim5', 'crank5'])

        cand_count = 0
        cand_size = 0
        last_mention = -1
        for row in df_vec.itertuples():
            # update feature vector for contextual feature's rank and largest pe
            if last_mention != row[2]:
                last_mention = row[2]
                cand_count = 0
                cand_size = row[5]
            entity_label = self.id_wiki[row[4]]
            cand_count += 1
            #update the largest pe in base features
            df_vec.loc[row[0], 'largest_pe'] = largest_pe
            #update context entity features
            if len(c_entities) > 0 and entity_label in self.tr_entity.vectors :
                c_ent_vec = np.zeros(self.tr_word.layer_size)
                c_ent_num = 0
                for ent in c_entities:
                    if ent in self.tr_entity.vectors:
                        c_ent_vec += self.tr_entity.vectors[ent]
                        c_ent_num += 1
                entity_vec = self.tr_entity.vectors[entity_label]
                if c_ent_num > 0:
                    c_ent_vec /= c_ent_num
                    df_vec.loc[row[0], 'csim2'] = self.cosSim(c_ent_vec, entity_vec)

            # update context entity features by entity title
            if len(c_entities) > 0 and entity_label in self.tr_sense.vectors:
                c_title_vec = np.zeros(self.tr_word.layer_size)
                c_title_num = 0
                for ent in c_entities:
                    if ent in self.tr_sense.vectors:
                        c_title_vec += self.tr_sense.vectors[ent]
                        c_title_num += 1
                title_vec = self.tr_sense.vectors[entity_label]
                if c_title_num > 0:
                    c_title_vec /= c_title_num
                    df_vec.loc[row[0], 'csim5'] = self.cosSim(c_title_vec, title_vec)

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

                t = -df_vec.loc[ row[0] - cand_size + 1:row[0], 'csim4']
                ranks = t.rank(method='min')
                for i in ranks.index:
                    df_vec.loc[i, 'crank4'] = ranks[i]

                t = -df_vec.loc[row[0] - cand_size + 1:row[0], 'csim5']
                ranks = t.rank(method='min')
                for i in ranks.index:
                    df_vec.loc[i, 'crank5'] = ranks[i]

                cand_size = 0
        return df_vec

    def extFeatures(self, corpus, candidate_dic, feature_file):
        if len(self.log_file) > 0:
            self.fout_log = codecs.open(self.log_file, 'w', encoding='UTF-8')
        for doc in corpus:
            vec = self.getFVec(doc, candidate_dic)
            vec.to_csv(feature_file, mode='a', header=False, index=False)
        if len(self.log_file) > 0:
            self.fout_log.close()


if __name__ == '__main__':
    aida_file = '/home/caoyx/data/conll/AIDA-YAGO2-dataset.tsv'
    candidate_file = '/home/caoyx/data/conll/ppr_candidate'
    wiki_id_file = '/home/caoyx/data/dump20170401/enwiki_cl/vocab_entity.dat'
    count_mention_file = '/home/caoyx/data/dump20170401/enwiki_cl/entity_prior'
    train_feature_file = '/home/caoyx/data/train15_file.csv'
    eval_feature_file = '/home/caoyx/data/eval15_file.csv'
    vec_path = '/home/caoyx/data/etc/exp8/'
    kb_entity_vector_file = vec_path + 'envec/vectors1_entity5'
    kb_sense_vector_file = vec_path + 'envec/vectors1_senses5'
    entity_vector_file = vec_path + '/envec/vectors1_entity5'
    word_vector_file = vec_path + '/envec/vectors1_word5'
    sense_vector_file = vec_path + '/envec/vectors1_senses5'
    log_file = '/home/caoyx/data/log/log_feature'
    res_file = '/home/caoyx/data/log/conll_pred.mpme'
    en_candidate_file = '/home/caoyx/data/candidates.en'
    es_candidate_file = '/home/caoyx/data/candidates.es'
    zh_candidate_file = '/home/caoyx/data/candidates.zh'

    eval_path = '/home/caoyx/data/kbp/LDC2017E03_TAC_KBP_Entity_Discovery_and_Linking_Comprehensive_Training_and_Evaluation_Data_2014-2016/data/'
    eval15_path = eval_path + '2015/eval/source_documents/'
    train15_path = eval_path + '2015/training/source_docs/'
    ans15_file = eval_path + '2015/eval/tac_kbp_2015_tedl_evaluation_gold_standard_entity_mentions.tab'
    ans15_train_file = eval_path + '2015/training/tac_kbp_2015_tedl_training_gold_standard_entity_mentions.tab'
    kbid_map_file = '/home/caoyx/data/kbp/id.key'

    languages = ['eng', 'cmn', 'spa']
    has_sense = True
    cur_lang = languages[0]
    features = Features()
    # kb lang is always 'eng', set for current lang
    features.setCurLang(cur_lang)

    wiki_word = Word()
    wiki_word.loadVector(word_vector_file)

    wiki_entity = Entity()
    wiki_entity.loadVector(entity_vector_file)

    wiki_sense = None
    if has_sense:
        wiki_sense = Sense()
        wiki_sense.loadVector(sense_vector_file)

    features.log_file = log_file
    # features.loadResult(res_file)
    features.loadCurVec(wiki_word, wiki_entity, sense=wiki_sense)
    if cur_lang == languages[0]:
        features.loadKbVec(wiki_entity, wiki_sense)
    else:
        kb_entity = Entity()
        kb_entity.loadVector(kb_entity_vector_file)

        kb_sense = None
        if has_sense:
            kb_sense = Sense()
            kb_sense.loadVector(kb_sense_vector_file)
        features.loadKbVec(kb_entity, kb_sense)
    features.loadIdWiki(wiki_id_file)

    # generate mention candidates in eng kb
    features.candidate = Candidate()
    features.candidate.en_mention_dic = features.candidate.loadCandidates(en_candidate_file)
    features.candidate.es_mention_dic = features.candidate.loadCandidates(es_candidate_file)
    features.candidate.zh_mention_dic = features.candidate.loadCandidates(zh_candidate_file)
    #mention's candidate entities {apple:{wiki ids}, ...}
    #p(e)
    features.loadPrior(count_mention_file)
    print("load {0} entities' priors!".format(len(features.entity_prior)))
    #{m:{e1:1, e2:3, ...}} for calculating p(e|m)
    print("load {0} mention names with prob !".format(len(features.me_prob)))

    # load doc
    en_server = 'http://localhost:9001'
    es_server = 'http://localhost:9002'
    jieba_dict = '/home/caoyx/data/dict.txt.big'
    doc_type = ['nw', 'df', 'newswire', 'discussion_forum']
    dr = DataReader()
    if cur_lang == languages[0]:
        dr.initNlpTool(en_server, cur_lang)
    elif cur_lang == languages[1]:
        dr.initNlpTool(es_server, cur_lang)
    elif cur_lang == languages[2]:
        dr.initNlpTool(jieba_dict, cur_lang)
    idmap = dr.loadKbidMap(kbid_map_file)
    mentions15 = dr.loadKbpMentions(ans15_file, id_map=idmap)
    mentions15_train = dr.loadKbpMentions(ans15_train_file, id_map=idmap)
    en_train_corpus = dr.readKbp(train15_path+languages[0]+'/'+doc_type[2]+'/', mentions15_train, '15')
    en_eval_corpus = dr.readKbp(eval15_path + languages[0] + '/' + doc_type[2] + '/', mentions15, '15')

    features.extFeatures(en_train_corpus, features.candidate.en_mention_dic, train_feature_file)
    features.extFeatures(en_eval_corpus, features.candidate.en_mention_dic, eval_feature_file)
