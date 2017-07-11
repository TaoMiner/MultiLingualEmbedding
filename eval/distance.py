#!/usr/bin/env python
# -*- coding: utf-8 -*-
from Entity import Entity
from Word import Word
from Sense import Sense
from scipy import spatial
import os
import codecs

languages = [u'en',u'zh']
topn = 10

class Ruler():
    def __init__(self):
        self.words = None
        self.entities = None
        self.senses = None

    def loadModels(self, op):
        if os.path.isfile(op.word_vector_file):
            self.words = Word()
            self.words.loadVector(op.word_vector_file)
        if os.path.isfile(op.entity_vector_file) and os.path.isfile(op.entity_dic_file):
            self.entities = Entity()
            self.entities.entity_id = self.entities.loadEntityDic(op.entity_dic_file)
            self.entities.id_entity = self.entities.loadEntityIdDic(op.entity_dic_file)
            self.entities.loadVector(op.entity_vector_file)
        if os.path.isfile(op.sense_vector_file) and not isinstance(self.entities,type(None)):
            self.senses = Sense()
            self.senses.setIdEntityDic(self.entities.id_entity)
            self.senses.loadVector(op.sense_vector_file)
            self.senses.buildMultiProto()

    def getWordVec(self, word):
        if not isinstance(self.words,type(None)) and word in self.words.vectors:
            return self.words.vectors[word]
        return []

    def getSenseVec(self, mention):
        if not isinstance(self.senses, type(None)):
            senses = self.senses.getMentSense(mention)
            if len(senses)>=1:
                if len(senses)==1: return self.senses.vectors[senses[0]]
                out = 'please input the candidate number: \n'
                for i in xrange(len(senses)):
                    if senses[i] not in self.entities.id_entity: continue
                    out += str(i) + ':' + self.entities.id_entity[senses[i]] + '\n'
                sense_index = int(raw_input(out))
                if sense_index >=0 and sense_index < len(senses) and senses[sense_index] in self.entities.id_entity:
                    return self.senses.vectors[senses[sense_index]]
        return []

    @staticmethod
    def findNearest(vec, model, topN, idDic=None, fout=None):
        sim = []
        tmp_line = u"\n                                              Cosine distance\n------------------------------------------------------------------------\n"
        output(fout,tmp_line)
        for w in model.vectors:
            sim.append([w,spatial.distance.cosine(vec,model.vectors[w])])
        sorted_sim = sorted(sim, key=lambda x: x[1])[:topN]

        for s in sorted_sim:
            if not isinstance(idDic, type(None)) and s[0] in idDic:
                tmp_line = u"%s:%f" % (idDic[s[0]], s[1])
                output(fout,tmp_line)
            else:
                tmp_line = u"%s:%f" % (s[0], s[1])
                output(fout, tmp_line)

class options():
    def __init__(self, lang):
        lang_index = str(languages.index(lang) + 1)

        self.vec_path = '/home/caoyx/data/etc/exp2/'+lang+'vec/'
        self.word_vector_file = self.vec_path + 'vectors'+ lang_index +'_word5'
        self.entity_vector_file = self.vec_path + 'vectors'+ lang_index +'_entity5'
        self.sense_vector_file = self.vec_path + 'vectors'+ lang_index +'_senses5'
        self.entity_dic_file = '/home/caoyx/data/dump20170401/'+lang+'wiki_cl/vocab_entity.dat'
        '''
        self.vec_path = '/Users/ethan/Downloads/mlmpme/' + lang + 'vec/'
        self.word_vector_file = self.vec_path + 'vectors'+ lang_index +'_word1'
        self.entity_vector_file = self.vec_path + 'vectors'+lang_index+'_entity1'
        self.sense_vector_file = self.vec_path + 'vectors'+lang_index+'_senses1'
        self.entity_dic_file = '/Users/ethan/Downloads/mlmpme/'+lang + 'wiki_cl/vocab_entity.dat'
        '''

class distance():
    def __init__(self):
        self.num_lang = len(languages)
        self.ops = [options(l) for l in languages]
        self.rulers = [Ruler() for i in xrange(self.num_lang)]
        for i in xrange(self.num_lang):
            self.rulers[i].loadModels(self.ops[i])

    def process(self, log_file = None):
        fout = None
        if not isinstance(log_file, type(None)):
            fout = codecs.open(log_file, 'w', encoding='UTF-8')
        while (1):
            item = raw_input("Enter word or mention (EXIT to break): ")
            if item == 'EXIT': break
            item = item.decode('utf-8')
            tmp_word_vec = []
            for i in xrange(self.num_lang):
                tmp_word_vec = self.rulers[i].getWordVec(item)
                if len(tmp_word_vec) > 0: break
            tmp_sense_vec = []
            for i in xrange(self.num_lang):
                tmp_sense_vec = self.rulers[i].getSenseVec(item)
                if len(tmp_sense_vec) > 0: break

            if len(tmp_word_vec) > 0:
                tmp_line = u"Finding nearest words for %s!" % item
                output(fout, tmp_line)
                for i in xrange(self.num_lang):
                    tmp_line = u"Searching %s words ..." % languages[i]
                    output(fout,tmp_line)
                    Ruler.findNearest(tmp_word_vec, self.rulers[i].words, topn, fout=fout)
            else:
                tmp_line = u"no such word!"
                output(fout, tmp_line)

            if len(tmp_sense_vec) > 0:
                tmp_line = u"Finding nearest entities for %s!" % item
                output(fout, tmp_line)
                for i in xrange(self.num_lang):
                    tmp_line = u"Searching %s entities ..." % languages[i]
                    output(fout,tmp_line)
                    Ruler.findNearest(tmp_sense_vec, self.rulers[i].senses, topn, idDic=self.rulers[i].entities.id_entity, fout=fout)
            else:
                tmp_line = u"no such entity!"
                output(fout,tmp_line)
        if not isinstance(fout, type(None)):
            fout.close()

def output(fout, str):
    if isinstance(fout, type(None)):
        print str.encode('utf-8')
    else:
        fout.write("%s\n" % str)

if __name__ == '__main__':
    log_file = './distance.out'
    dis = distance()
    dis.process()
