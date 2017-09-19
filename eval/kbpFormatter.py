import codecs

class formatter:
    def __init__(self):
        self.eval_path = '/home/caoyx/data/kbp/LDC2017E03_TAC_KBP_Entity_Discovery_and_Linking_Comprehensive_Training_and_Evaluation_Data_2014-2016/data/'


    def readDoc(self, file):
        with codecs.open(file, 'r', encoding='UTF-8') as fin:
            doc = fin.readlines()
            print doc[587:591]


    def loadAnswers(self, file):
        print ''

if __name__ == '__main__':
    file = '/home/caoyx/data/kbp/LDC2017E03_TAC_KBP_Entity_Discovery_and_Linking_Comprehensive_Training_and_Evaluation_Data_2014-2016/data/2016/eval/source_documents/cmn/nw/CMN_NW_001278_20130627_F00010JF8.xml'
    fm = formatter()
    fm.readDoc(file)