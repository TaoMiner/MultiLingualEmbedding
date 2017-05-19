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
        self.entity_dics = [None, None]
        self.corpus = [{},{}]
        self.clinks = {}
        self.parallel_contexts = []
        self.window = 15
        self.has_brace = True

    def loadCrossLink(self, filename):
        with codecs.open(filename, 'rb', 'utf-8') as fin:
            line_count = 0
            for line in fin:
                line_count += 1
                items = re.split(r'\t', line.strip('\n'))
                if len(items) != len(languages): continue
                if len(items[self.lang1]) > 0 and len(items[self.lang2]) > 0:
                    self.clinks[items[self.lang1]] = items[self.lang2]
        print 'successfully load %d clinks from %s to %s!' % (len(self.clinks), languages[self.lang1], languages[self.lang2])

    def readDoc(self):
        for i in xrange(2):
            self.readMonoDoc(i)
            print "successfully load %d doc for %s language!" % (len(self.corpus[i]), self.ops[i].lang)

    def readMonoDoc(self, i):
        op = self.ops[i]
        pre = preprocess.Preprocessor()
        entity_dic = pre.loadEntityDic(op.vocab_entity_file)
        redirects = pre.loadRedirects(op.redirect_file)
        with codecs.open(op.cross_corpus_file, 'rb', 'utf-8') as fin:
            cur_title_id = ''
            tmp_sents = None
            for line in fin:
                line = line.strip()
                tmp_line = ''
                if len(line) < 1: continue
                m = footerRE.match(line)
                if not isinstance(m, type(None)) :
                    self.corpus[i][cur_title_id] = tmp_sents
                    cur_title_id = ''
                    tmp_sents = None
                    continue
                m = headerRE.match(line)
                if m:
                    cur_title = redirects[m.group(1)] if m.group(1) in redirects else m.group(1)
                    cur_title_id = entity_dic[cur_title] if cur_title in entity_dic else ''
                    if len(cur_title_id) > 0:
                        tmp_sents = self.corpus[i][cur_title_id] if cur_title_id in self.corpus[i] else []
                    continue
                elif not isinstance(tmp_sents, type(None)) and len(cur_title_id) > 0:
                    tmp_line = cleaner.cleanAnchorSent(line, op.lang, isReplaceId=True, entity_id=entity_dic, redirects=redirects)
                    tmp_sents.append(tmp_line)

    def extractContext(self, sents):
        contexts_dict = {}
        for sent in sents:
            cur = 0
            sent_words = []
            # [[start, end],...]
            anchors = []
            for s, e in  cleaner.findBalanced(sent):
                tmp_words = re.split(r' ', sent[cur:s].strip())
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
                end = anc[1] + anc[2] + self.window + 1 if anc[1] + anc[2] + self.window +1 < len(sent_words) else len(sent_words)
                for i in xrange(begin, end):
                    if i >= anc[1] and i < anc[1]+anc[2]: continue
                    if len(sent_words[i]) > 0:
                        tmp_contexts.append(sent_words[i])
                if len(tmp_contexts) > 0:
                    contexts_dict[anc[0]] = tmp_contexts
        return contexts_dict

    # keep the anchor
    def extractContext2(self, sents, entity_dic=None, has_brace = False):
        contexts_dict = {}
        for sent in sents:
            cur = 0
            sent_words = []
            # [[start, end],...]
            anchors = []
            for s, e in  cleaner.findBalanced(sent):
                tmp_words = re.split(r' ', sent[cur:s].strip())
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
                    anchors.append([tmp_title, tmp_label, start_index,length])
                cur = e
            if cur < len(sent):
                tmp_words = re.split(r' ', sent[cur:])
                sent_words.extend(tmp_words)
            # sent_words contains all words in sent
            # anchors contains start pos and end pos in the sentwords index
            for anc in anchors:
                has_anchor = False
                tmp_contexts = []
                begin = anc[2]-self.window if anc[2]-self.window > 0 else 0
                end = anc[2] + anc[3] + self.window + 1 if anc[2] + anc[3] + self.window +1 < len(sent_words) else len(sent_words)
                for i in xrange(begin, end):
                    if i >= anc[2] and i < anc[2]+anc[3]:
                        if not has_anchor:
                            if isinstance(entity_dic, type(None)):
                                title = anc[0]
                            else:
                                title = entity_dic[anc[0]] if anc[0] in entity_dic else ''
                            if len(title) > 0:
                                if has_brace:
                                    tmp_anchor_str = '[[' + title + '|' + anc[1] + ']]'
                                else:
                                    tmp_anchor_str = anc[1]
                                tmp_contexts.append(tmp_anchor_str)
                                has_anchor = True
                            else:
                                del tmp_contexts[:]
                                break
                        continue
                    if len(sent_words[i]) > 0:
                        tmp_contexts.append(sent_words[i])
                if len(tmp_contexts) > 1:
                    tmp_context_set = contexts_dict[anc[0]] if anc[0] in contexts_dict else []
                    tmp_context_set.append(tmp_contexts)
                    contexts_dict[anc[0]] = tmp_context_set
        return contexts_dict

    def extract(self):
        num_nonequal = 0
        for cl in self.clinks:
            if cl not in self.corpus[0] or self.clinks[cl] not in self.corpus[1]:
                continue
            sents1 = self.corpus[0][cl]
            sents2 = self.corpus[1][self.clinks[cl]]
            contexts_dict1 = self.extractContext2(sents1, entity_dic=self.entity_dics[0], has_brace=self.has_brace)
            contexts_dict2 = self.extractContext2(sents2, entity_dic=self.entity_dics[1], has_brace=self.has_brace)
            for t1 in contexts_dict1:
                if t1 not in self.clinks or self.clinks[t1] not in contexts_dict2:
                    continue
                context_set1 = contexts_dict1[t1]
                context_set2 = contexts_dict2[self.clinks[t1]]
                min_set_num = min(len(context_set1), len(context_set2))
                for i in xrange(min_set_num):
                    self.parallel_contexts.append([context_set1[i], context_set2[i]])
                if len(context_set1) != len(context_set2):
                    num_nonequal += 1
        print "successfully load %d parallel contexts! non equal %d context!" % (len(self.parallel_contexts), num_nonequal)

    def saveParaData(self, filename):
        with codecs.open(filename, 'w', 'utf-8') as fout:
            for context in self.parallel_contexts:
                if len(context) != 2: continue
                if len(context[0]) <1 or len(context[1])<1: continue
                fout.write("%s\t%s\n" % (' '.join(context[0]), ' '.join(context[1])))

if __name__ == '__main__':
    str_lang1 = 'en'
    str_lang2 = 'es'
    cross_file = '/home/caoyx/data/dump20170401/cross_links_all_id.dat'
    par_file = '/home/caoyx/data/paradata/para_contexts2.' + str_lang1 + '-' + str_lang2
    lang1 = languages.index(str_lang1)
    lang2 = languages.index(str_lang2)
    par = Parallel(lang1, lang2)
    par.loadCrossLink(cross_file)
    par.entity_dics[0] = preprocess.Preprocessor.loadEntityIdDic(par.ops[0].vocab_entity_file)
    par.entity_dics[1] = preprocess.Preprocessor.loadEntityIdDic(par.ops[1].vocab_entity_file)
    # whether output brace for anchors
    par.has_brace = True
    par.readDoc()
    par.extract()
    par.saveParaData(par_file)