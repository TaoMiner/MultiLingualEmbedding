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

inputRE = re.compile(r'^(.*):(.*):(.*?)$')

class Distance():
    def __init__(self):
        self.words = []
        self.entities = []
        self.lang = []
        self.topN = 10
        self.fout_log = None

    def setTopN(self, n):
        self.topN = n

    def loadModels(self, w, e, lang):
        self.words.append(w)
        self.entities.append(e)
        self.lang.append(lang)

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

    def findNeighbors(self, item, item_type, lang):
        out = 'OK!{0}:{1}:{2}, Choose neighbors type:\n\
                            1: nearest type in current language.\n\
                            2: nearest other type in current language.\n\
                            3: nearest type in other languages.\n\
                            4: nearest other type in other languages.\n\
                            5: EXIT.\n'.format(item_type, Options.getLangStr(lang), item)
        res = 0
        while (1):
            mode_index = int(input(out))
            if mode_index<=0 or mode_index >= 6 : continue
            if mode_index==5 : break
            self.output("choose {0}\n".format(mode_index))
            if (item_type == Options.entity_type and mode_index % 2 == 1) or (item_type == Options.word_type and mode_index % 2 == 0):
                res = self.findEntityNeighbor(mode_index, item, lang)
            else :
                res = self.findWordNeighbor(mode_index, item, lang)
            if not res: break

    def findWordNeighbor(self, mode_index, label, lang):
        # model index 1,3 means label is a word, 2,4 means label is a entity
        lang_index = self.lang.index(lang)

        type_str = ''
        if mode_index % 2 == 0:
            if not isinstance(self.entities[lang_index].id_entity, type(None)) and label in self.entities[
                lang_index].id_entity:
                id = self.entities[lang_index].id_entity[label]
            else:
                self.output("no such entity:{0}!".format(label))
                return False
            if id in self.entities[lang_index].vectors:
                v1 = self.entities[lang_index].vectors[id]
                type_str = "Entity: {0}".format(id)
            else:
                self.output("no such entity embedding:{0}!".format(label))
                return False
        else:
            if label in self.words[lang_index].vectors:
                v1 = self.words[lang_index].vectors[label]
                type_str = "Word"
            else:
                self.output("no such word embedding:{0}!".format(label))
                return False

        # single language
        if mode_index <= 2:
            self.output("{0}:{1}'s nearest {2} neighbors in lang: {3}.\n".format(type_str, label, self.topN, lang))
            self.findNearest(v1, self.words[lang_index], item=label)
        else:  # cross lingual
            for i in range(len(self.lang)):
                if i == lang_index: continue
                self.output("{0}:{1}'s nearest {2} neighbors in lang: {3}.\n".format(type_str, label, self.topN,
                                                                                             self.lang[i]))
                self.findNearest(v1, self.words[i])
        return True

    def findEntityNeighbor(self, mode_index, label, lang):
        lang_index = self.lang.index(lang)
        # model index 1,3 means label is a entity, 2,4 means label is a word
        type_str = ''
        if mode_index %2 ==1:
            if not isinstance(self.entities[lang_index].entity_id, type(None)) and label in self.entities[lang_index].entity_id:
                id = self.entities[lang_index].entity_id[label]
            else:
                self.output("no such entity:{0}!".format(label))
                return False
            if id in self.entities[lang_index].vectors:
                v1 = self.entities[lang_index].vectors[id]
                type_str = "Entity: {0}".format(id)
            else:
                self.output("no such entity embedding:{0}!".format(label))
                return False
        else:
            if label in self.words[lang_index].vectors:
                v1 = self.words[lang_index].vectors[label]
                type_str = "Word"
            else:
                self.output("no such word embedding:{0}!".format(label))
                return False

        # single language
        if mode_index <=2:
            self.output("{0}:{1}'s nearest {2} entity neighbors in lang: {3}.\n".format(type_str, label, self.topN, lang))
            self.findNearest(v1, self.entities[lang_index], idDic=self.entities[lang_index].id_entity)
        else:   #cross lingual
            for i in range(len(self.lang)):
                if i == lang_index: continue
                self.output("{0}:{1}'s nearest {2} entity neighbors in lang: {3}.\n".format(type_str, label, self.topN, self.lang[i]))
                self.findNearest(v1, self.entities[i], idDic=self.entities[i].id_entity)
        return True

    def findNearest(self, vec, model, item='', idDic = None):
        sim = []
        tmp_line = u"\n                                              Cosine distance\n------------------------------------------------------------------------\n"
        self.output(tmp_line)
        for w in model.vectors:
            if len(item) > 0 and w==item:continue
            sim.append([w,self.sim(vec, model.vectors[w])])
        sorted_sim = heapq.nlargest(self.topN, sim, key=lambda x: x[1])
        for s in sorted_sim:
            label = s[0]
            if not isinstance(idDic, type(None)) and label in idDic:
                label = idDic[label]
            tmp_line = "{0}:{1}\n".format(label, s[1])
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

    def process(self):
        while (1):
            item = input("Enter word or entity (EXIT to break): ")
            if item == 'EXIT': break
            m = inputRE.match(item)
            if not m:
                print("Error format! Please input again! Format:\"[w|e]:[en|zh|es]:item\"\nFor example, w:en:apple\n")
                continue
            tmp_type = m.group(1)
            tmp_lang = m.group(2)
            item = m.group(3)

            item_type = Options.word_type if tmp_type == 'w' else Options.entity_type
            item_lang = Options.getLangType(tmp_lang)
            self.findNeighbors(item, item_type, item_lang)
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
