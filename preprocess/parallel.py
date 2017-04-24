# -*- coding: utf-8 -*-
import re
import codecs
from itertools import izip
import string
import preprocess

options = preprocess.options
cleaner = preprocess.cleaner
languages = preprocess.languages

# <doc id="12" url="https://en.wikipedia.org/wiki?curid=12" title="Anarchism">
headerRE = re.compile(r'<doc.*?title="(.*?)">')
footerRE = re.compile(r'</doc>')
class Parallel():

    def __init__(self, lang1, lang2):
        # title:[[sent],...]
        if lang1 == lang2:
            print 'error:same languages!'
            exit()
        self.lang1 = lang1
        self.lang2 = lang2
        self.ops = [options(lang1), options(lang2)]
        self.corpus = [{},{}]
        self.clinks = {}
        self.parallel_contexts = []
        self.window = 5

    def loadCrossLink(self, filename):
        with codecs.open(filename, 'rb', 'utf-8') as fin:
            line_count = 0
            for line in fin:
                line_count += 1
                items = re.split(r'\t', line.strip())
                if len(items) != len(languages): continue
                if len(items[self.lang1]) > 0 and len(items[self.lang2]) > 0:
                    self.clinks[items[self.lang1]] = items[self.lang2]
        print 'successfully load %d clinks from %s to %s!' % (len(self.clinks), languages[self.lang1], languages[self.lang2])

    def readDoc(self):
        for i in xrange(2):
            self.readMonoDoc(i)

    def readMonoDoc(self, i):
        op = self.ops[i]
        with codecs.open(op.cross_corpus_file, 'rb', 'utf-8') as fin:
            cur_title = ''
            for line in fin:
                line = line.strip()
                if len(line) < 1: continue
                if not isinstance(footerRE.match(line), type(None)) :
                    cur_title = ''
                    continue
                m = headerRE.match(line)
                if m:
                    cur_title = m.group(1)
                    continue
                elif len(cur_title) > 0:
                    tmp_sents = self.corpus[i][cur_title] if cur_title in self.corpus[i] else []
                    tmp_sents.append(cleaner.cleanAnchorSent(line, op.lang, isReplaceId=False))
                    self.corpus[i][cur_title] = tmp_sents

    def extractContext(self, sents):
        contexts_dict = {}
        for sent in sents:
            cur = 0
            sent_words = []
            # [[start, end],...]
            anchors = []
            for s, e in  cleaner.findBalanced(sent):
                tmp_words = re.split(r' ', sent[cur:s])
                sent_words.extend(tmp_words)
                tmp_anchor = sent[s:e]
                tmp_vbar = tmp_anchor.find('|')
                tmp_label = ''
                tmp_title = ''
                if tmp_vbar > 0:
                    tmp_title = tmp_anchor[2:tmp_vbar]
                    tmp_label = tmp_anchor[tmp_vbar + 1 :-2]
                else:
                    tmp_label = tmp_anchor[2:-2]
                    tmp_title = tmp_label
                tmp_words = re.split(r' ', tmp_label)
                start_index = len(sent_words)
                sent_words.extend(tmp_words)
                length = len(tmp_words)
                if length > 0 and len(tmp_title) > 0:
                    anchors.append([tmp_title, start_index,length])
                cur = e
            if cur < len(sent):
                tmp_words = re.split(r' ', sent[cur:])
                sent_words.extend(tmp_words)
            # sent_words contains all words in sent
            # anchors contains start pos and end pos in the sentwords index
            for anc in anchors:
                tmp_contexts = []
                begin = anc[1]-self.window if anc[1]-self.window > 0 else 0
                end = anc[1] + anc[2] -1 + self.window if anc[1] + anc[2] -1 + self.window < len(sent_words) else len(sent_words)
                for i in xrange(begin, end):
                    if i >= anc[1] and i < anc[1]+anc[2]: continue
                    if len(sent_words[i]) > 0:
                        tmp_contexts.append(sent_words[i])
                if len(tmp_contexts) > 0:
                    contexts_dict[anc[0]] = tmp_contexts
        return contexts_dict

    def extract(self):
        for cl in self.clinks:
            if cl not in self.corpus[0] or self.clinks[cl] not in self.corpus[1]:
                continue
            sents1 = self.corpus[0][cl]
            sents2 = self.corpus[1][self.clinks[cl]]
            contexts_dict1 = self.extractContext(sents1)
            contexts_dict2 = self.extractContext(sents2)
            for t1 in contexts_dict1:
                if t1 not in self.clinks or self.clinks[t1] not in contexts_dict2:
                    continue
                self.parallel_contexts.append([contexts_dict1[t1], contexts_dict2[self.clinks[t1]]])
        print "successfully load %d parallel contexts!" % len(self.parallel_contexts)

    def saveParaData(self, filename):
        with codecs.open(filename, 'w', 'utf-8') as fout:
            for context in self.parallel_contexts:
                if len(context) != 2: continue
                fout.write("%s\t%s\n" % (' '.join(context[0]), ' '.join(context[1])))

if __name__ == '__main__':
    cross_file = '/data/m1/cyx/MultiMPME/data/dumps20170401/cross_links_all.dat'
    par_file = '/data/m1/cyx/MultiMPME/data/dumps20170401/para_data.dat'
    lang1 = languages.index('en')
    lang2 = languages.index('zh')
    par = Parallel(lang1, lang2)
    par.loadCrossLink(cross_file)
    par.readDoc()
    par.extract()
    par.saveParaData(par_file)