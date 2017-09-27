import codecs
import regex as re
import string
import os
import copy
from pycorenlp import StanfordCoreNLP
import simplejson
import jieba
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

# jieba.set_dictionary('/home/caoyx/data/dict.txt.big')

xmlDefRE = re.compile(r'<?xml.*?>')
textHeadRE = re.compile(r'<TEXT>|<HEADLINE>')
textTailRE = re.compile(r'</TEXT>|</HEADLINE>')
sourceRE = re.compile(r'<SOURCE>.*</SOURCE>')
timeRE = re.compile(r'<DATE_TIME>.*</DATE_TIME>')
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
        self.mentions = []      # [[w_index, mention_lenth, ent_id, ment_str], ...]

class DataReader:
    def __init__(self):
        self.lang = ''
        self.nlp = None
        self.prop = None

    def loadKbidMap(self, filename):
        id_map = {}
        with codecs.open(file, 'r') as fin:
            for line in fin:
                items = re.split(r'\t', line.strip())
                if len(items)!= 4: continue
                id_map[items[0]] = items[1:]
        print("load {0} kbids!".format(len(id_map)))

    def initNlpTool(self, url, lang):
        if not isinstance(self.nlp, type(None)):return
        self.lang = lang
        if lang != 'cmn':
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
        if self.lang == 'cmn':
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
        print("load {0} mentions for {1} docs from {2}!".format(count, len(mentions), file))
        return mentions

    def readKbp(self, path, mentions, doc_type):
        if len(mentions) < 1 or not os.path.isdir(path) :
            print("please check kbp mentions and input path!")
            return
        files = os.listdir(path)
        corpus = []
        offset = -4
        if doc_type == 'df':
            extract = self.extractKBP16DfText
        elif doc_type == 'nw':
            extract = self.extractKBP16NwText
        else:
            extract = self.extractKBP15Text
            offset = -11
        for f in files:
            if f[:offset] in mentions:
                print("processing {0}!".format(f))
                sents = extract(os.path.join(path, f))
                doc = self.readDoc(sents, mentions[f[:offset]])
                doc.doc_id = f[:offset]
                corpus.append(doc)
        return corpus

    # return original text and its count, according to dataset year
    def extractKBP15Text(self, file):
        sents = []
        tree = ET.ElementTree(file=file)
        for seg_e in tree.iterfind('DOC/TEXT/SEG'):
            cur_pos = int(seg_e.attrib['start_char'])
            for text_e in seg_e.iter(tag='ORIGINAL_TEXT'):
                line = text_e.text
                source_m = sourceRE.match(line.strip())
                time_m = timeRE.match(line.strip())
                m = nonTextRE.match(line.strip())
                if m == None and len(line.strip()) > 0 and source_m == None and time_m == None:
                    sents.append([cur_pos-40, text_e.text])     # ignore the begining xml definition
        return sents
    # skip all the lines <...>
    def extractKBP16DfText(self, file):
        sents = []
        cur_pos = -1
        with codecs.open(file, 'r') as fin:
            for line in fin:
                cur_len = len(line)
                m = nonTextRE.match(line.strip())
                if m == None and len(line.strip()) > 0:
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
                    if len(line.strip()) > 0:
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
        tmp_map = {}
        for sent in sents:
            print(sent)
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
            if len(tmp_line.strip()) < 1: continue
            lspace = len(tmp_line) - len(tmp_line.lstrip())
            tokens = self.tokenize(tmp_line)
            # tokens : [[word, start, end, lemma],...]  no lemma for chinese
            for token in tokens:
                w = token[0]
                lemma = w if self.lang=='zh' else token[3]
                t_start = cur_pos + token[1] + 1 + lspace
                t_end = cur_pos + token[2] + 1 + lspace
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
                            tmp_map[m_index] = len(doc.text)-add_text
                        elif m_index in tmp_map:
                            doc.mentions.append([tmp_map[m_index], len(doc.text)-tmp_map[m_index]-add_text, mentions[m_index][2], doc.text[tmp_map[m_index]:tmp_map[m_index]+len(doc.text)-tmp_map[m_index]-add_text]])
        return doc

    def readConll(self, file_name):
        corpus = []
        with codecs.open(file_name, 'r', encoding='UTF-8') as fin:
            doc_id = 0
            is_mention = False
            doc = None
            for line in fin:
                line = line.strip()
                if line.startswith('-DOCSTART-'):
                    if doc_id > 0 and not isinstance(doc, type(None)) and len(doc.text) > 0 and len(doc.mentions) > 0:
                        corpus.append(doc)
                    doc_id += 1
                    if doc_id % 20 ==0:
                        print 'has processed %d docs!' % doc_id
                    doc = Doc()
                    doc.doc_id = doc_id
                    is_mention = False
                    continue
                elif len(line) < 1:
                    is_mention = False
                    continue
                else:
                    items = re.split(r'\t', line)
                    if len(items) > 4 and items[1] == 'B':
                        doc.mentions.append([len(doc.text), 1, items[5], items[2]])
                        doc.text.append(items[2])
                        is_mention = True
                    elif is_mention and len(items) > 2 and items[1] == 'I':
                        doc.mentions[-1][1] += 1
                        continue
                    else:
                        doc.text.append(items[0])
                        is_mention = False
                        continue
                if doc_id > 0 and not isinstance(doc, type(None)) and len(doc.text) > 0 and len(doc.mentions) > 0:
                    corpus.append(doc)
        return corpus

    def extractMentionDic(self, ans15_file, ans15_train_file, ans16_file, conll_file):
        mentions15 = self.loadKbpMentions(ans15_file)
        mentions15_train = self.loadKbpMentions(ans15_train_file)
        mentions16 = self.loadKbpMentions(ans16_file)

        mention_dic = {}
        count = 0
        for doc in mentions15:
            tmp_mentions = mentions15[doc]
            ment = tmp_mentions[3]
            ent_id = tmp_mentions[2]
            tmp_ans = set() if ment not in mention_dic else mention_dic[ment]
            if ent_id not in tmp_ans: count += 1
            tmp_ans.add(ent_id)
            mention_dic[ment] = tmp_ans
        for doc in mentions15_train:
            tmp_mentions = mentions15_train[doc]
            ment = tmp_mentions[3]
            ent_id = tmp_mentions[2]
            tmp_ans = set() if ment not in mention_dic else mention_dic[ment]
            if ent_id not in tmp_ans: count += 1
            tmp_ans.add(ent_id)
            mention_dic[ment] = tmp_ans
        for doc in mentions16:
            tmp_mentions = mentions16[doc]
            ment = tmp_mentions[3]
            ent_id = tmp_mentions[2]
            tmp_ans = set() if ment not in mention_dic else mention_dic[ment]
            if ent_id not in tmp_ans: count += 1
            tmp_ans.add(ent_id)
            mention_dic[ment] = tmp_ans
        print("kbp has totally {0} mentions of {1} entities!".format(len(mention_dic), count))
        conll_corpus = self.readConll(conll_file)
        for doc in conll_corpus:
            for mention in doc.mentions:
                ment = mention[3]
                ent_id = mention[2]
                tmp_ans = set() if ment not in mention_dic else mention_dic[ment]
                if ent_id not in tmp_ans: count += 1
                tmp_ans.add(ent_id)
                mention_dic[ment] = tmp_ans
        print("Conll has totally {0} mentions of {1} entities!".format(len(mention_dic), count))
        return mention_dic

    def saveMentionDic(self, mention_dic, mention_dic_file):
        with codecs.open(mention_dic_file, 'w', encoding='UTF-8') as fout:
            for ment in mention_dic:
                fout.write("%s\t%s\n" % (ment, '\t'.join(mention_dic[ment])))

