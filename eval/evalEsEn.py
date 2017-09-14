import codecs
import regex as re
from Word import Word
from scipy import spatial
import os

languages = [u'en',u'es']
topn = 1

class evaluator():

    def __init__(self):
        self.expnum = 8
        self.vec_path = '/home/caoyx/data/etc/exp' + str(self.expnum)
        self.en_word_file = self.vec_path + '/envec/vectors1_word5'
        self.es_word_file = self.vec_path + '/esvec/vectors2_word5'
        self.lex_file = '/home/caoyx/data/all.es-en.lex'

        self.words = [Word(), Word()]
        self.lex = []
        self.tp = 0

    def loadWords(self):
        if os.path.isfile(self.en_word_file):
            self.words[1].loadVector(self.en_word_file)

        if os.path.isfile(self.es_word_file):
            self.words[0].loadVector(self.es_word_file)

    def loadBiLexicon(self):
        with codecs.open(self.lex_file, 'r', 'utf8') as fin:
            for line in fin:
                items = re.split(r'\t', line.strip())
                if len(items) < 2 : continue
                es_label = re.sub(r'_', ' ', items[0])

                if es_label not in self.words[0].vectors : continue
                en_labels = re.split(r' ', items[1])
                for label in en_labels:
                    label = re.sub(r'_', ' ', label)
                    if len(label) < 1 or label not in self.words[1].vectors: continue
                if len(en_labels) > 0:
                    self.lex.append([es_label, en_labels])
        print "successfully load %d word pairs!" % len(self.lex)

    def eval(self, topN = topn, log_file = None):
        fout = None
        if not isinstance(log_file, type(None)):
            fout = codecs.open(log_file, 'a', encoding='UTF-8')
        count = 0
        for p in self.lex:
            count += 1
            zh_w = p[0]
            en_ws = p[1]
            is_correct = False
            for en_w in en_ws:
                if en_w in self.words[1].vectors:
                    vec = self.words[1].vectors[en_w]
                    sim = []
                    for w in self.words[0].vectors:
                        sim.append([w, spatial.distance.cosine(vec, self.words[0].vectors[w])])
                    sorted_sim = sorted(sim, key=lambda x: x[1])[:topN]

                    for s in sorted_sim:
                        if zh_w == s[0]:
                            self.tp += 1
                            is_correct = True
                            break
                if is_correct: break
            if count % 10 == 0:
                print "%d/%d, tp is %d!" % (count, len(self.lex), self.tp)
        print "top %d acc is %f" % (topn, float(self.tp)/len(self.lex))
        if not isinstance(fout, type(None)):
            fout.write("exp%d top %d acc is %f.\n" % (self.expnum, topn, float(self.tp) / len(self.lex)))
            fout.close()

if __name__ == '__main__':
    log_file = './distance.out'
    evaluator = evaluator()
    evaluator.loadWords()
    evaluator.loadBiLexicon()
    evaluator.eval(log_file=log_file)