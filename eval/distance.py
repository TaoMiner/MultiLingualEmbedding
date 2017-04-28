#!/usr/bin/env python
# -*- coding: utf-8 -*-
from Entity import Entity
from Word import Word
from Sense import Sense
from scipy import spatial

class distance():
    def __init__(self):
        self.words = None
        self.entities = None
        self.senses = None

    def loadModels(self, op):
        self.words = Word()
        self.words.loadVector(op.word_vector_file)

        self.entities = Entity()
        self.entities.entity_id = self.entities.loadEntityDic(op.entity_dic_file)
        self.entities.id_entity = self.entities.loadEntityIdDic(op.entity_dic_file)
        self.entities.loadVector(op.entity_vector_file)

        self.senses = Sense()
        self.senses.setIdEntityDic(self.entities.id_entity)
        self.senses.loadVector(op.sense_vector_file)
        self.senses.buildMultiProto()

    def getWordVec(self, word):
        if word in self.words.vectors:
            return self.words.vectors[word]
        return []

    def getSenseVec(self, mention):
        senses = self.senses.getMentSense(mention)
        if senses and len(senses)>=1:
            if len(senses)==1: return self.senses.vectors[senses[0]]
            out = 'please input the candidate number: \n'
            for i in xrange(len(senses)):
                if senses[i] not in self.entities.id_entity: continue
                out += i + ':' + self.entities.id_entity[senses[i]] + '\n'
            sense_index = int(raw_input(out))
            if sense_index >=0 and sense_index < len(senses) and senses[sense_index] in self.entities.id_entity:
                return self.senses.vectors[senses[sense_index]]
        return []

    @staticmethod
    def findNearest(vec, model, topN, idDic=None):
        sim = []
        print "\n                                              Cosine distance\n------------------------------------------------------------------------\n"
        for w in model.vectors:
            sim.append([w,spatial.distance.cosine(vec,model.vectors[w])])
        sorted_sim = sorted(sim, key=lambda x: x[1])[:topN]

        for s in sorted_sim:
            if not isinstance(idDic, type(None)):
                print "%s:%f" % (idDic[s[0]].encode('utf-8'), s[1])
            else:
                print "%s:%f" % (s[0].encode('utf-8'), s[1])

class options():
    def __init__(self, lang):
        self.vec_path = '/Users/ethan/Downloads/mlmpme/'+lang+'vec/'
        self.word_vector_file = self.vec_path + 'vectors1_word1'
        self.entity_vector_file = self.vec_path + 'vectors1_entity1'
        self.sense_vector_file = self.vec_path + 'vectors1_senses1'
        self.entity_dic_file = '/Users/ethan/Downloads/mlmpme/vocab_entity.dat'

if __name__ == '__main__':
    topn = 10
    languages = ['en']
    num_lang = len(languages)
    ops = [options(l) for l in languages]

    rulers = [distance() for i in xrange(num_lang)]
    for i in xrange(num_lang):
        rulers[i].loadModels(ops[i])


    while(1):
        item = raw_input("Enter word or mention (EXIT to break): ")
        if item == 'EXIT' : break
        item = item.decode('utf-8')
        tmp_word_vec = []
        for i in xrange(num_lang):
            tmp_word_vec = rulers[i].getWordVec(item)
            if len(tmp_word_vec) > 0: break
        tmp_sense_vec = []
        for i in xrange(num_lang):
            tmp_sense_vec = rulers[i].getSenseVec(item)
            if len(tmp_sense_vec) > 0: break

        if len(tmp_word_vec) > 0:
            print "Finding nearest words for %s!" % item.encode('utf-8')
            for i in xrange(num_lang):
                print "Searching %s words ..." % languages[i]
                distance.findNearest(tmp_word_vec, rulers[i].words, topn)
        else:
            print "no such word!"

        if len(tmp_sense_vec) > 0:
            print "Finding nearest entities for %s!" % item.encode('utf-8')
            for i in xrange(num_lang):
                print "Searching %s entities ..." % languages[i]
                distance.findNearest(tmp_sense_vec, rulers[i].senses, topn, rulers[i].entities.id_entity)
        else:
            print "no such entity!"
