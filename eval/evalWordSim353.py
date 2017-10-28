import codecs
import struct
import numpy as np
from Word import Word
from Sense import Sense
from Entity import Entity
from scipy import stats
from scipy import spatial
from options import Options
import math

class Evaluator:
    def __init__(self):
        self.standard = []
        self.fout_debug = None
        self.fout_log = None

    def setLog(self, filename, exp=''):
        self.fout_log = codecs.open(filename, 'a', encoding='UTF-8')
        self.fout_log.write('*************************************************\n')
        if len(exp) > 0:
            self.fout_log.write("{0}:".format(exp))

    def setDebug(self, filename):
        self.fout_debug = codecs.open(filename, 'w', encoding='UTF-8')

    def loadData(self,file):
        self.data = map(lambda x: x.strip().lower().split('\t'), open(file).readlines()[11:])
        self.standard = [float(d[3]) for d in self.data]

    def loadModel(self, w):
        self.tr_word = w

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

    def evaluate(self):
        glb = []
        actual_count = 0
        for d in self.data:
            if d[1] not in self.tr_word.vectors or d[2] not in self.tr_word.vectors:
                glb.append(0)
            else:
                actual_count += 1
                sim = self.cosSim(self.tr_word.vectors[d[1]], self.tr_word.vectors[d[2]])
                glb.append(sim)
        if not isinstance(self.fout_debug, type(None)):
            for i in xrange(len(self.data)):
                self.fout_debug.write('{0}\t{1}\t{2}\t{3}\n'.format(self.data[i][1], self.data[i][2], self.standard[i], glb[i] * 10))
            self.fout_debug.close()
        res = stats.spearmanr(self.standard, glb)
        if not isinstance(self.fout_log, type(None)):
            self.fout_log.write('spearmanr:{0}, actual word pairs:{1}, total:{2}\n'.format(res, actual_count, len(self.standard)))
            self.fout_log.write('*************************************************\n')
            self.fout_log.close()


if __name__ == '__main__':
    exp = 'exp2'
    it = 5
    log_file = Options.getLogFile('log_wordsim353')

    w = Word()
    w.loadVector(Options.getExpVecFile(exp, Options.en, Options.word_type, it))

    eval = Evaluator()
    eval.setLog(log_file, exp=exp)
    eval.loadData(Options.wordsim353_file)
    eval.loadModel(w)

    eval.evaluate()