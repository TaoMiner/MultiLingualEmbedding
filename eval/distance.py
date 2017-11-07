#!/usr/bin/env python
# -*- coding: utf-8 -*-
from Entity import Entity
from Word import Word
from Sense import Sense
from scipy import spatial
import math
import numpy as np
import codecs
from options import Options
import heapq
import regex as re

inputRE = re.compile(r'^([+-])([we]):(en|zh|es):(.*?)$')
modeRE = re.compile(r'[\d]+')

class Distance():
    def __init__(self):
        self.words = []
        self.entities = []
        self.lang = []
        self.topN = 10
        self.fout_log = None
        self.input_vec = None
        self.layer_size = 0
        self.input_str = ''

    def setTopN(self, n):
        self.topN = n

    def setInput(self, layer_size):
        self.input_vec = np.zeros(layer_size, dtype=float)
        self.input_str = ''

    def loadModels(self, w, e, lang):
        if isinstance(w, type(None)) and isinstance(e, type(None)):
            print("Error! empty model!\n")
            return
        tmp_layer_size = w.layer_size if not isinstance(w, type(None)) else e.layer_size
        if self.layer_size == 0:
            self.layer_size = tmp_layer_size
        elif self.layer_size!=tmp_layer_size:
            print("Error! not match layer size!\n")
            return
        self.words.append(w)
        self.entities.append(e)
        self.lang.append(lang)
        self.setInput(self.layer_size)

    def sim(self, v1, v2):
        res = 0
        len_v1 = math.sqrt(np.dot(v1, v1))
        len_v2 = math.sqrt(np.dot(v2, v2))
        if len_v1 > 0.000001 and len_v2 > 0.000001:
            res = np.dot(v1, v2) / len_v1 / len_v2
            res = (res + 1) / 2
        if math.isnan(res) or math.isinf(res) or res > 1 or res < 0:
            res = 0
        return res

    def findNeighbors(self):
        out = 'OK! your input: {0}\n\
              '.format(self.input_str)
        for i in range(len(self.lang)):
            if isinstance(self.words[i], type(None)):
                out += '{0}: no word model for {1} language!\n'.format(2*i, self.lang[i])
            else:
                out += '{0}: nearest {1} words!\n'.format(2*i, self.lang[i])
            if isinstance(self.entities[i], type(None)):
                out += '{0}: no entity model for {1} language!\n'.format(2*i+1, self.lang[i])
            else:
                out += '{0}: nearest {1} entities!\n'.format(2*i+1, self.lang[i])
        out += '{0}: EXIT.\nYour choice:'.format(2*len(self.lang))
        while (1):
            choose_str = input(out)
            m = modeRE.match(choose_str)
            if not m:
                print("Error input!")
                continue
            mode_index = int(choose_str)
            if mode_index <0 or mode_index > 2*len(self.lang):
                print("Error input!")
                continue
            if mode_index==2*len(self.lang) :
                self.setInput(self.layer_size)
                break
            self.output(" {0}\n".format(mode_index))
            tmp_model = self.words if mode_index % len(self.lang)==0 else self.entities
            tmp_lang_index = mode_index / len(self.lang)
            if isinstance(tmp_model[tmp_lang_index], type(None)):
                print("Empty model, please choose again!\n")
                continue
            idDic = None
            if mode_index % len(self.lang) == 1 and not isinstance(tmp_model[tmp_lang_index].id_entity, type(None)):
                idDic = tmp_model[tmp_lang_index].id_entity
            self.findNearest(tmp_model[tmp_lang_index], idDic=idDic)

    def findNearest(self, model, idDic = None):
        sim = []
        tmp_line = u"\n                                              Cosine distance\n------------------------------------------------------------------------\n"
        self.output(tmp_line)
        for w in model.vectors:
            sim.append([w,self.sim(self.input_vec, model.vectors[w])])
        sorted_sim = heapq.nlargest(self.topN, sim, key=lambda x: x[1])
        for s in sorted_sim:
            label = s[0]
            if not isinstance(idDic, type(None)) and label in idDic:
                label = idDic[label]
            tmp_line = "{0:>50s}:{1}\n".format(label, s[1])
            self.output(tmp_line)

    def output(self, output_str):
        if not isinstance(self.fout_log, type(None)):
            self.fout_log.write("{0}".format(output_str))
        print(output_str)

    def setLogFile(self, filename, exp=''):
        self.fout_log = codecs.open(filename, 'a', encoding='UTF-8')
        self.fout_log.write('*************************************************\n')
        if len(exp) > 0:
            self.fout_log.write("{0}\n".format(exp))

    def getVec(self,item, item_type, lang_index):
        vec = None
        id = ''
        if item_type == Options.word_type and not isinstance(self.words[lang_index], type(None)) and item in self.words[lang_index].vectors:
            vec = self.words[lang_index].vectors[item]
            self.output("success find {0} word {1}!\n".format(self.lang[lang_index], item))
        if item_type == Options.entity_type and not isinstance(self.entities[lang_index], type(None)) and not isinstance(self.entities[lang_index].entity_id, type(None)) and item in self.entities[lang_index].entity_id:
                id = self.entities[lang_index].entity_id[item]
                if id in self.entities[lang_index].vectors:
                    vec = self.entities[lang_index].vectors[id]
                    self.output("success find {0} entity {1}:{2}!\n".format(self.lang[lang_index], id, item))
        return vec

    def process(self):
        while (1):
            str = input("Enter word or entity (EXIT to break, FINISH to find nearest): ")
            if str == 'EXIT': break
            if str == 'FINISH':
                if self.input_vec[0] == 0 : continue
                self.findNeighbors()
            m = inputRE.match(str)
            if not m:
                print("Error format! Please input again! Format:\"[+|-][w|e]:[en|zh|es]:item\"\nFor example, -w:en:apple\n")
                continue
            tmp_sign = 1 if m.group(1)=='+' else -1
            tmp_type = m.group(2)
            tmp_lang = m.group(3)
            item = m.group(4)

            item_type = Options.word_type if tmp_type == 'w' else Options.entity_type
            item_lang = Options.getLangType(tmp_lang)
            if item_lang not in self.lang:
                print("no model for this language!")
                continue
            lang_index = self.lang.index(item_lang)
            model = self.words if item_type == Options.word_type else self.entities
            if isinstance(model[lang_index], type(None)):
                print("no {0} for this language!".format(tmp_type))
                continue
            vec = self.getVec(item, item_type, lang_index)
            if isinstance(vec, type(None)):
                print("no such entity or word: {0}!\n".format(item))
                continue
            self.input_str += str + ' '
            self.input_vec += tmp_sign*vec
        if not isinstance(self.fout_log, type(None)):
            self.fout_log.write('*************************************************\n')
            self.fout_log.close()


if __name__ == '__main__':
    exp = 'exp2'
    it = 5
    lang = [Options.en, Options.zh]
    log_file = Options.getLogFile('distance.out')

    w1 = Word()
    w1.loadVector(Options.getExpVecFile(exp, lang[0], Options.word_type, it))
    e1 = Entity()
    e1.id_entity = e1.loadEntityIdDic(Options.getEntityIdFile(lang[0]))
    e1.entity_id = e1.loadEntityDic(Options.getEntityIdFile(lang[0]))
    e1.loadVector(Options.getExpVecFile(exp, lang[0], Options.entity_type, it))

    w2 = Word()
    w2.loadVector(Options.getExpVecFile(exp, lang[1], Options.word_type, it))
    e2 = Entity()
    e2.id_entity = e2.loadEntityIdDic(Options.getEntityIdFile(lang[1]))
    e2.entity_id = e2.loadEntityDic(Options.getEntityIdFile(lang[1]))
    e2.loadVector(Options.getExpVecFile(exp, lang[1], Options.entity_type, it))

    dis = Distance()
    dis.setLogFile(log_file)
    dis.loadModels(w1, e1, lang[0])
    dis.loadModels(w2, e2, lang[1])
    dis.process()
