from Word import Word
from options import Options
import regex as re
import math
import numpy as np

TASK1 = 'task1-monolingual'
TASK2 = 'task2-crosslingual'

class similarity:
    def __init__(self):
        self.words = None
        self.word_pair = []
        self.wp_sim = []
        self.default_sim = 0.5

    def loadWords(self, w1, w2):
        self.words = [w1, w2]

    def loadData(self, filename, isLower=True):
        with open(filename, 'r') as fin:
            for line in fin:
                if isLower:
                    line = line.lower()
                items = re.split(r'\t', line.strip())
                if len(items) != 2: continue
                self.word_pair.append(items)

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

    def compute(self, isComp=True):
        assert not isinstance(self.words, type(None)) and len(self.words) == 2 and self.words[0].layer_size == self.words[1].layer_size, "please load correct words vector!"
        assert len(self.word_pair) > 0, "please load word pairs!"
        for ws in self.word_pair:
            vec_pair = [None, None]
            for i in range(2):
                vec_pair[i] = self.words[i][ws[i]] if ws[i] in self.words[i] else None
                if isinstance(vec_pair[i], type(None)) and isComp:
                    tmp_items = re.split(r' ', ws[i])
                    if len(tmp_items) > 1:
                        tmp_vec = np.zeros(self.words[i].layer_size)
                        actual_word_count = 0
                        for item in tmp_items:
                            if item in self.words[i]:
                                tmp_vec += self.words[i][item]
                                actual_word_count += 1
                        if actual_word_count >= 1:
                            vec_pair[i] = tmp_vec/actual_word_count
            if not isinstance(vec_pair[0], type(None)) and not isinstance(vec_pair[1], type(None)):
                self.wp_sim.append(self.cosSim(vec_pair[0], vec_pair[1]))
            else:
                self.wp_sim.append(self.default_sim)

    def output(self, filename):
        assert len(self.word_pair)==len(self.wp_sim), "incorrect sim length!"
        print("compute similarity for {0} word pairs!".format(len(self.word_pair)))
        with open(filename, 'w') as fout:
            fout.write("\n".join([str(x) for x in self.wp_sim]))

if __name__ == '__main__':
    base_path = '/home/caoyx/'
    exp = 'exp2'
    it = 5
    lang_pair = [Options.en, Options.es]


    task = TASK1 if lang_pair[0] == lang_pair[1] else TASK2
    lang_str = Options.getLangStr(lang_pair[0])
    if task == TASK2:
        lang_str += '-' + Options.getLangStr(lang_pair[1])
    word_pair_file = '{0}/data/SemEval17-Task2/test/sub{1}/data/{2}.test.data.txt'.format(base_path, task, lang_str)
    output_file = '{0}/data/SemEval17-Task2/output/{1}.output.txt'.format(base_path, lang_str)

    w1 = Word()
    w1.loadVector(Options.getExpVecFile(exp, lang_pair[0], Options.word_type, it))

    w2 = Word()
    w2.loadVector(Options.getExpVecFile(exp, lang_pair[1], Options.word_type, it))

    sim = similarity()
    sim.loadWords(w1, w2)
    sim.loadData(word_pair_file)
    sim.compute()
    sim.output(output_file)