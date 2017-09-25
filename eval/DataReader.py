import codecs
import regex as re
import string
import os
import copy
from pycorenlp import StanfordCoreNLP
import simplejson
import jieba

# jieba.set_dictionary('/home/caoyx/data/dict.txt.big')

textHeadRE = re.compile(r'<TEXT>|<HEADLINE>')
textTailRE = re.compile(r'</TEXT>|</HEADLINE>')
nonTextRE = re.compile(r'^<[^<>]+?>$')
eleTagRE = re.compile(r'(<[^<>]+?>)([^<>]+?)(</[^<>]+?>)')
propTagRE = re.compile(r'(<[^<>]+?/>)')
puncRE = re.compile("[{0}]".format(re.escape(string.punctuation)))
zh_punctuation = "！？｡。·＂＃＄％＆＇（）＊＋，－／：；＜＝＞＠［＼］＾＿｀｛｜｝～｟｠｢｣､、〃》「」『』【】〔〕〖〗〘〙〚〛〜〝〞〟〰〾〿–—‘’‛“”„‟…‧﹏."
zhpunc = re.compile("[{0}]".format(re.escape(zh_punctuation)))


class Doc:
    def __init__(self):
        self.doc_id = -1
        self.text = []          # [w, ..., w] token lists
        self.mentions = []      # [[w_index, mention_lenth, ent_id, ent_label], ...]

