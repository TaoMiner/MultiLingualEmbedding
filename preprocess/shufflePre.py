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
headerRE = re.compile(r'<doc id="(.*?)".*>')
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
        self.stop_words = [set(), set()]
        self.words = [{}, {}]    # vocab {w:freq,...}

    def loadStopWords(self, filename):
        stopwords = set()
        with codecs.open(filename, 'rb', 'utf-8') as fin:
            for line in fin:
                stopwords.add(line.strip())
        return stopwords

    def loadWordVocab(self, filename):
        words = set()
        with codecs.open(filename, 'rb', 'utf-8') as fin:
            for line in fin:
                items = re.split(r'\t', line.strip())
                words.add(items[0])
        return words

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
        entity_id_dic = pre.loadEntityIdDic(op.vocab_entity_file)
        total_entity_id, total_id_entity = pre.loadWikiIndex(op.entity_index_dump)
        redirects_id = pre.loadRedirectsId(op.redirect_file, total_entity_id)
        with codecs.open(op.cross_corpus_file, 'rb') as fin:
            cur_title_id = ''
            tmp_sents = None
            for line in fin:
                line = line.decode('utf-8', 'ignore')
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
                    cur_title_id = m.group(1) if m.group(1) in entity_id_dic else ''
                    cur_title_id = redirects_id[cur_title_id] if cur_title_id in redirects_id else cur_title_id
                    if len(cur_title_id) > 0:
                        tmp_sents = self.corpus[i][cur_title_id] if cur_title_id in self.corpus[i] else []
                    continue
                elif not isinstance(tmp_sents, type(None)) and len(cur_title_id) > 0:
                    if self.lang2 == languages.index('zh') and i == 1:
                        tmp_line = line.strip()
                    else:
                        tmp_line = cleaner.removeAnchorSent(line, op.lang)
                    tmp_sents.append(tmp_line)

    def merge(self, filename):
        with codecs.open(filename, 'w','utf8') as fout:
            for cl in self.clinks:
                if cl not in self.corpus[0] or self.clinks[cl] not in self.corpus[1]:
                    continue
                sents1 = self.corpus[0][cl]
                sents2 = self.corpus[1][self.clinks[cl]]
                # sents=['','','',...]
                long_sents = sents1 if len(sents1)>len(sents2) else sents2
                short_sents = sents2 if len(sents1)>len(sents2) else sents1
                for sent in sents1:
                    items = re.split(r' ', sent)
                    for item in items:
                        tmp_count = self.words[0][item] if item in self.words[0] else 0
                        tmp_count += 1
                        self.words[0][item] = tmp_count
                for sent in sents2:
                    items = re.split(r' ', sent)
                    for item in items:
                        tmp_count = self.words[1][item] if item in self.words[1] else 0
                        tmp_count += 1
                        self.words[1][item] = tmp_count

                ratio = len(long_sents)/len(short_sents)
                ratio = int(ratio)
                if ratio <= 0 : ratio = 1
                bi_sents = []
                for i in range(len(short_sents)):
                    bi_sents.append(short_sents[i])
                    bi_sents.extend(long_sents[i*ratio:(i+1)*ratio])
                if len(bi_sents)>0:
                    fout.write('%s\n' % '\n'.join(bi_sents))

        print "successfully load %d parallel contexts!" % len(self.parallel_contexts)

    def saveVocab(self, vocab, filename):
        with codecs.open(filename, 'w','utf8') as fout:
            for item in vocab:
                if len(item) > 0:
                    fout.write("%s\t%d" % (item, vocab[item]))

if __name__ == '__main__':
    str_lang1 = 'en'
    str_lang2 = 'es'
    cross_file = '/home/caoyx/data/paradata/cross_links_all_id.dat'
    par_file = '/home/caoyx/data/paradata/para_contexts.' + str_lang1 + '-' + str_lang2
    stop_word_file = ['/home/caoyx/data/en_stop_words', '/home/caoyx/data/es_stop_words','/home/caoyx/data/zh_stop_words']
    # save vocab
    word_vocab_file = ['/home/caoyx/data/shuffle/envocab_word.txt', '/home/caoyx/data/shuffle/esvocab_word.txt', '/home/caoyx/data/shuffle/zhvocab_word.txt']
    # merged wiki text
    merged_wiki_text = '/home/caoyx/data/merged_wiki_text'
    lang1 = languages.index(str_lang1)
    lang2 = languages.index(str_lang2)
    par = Parallel(lang1, lang2)
    par.loadCrossLink(cross_file)
    # whether output brace for anchors
    par.has_brace = False
    par.readDoc()
    par.merge(merged_wiki_text)
    par.saveVocab(par.words[0], word_vocab_file[lang1])
    par.saveVocab(par.words[1], word_vocab_file[lang2])
