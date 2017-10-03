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

    def initVectorFormat(self, size):
        tmp_struct_fmt = []
        for i in range(size):
            tmp_struct_fmt.append('f')
        p_struct_fmt = "".join(tmp_struct_fmt)
        return p_struct_fmt

    def readVocab(self, file):
        vocab = set()
        with codecs.open(file, 'r', encoding='UTF-8') as fin:
            for line in fin:
                items = re.split(r'\t', line.strip())
                vocab.add(items[0])
        print('read {0} words!'.format(len(vocab)))
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
        print('sample {0} words!'.format(new_word_count))

    def sampleMulti(self, vocab_file, vector_file,  sample_file, lang):
        new_vocab = self.readVocab(vocab_file)
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
                for i in xrange(vocab_size):
                    # read entity label
                    del char_set[:]
                    while True:
                        ch = struct.unpack('c', fin_vec.read(1))[0]
                        if ch == '\t':
                            break
                        char_set.append(ch)
                    label = "".join(char_set).decode('utf-8')
                    label = lang + ":" + label
                    str_o = ''
                    if label in new_vocab:
                        new_word_count += 1
                        str_o = label.encode('utf-8')
                        for i in xrange(layer_size):
                            str_o = "{0} {1:%17f}".format(str_o, struct.unpack('f', fin_vec.read(4))[0])
                        str_o += '\n'
                        fin_vec.read(1)
                        fout_vec.write(str_o)
                    else:
                        fin_vec.read(4 * layer_size)
                        fin_vec.read(1)  # \n
        print('sample {0} words!'.format(new_word_count))

    def loadVector(self, filename):
        if isinstance(self.vectors, type(None)): self.vectors = {}
        else: self.vectors.clear()
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
                self.vectors[label] = np.array(struct.unpack(p_struct_fmt, fin_vec.read(4*self.layer_size)), dtype=float)
                fin_vec.read(1)     #\n
            self.vocab_size = len(self.vectors)
            print('load {0} words!'.format(self.vocab_size))

if __name__ == '__main__':
    w = Word()
    word_vector_file = '/Users/ethan/Downloads/sub_words2'
    '''
    lang = 'en'
    word_vector_file = '/home/caoyx/data/etc/exp2/' + lang + 'vec/vectors1_word5'
    vocab_file = '/home/caoyx/data/evaluation_vocabulary3'
    output_file = '/home/caoyx/data/etc/exp2/' + lang + 'vec/sub_words'
    word = Word()
    word.sampleMulti(vocab_file,word_vector_file,output_file, lang)
    '''