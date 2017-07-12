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
        for i in xrange(size):
            tmp_struct_fmt.append('f')
        p_struct_fmt = "".join(tmp_struct_fmt)
        return p_struct_fmt

    def readVocab(self, file):
        vocab = set()
        with codecs.open(file, 'r', encoding='UTF-8') as fin:
            for line in fin:
                items = re.split(r'\t', line.strip())
                vocab.add(items[0])
        print 'read %d words!' % len(vocab)
        return vocab

    def sample(self, subvocab_file, vector_file,  sample_file):
        new_vocab = self.readVocab(subvocab_file)
        new_vocab_size = len(new_vocab)
        new_word_count = 0
        vocab_size = 0
        layer_size = 0
        print 'new vocab size: %d\n' % new_vocab_size
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
                fout_vec.write("%d %d\n" % (new_vocab_size, layer_size))
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
                        fout_vec.write("%s\t" % label.encode('utf-8'))
                        fout_vec.write(fin_vec.read(4 * layer_size))
                        fout_vec.write(fin_vec.read(1))
                    else:
                        fin_vec.read(4 * layer_size)
                        fin_vec.read(1)  # \n
        print 'sample %d words!' % new_word_count

    def sampleMulti(self, vocab_file, vector_file,  sample_file, lang):
        new_vocab = self.readVocab(vocab_file)
        new_vocab_size = len(new_vocab)
        new_word_count = 0
        vocab_size = 0
        layer_size = 0
        print 'new vocab size: %d\n' % new_vocab_size
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
                        str_o = label
                        for i in xrange(layer_size):
                            str_o = str_o + ' ' + str(struct.unpack('f', fin_vec.read(4)))
                        str_o += '\n'
                        fin_vec.read(1)
                        fout_vec.write(str_o)
                    else:
                        fin_vec.read(4 * layer_size)
                        fin_vec.read(1)  # \n
        print 'sample %d words!' % new_word_count

    def loadVector(self, filename):
        if isinstance(self.vectors, type(None)): self.vectors = {}
        else: self.vectors.clear()
        with codecs.open(filename, 'rb') as fin_vec:
            # read file head: vocab size and layer size
            char_set = []
            while True:
                ch = fin_vec.read(1)
                if ch==' ' or ch=='\t':
                    self.vocab_size = (int)("".join(char_set))
                    del char_set[:]
                    continue
                if ch=='\n':
                    self.layer_size = (int)("".join(char_set))
                    break
                char_set.append(ch)
            p_struct_fmt = self.initVectorFormat(self.layer_size)
            for i in xrange(self.vocab_size):
                # read entity label
                del char_set[:]
                while True:
                    ch = struct.unpack('c',fin_vec.read(1))[0]
                    # add split interval white space
                    if ch==' ' or ch=='\t':
                        break
                    char_set.append(ch)
                label = "".join(char_set).decode('utf-8')
                self.vectors[label] = np.array(struct.unpack(p_struct_fmt, fin_vec.read(4*self.layer_size)), dtype=float)
                fin_vec.read(1)     #\n
            self.vocab_size = len(self.vectors)
            print 'load %d words!' % self.vocab_size

if __name__ == '__main__':
    lang = 'en'
    word_vector_file = '/home/caoyx/data/etc/exp2/' + lang + 'vec/vectors1_word5'
    vocab_file = '/home/caoyx/data/evaluation_vocabulary3'
    output_file = '/home/caoyx/data/etc/exp2/' + lang + 'vec/sub_words'
    word = Word()
    word.sampleMulti(vocab_file,word_vector_file,output_file, lang)