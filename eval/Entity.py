#!/usr/bin/env python
# -*- coding: utf-8 -*-
import codecs
import struct
import numpy as np
import regex as re

class Entity():

    def __init__(self):
        self.vocab_size = 0
        self.layer_size = 0
        self.entity_id = None
        self.id_entity = None
        self.vectors = None
        self.vocab_dic = None

    def loadVocab(self, filename):
        vocab = set()
        with codecs.open(filename, 'r', encoding='UTF-8') as fin:
            for line in fin:
                items = re.split(r'\t', line.strip())
                if (items[0] == '</s>'): continue
                vocab.add(items[0])
        print('load vocab of {0} entities!'.format(len(vocab)))
        return vocab

    @staticmethod
    def loadEntityDic(filename):
        entity_id = {}
        with codecs.open(filename, 'r', encoding='UTF-8') as fin:
            for line in fin:
                items = re.split(r'\t', line.strip())
                if len(items) < 2 or items[0]=="" or items[0] ==" ": continue
                entity_id[items[1]] = items[0]
        print('load {0} entities!'.format(len(entity_id)))
        return entity_id

    @staticmethod
    def loadEntityIdDic(filename):
        id_entity = {}
        with codecs.open(filename, 'r', encoding='UTF-8') as fin:
            for line in fin:
                items = re.split(r'\t', line.strip())
                if len(items) < 2 or items[0] == "" or items[0] == " ": continue
                id_entity[items[0]] = items[1]
        print('load {0} entities id!'.format(len(id_entity)))
        return id_entity

    def initVectorFormat(self, size):
        tmp_struct_fmt = []
        for i in range(size):
            tmp_struct_fmt.append('f')
        p_struct_fmt = "".join(tmp_struct_fmt)
        return p_struct_fmt

    def loadVocabDic(self, file, topn = 0):
        count = 0
        if isinstance(self.vocab_dic, type(None)):
            self.vocab_dic = {}
        with codecs.open(file, 'r', encoding='UTF-8') as fin:
            for line in fin:
                items = re.split(r'\t', line.strip())
                if (len(items)<2 or items[0] == '</s>'): continue
                count += 1
                if topn <= 0 or count >= topn: break
                self.vocab_dic[items[0]] = int(items[1])
        print('load vocab of {0} entities!'.format(len(self.vocab_dic)))

    def loadVector(self, filename, vocab = None):
        if isinstance(self.vectors, type(None)):
            self.vectors = {}
        with codecs.open(filename, 'rb') as fin_vec:
            # read file head: vocab size and layer size
            char_set = []
            while True:
                ch = fin_vec.read(1)
                if ch==b' ' or ch== b'\t':
                    self.vocab_size = (int)(b''.join(char_set).decode())
                    del char_set[:]
                    continue
                if ch==b'\n':
                    self.layer_size = (int)(b''.join(char_set).decode())
                    break
                char_set.append(ch)
            p_struct_fmt = self.initVectorFormat(self.layer_size)
            for i in range(self.vocab_size):
                # read entity label
                del char_set[:]
                while True:
                    ch = struct.unpack('c',fin_vec.read(1))[0]
                    # add split interval white space
                    if ch==b' ' or ch==b'\t':
                        break
                    char_set.append(ch)
                label = b''.join(char_set).decode('utf-8')
                tmp_vec = np.array(struct.unpack(p_struct_fmt, fin_vec.read(4*self.layer_size)), dtype=float)
                if isinstance(vocab, type(None)) or (not isinstance(vocab, type(None)) and label in vocab):
                    self.vectors[label] = tmp_vec
                fin_vec.read(1)     #\n
            self.vocab_size = len(self.vectors)
            print('load {0} entities!'.format(self.vocab_size))

    def saveVector(self, filename):
        with codecs.open(filename, 'wb') as fout:
            fout.write("{0} {1}\n".format(self.vocab_size, self.layer_size))
            for label in self.vectors:
                fout.write("{0}\t".format(label.encode('utf-8')))
                for i in range(self.layer_size):
                    fout.write(struct.pack('f', self.vectors[label][i]))
                fout.write('\n')

if __name__ == '__main__':
    entity_vector_file = '/Users/ethan/Downloads/mlmpme/envec/vectors1_entity.dat'
    wiki_entity = Entity()
    wiki_entity.loadVector(entity_vector_file)