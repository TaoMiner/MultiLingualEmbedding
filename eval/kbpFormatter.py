import codecs
import regex as re

class formatter:
    def __init__(self):
        self.eval_path = '/home/caoyx/data/kbp/LDC2017E03_TAC_KBP_Entity_Discovery_and_Linking_Comprehensive_Training_and_Evaluation_Data_2014-2016/data/'
        self.textHeadRE = re.compile(r'<TEXT>')
        self.textTailRE = re.compile(r'</TEXT>')

    def readDoc(self, file, start_p, end_p):
        isDoc = False
        count = 0
        with codecs.open(file, 'r', encoding='UTF-8') as fin:
            for line in fin:
                line = line.strip()
                if len(line) < 1 : continue
                head_m = self.textHeadRE.match(line)
                tail_m = self.textTailRE.match(line)
                if head_m != None : isDoc = True
                if isDoc:
                    tail_m = self.textTailRE.match(line)
                    if tail_m != None : isDoc = False
                    if count + len(line) >= end_p:
                        print line[start_p-count:end_p-count]



    def loadAnswers(self, file):
        print ''

if __name__ == '__main__':
    file = '/home/caoyx/data/kbp/LDC2017E03_TAC_KBP_Entity_Discovery_and_Linking_Comprehensive_Training_and_Evaluation_Data_2014-2016/data/2016/eval/source_documents/cmn/nw/CMN_NW_001278_20130627_F00010JF8.xml'
    fm = formatter()
    fm.readDoc(file, 587, 591)