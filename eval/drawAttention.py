import regex as re
from options import Options
from Entity import Entity
from Word import Word
import numpy as np
from scipy import spatial
import math

from ctypes import *

MAX_PAR_SENT = 10
MAX_SENTENCE_LENGTH = 1000
TOTAL_LENGTH = MAX_PAR_SENT * MAX_SENTENCE_LENGTH
class KMVar(Structure):
    _fields_=[('m',c_int),('n', c_int),('matrix', POINTER(c_float)),\
            ('match1', c_int*TOTAL_LENGTH), ('match2',c_int*TOTAL_LENGTH), \
              ('s', c_int * TOTAL_LENGTH), ('t', c_int * TOTAL_LENGTH), \
              ('l1', c_float * TOTAL_LENGTH), ('l2', c_float * TOTAL_LENGTH)]

km = CDLL("./km.so")
km.km_match.restype = c_float
km.km_match.argtype = POINTER(KMVar)

km_var = KMVar()
i_array = c_int * TOTAL_LENGTH
f_array = c_float * TOTAL_LENGTH
km_var.match1 = i_array()
km_var.match2 = i_array()
km_var.s = i_array()
km_var.t = i_array()
km_var.l1 = f_array()
km_var.l2 = f_array()

def cosSim(v1, v2):
    res = spatial.distance.cosine(v1, v2)
    if math.isnan(res) or math.isinf(res) or res > 1 or res < -1:
        res = 1
    return 1 - res

def getKGatt(sents, word_model, e_vec):
    if len(sents) == 1:
        att = np.ones(1)
    else:
        att = np.zeros(len(sents))
        for i in range(len(sents)):
            sent_vec = np.zeros(word_model.layer_size)
            for w in sents[i]:
                sent_vec += word_model.vectors[w]
            if len(sents[i]) > 1:
                sent_vec /= len(sents[i])
            if not isinstance(e_vec, type(None)):
                att[i] = (cosSim(sent_vec,e_vec))
            else:
                att[i] = 1.0
        sim_total = sum(att)
        att /= sim_total
    return att

# must m < n
def setKMVar(m, n):
    km_var.m = m
    km_var.n = n
    mat_array = c_float * (m*n)
    km_var.matrix = mat_array()
    return km_var.matrix

def getWordAtt(par_sents, word_models):
    sent_len = [sum([len(x) for x in par_sents[0]]), sum([len(x) for x in par_sents[1]])]
    m_idx = 0 if sent_len[0] < sent_len[1] else 1
    n_idx = 1 if sent_len[0] < sent_len[1] else 0
    sim_matrix = setKMVar(sent_len[m_idx], sent_len[n_idx])
    for i in range(sent_len[m_idx]):
        for j in range(sent_len[n_idx]):
            sim_matrix[i*sent_len[n_idx] + j] = cosSim(word_models[m_idx].vectors[par_sents[m_idx][i]], word_models[n_idx].vectors[par_sents[n_idx][j]])
    res = km.km_match(byref(km_var))
    att = [[ [0.0 for x in sent] for sent in par_sent] for par_sent in par_sents]
    if res>0:
        c = 0
        for i in range(len(att[m_idx])):
            for j in range(len(att[m_idx][i])):
                att[m_idx][i][j] = km_var.matrix[c*km_var.n+km_var.match1[c]] if km_var.match1[c] >= 0 else 0
                c += 1
        c = 0
        for i in range(len(att[n_idx])):
            for j in range(len(att[n_idx][i])):
                att[n_idx][i][j] = 0
                if km_var.match2[c] >= 0:
                    att[n_idx][i][j] = km_var.matrix[km_var.match2[c]*km_var.n+c]
                    tmp_c = 0
                    for ii in range(len(att[n_idx])):
                        for jj in range(len(att[n_idx][ii])):
                            if par_sents[n_idx][ii][jj] == par_sents[n_idx][i][j] and km_var.match2[tmp_c] == -1:
                                att[n_idx][ii][jj] = att[n_idx][i][j]
                            tmp_c += 1
                    c += 1
        sim_sum = sum([ sum([w_att for w_att in s_att]) for s_att in att[0]])
        att[0] /= sim_sum
        sim_sum = sum([sum([w_att for w_att in s_att]) for s_att in att[1]])
        att[1] /= sim_sum
    return att


exp = 'exp4'
it = 0
lang = Options.es
par_context_file = Options.getParFile(lang)
att_file = './att.out'

word_models = [Word(), Word()]
entity_models = [Entity(), Entity()]

word_models[0].loadVector(Options.getExpVecFile(exp,Options.en,Options.word_type, it))
word_models[1].loadVector(Options.getExpVecFile(exp,lang, Options.word_type, it))

entity_models[0].loadVector(Options.getExpVecFile(exp,Options.en,Options.entity_type, it))
entity_models[1].loadVector(Options.getExpVecFile(exp,lang, Options.entity_type, it))

with open(par_context_file) as fin:
    with open(att_file) as fout:
        tmp_lines = []
        for line in fin:
            tmp_lines.append(line.strip())
            if len(tmp_lines) == 2:
                splited_lines = [[re.split(r'\t', x)] for x in tmp_lines]
                if splited_lines[0][0] == '1' and splited_lines[1][0] == '2':
                    tmp_par_sents = [[[re.split(r' ', x)] for x in sents[3:]] for sents in splited_lines]
                    par_sents = []
                    par_entities = [splited_lines[0][1], splited_lines[1][1], splited_lines[0][2], splited_lines[1][2]]
                    for i in range(2):
                        sents = []
                        for tmp_sent in tmp_par_sents[i]:
                            sent = []
                            for item in tmp_sent:
                                if item in word_models[i].vectors:
                                    sent.append(item)
                            if len(sent) > 0:
                                sents.append(sent)
                        par_sents.append(sents)
                    if len(par_sents[0]) <1 or len(par_sents[1]) < 1:
                        del tmp_lines[:]
                        continue
                    # compute kg attention
                    kg_att = []
                    for i in range(2):
                        e_vec = entity_models[i].vectors[par_entities[i]] if par_entities[i] in entity_models[i].vectors else None
                        kg_att.append(getKGatt(par_sents[i], word_models[i], e_vec))
                    # compute word attention
                    word_att = getWordAtt(par_sents,word_models)
                    for i in range(2):
                        out_str = "{0}\t{1}\t{2}\t".format(i, par_entities[i], par_entities[i+2])
                        for j in range(len(par_sents[i])):
                            for k in range(len(par_sents[i][j])):
                                tmp_att = kg_att[i][j] * word_att[i][j][k]
                                out_str += "{0}({1}\{2}\{3}) ".format(par_sents[i][j][k], kg_att[i][j], word_att[i][j][k], tmp_att)
                            out_str = out_str.strip() + '\t'
                        fout.write("{0}\n".format(out_str))
                del tmp_lines[:]
                continue