if __name__ == '__main__':
    eval_path = '/home/caoyx/data/kbp/LDC2017E03_TAC_KBP_Entity_Discovery_and_Linking_Comprehensive_Training_and_Evaluation_Data_2014-2016/data/'
    ans15_file = eval_path+'2015/eval/tac_kbp_2015_tedl_evaluation_gold_standard_entity_mentions.tab'
    ans15_train_file = eval_path + '2015/training/tac_kbp_2015_tedl_training_gold_standard_entity_mentions.tab'
    ans16_file = eval_path+'2016/eval/tac_kbp_2016_edl_evaluation_gold_standard_entity_mentions.tab'
    eval15_path = eval_path + '2015/eval/source_documents/'
    train15_path = eval_path + '2015/training/source_docs/'
    eval16_path = eval_path + '2016/eval/source_documents/'
    conll_file = '/home/caoyx/data/conll/AIDA-YAGO2-dataset.tsv'
    mention_dic_file = '/home/caoyx/data/eval_mention_dic'
    kbid_map_file = ''
    en_server = 'http://localhost:9001'
    es_server = 'http://localhost:9002'
    jieba_dict = '/home/caoyx/data/dict.txt.big'
    languages = ['eng','cmn','spa']
    doc_type = ['nw','df','newswire','discussion_forum']
    dr = DataReader()
    mention_dic = dr.extractMentionDic(ans15_file, ans15_train_file,ans16_file, conll_file)
    dr.saveMentionDic(mention_dic,mention_dic_file)
    # 15 16 en
    #dr.initNlpTool(en_server, languages[0])

    #dr.initNlpTool(jieba_dict, 'zh')
    #mentions = dr.loadKbpMentions(ans16_file)
    #dr.readKbp(eval_path+'2016/eval/source_documents/eng/df/', mentions, 'df')
    #dr.readKbp(eval_path+'2015/eval/source_documents/cmn/newswire/', mentions, '15')