#!/usr/bin/env python
# -*- coding: utf-8 -*-
import codecs
import regex as re
import string

textHeadRE = re.compile(r'<TEXT>')
textTailRE = re.compile(r'</TEXT>')
puncRE = re.compile(ur'[%s]' % re.escape(string.punctuation))
zh_punctuation = "！？｡。·＂＃＄％＆＇（）＊＋，－／：；＜＝＞＠［＼］＾＿｀｛｜｝～｟｠｢｣､、〃》「」『』【】〔〕〖〗〘〙〚〛〜〝〞〟〰〾〿–—‘’‛“”„‟…‧﹏."
zhpunc = re.compile(ur'[%s]' % re.escape(zh_punctuation.decode('utf-8')))
tagRE = re.compile(r'<.*?>')


class formatter:
    def __init__(self):
        self.eval_path = '/home/caoyx/data/kbp/LDC2017E03_TAC_KBP_Entity_Discovery_and_Linking_Comprehensive_Training_and_Evaluation_Data_2014-2016/data/'


    def readDoc(self, file, start_p, end_p):
        isDoc = False
        count = -1
        with codecs.open(file, 'r', encoding='UTF-8') as fin:
            for line in fin:
                sent_len = len(line)
                count += sent_len
                line = line.strip()
                if len(line) < 1 : continue
                head_m = textHeadRE.match(line)
                tail_m = textTailRE.match(line)
                if head_m != None :
                    isDoc = True
                    continue
                if isDoc:
                    tail_m = textTailRE.match(line)
                    if tail_m != None :
                        isDoc = False
                        continue
                    if count >= end_p:
                        print line[start_p-count+sent_len-1:end_p-count+sent_len]

    def loadAnswers(self, file):
        print ''

if __name__ == '__main__':
    file = '/home/caoyx/data/kbp/LDC2017E03_TAC_KBP_Entity_Discovery_and_Linking_Comprehensive_Training_and_Evaluation_Data_2014-2016/data/2016/eval/source_documents/cmn/nw/CMN_NW_001278_20130627_F00010JF8.xml'
    fm = formatter()
    fm.readDoc(file, 587, 591)