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

    def set(self, words, entities, senses):
        self.words = words
        self.entities = entities
        self.senses = senses

    def findNearestWords(self, vec, topN):
        sim = []
        for w in self.words.vectors:
            sim.append([w,spatial.distance.cosine(vec,self.words.vectors[w])])
        sorted_sim = sorted(sim, key=lambda x: x[1])[:topN]
        print "\n                                              word      Cosine distance\n------------------------------------------------------------------------\n"
        for s in sorted_sim:
            print s

    def findNearestEntity(self, vec, topN):
        sim = []
        for e in self.entities.vectors:
            if e in self.entities.id_entity:
                sim.append([self.entities.id_entity[e], spatial.distance.cosine(vec,self.entities.vectors[e])])
        sorted_sim = sorted(sim, key=lambda x: x[1])[:topN]
        print "\n                                              entity       Cosine distance\n------------------------------------------------------------------------\n"
        for s in sorted_sim:
            print s

if __name__ == '__main__':
    topn = 10
    vec_path = '/data/m1/cyx/MultiMPME/etc/test/envec/'
    entity_dic_file = '/data/m1/cyx/MultiMPME/data/dumps20170401/enwiki_cl/vocab_entity.dat'

    word_vector_file = vec_path + 'vectors1_word.dat'
    entity_vector_file = vec_path + 'vectors1_entity.dat'
    sense_vector_file = vec_path + 'vectors1_senses.dat'
    wiki_word = Word()
    wiki_word.loadVector(word_vector_file)

    wiki_entity = Entity()
    wiki_entity.entity_id = wiki_entity.loadEntityDic(entity_dic_file)
    wiki_entity.id_entity = wiki_entity.loadEntityIdDic(entity_dic_file)
    wiki_entity.loadVector(entity_vector_file)

    wiki_sense = Sense()
    wiki_sense.setIdEntityDic(wiki_entity.id_entity)
    wiki_sense.loadVector(sense_vector_file)
    wiki_sense.buildMultiProto()

    dis = distance()
    dis.set(wiki_word, wiki_entity, wiki_sense)

    while(1):
        item = input("Enter word or mention (EXIT to break): ")
        if item == 'EXIT' : break
        if item in dis.words.vectors:
            dis.findNearestWords(dis.words.vectors[item], topn)
        senses = dis.senses.getMentSense(item)
        if senses:
            if len(senses) > 1:
                out = 'please input the candidate number: \n'
                for i in xrange(len(senses)):
                    if senses[i] not in dis.entities.id_entity : continue
                    out += i + ':' + dis.entities.id_entity[senses[i]] + '\n'
                sense_index = input(out)
                if sense_index < len(senses) and sense_index >= 0 and sense_index in dis.entities.id_entity:
                    dis.findNearestEntity(dis.senses.vectors[senses[sense_index]], topn)