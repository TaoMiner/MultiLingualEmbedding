import codecs
import regex as re
from Word import Word
from scipy import spatial
from options import Options
import heapq

class evaluator():

    def __init__(self):
        self.words = []
        self.lang = []
        self.lex = []
        self.tp = 0
        self.exp = ''
        self.topn = 1
        self.max_heap = None

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
                en_labels = re.split(r' ', items[1])
                for label in en_labels:
                    label = re.sub(r'_', ' ', label)
                    if len(label) < 1 or label not in self.words[0].vectors: continue
                if len(en_labels) > 0:
                    self.lex.append([es_label, en_labels])
        print("successfully load {0} word pairs!".format(len(self.lex)))

    def eval(self, log_file = None):
        count = 0
        for p in self.lex:
            count += 1
            lang2_w = p[0]
            lang1_ws = p[1]
            is_correct = False
            for en_w in lang1_ws:
                if en_w in self.words[0].vectors:
                    vec = self.words[0].vectors[en_w]
                    sim = []
                    for w in self.words[1].vectors:
                        sim.append([w, spatial.distance.cosine(vec, self.words[1].vectors[w])])
                    sorted_sim = heapq.nlargest(self.topn, sim, key=lambda x: x[1])

                    for s in sorted_sim:
                        if lang2_w.lower() == s[0].lower():
                            self.tp += 1
                            is_correct = True
                            break
                if is_correct: break
            if count % 10 == 0:
                print("{0}/{1}, tp is {2}!".format(count, len(self.lex), self.tp))
        print("top {0} acc is {1}".format(topn, float(self.tp) / len(self.lex)))

        if not isinstance(log_file, type(None)):
            fout = codecs.open(log_file, 'a', encoding='UTF-8')
            fout.write('*************************************************\n')
            fout.write('{0}, lang1:{1}, lang2:{2}, topn:{3}, acc:{4}.\n'.format(self.exp, self.lang[0], self.lang[1], self.topn, float(self.tp) / len(self.lex)))
            fout.write('*************************************************\n')
            fout.close()

if __name__ == '__main__':
    exp = 'exp18'
    it = 5
    topn = 1
    lang1 = Options.en
    lang2 = Options.es
    topn1 = 100000
    topn2 = 100000
    log_file = Options.getLogFile('log_trans')

    w1 = Word()
    w1.loadVocabDic(Options.getExpVocabFile(lang1, Options.word_type), topn=topn1)
    w1.loadVector(Options.getExpVecFile(exp, lang1, Options.word_type, it))

    w2 = Word()
    w2.loadVocabDic(Options.getExpVocabFile(lang2, Options.word_type), topn=topn2)
    w2.loadVector(Options.getExpVecFile(exp, lang2, Options.word_type, it))

    evaluator = evaluator()
    evaluator.exp = exp
    evaluator.setTopN(topn)
    evaluator.loadWords(w1, w2, lang1, lang2)
    evaluator.loadLex()
    evaluator.eval(log_file=log_file)