class DataReader:
    def __init__(self):
        self.lang = ''
        self.nlp = None
        self.prop = None

    def initNlpTool(self, url, lang):
        if not isinstance(self.nlp, type(None)):return
        self.lang = lang
        if lang != 'zh':
            self.nlp = StanfordCoreNLP(url)
            self.prop = {'annotators': 'tokenize, ssplit, lemma', 'outputFormat': 'json'}
        elif os.path.isfile(url):
            jieba.set_dictionary(url)
            self.nlp = jieba
        print("set nlp tool!")

    def tokenize(self, sent):
        if isinstance(self.nlp, type(None)):
            print("please init nlp tool!")
            return
        tokens = []
        if self.lang == 'zh':
            tokens = self.nlp.tokenize(sent)
        else:
            results = self.nlp.annotate(sent, properties=self.prop)
            for sent in results['sentences']:
                for token in sent['tokens']:
                    tokens.append([token['word'], token['characterOffsetBegin'], token['characterOffsetEnd'], token['lemma']])
        return tokens

    # {doc_id:[[startP, endP, wikiId, mention_str],...], ...}
    def loadKbpMentions(self, file):
        count = 0
        mentions = {}
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
                mention_str = items[2]
                if freebase_id.startswith('NIL') : continue
                tmp_mention = [start_p, end_p, freebase_id, mention_str]
                doc_mentions = [] if doc_id not in mentions else mentions[doc_id]
                index = 0
                for m in doc_mentions:
                    if tmp_mention[0] <= m[0]:
                        break
                    index += 1
                doc_mentions.insert(index, tmp_mention)
                mentions[doc_id] = doc_mentions
                count += 1
        print("load {0} mentions for {1} docs!".format(count, len(mentions)))
        return mentions

    def readKbp16(self, path, mentions, doc_type):
        if len(mentions) < 1 or not os.path.isdir(path) :
            print("please check kbp mentions and input path!")
            return
        files = os.listdir(path)
        corpus = []
        for f in files:
            if f[:-4] in mentions:
                print("processing {0}!".format(f))
                if doc_type=='df':
                    sents = self.extractKBP16DfText(os.path.join(path, f))
                elif doc_type == 'nw':
                    sents = self.extractKBP16NwText(os.path.join(path, f))
                else:
                    sents = self.extractKBP15Text(os.path.join(path, f))
                corpus.append(self.readDoc(sents, mentions[f[:-4]]))

    # return original text and its count, according to dataset year
    def extractKBP15Text(self, file):
        sents = []
        return sents
    # skip all the lines <...>
    def extractKBP16DfText(self, file):
        sents = []
        cur_pos = -1
        with codecs.open(file, 'r') as fin:
            for line in fin:
                cur_len = len(line)
                m = nonTextRE.match(line.strip())
                if m == None :
                    sents.append([cur_pos, line])
                cur_pos += cur_len
        return sents
    # sents: [[sent,start_pos, sent_line]]
    def extractKBP16NwText(self, file):
        sents = []
        isDoc = False
        cur_pos = -1
        with codecs.open(file, 'r') as fin:
            for line in fin:
                cur_len = len(line)
                if isDoc:
                    # text ends or <P>
                    text_m = nonTextRE.match(line.strip())
                    tail_m = textTailRE.match(line.strip())
                    if text_m != None or tail_m != None:
                        cur_pos += cur_len
                        if tail_m != None : isDoc = False
                        continue
                    sents.append([cur_pos, line])
                else:
                    head_m = textHeadRE.match(line.strip())
                    # text starts
                    if head_m != None:
                        isDoc = True
                cur_pos += cur_len
        return sents
    # return class doc
    def readDoc(self, sents, mentions):
        doc = Doc()
        mention_index = 0
        print(mentions)
        tmp_map = {}
        for sent in sents:
            cur_pos = sent[0]
            line = sent[1]
            # some line contains <>..</>   or  <.../>
            tag_pos = []
            tag_len = 0
            tag_index = 0
            for etm in eleTagRE.finditer(line):
                tag_pos.append(etm.span(1))
                tag_pos.append(etm.span(3))
            for ptm in propTagRE.finditer(line):
                tag_pos.append(ptm.span(1))
            tmp_line = line
            if len(tag_pos) > 0:
                tag_pos = sorted(tag_pos, key=lambda x:x[0])
                tmp_line = line[0:tag_pos[0][0]]
                for i in range(len(tag_pos)-1):
                    tmp_line += line[tag_pos[i][1]:tag_pos[i+1][0]]
                tmp_line += line[tag_pos[len(tag_pos)-1][1]:]
            tokens = self.tokenize(tmp_line)
            # tokens : [[word, start, end, lemma],...]  no lemma for chinese
            for token in tokens:
                print("curpos:{0},token:{1}".format(cur_pos, token))
                w = token[0]
                lemma = w if self.lang=='zh' else token[3]
                t_start = cur_pos + token[1] + 1
                t_end = cur_pos + token[2] + 1
                if tag_index < len(tag_pos) and t_start + tag_len >= tag_pos[tag_index][0] + cur_pos +1:
                    tag_len += tag_pos[tag_index][1] - tag_pos[tag_index][0]
                    tag_index += 1
                if len(tag_pos) > 0:
                    t_start += tag_len
                    t_end += tag_len
                tmp_seg = [[0, -1, 0], [len(w), 1000, 1]]
                # put all the mention boundary into the set
                for j in range(mention_index, len(mentions),1):
                    if mentions[j][0] > t_end-1 : break
                    if mentions[j][0] >= t_start and mentions[j][0] < t_end:
                        tmp_seg.append([mentions[j][0]-t_start, j, 0])
                    if mentions[j][1] >= t_start and mentions[j][1] < t_end:
                        tmp_seg.append([mentions[j][1]-t_start+1, j, 1])
                if len(tmp_seg) <= 2 :       # if no mention is in this token
                    doc.text.append(lemma)
                else:
                    tmp_seg = sorted(tmp_seg, key=lambda x:(x[0], x[2], x[1]))
                    print("ts:{0},te:{1},seg:{2}".format(t_start, t_end, tmp_seg))
                    for j in range(len(tmp_seg)-1):
                        m_index = tmp_seg[j][1]
                        add_text = 1
                        if tmp_seg[j][0] == 0 and tmp_seg[j+1][0] == len(w) :
                            doc.text.append(lemma)
                        elif tmp_seg[j+1][0] > tmp_seg[j][0]:
                            doc.text.append(w[tmp_seg[j][0]:tmp_seg[j+1][0]])
                        else:
                            add_text = 0
                        if m_index == -1 or m_index >= 1000: continue
                        if tmp_seg[j][2] == 0:
                            tmp_map[m_index] = len(doc.text)-1
                        elif m_index in tmp_map:
                            doc.mentions.append([tmp_map[m_index], len(doc.text)-tmp_map[m_index]-add_text, mentions[m_index][2], doc.text[tmp_map[m_index]:tmp_map[m_index]+len(doc.text)-tmp_map[m_index]-add_text]])
        print(doc.mentions)
        print(doc.text)
        return doc

if __name__ == '__main__':
    eval_path = '/home/caoyx/data/kbp/LDC2017E03_TAC_KBP_Entity_Discovery_and_Linking_Comprehensive_Training_and_Evaluation_Data_2014-2016/data/'
    stanfordNlp_server = 'http://localhost:9001'
    jieba_dict = '/home/caoyx/data/dict.txt.big'
    dr = DataReader()
    #dr.initNlpTool(stanfordNlp_server, 'en')
    dr.initNlpTool(jieba_dict, 'zh')
    mentions = dr.loadKbpMentions(eval_path+'2016/eval/tac_kbp_2016_edl_evaluation_gold_standard_entity_mentions.tab')
    dr.readKbp16(eval_path+'2016/eval/source_documents/eng/df/', mentions, 'df')