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
        self.vocab_size = 0
        self.layer_size = 0
        self.vectors = None
        self.vocab_dic = None
        # context cluster center
        self.mu = None

    def loadVocab(self, filename):
        vocab = set()
        with codecs.open(filename, 'r', encoding='UTF-8') as fin:
            for line in fin:
                items = re.split(r'\t', line.strip())
                if (items[0] == '</s>'): continue
                vocab.add(items[0])
        print('load vocab of {0} senses!'.format(len(vocab)))
        return vocab

    def loadVocabDic(self, file, topn = 0):
        count = 0
        if isinstance(self.vocab_dic, type(None)):
            self.vocab_dic = {}
        with codecs.open(file, 'r', encoding='UTF-8') as fin:
            for line in fin:
                items = re.split(r'\t', line.strip())
                if (items[0] == '</s>'): continue
                count += 1
                if topn <= 0 or count >= topn: break
                self.vocab_dic[items[0]] = int(items[1])
        print('load vocab of {0} senses!'.format(len(self.vocab_dic)))

    def initVectorFormat(self, size):
        tmp_struct_fmt = []
        for i in range(size):
            tmp_struct_fmt.append('f')
        p_struct_fmt = "".join(tmp_struct_fmt)
        return p_struct_fmt

    def loadVector(self, filename, vocab = None):
        if isinstance(self.vectors, type(None)):
            self.vectors = {}
            self.mu = {}
        with codecs.open(filename, 'rb') as fin_vec:
            # read file head: vocab size, layer size and max_sense_num
            char_set = []
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
                    ch = struct.unpack('c',fin_vec.read(1))[0]
                    # add split interval white space
                    if ch==b' ' or ch==b'\t':
                        break
                    char_set.append(ch)
                label = b''.join(char_set).decode('utf-8')
                # embedding
                tmp_vec = np.array(struct.unpack(p_struct_fmt, fin_vec.read(4*self.layer_size)), dtype=float)
                # context cluster senter
                tmp_mu = np.array(struct.unpack(p_struct_fmt, fin_vec.read(4*self.layer_size)), dtype=float)
                if not isinstance(vocab, type(None)) and label in vocab:
                    self.vectors[label] = tmp_vec
                    self.mu[label] = tmp_mu
                fin_vec.read(1)  # \n
            self.vocab_size = len(self.vectors)
        print('load {0} senses!'.format(self.vocab_size))

if __name__ == '__main__':
    sense_vector_file = '/Users/ethan/Downloads/mlmpme/envec/vectors1_senses1'
    entity_dic_file = '/Users/ethan/Downloads/mlmpme/vocab_entity.dat'
    wiki_sense = Sense()
    wiki_sense.loadVector(sense_vector_file)