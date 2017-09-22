import codecs
import regex as re
import string
import os
import copy
from stanfordcorenlp import StanfordCoreNLP
import simplejson

KBP16 = 3
KBP15 = 2
CONLL = 1

textHeadRE = re.compile(r'<TEXT>|<HEADLINE>')
textTailRE = re.compile(r'</TEXT>|</HEADLINE>')
nonTextRE = re.compile(r'^<[^<>]+?>$')
puncRE = re.compile("[{0}]".format(re.escape(string.punctuation)))
zh_punctuation = "！？｡。·＂＃＄％＆＇（）＊＋，－／：；＜＝＞＠［＼］＾＿｀｛｜｝～｟｠｢｣､、〃》「」『』【】〔〕〖〗〘〙〚〛〜〝〞〟〰〾〿–—‘’‛“”„‟…‧﹏."
zhpunc = re.compile("[{0}]".format(re.escape(zh_punctuation)))
tagRE = re.compile(r'<.*?>')

class Doc:
    def __init__(self):
        self.doc_id = -1
        self.text = []          # [w, ..., w] token lists
        self.mentions = []      # [[w_index, mention_lenth, ent_id, ent_label], ...]

class DataReader:
    def __init__(self):
        self.en_corpus = []        # [doc, ...]
        self.zh_corpus = []         # [doc, ...]
        self.es_corpus = []         # [doc, ...]
        self.kbpMentions = {}          # {doc_id:[[startP, endP, wikiId],...], ...}
        self.nlp = None

    def setNlpTool(self, path):
        self.nlp = StanfordCoreNLP(path)
        self.en_props = {'annotators': 'tokenize,lemma', 'pipelineLanguage': 'en', 'outputFormat': 'json'}
        self.es_props = {'annotators': 'tokenize,lemma', 'pipelineLanguage': 'es', 'outputFormat': 'json'}
        print("set nlp tool!")

    # doc_type: 1 -- conll; 2 -- kbp15; 3 -- kbp16
    def readDoc(self, doc_type):
        if doc_type == 3:
            self.readKbp16()
        else: print("No reader for such doc!")

    def loadKbpMentions(self, file):
        count = 0
        with codecs.open(file, 'r') as fin:
            for line in fin:
                items = re.split(r'\t', line.strip())
                if len(items) < 5 : continue
                tmp_items = re.split(r':|-', items[3])
                if len(tmp_items) < 3: continue
                doc_id = tmp_items[0]
                start_p = int(tmp_items[1])
                end_p = int(tmp_items[2])
                freebase_id = items[4]
                if freebase_id.startswith('NIL') : continue
                tmp_mention = [start_p, end_p, freebase_id]
                doc_mentions = [] if doc_id not in self.kbpMentions else self.kbpMentions[doc_id]
                index = 0
                for m in doc_mentions:
                    if tmp_mention[0] <= m[0]:
                        break
                    index += 1
                doc_mentions.insert(index, tmp_mention)
                self.kbpMentions[doc_id] = doc_mentions
                count += 1
        print("load {0} mentions for {1} docs!".format(count, len(self.kbpMentions)))


    def readKbp16(self, en_path):
        if len(self.kbpMentions) < 1 or not os.path.isdir(en_path) :
            print("please check kbp mentions and input path!")
            return
        files = os.listdir(en_path)
        for f in files:
            if f[:-4] in self.kbpMentions:
                print("processing {0}!".format(f))
                self.en_corpus.append(self.readEnDoc(os.path.join(en_path, f), self.kbpMentions[f[:-4]]))

    # return original text and its count, according to dataset year

    # return class doc for kbp16
    def readEnDoc(self, file, mentions):
        doc = Doc()
        isDoc = False
        cur_pos = -1
        mention_index = 0
        tmp_map = {}
        with codecs.open(file, 'r') as fin:
            for line in fin:
                cur_len = len(line)
                if len(line.strip()) < 1:
                    cur_pos += cur_len
                    continue
                if isDoc:
                    # text ends or <P>
                    text_m = nonTextRE.match(line.strip())
                    tail_m = textTailRE.match(line.strip())
                    if text_m != None or tail_m != None:
                        cur_pos += cur_len
                        if tail_m != None : isDoc = False
                        continue
                    seg_lines = simplejson.loads(self.nlp.annotate(line, properties=self.en_props))
                    for sent in seg_lines['sentences']:
                        tokens = sent['tokens']
                        # iterate each token such as
                        # {u'index': 1, u'word': u'we', u'lemma': u'we', u'after': u' ', u'pos': u'PRP', u'characterOffsetEnd': 2, u'characterOffsetBegin': 0, u'originalText': u'we', u'before': u''}
                        # segment the tokens according to mention boundary
                        for i in range(len(tokens)):
                            token = tokens[i]
                            t_start = cur_pos+token['characterOffsetBegin']+1
                            t_end = cur_pos + token['characterOffsetEnd'] +1
                            tmp_seg = [[0, -1, 0], [len(token['word']), 1000, 1]]
                            # put all the mention boundary into the set
                            for j in range(mention_index, len(mentions),1):
                                if mentions[j][0] > t_end-1 : break
                                if mentions[j][0] >= t_start and mentions[j][0] < t_end:
                                    tmp_seg.append([mentions[j][0]-t_start, j, 0])
                                if mentions[j][1] >= t_start and mentions[j][1] < t_end:
                                    tmp_seg.append([mentions[j][1]-t_start+1, j, 1])
                            if len(tmp_seg) <= 2 :       # if no mention is in this token
                                doc.text.append(token['lemma'])
                            else:
                                tmp_seg = sorted(tmp_seg, key=lambda x:(x[0], x[2], x[1]))
                                for j in range(len(tmp_seg)-1):
                                    m_index = tmp_seg[j][1]
                                    if tmp_seg[j][0] == 0 and tmp_seg[j+1][0] == len(token['word']) :
                                        doc.text.append(token['lemma'])
                                    elif tmp_seg[j+1][0] > tmp_seg[j][0]:
                                        doc.text.append(token['word'][tmp_seg[j][0]:tmp_seg[j+1][0]])
                                    if m_index == -1: continue
                                    if tmp_seg[j][2] == 0:
                                        tmp_map[m_index] = len(doc.text)-1
                                    else:
                                        doc.mentions.append([tmp_map[m_index], len(doc.text) - tmp_map[m_index], mentions[m_index][2], ''])
                        doc.text.append('')
                else:
                    head_m = textHeadRE.match(line.strip())
                    # text starts
                    if head_m != None:
                        isDoc = True
                cur_pos += cur_len
        return doc

if __name__ == '__main__':
    eval_path = '/home/caoyx/data/kbp/LDC2017E03_TAC_KBP_Entity_Discovery_and_Linking_Comprehensive_Training_and_Evaluation_Data_2014-2016/data/'
    stanfordNlp_path = '/home/caoyx/stanford-corenlp_38'
    dr = DataReader()
    dr.loadKbpMentions(eval_path+'2016/eval/tac_kbp_2016_edl_evaluation_gold_standard_entity_mentions.tab')
    dr.setNlpTool(stanfordNlp_path)
    dr.readKbp16(eval_path+'2016/eval/source_documents/eng/nw/')