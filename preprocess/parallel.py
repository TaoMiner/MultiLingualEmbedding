import re
import codecs
import preprocess

options = preprocess.options
cleaner = preprocess.cleaner
languages = preprocess.languages

# <doc id="12" url="https://en.wikipedia.org/wiki?curid=12" title="Anarchism">
headerRE = re.compile(r'<doc id="(.*?)".*>')
footerRE = re.compile(r'</doc>')
class Parallel():

    def __init__(self, lang1, lang2):
        # title:[[sent],...]
        if lang1 == lang2:
            print('error:same languages!')
            exit()
        self.lang1 = lang1
        self.lang2 = lang2
        self.ops = [options(lang1), options(lang2)]
        self.entity_dics = [None, None]
        self.corpus = [{},{}]
        self.clinks = {}
        self.parallel_contexts = []
        self.window = 5
        self.has_brace = True
        self.stop_words = [set(), set()]
        self.words = [set(), set()]

    def loadStopWords(self, filename):
        stopwords = set()
        with codecs.open(filename, 'rb', 'utf-8') as fin:
            for line in fin:
                stopwords.add(line.strip())
        return stopwords

    def loadWordVocab(self, filename):
        words = set()
        with codecs.open(filename, 'rb', 'utf-8') as fin:
            for line in fin:
                items = re.split(r'\t', line.strip())
                words.add(items[0])
        return words

    def loadCrossLink(self, filename):
        with codecs.open(filename, 'rb', 'utf-8') as fin:
            line_count = 0
            for line in fin:
                line_count += 1
                items = re.split(r'\t', line.strip('\n'))
                if len(items) != len(languages): continue
                if len(items[self.lang1]) > 0 and len(items[self.lang2]) > 0:
                    self.clinks[items[self.lang1]] = items[self.lang2]
        print('successfully load {0} clinks from {1} to {2}!'.format(len(self.clinks), languages[self.lang1], languages[self.lang2]))

    def readDoc(self):
        for i in range(2):
            self.readMonoDoc(i)
            print("successfully load {0} doc for {1} language!".format(len(self.corpus[i]), self.ops[i].lang))

    def readMonoDoc(self, i):
        op = self.ops[i]
        pre = preprocess.Preprocessor()
        entity_id_dic = pre.loadEntityIdDic(op.vocab_entity_file)
        entity_dic = pre.loadEntityDic(op.vocab_entity_file)
        total_entity_id, total_id_entity = pre.loadWikiIndex(op.entity_index_dump)
        redirects = pre.loadRedirects(op.redirect_file)
        redirects_id = pre.loadRedirectsId(op.redirect_file, total_entity_id)
        with codecs.open(op.cross_corpus_file, 'r') as fin:
            cur_title_id = ''
            tmp_sents = None
            for line in fin:
                line = line.strip()
                tmp_line = ''
                if len(line) < 1: continue
                m = footerRE.match(line)
                if not isinstance(m, type(None)) :
                    self.corpus[i][cur_title_id] = tmp_sents
                    cur_title_id = ''
                    tmp_sents = None
                    continue
                m = headerRE.match(line)
                if m:
                    cur_title_id = m.group(1) if m.group(1) in entity_id_dic else ''
                    cur_title_id = redirects_id[cur_title_id] if cur_title_id in redirects_id else cur_title_id
                    if len(cur_title_id) > 0:
                        tmp_sents = self.corpus[i][cur_title_id] if cur_title_id in self.corpus[i] else []
                    continue
                elif not isinstance(tmp_sents, type(None)) and len(cur_title_id) > 0:
                    seg_sents = re.split(r'[\.!?！？｡。]', line.strip('\r\n\t .?!！？｡。'))
                    for tmp_line in seg_sents:
                        tmp_line = tmp_line.strip()
                        if len(tmp_line) > 0:
                            if op.lang == 'zh':
                                tmp_line = cleaner.cleanAnchorSent(tmp_line, op.lang, isReplaceId=False)
                            else:
                                tmp_line = cleaner.cleanAnchorSent(tmp_line, op.lang, isReplaceId=True, entity_id=entity_dic, redirects=redirects)
                            if len(tmp_line) > 0:
                                tmp_sents.append(tmp_line)

    def extractContext(self, sents, stop_words = None, words = None):
        contexts_dict = {}
        for sent in sents:
            cur = 0
            sent_words = []
            # [[start, end],...]
            anchors = []
            for s, e in  cleaner.findBalanced(sent):
                tmp_words = re.split(r' ', sent[cur:s].strip())
                if not isinstance(stop_words, type(None)) and not isinstance(words, type(None)):
                    for w in tmp_words:
                        if w in words and w not in stop_words and w != 'dddddd':
                            sent_words.append(w)
                else:
                    sent_words.extend(tmp_words)
                tmp_anchor = sent[s:e]
                tmp_vbar = tmp_anchor.find('|')
                tmp_label = ''
                tmp_title = ''
                if tmp_vbar > 0:
                    tmp_title = tmp_anchor[2:tmp_vbar]
                    tmp_label = tmp_anchor[tmp_vbar + 1 :-2]
                else:
                    tmp_label = tmp_anchor[2:-2]
                    tmp_title = tmp_label
                tmp_words = re.split(r' ', tmp_label)
                start_index = len(sent_words)
                if not isinstance(stop_words, type(None)) and not isinstance(words, type(None)):
                    for w in tmp_words:
                        if w in words and w not in stop_words and w != 'dddddd':
                            sent_words.append(w)
                else:
                    sent_words.extend(tmp_words)
                length = len(sent_words) - start_index
                if length > 0 and len(tmp_title) > 0:
                    anchors.append([tmp_title, start_index,length])
                cur = e
            if cur < len(sent):
                tmp_words = re.split(r' ', sent[cur:])
                if not isinstance(stop_words, type(None)) and not isinstance(words, type(None)):
                    for w in tmp_words:
                        if w in words and w not in stop_words and w != 'dddddd':
                            sent_words.append(w)
                else:
                    sent_words.extend(tmp_words)
            # sent_words contains all words in sent
            # anchors contains start pos and end pos in the sentwords index
            for anc in anchors:
                tmp_contexts = []
                begin = anc[1]-self.window if anc[1]-self.window > 0 else 0
                end = anc[1] + anc[2] + self.window + 1 if anc[1] + anc[2] + self.window +1 < len(sent_words) else len(sent_words)
                for i in range(begin, end):
                    # if i >= anc[1] and i < anc[1]+anc[2]: continue
                    if len(sent_words[i]) > 0:
                        tmp_contexts.append(sent_words[i])
                if len(tmp_contexts) > 0:
                    tmp_context_list = contexts_dict[anc[0]] if anc[0] in contexts_dict else []
                    tmp_context_list.append(tmp_contexts)
                    contexts_dict[anc[0]] = tmp_context_list
        return contexts_dict            # {ent_id:[context_set, ...], ...}

    # keep the anchor
    def extractContext2(self, sents, entity_dic=None, has_brace = False):
        contexts_dict = {}
        for sent in sents:
            cur = 0
            sent_words = []
            # [[start, end],...]
            anchors = []
            for s, e in  cleaner.findBalanced(sent):
                tmp_words = re.split(r' ', sent[cur:s].strip())
                sent_words.extend(tmp_words)
                tmp_anchor = sent[s:e]
                tmp_vbar = tmp_anchor.find('|')
                tmp_label = ''
                tmp_title = ''
                if tmp_vbar > 0:
                    tmp_title = tmp_anchor[2:tmp_vbar]
                    tmp_label = tmp_anchor[tmp_vbar + 1 :-2]
                else:
                    tmp_label = tmp_anchor[2:-2]
                    tmp_title = tmp_label
                tmp_words = re.split(r' ', tmp_label)
                start_index = len(sent_words)
                sent_words.extend(tmp_words)
                length = len(tmp_words)
                if length > 0 and len(tmp_title) > 0:
                    anchors.append([tmp_title, tmp_label, start_index,length])
                cur = e
            if cur < len(sent):
                tmp_words = re.split(r' ', sent[cur:])
                sent_words.extend(tmp_words)
            # sent_words contains all words in sent
            # anchors contains start pos and end pos in the sentwords index
            for anc in anchors:
                has_anchor = False
                tmp_contexts = []
                begin = anc[2]-self.window if anc[2]-self.window > 0 else 0
                end = anc[2] + anc[3] + self.window + 1 if anc[2] + anc[3] + self.window +1 < len(sent_words) else len(sent_words)
                for i in range(begin, end):
                    if i >= anc[2] and i < anc[2]+anc[3]:
                        if not has_anchor:
                            if isinstance(entity_dic, type(None)):
                                title = anc[0]
                            else:
                                title = entity_dic[anc[0]] if anc[0] in entity_dic else ''
                            if len(title) > 0:
                                if has_brace:
                                    tmp_anchor_str = '[[' + title + '|' + anc[1] + ']]'
                                else:
                                    tmp_anchor_str = anc[1]
                                tmp_contexts.append(tmp_anchor_str)
                                has_anchor = True
                            else:
                                del tmp_contexts[:]
                                break
                        continue
                    if len(sent_words[i]) > 0:
                        tmp_contexts.append(sent_words[i])
                if len(tmp_contexts) > 1:
                    tmp_context_set = contexts_dict[anc[0]] if anc[0] in contexts_dict else []
                    tmp_context_set.append(tmp_contexts)
                    contexts_dict[anc[0]] = tmp_context_set
        return contexts_dict

    def extract(self):
        num_nonequal = 0
        for cl in self.clinks:
            if cl not in self.corpus[0] or self.clinks[cl] not in self.corpus[1]:
                continue
            sents1 = self.corpus[0][cl]
            sents2 = self.corpus[1][self.clinks[cl]]
            contexts_dict1 = self.extractContext(sents1, stop_words=self.stop_words[0], words=self.words[0])
            contexts_dict2 = self.extractContext(sents2, stop_words=self.stop_words[1], words=self.words[1])
            for t1 in contexts_dict1:       # {ent_id:[context_set, ...], ...}
                if t1 not in self.clinks or self.clinks[t1] not in contexts_dict2:
                    continue
                context_list1 = contexts_dict1[t1]
                context_list2 = contexts_dict2[self.clinks[t1]]
                self.parallel_contexts.append([cl, t1, context_list1, self.clinks[cl], self.clinks[t1], context_list2])
        print("successfully load {0} parallel contexts!".format(len(self.parallel_contexts)))

    def saveParaData(self, filename):
        with codecs.open(filename, 'w') as fout:
            for context in self.parallel_contexts:
                if len(context) != 6: continue
                if len(context[0]) <1 or len(context[1])<1 or len(context[2])<1 or len(context[3])<1 or len(context[4])<1 or len(context[5])<1: continue
                fout.write("1\t{0}\t{1}\t{2}\n".format(context[0], context[1], "\t".join(" ".join(x) for x in context[2]) ))
                fout.write("2\t{0}\t{1}\t{2}\n".format(context[3], context[4], "\t".join(" ".join(x) for x in context[5]) ))
                #fout.write("%s\t%s\t%s\t%s\n" % (context[0], context[1], ' '.join(context[2]), ' '.join(context[3])))

