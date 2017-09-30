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
        for i in xrange(size):
            tmp_struct_fmt.append('f')
        p_struct_fmt = "".join(tmp_struct_fmt)
        return p_struct_fmt

    def readVocab(self, file):
        vocab = set()
        with codecs.open(file, 'r', encoding='UTF-8') as fin:
            for line in fin:
                items = re.split(r'\t', line.strip())
                if items[0] in self.vectors:
                    vocab.add(items[0])
        print('read {0} entities!'.format(len(vocab)))
        return vocab

    def sample(self, subvocab_file, vector_file,  sample_file):
        new_vocab = self.readVocab(subvocab_file)
        new_vocab_size = len(new_vocab)
        new_word_count = 0
        vocab_size = 0
        layer_size = 0
        print('new vocab size: {0}\n'.format(new_vocab_size))
        with codecs.open(vector_file, 'rb') as fin_vec:
            with codecs.open(sample_file, 'wb') as fout_vec:
                # read file head: vocab size and layer size
                char_set = []
                while True:
                    ch = fin_vec.read(1)
                    if ch == ' ':
                        vocab_size = (int)("".join(char_set))
                        del char_set[:]
                        continue
                    if ch == '\n':
                        layer_size = (int)("".join(char_set))
                        break
                    char_set.append(ch)
                fout_vec.write("{0} {1}\n".format(new_vocab_size, layer_size))
                for i in xrange(vocab_size):
                    # read entity label
                    del char_set[:]
                    while True:
                        ch = struct.unpack('c', fin_vec.read(1))[0]
                        if ch == '\t':
                            break
                        char_set.append(ch)
                    label = "".join(char_set).decode('utf-8')
                    if label in new_vocab:
                        new_word_count += 1
                        fout_vec.write("{0}\t".format(label.encode('utf-8')))
                        fout_vec.write(fin_vec.read(4 * layer_size))
                        fout_vec.write(fin_vec.read(1))
                    else:
                        fin_vec.read(4 * layer_size)
                        fin_vec.read(1)  # \n
        print('sample {0} entities!'.format(new_word_count))

    def loadVector(self, filename):
        if isinstance(self.vectors, type(None)): self.vectors = {}
        else: self.vectors.clear()
        with codecs.open(filename, 'rb') as fin_vec:
            # read file head: vocab size and layer size
            char_set = []
            while True:
                ch = fin_vec.read(1)
                if ch==b' ' or ch==b'\t':
                    self.vocab_size = (int)(b''.join(char_set))
                    del char_set[:]
                    continue
                if ch==b'\n':
                    self.layer_size = (int)(b''.join(char_set))
                    break
                char_set.append(ch)
            p_struct_fmt = self.initVectorFormat(self.layer_size)
            for i in xrange(self.vocab_size):
                # read entity label
                del char_set[:]
                while True:
                    tmp_c = fin_vec.read(1)
                    if not tmp_c : break
                    ch = struct.unpack('c', tmp_c)[0]
                    if ch==b'\t':
                        break
                    char_set.append(ch)
                if len(char_set) < 1: break
                label = b''.join(char_set).decode('utf-8')
                self.vectors[label] = np.array(struct.unpack(p_struct_fmt, fin_vec.read(4*self.layer_size)), dtype=float)
                fin_vec.read(1)     #\n
            self.vocab_size = len(self.vectors)
        print('load {0} entity vectors!'.format(len(self.vectors)))

if __name__ == '__main__':
    entity_vector_file = '/Users/ethan/Downloads/mlmpme/envec/vectors1_entity.dat'
    wiki_entity = Entity()
    wiki_entity.loadVector(entity_vector_file)