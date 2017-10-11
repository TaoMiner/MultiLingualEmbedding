#!/usr/bin/env python
# -*- coding: utf-8 -*-
import codecs
import struct
import numpy as np
import regex as re
from Entity import Entity

titleRE = re.compile(r' \([^\(]*?\)$')
class Sense():

    def __init__(self):
        self.vocab = None
        self.vocab_size = 0
        self.layer_size = 0
        self.vectors = None
        # context cluster center
        self.mu = None
        self.mention_dic = None
        self.id_entity = None

    def loadVocab(self, filename):
        if isinstance(self.vocab, type(None)):
            self.vocab = set()
        with codecs.open(filename, 'r', encoding='UTF-8') as fin:
            for line in fin:
                items = re.split(r'\t', line.strip())
                self.vocab.add(items[0])
        print('load vocab of {0} senses!'.format(len(self.vocab)))

    def getMentSense(self, mention):
        senses = []
        if not isinstance(self.mention_dic,type(None)) and mention in self.mention_dic:
            senses = self.mention_dic[mention]
        return senses

    def getSenseTitle(self, sense_id):
        title = ''
        if not isinstance(self.id_entity,type(None)) and sense_id in self.id_entity:
            title = self.id_entity[sense_id]
        if len(title) > 0:
            title = titleRE.sub('', title)
        return title

    def setIdEntityDic(self, id_entity):
        self.id_entity = id_entity

    def buildMultiProto(self):
        if isinstance(self.id_entity, type(None)):
            print("please set id entity dic!")
            return
        if isinstance(self.mention_dic, type(None)):
            self.mention_dic = {}
        else: self.mention_dic.clear()
        for t_id in self.vectors:
            title = self.getSenseTitle(t_id)
            if len(title) < 1 : continue
            tmp_senses = self.mention_dic[title] if title in self.mention_dic else []
            tmp_senses.append(t_id)
            self.mention_dic[title] = tmp_senses
        print("successfully build {0} multiproto mentions!".format(len(self.mention_dic)))

    def initVectorFormat(self, size):
        tmp_struct_fmt = []
        for i in range(size):
            tmp_struct_fmt.append('f')
        p_struct_fmt = "".join(tmp_struct_fmt)
        return p_struct_fmt

    def loadVector(self, filename):
        if isinstance(self.vectors, type(None)):
            self.vectors = {}
            self.mu = {}
        else:
            self.vectors.clear()
            self.mu.clear()
        with codecs.open(filename, 'rb') as fin_vec:
            # read file head: vocab size, layer size and max_sense_num
            char_set = []
            var_pos = 0
            while True:
                ch = fin_vec.read(1)
                if ch == b' ' or ch == b'\t':
                    self.vocab_size = (int)(b''.join(char_set))
                    del char_set[:]
                    continue
                if ch == b'\n':
                    self.layer_size = (int)(b''.join(char_set))
                    break
                char_set.append(ch)
            p_struct_fmt = self.initVectorFormat(self.layer_size)
            for i in range(self.vocab_size):
                # read title label
                del char_set[:]
                while True:
                    tmp_c = fin_vec.read(1)
                    if not tmp_c: break
                    ch = struct.unpack('c', tmp_c)[0]
                    if ch == b'\t':
                        break
                    char_set.append(ch)
                if len(char_set) < 1: break
                label = b''.join(char_set).decode('utf-8')
                # embedding
                self.vectors[label] = np.array(struct.unpack(p_struct_fmt, fin_vec.read(4*self.layer_size)), dtype=float)
                # context cluster senter
                self.mu[label] = np.array(struct.unpack(p_struct_fmt, fin_vec.read(4*self.layer_size)), dtype=float)
                fin_vec.read(1)  # \n
            self.vocab_size = len(self.vectors)
        print('load {0} senses!'.format(self.vocab_size))

if __name__ == '__main__':
    sense_vector_file = '/Users/ethan/Downloads/mlmpme/envec/vectors1_senses1'
    entity_dic_file = '/Users/ethan/Downloads/mlmpme/vocab_entity.dat'
    wiki_sense = Sense()
    wiki_sense.setIdEntityDic(Entity.loadEntityIdDic(entity_dic_file))
    wiki_sense.loadVector(sense_vector_file)
    wiki_sense.buildMultiProto()