if __name__ == '__main__':
    str_lang1 = 'en'
    str_lang2 = 'es'
    context_window = 5
    cross_file = '/home/caoyx/data/paradata/cross_links_all_id.dat'
    par_file = '/home/caoyx/data/paradata/para_contexts.' + str_lang1 + '-' + str_lang2
    stop_word_file = ['/home/caoyx/data/en_stop_words', '/home/caoyx/data/es_stop_words','/home/caoyx/data/zh_stop_words']
    word_vocab_file = ['/home/caoyx/data/etc/vocab/envocab/vocab_word.txt', '/home/caoyx/data/etc/vocab/esvocab/vocab_word.txt', '/home/caoyx/data/etc/vocab/zhvocab/vocab_word.txt']
    lang1 = languages.index(str_lang1)
    lang2 = languages.index(str_lang2)
    par = Parallel(lang1, lang2)
    par.window = context_window
    # par.stop_words[0].update(par.loadStopWords(stop_word_file[0]))
    # par.stop_words[1].update(par.loadStopWords(stop_word_file[2]))
    par.words[0].update(par.loadWordVocab(word_vocab_file[0]))
    par.words[1].update(par.loadWordVocab(word_vocab_file[1]))
    par.loadCrossLink(cross_file)
    # whether output brace for anchors
    par.has_brace = False
    par.readDoc()
    par.extract()
    par.saveParaData(par_file)
