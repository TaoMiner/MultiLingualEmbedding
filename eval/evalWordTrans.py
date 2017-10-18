import codecs
import regex as re
from Word import Word
from scipy import spatial
from options import Options
import heapq
import math
import numpy as np

class evaluator():

    def __init__(self):
        self.words = []
        self.lang = []
        self.exp = ''
        self.lex = []
        self.topn = 1

    def setTopN(self, topn):
        self.topn = topn

    def loadWords(self, w1, w2, lang1, lang2):
        self.words.append(w1)
        self.words.append(w2)
        self.lang.append(lang1)
        self.lang.append(lang2)

    def loadLex(self):
        if self.lang[1] == Options.es:
            self.loadEnEsLex(Options.getBiLexFile(self.lang[1]))
        elif self.lang[1] == Options.zh:
            self.loadEnZhLex(Options.getBiLexFile(self.lang[1]))

    def loadEnZhLex(self, filename):
        with codecs.open(filename, 'r', 'gbk') as fin:
            for line in fin:
                items = re.split(r'\t', line.strip())
                if len(items) < 2 or items[0] not in self.words[1].vectors : continue
                en_labels = []
                tmp_en_labels = re.split(r'/', items[1])
                for l in tmp_en_labels:
                    if len(l) < 1 or l not in self.words[0].vectors: continue
                    en_labels.append(l)
                if len(en_labels) > 0:
                    self.lex.append([items[0], en_labels])
        print("successfully load {0} word pairs!".format(len(self.lex)))

    def loadEnEsLex(self, filename):
        with codecs.open(filename, 'r', 'utf8') as fin:
            for line in fin:
                items = re.split(r'\t', line.strip())
                if len(items) < 2 : continue
                es_label = re.sub(r'_', ' ', items[0])
                if es_label not in self.words[1].vectors : continue
                en_labels = []
                tmp_en_labels = re.split(r' ', items[1])
                for label in tmp_en_labels:
                    label = re.sub(r'_', ' ', label)
                    if len(label) < 1 or label not in self.words[0].vectors: continue
                    en_labels.append(label)
                if len(en_labels) > 0:
                    self.lex.append([es_label, en_labels])
        print("successfully load {0} word pairs!".format(len(self.lex)))

    def cosSim(self, v1, v2):
        res = 0
        len_v1 = math.sqrt(np.dot(v1,v1))
        len_v2 = math.sqrt(np.dot(v2,v2))
        if len_v1 > 0.000001 and len_v2 > 0.000001:
            res = np.dot(v1,v2)/len_v1/len_v2
            res = (res +1)/2
        if math.isnan(res) or math.isinf(res) or res >1 or res <0:
            res = 0
        return res

    def evalHit(self, log_file = None):
        count = 0
        total_p = 0
        actual_pairs = 0
        for p in self.lex:
            count += 1
            lang2_w = p[0]
            lang1_ws = p[1]
            is_correct = False
            sim = []
            if lang2_w in self.words[1].vectors:
                actual_pairs += 1
                vec = self.words[1].vectors[lang2_w]
                for w in self.words[0].vectors:
                    sim.append([w, self.cosSim(vec, self.words[0].vectors[w])])
                sorted_sim = heapq.nlargest(self.topn, sim, key=lambda x: x[1])
                # print("{0}:{1}\n{2}\n".format(lang2_w,lang1_ws,sorted_sim))
                for cand in sorted_sim:
                    for en_w in lang1_ws:
                        if en_w.lower() == cand[0].lower():
                            total_p += 1
                            is_correct = True
                            break
                    if is_correct: break
                    # print("{0}:{1},{2}\n".format(cand[0],en_w,self.cosSim(self.words[0].vectors[cand[0]], self.words[0].vectors[en_w])))
            if count % 10 == 0:
                print("{0}/{1}, tp is {2}!".format(count, actual_pairs, total_p))
        print("top {0} acc is {1}".format(topn, float(total_p) / actual_pairs))

        if not isinstance(log_file, type(None)):
            fout = codecs.open(log_file, 'a', encoding='UTF-8')
            fout.write('*************************************************\n')
            fout.write('{0}, lang1:{1}, lang2:{2}, topn:{3}, hit acc:{4}.\n'.format(self.exp, self.lang[0], self.lang[1], self.topn, float(total_p) / actual_pairs))
            fout.write('*************************************************\n')
            fout.close()

    def evalRank(self, log_file = None):
        count = 0
        total_rank = 0
        actual_pairs = 0
        for p in self.lex:
            count += 1
            lang2_w = p[0]
            lang1_ws = p[1]
            sim = []
            smallest_rank = self.words[0].vocab_size+1
            if lang2_w in self.words[1].vectors:
                actual_pairs += 1
                vec = self.words[1].vectors[lang2_w]
                for w in self.words[0].vectors:
                    sim.append([w, self.cosSim(vec, self.words[0].vectors[w])])
                sim.sort(key=lambda x: x[1], reverse=True)
                for en_w in lang1_ws:
                    for i in range(len(sim)):
                        if sim[i][0] == en_w:
                            if smallest_rank > i+1:
                                smallest_rank = i+1
                            break
                total_rank += smallest_rank
            if count % 10 == 0:
                print("{0}/{1}, sum rank is {2}!".format(count, actual_pairs, total_rank))
        print("mean rank {0}".format(float(total_rank) / actual_pairs))

        if not isinstance(log_file, type(None)):
            fout = codecs.open(log_file, 'a', encoding='UTF-8')
            fout.write('*************************************************\n')
            fout.write('{0}, lang1:{1}, lang2:{2}, topn:{3}, mean rank:{4}.\n'.format(self.exp, self.lang[0], self.lang[1], self.topn, float(total_rank) / actual_pairs))
            fout.write('*************************************************\n')
            fout.close()

if __name__ == '__main__':
    exp = 'exp17'
    it = 5
    topn = 1
    lang1 = Options.en
    lang2 = Options.zh
    # >1000, en:51935, es:23878, zh:15148. small scale: en-zh, en:5154,zh:3349. en-es, en:6637,es:4774
    topn1 = 50000
    topn2 = 50000
    log_file = Options.getLogFile('log_trans')

    w1 = Word()
    w1.loadVocabDic(Options.getExpVocabFile(lang1, Options.word_type), topn=topn1)
    w1.loadVector(Options.getExpVecFile(exp, lang1, Options.word_type, it), vocab=w1.vocab_dic)

    w2 = Word()
    w2.loadVocabDic(Options.getExpVocabFile(lang2, Options.word_type), topn=topn2)
    w2.loadVector(Options.getExpVecFile(exp, lang2, Options.word_type, it), vocab=w2.vocab_dic)

    evaluator = evaluator()
    evaluator.exp = exp
    evaluator.setTopN(topn)
    evaluator.loadWords(w1, w2, lang1, lang2)
    evaluator.loadLex()
    evaluator.evalHit(log_file=log_file)