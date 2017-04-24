# -*- coding: utf-8 -*-
import re
import codecs
from itertools import izip
import string
from preprocess import cleaner, options

ENGLISH = 0
CHINESE = 1
SPANISH = 2
languages = ('enwiki', 'zhwiki', 'eswiki')

# <doc id="12" url="https://en.wikipedia.org/wiki?curid=12" title="Anarchism">
headerRE = re.compile(r'<doc.*?title="(.*?)">')
footerRE = re.compile(r'</doc>')
class Parallel():

    def __init__(self, lang1, lang2):
        # title:[[sent],...]
        self.ops = [options(lang1), options(lang2)]
        self.corpus = [{},{}]
        self.clinks = {}
        self.parallel_contexts = []
        self.window = 5

    def getIndex(self, lang):
        index = -1
        if lang == 'enwiki':
            index = 0
        elif lang == 'zhwiki':
            index = 1
        elif lang == 'eswiki':
            index = 2
        return index

    def loadCrossLink(self, filename):
        with codecs.open(filename, 'rb', 'utf-8') as fin:
            line_count = 0
            for line in fin:
                line_count += 1
                if line_count < 2: continue
                items = re.split(r'\t', line.strip())
                if len(items) != 3: continue
                from_index = self.getIndex(self.ops[0].lang)
                to_index = self.getIndex(self.ops[1].lang)
                if from_index == -1 or to_index == -1 or from_index == to_index:
                    print 'error two languages!'
                    return
                for i in xrange(3):
                    if len(items[from_index]) > 0 and len(items[to_index]) > 0:
                        self.clinks[items[from_index]] = items[to_index]
        print 'successfully load %d clinks from %s to %s!' % (len(self.clinks), self.ops[0].lang, self.ops[1].lang)

    def readDoc(self):
        for i in xrange(2):
            self.readMonoDoc(self.ops[i])

    def readMonoDoc(self, op):
        with codecs.open(op.corpus_file, 'rb', 'utf-8') as fin:
            cur_title = None
            for line in fin:
                line = line.strip()
                if len(line) < 1 or not isinstance(footerRE.match(line), type(None)): continue
                m = headerRE.match(line)
                if m:
                    cur_title = m.group(1)
                    if len(cur_title) < 1:
                        cur_title = None
                    continue
                elif not isinstance(cur_title, type(None)):
                    tmp_sents = op.corpus[cur_title] if cur_title in op.corpus else []
                    tmp_sents.append(cleaner.cleanAnchorSent(line, op.lang, isReplaceId=False))
                    op.corpus[cur_title] = tmp_sents

    def extractContext(self, sents, op):
        contexts_dict = {}
        for sent in sents:
            sent_cl = op.cl.cleanSent(sent)
            for s, e in  op.cl.findBalanced(sent):

        return contexts_dict

    def extract(self):
        for cl in self.clinks:
            if cl not in self.ops[0].corpus or self.clinks[cl] not in self.ops[1].corpus:
                continue
            sents1 = self.ops[0].corpus[cl]
            sents2 = self.ops[1].corpus[self.clinks[cl]]
            contexts_dict1 = self.extractContext(sents1)
            contexts_dict2 = self.extractContext(sents2)
            for t1 in contexts_dict1:
                if t1 not in self.clinks or self.clinks[t1] not in contexts_dict2:
                    continue
                self.parallel_contexts.append([contexts_dict1[t1], contexts_dict2[self.clinks[t1]]])
        print "successfully load %d parallel contexts!" % len(self.parallel_contexts)