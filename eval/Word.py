#!/usr/bin/env python
# -*- coding: utf-8 -*-
import codecs
import struct
import numpy as np
import regex as re

class Word():

    def __init__(self):
        self.vocab_size = 0
        self.layer_size = 0
        self.vectors = None
        self.vocab_dic = None

    def initVectorFormat(self, size):
        tmp_struct_fmt = []
        for i in range(size):
            tmp_struct_fmt.append('f')
        p_struct_fmt = "".join(tmp_struct_fmt)
        return p_struct_fmt

    def loadVocab(self, file):
        vocab = set()
        with codecs.open(file, 'r', encoding='UTF-8') as fin:
            for line in fin:
                items = re.split(r'\t', line.strip())
                if (items[0] == '</s>'): continue
                vocab.add(items[0])
        print('load vocab of {0} words!'.format(len(vocab)))
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
        print('load vocab of {0} words!'.format(len(self.vocab_dic)))

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
                if not isinstance(vocab, type(None)) and label in vocab:
                    self.vectors[label] = tmp_vec
                fin_vec.read(1)     #\n
            self.vocab_size = len(self.vectors)
            print('load {0} words!'.format(self.vocab_size))

    def saveVector(self, filename):
        with codecs.open(filename, 'wb') as fout:
            fout.write("{0} {1}\n".format(self.vocab_size, self.layer_size))
            for label in self.vectors:
                fout.write("{0}\t".format(label.encode('utf-8')))
                for i in range(self.layer_size):
                    fout.write(struct.pack('f', self.vectors[label][i]))
                fout.write('\n')


if __name__ == '__main__':
    w = Word()
    word_vector_file = '/Users/ethan/Downloads/sub_words2'