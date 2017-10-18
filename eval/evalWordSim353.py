import codecs
import struct
import numpy as np
from Word import Word
from Sense import Sense
from Entity import Entity
from scipy import stats
from scipy import spatial
from options import Options

class Evaluator:
    def __init__(self):
        self.standard = []

    def loadData(self,file):
        self.data = map(lambda x: x.strip().lower().split('\t'), open(file).readlines()[11:])
        self.standard = [float(d[3]) for d in self.data]

    def loadWordEmbeddings(self, word):
        self.tr_word = word
        self.tr_title = None
        self.tr_map = None

    def loadEmbeddings(self, word, title):
        self.tr_word = word
        self.tr_title = title

    def cosSim(self, v1, v2):
	return 1 - spatial.distance.cosine(v1,v2)

    def getSenseVec(self,word):
        if not self.tr_map or word not in self.tr_map.names or not self.tr_title:
            return [self.tr_word.vectors[word]]
        re_vec = [self.tr_word.vectors[word]]
        for m in self.tr_map.names[word]:
            if m in self.tr_title.ent_vectors:
                re_vec.append(self.tr_title.ent_vectors[m])
        return re_vec

    def evaluate(self):
        glb = []
        avg = []
        simmax = []
        for d in self.data:
            if d[1] not in self.tr_word.vectors or d[2] not in self.tr_word.vectors:
                glb.append(0)
                avg.append(0)
                simmax.append(0)
            else:
                sim = self.cosSim(self.tr_word.vectors[d[1]], self.tr_word.vectors[d[2]])
                glb.append(sim)
                if self.tr_map:
                    sumsim, tmp_sim, count, largest_sim = 0, 0, 0, -1.0
                    for i in self.getSenseVec(d[1]):
                        for j in self.getSenseVec(d[2]):
                            tmp_sim = self.cosSim(i, j)
                            if tmp_sim > largest_sim:
                                largest_sim = tmp_sim
                            sumsim += tmp_sim
                            count += 1
                    avg.append(sumsim / count)
                    simmax.append(largest_sim)
                else:
                    avg.append(sim)
                    simmax.append(sim)
        output = open('/data/m1/cyx/MultiMPME/expdata/wordsim353_pred', 'w')
        for i in xrange(len(self.data)):
            output.write('%s\t%s\t%f\t%f\n' % (self.data[i][1], self.data[i][2], self.standard[i], glb[i]*10 ))
        output.close()
        return stats.spearmanr(self.standard, glb), stats.spearmanr(self.standard, avg), stats.spearmanr(self.standard, simmax)

if __name__ == '__main__':
    exp = 'exp18'
    it = 5
    output_file = base_path + 'expdata/log_wordsim353'

    w = Word()
    w.loadVector(Options.getExpVecFile(exp, Options.en, Options.word_type, it))
    print len(wiki_word.vectors)
    if has_sense:
        wiki_sense = Sense()
        wiki_sense.setIdEntityDic(Entity.loadEntityIdDic(entity_dic_file))
        wiki_sense.loadVector(sense_vector_file)
        wiki_sense.buildMultiProto()

    eval = Evaluator()
    eval.loadData(word_sim_file)
    if has_sense:
        eval.loadEmbeddings(wiki_word, wiki_sense)
    else:
        eval.loadWordEmbeddings(wiki_word)
    gs, avgs, maxs = eval.evaluate()
    output = open(output_file, 'a')
    output.write('\n*****************************************************')
    if has_sense:
        output.write('\n'+word_sim_file+'\n' + word_vector_file + '\n' + sense_vector_file +'\n' + 'glb: ' + str(gs)+ 'avg: ' + str(avgs)+ 'glb: ' + str(maxs))
    else:
        output.write('\n' +word_sim_file+'\n'+ word_vector_file + '\n' + 'glb: ' + str(gs) )
    output.write('\n*****************************************************')
    output.close()

