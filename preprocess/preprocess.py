#!/usr/bin/env python
# -*- coding: utf-8 -*-
import codecs
import re
# import HTMLParser
import string
import jieba
from pycorenlp import StanfordCoreNLP
import os

# htmlparser = HTMLParser.HTMLParser()
jieba.set_dictionary('/home/caoyx/data/dict.txt.big')
# jieba.set_dictionary('/Users/ethan/Downloads/zhwiki/dict.txt.big')

languages = ('en', 'zh', 'es')

# parameters
class options():
    def __init__(self, lang):
        if lang >= len(languages) or lang < 0 :
            print("invalid lang id!")
            exit()
        self.dump_path = '/home/caoyx/data/dump20170401/'
        self.lang = languages[lang]
        self.lang_wiki = self.lang+ 'wiki'
        self.redirect_dump = self.dump_path + self.lang_wiki + '/' + self.lang_wiki + '-20170401-redirect.sql'
        self.title_dump = self.dump_path + self.lang_wiki + '/' + self.lang_wiki + '-20170401-all-titles-in-ns0'
        self.entity_index_dump = self.dump_path + self.lang_wiki + '/' + self.lang_wiki + '-20170401-pages-articles-multistream-index.txt'
        self.pagelink_dump = self.dump_path + self.lang_wiki + '/' + self.lang_wiki + '-20170401-pagelinks.sql'
        self.langlink_dump = self.dump_path + self.lang_wiki + '/' + self.lang_wiki + '-20170401-langlinks.sql'
        # output
        self.output_path = self.lang_wiki + '_cl'
        # WikiExtractor output
        self.title_file = self.dump_path + self.output_path + '/wiki_article_title'
        self.raw_anchor_file = self.dump_path + self.output_path + '/wiki_anchor_text'
        # redirect vocab
        self.redirect_file = self.dump_path + self.output_path + '/vocab_redirects.dat'
        self.raw_vocab_entity_file = self.dump_path + self.output_path + '/vocab_entity_all.dat'
        # kg file
        self.mono_outlink_file = self.dump_path + self.output_path + '/mono_kg.dat'
        self.mono_outlink_idfile = self.dump_path + self.output_path + '/mono_kg_id.dat'
        # linked entity vocab
        self.vocab_entity_file = self.dump_path + self.output_path + '/vocab_entity.dat'
        # cross links file
        self.cross_link_file = self.dump_path + self.output_path + '/cross_links.dat'
        # cleaned anchor text
        self.anchor_file = self.dump_path + self.output_path + '/anchor_text_cl.dat'
        # entity mention mapping
        self.mention_file = self.dump_path + self.output_path + '/mention_count.dat'
        # linked wiki xml
        self.cross_corpus_file = self.dump_path + self.output_path + '/linked_wiki_pages.dat'
        # wiki text
        self.raw_text_file = self.dump_path + self.output_path + '/wiki_text'
        self.text_file = self.dump_path + self.output_path + '/wiki_text_cl'

nsidRE = re.compile(r'(\d{1,}):(\d{1,}):(.*)')
# pagelink: (pl_from_id, pl_namespace, pl_title, pl_from_namespace),
# only for main namespace 0
linkRE = re.compile(r'(\d{1,}),0,\'(.*?)\',0')
# redirect: (rd_from_id, rd_namespace_id, rd_title, rd_interwiki, rd_fragment),
# only for main namespace 0
redirectRE = re.compile(r'(\d{1,}),0,\'(.*?)\',\'(.*?)\',\'(.*?)\'')
# langlinks: (cur_id, target_lang, target_title),
# only considering english, chinese and Spanish
link_pattern = '(\d{1,}),\'(' + '|'.join(languages) + ')\',\'(.*?)\''
langlinkRE = re.compile(link_pattern)
# -{zh-cn:xxx1;zh-cn:xxx2}-
formatRE = re.compile(r'-\{.*?(zh-hans|zh-cn):(?P<label>[^;]*?)([;].*?\}|\})-')
# sql extract language
langRE = re.compile(r'Database: ([a-z]{2})wiki')
class Preprocessor():

    def __init__(self):
        # total id dict of entity in namespace 0
        self.total_entity_id = {}
        self.total_id_entity = {}
        # entity dict filter out redirects
        self.entity_id = {}
        self.id_entity = {}
        # redirects dict extracted from wiki-redirect.sql
        self.redirects = {}
        #
        self.outlinks = {}
        self.cur_lang_index = -1
        self.langlinks = None
        self.langlinksCount = None

    # format -{zh-cn:xxx1;zh-cn:xxx2}- to xxx1
    def formatRawWiki(self, zhwiki_file, zhwiki_format_file):
        line_count = 0
        with codecs.open(zhwiki_file, 'r') as fin:
            with codecs.open(zhwiki_format_file, 'w', 'utf-8') as fout:
                for line in fin:
                    line_count += 1
                    if line_count % 1000000 == 0: print("has processed {0} lines!".format(line_count))
                    line = line.decode('utf-8', 'ignore')
                    line = formatRE.sub('\g<label>', line)
                    fout.write(line)

    @staticmethod
    def loadWikiIndex(filename):
        total_entity_id = {}
        total_id_entity = {}
        with codecs.open(filename, 'r', 'utf-8') as fin:
            for line in fin:
                m = nsidRE.match(line.strip())
                if m != None:
                    id = m.group(2)
                    title = m.group(3)
                    total_entity_id[title] = id
                    total_id_entity[id] = title
        print("successfully load {0} wiki index!".format(len(total_entity_id)))
        return total_entity_id, total_id_entity

    # build wiki_aritle_title dict that doesnt contain any redirects
    def buildEntityDic(self, filename):
        with codecs.open(filename, 'r', 'utf-8') as fin:
            for line in fin:
                title = line.strip()
                if title in self.total_entity_id:
                    self.entity_id[title] = self.total_entity_id[title]
                    self.id_entity[self.total_entity_id[title]] = title
        print("successfully build {0} entities!".format(len(self.entity_id)))


    def parseRedirects(self, filename):
        with codecs.open(filename, 'rb') as fin:
            for line in fin:
                line = line.decode('utf-8', 'ignore')
                line = line.replace('INSERT INTO `redirect` VALUES (', '')
                for i in line.strip().split('),('):
                    m = redirectRE.match(i)  # Only select namespace 0 (Main/Article) pages
                    if m != None:
                        rd_id = m.group(1)
                        rd_title = m.group(2)
                        rd_title = rd_title.replace('\\', '')
                        rd_title = rd_title.replace('_', ' ')

                        if rd_id not in self.total_id_entity or rd_title not in self.entity_id or self.total_id_entity[rd_id] == rd_title:
                            continue
                        self.redirects[self.total_id_entity[rd_id]] = rd_title
                        # remove redirect title in entity dic
                        if rd_id in self.id_entity:
                            del self.entity_id[self.id_entity[rd_id]]
                            del self.id_entity[rd_id]
        print("successfully parse {0} redirects for {1} entities!".format((len(self.redirects), len(self.entity_id))))

    def lowerTitleToRedirects(self):
        tmp_redirects = {}
        overlapped_set = set()
        for ent in self.entity_id:
            lower_ent = ent.lower()
            if lower_ent in tmp_redirects:
                overlapped_set.add(lower_ent)
            elif lower_ent not in self.redirects and lower_ent!=ent:
                    tmp_redirects[lower_ent] = ent
        for o in overlapped_set:
            del tmp_redirects[o]
        print("lowered {0} new redirects!".format(len(tmp_redirects)))
        self.redirects.update(tmp_redirects)
        del tmp_redirects

    def saveEntityDic(self, filename):
        with codecs.open(filename, 'w', 'utf-8') as fout:
            for ent in self.entity_id:
                fout.write('{0}\t{1}\n'.format((htmlparser.unescape(self.entity_id[ent]), htmlparser.unescape(ent))))

    def saveRedirects(self, filename):
        with codecs.open(filename, 'w', 'utf-8') as fout:
            for r in self.redirects:
                # r_title \t title
                fout.write('{0}\t{1}\n'.format(htmlparser.unescape(r), htmlparser.unescape(self.redirects[r])))

    @staticmethod
    def loadEntityDic(filename):
        entity_id = {}
        with codecs.open(filename, 'rb', 'utf-8') as fin:
            for line in fin:
                items = re.split(r'\t', line.strip())
                if len(items) != 2 : continue
                entity_id[items[1]] = items[0]
        print("successfully load {0} entities!".format(len(entity_id)))
        return entity_id

    @staticmethod
    def loadEntityIdDic(filename):
        id_entity = {}
        with codecs.open(filename, 'rb', 'utf-8') as fin:
            for line in fin:
                items = re.split(r'\t', line.strip())
                if len(items) != 2 : continue
                id_entity[items[0]] = items[1]
        print("successfully load {0} entities!".format(len(id_entity)))
        return id_entity

    @staticmethod
    def loadRedirects(filename):
        redirects = {}
        with codecs.open(filename, 'rb', 'utf-8') as fin:
            for line in fin:
                items = re.split(r'\t', line.strip())
                if len(items) != 2 : continue
                redirects[items[0]] = items[1]
        print("successfully load {0} redirects!".format(len(redirects)))
        return redirects

    @staticmethod
    def loadRedirectsId(filename, entity_id_dic):
        redirects = {}
        with codecs.open(filename, 'rb', 'utf-8') as fin:
            for line in fin:
                items = re.split(r'\t', line.strip())
                if len(items) != 2: continue
                if items[0] in entity_id_dic and items[1] in entity_id_dic:
                    redirects[entity_id_dic[items[0]]] = entity_id_dic[items[1]]
        print("successfully load {0} redirect ids!".format(len(redirects)))
        return redirects

    def parsePageLinks(self, filename):
        with codecs.open(filename, 'rb') as fin:
            for line in fin:
                line = line.decode('utf-8', 'ignore')
                line = line.replace(u'INSERT INTO `pagelinks` VALUES (', '')
                for i in line.strip().split(u'),('):
                    m = linkRE.match(i)  # Only select namespace 0 (Main/Article) pages
                    if m != None:
                        from_title = None
                        target_title = None
                        tmp_target_title = m.group(2)
                        tmp_target_title = tmp_target_title.replace(u'\\', '')
                        tmp_target_title = tmp_target_title.replace(u'_', ' ')
                        tmp_from_id = m.group(1)
                        if tmp_target_title in self.redirects:
                            target_title = self.redirects[tmp_target_title]
                        elif tmp_target_title in self.entity_id:
                            target_title = tmp_target_title
                        if tmp_from_id in self.total_id_entity:
                            tmp_from_title = self.total_id_entity[tmp_from_id]
                            if tmp_from_title in self.redirects:
                                from_title = self.redirects[tmp_from_title]
                            elif tmp_from_id in self.id_entity:
                                from_title = self.id_entity[tmp_from_id]
                        if from_title and target_title:
                            tmp_set = set() if from_title not in self.outlinks else self.outlinks[from_title]
                            tmp_set.add(target_title)
                            self.outlinks[from_title] = tmp_set
        outlink_num = 0
        for t in self.outlinks:
            outlink_num += len(self.outlinks[t])
        print("successfully extract {0} outlinks for {1} entities!".format(outlink_num, len(self.outlinks)))

    def saveOutlinks(self,filename, isId = True):
            with codecs.open(filename, 'w', 'utf-8') as fout:
                tmp_line = []
                for t in self.outlinks:
                    if t not in self.entity_id or len(self.entity_id[t]) < 1: continue
                    if not isId:
                        fout.write('{0}\t{1}\n'.format(htmlparser.unescape(t), htmlparser.unescape('\t'.join(self.outlinks[t]))))
                    else:
                        tmp_line.append(self.entity_id[t])
                        for tt in self.outlinks[t]:
                            if tt in self.entity_id:
                                tmp_line.append(self.entity_id[tt])
                        if len(tmp_line) > 1:
                            fout.write('{0}\n'.format('\t'.join(tmp_line)))
                        del tmp_line[:]


    def saveLinkedEntity(self, filename):
        linked_entities = set()
        for t in self.outlinks:
            linked_entities.add(t)
            for lt in self.outlinks[t]:
                linked_entities.add(lt)
        print("totally {0} linked entities!".format(len(linked_entities)))
        error_count = 0
        with codecs.open(filename, 'w', 'utf-8') as fout:
            for t in linked_entities:
                if t not in self.entity_id:
                    error_count += 1
                    continue
                fout.write('{0}\t{1}\n'.format(htmlparser.unescape(self.entity_id[t]), htmlparser.unescape(t)))
        print("{0} linked entities not in vocab!".format(error_count))

    def parseLangLinks(self, filename):
        with codecs.open(filename, 'rb') as fin:
            cur_lang = None
            for line in fin:
                line = line.decode('utf-8', 'ignore')
                m = langRE.search(line)
                if m:
                    cur_lang = m.group(1)
                    self.cur_lang_index = languages.index(cur_lang)
                    print("extract {0} language links!".format(cur_lang))
                if self.cur_lang_index==-1: continue
                line = line.replace('INSERT INTO `langlinks` VALUES (', '')
                for i in line.strip().split('),('):
                    m = langlinkRE.match(i)
                    if m != None:
                        cur_title = None
                        cur_id = m.group(1)
                        target_lang = m.group(2)
                        if target_lang == cur_lang : continue
                        target_title = m.group(3)
                        if target_lang == cur_lang : continue
                        target_title = target_title.replace('\\', '')
                        target_title = target_title.replace('_', ' ')
                        if cur_id in self.total_id_entity:
                            tmp_cur_title = self.total_id_entity[cur_id]
                            if tmp_cur_title in self.redirects:
                                cur_title = self.redirects[tmp_cur_title]
                            elif cur_id in self.id_entity:
                                cur_title = self.id_entity[cur_id]
                        # not redirect target title
                        if cur_title:
                            self.addLangLink(cur_title, target_title, target_lang)
        out = ''
        for i in xrange(len(languages)):
            out += "{0} links to {1} lang! ".format(self.langlinksCount[i], languages[i] )
        print("successfully parsed {0} linked entity of {1} lang, {2}".format(len(self.langlinks), cur_lang, out))

    def addLangLink(self, cur_title, tar_title, tar_lang):
        if isinstance(self.langlinks, type(None)):
            self.langlinks = {}
            self.langlinksCount = [0 for i in xrange(len(languages))]

        tar_index = languages.index(tar_lang)
        if cur_title in self.langlinks:
            tmp_tarlinks = self.langlinks[cur_title]
        else:
            tmp_tarlinks = ['' for i in xrange(len(languages))]
            tmp_tarlinks[self.cur_lang_index] = cur_title
        if tmp_tarlinks[self.cur_lang_index] != cur_title:
            print("error! different cur titles!")
        if len(tmp_tarlinks[tar_index]) < 1 and tmp_tarlinks[tar_index]!=tar_title:
            tmp_tarlinks[tar_index] = tar_title
            self.langlinksCount[tar_index] += 1
            self.langlinks[cur_title] = tmp_tarlinks

    def saveLangLink(self, filename):
        with codecs.open(filename, 'w', 'utf-8') as fout:
            fout.write("{0}\n".format(len(self.langlinks)))
            fout.write("{0}\n".format(' '.join(languages)))
            for ct in self.langlinks:
                fout.write("{0}\n".format('\t'.join(self.langlinks[ct])))

    @staticmethod
    def loadCrossLinks(filename):
        with codecs.open(filename, 'rb', 'utf-8') as fin:
            link_set = set()
            for line in fin:
                items = re.split(r'\t', line.strip('\n'))
                if len(items) != len(languages): continue
                for i in items:
                    if len(i) < 1: continue
                    link_set.add(i)
        print("successfully load {0} cross lingual entities!".format(len(link_set)))
        return link_set

punc = re.compile('[{0}]'.format(re.escape(string.punctuation)))
zh_punctuation = "！？｡。·＂＃＄％＆＇（）＊＋，－／：；＜＝＞＠［＼］＾＿｀｛｜｝～｟｠｢｣､、〃》「」『』【】〔〕〖〗〘〙〚〛〜〝〞〟〰〾〿–—‘’‛“”„‟…‧﹏."
zhpunc = re.compile('[{0}]'.format(re.escape(zh_punctuation)))

numRE1 = re.compile(r'(?<=\s)[\d\s]+(?=($|\s))')
numRE2 = re.compile(r'(?<=^)[\d\s]+(?=($|\s))')
spaceRE = re.compile(r'[\s]+')

class cleaner():
    def __init__(self):
        self.entity_id = None
        self.redirects = None
        self.mentions = None
        self.formatRE = re.compile(r'-\{.*?(zh-hans|zh-cn):(?P<label>[^;]*?)([;].*?\}|\})-')
        self.nlp = None
        self.tagRE = re.compile(r'^<.*>$')

    def init(self, lang):
        self.lang = languages[lang]
        self.mentions = {}
        print("cleaning {0} language!".format(self.lang))

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

    # format -{zh-cn:xxx1;zh-cn:xxx2}- to xxx1
    def formatRawWiki(self, raw_anchor_file):
        line_count = 0
        with codecs.open(raw_anchor_file, 'r', 'utf-8') as fin:
            with codecs.open('./tmp', 'w', 'utf-8') as fout:
                for line in fin:
                    line_count += 1
                    if line_count % 1000000 == 0: print("has processed {0} lines!".format(line_count))
                    line = self.formatRE.sub('\g<label>', line)
                    self.findBalanced(line)
                    fout.write(line)
        with codecs.open('./tmp', 'r', 'utf-8') as fin:
            with codecs.open(raw_anchor_file, 'w', 'utf-8') as fout:
                for line in fin:
                    fout.write(line)

    def replaceId(self, sent , entity_id = None, redirects = None):
        cur = 0
        sent_cl = ''
        for s, e in cleaner.findBalanced(sent):
            sent_cl += sent[cur:s]
            tmp_anchor = sent[s:e]
            # extract title and label
            tmp_vbar = tmp_anchor.find('|')
            tmp_ent = ''
            tmp_ment = ''
            tmp_title_id = ''
            if tmp_vbar > 0:
                tmp_ent = tmp_anchor[2:tmp_vbar]
                tmp_ment = tmp_anchor[tmp_vbar + 1:-2]
            else:
                tmp_ent = tmp_anchor[2:-2]
                tmp_ment = tmp_ent

            if len(tmp_ent) > 0:
                if not isinstance(redirects, type(None)) and tmp_ent in redirects:
                    tmp_ent = redirects[tmp_ent]
                if not isinstance(entity_id, type(None)) and tmp_ent in entity_id:
                    tmp_title_id = entity_id[tmp_ent]
            sent_cl += '[['+tmp_title_id+'|'+tmp_ment+']]' if len(tmp_title_id) > 0 else tmp_ment
            cur = e
        sent_cl += sent[cur:]
        return sent_cl

    def formatZhDoc(self, filename, outputfile):
        with codecs.open(filename, 'r', 'utf-8') as fin:
            with codecs.open(outputfile, 'w', 'utf-8') as fout:
                for line in fin:
                    m = self.tagRE.match(line.strip())
                    if m:
                        fout.write("{0}\n".format(line.strip()))
                    else:
                        tmp_line = self.replaceId(line, entity_id=self.entity_id, redirects=self.redirects)
                        fout.write("{0}\n".format(tmp_line))

    @staticmethod
    def regularize(str, lang):
        # possessive case 's
        # tmp_line = re.sub(r' s |\'s', ' ', str)
        # following clean wiki xml, punctuation, numbers, and lower case

        tmp_line = punc.sub('', str)
        if lang == 'zh':
            tmp_line = zhpunc.sub('', tmp_line)
        tmp_line = spaceRE.sub(' ', tmp_line)
        tmp_line = numRE1.sub('dddddd', tmp_line)
        tmp_line = numRE2.sub('dddddd', tmp_line).lower().strip()
        return tmp_line

    def cleanText(self, raw_text_file, text_file):
        with codecs.open(raw_text_file, 'rb', 'utf-8') as fin:
            with codecs.open(text_file, 'w', 'utf-8') as fout:
                for line in fin:
                    line = self.regularize(line, self.lang)
                    if len(line) > 11:
                        fout.write("{0}\n".format(line))

    @staticmethod
    def findBalanced(text, openDelim=['[['], closeDelim=[']]']):
        """
        Assuming that text contains a properly balanced expression using
        :param openDelim: as opening delimiters and
        :param closeDelim: as closing delimiters.
        :return: an iterator producing pairs (start, end) of start and end
        positions in text containing a balanced expression.
        """
        openPat = '|'.join([re.escape(x) for x in openDelim])
        afterPat = dict()
        for o, c in zip(openDelim, closeDelim):
            afterPat[o] = re.compile(openPat + '|' + c, re.DOTALL)
        stack = []
        start = 0
        cur = 0
        # end = len(text)
        startSet = False
        startPat = re.compile(openPat)
        nextPat = startPat
        while True:
            next = nextPat.search(text, cur)
            if not next:
                return
            if not startSet:
                start = next.start()
                startSet = True
            delim = next.group(0)
            if delim in openDelim:
                stack.append(delim)
                nextPat = afterPat[delim]
            else:
                opening = stack.pop()
                # assert opening == openDelim[closeDelim.index(next.group(0))]
                if stack:
                    nextPat = afterPat[stack[-1]]
                else:
                    yield start, next.end()
                    nextPat = startPat
                    start = next.end()
                    startSet = False
            cur = next.end()

    @staticmethod
    def cleanSent(sent, lang):
        anchor_count = 0
        cur = 0
        res = ''
        openDelim = ['[[']
        closeDelim = [']]']
        boundary = 1
        if lang == 'zh':
            seg_list = jieba.cut(sent, cut_all=False)
            # some chinese entities contain whitespace
            seg_line = " ".join(seg_list)
            openDelim = ['[ [']
            closeDelim = ['] ]']
            boundary = 2
        else:
            seg_line = sent
        for s, e in cleaner.findBalanced(seg_line, openDelim, closeDelim):
            # remove postfix of an anchor
            tmp_line = cleaner.regularize(seg_line[cur:s], lang)
            if len(tmp_line) > 0:
                res += tmp_line + ' '

            tmp_anchor = seg_line[s:e]
            # extract title and label
            # [_[_word_word_|_word_word_]_] or [_[_word_word_]_]
            tmp_vbar = tmp_anchor.find('|')
            tmp_label = ''
            if tmp_vbar > 0:
                tmp_label = tmp_anchor[tmp_vbar + 1 * boundary:-2 * boundary]
            else:
                tmp_label = tmp_anchor[2 * boundary:-2 * boundary]
            # map the right title
            tmp_label = cleaner.regularize(tmp_label, lang)

            if len(tmp_label) > 0:
                res += tmp_label + ' '
            cur = e
        tmp_line = cleaner.regularize(seg_line[cur:], lang)
        if len(tmp_line) > 0:
            res += tmp_line
        return res.strip()

    def processSent(self, sent, entity_id=None, redirects=None, mentions=None):
        anchor_count = 0
        cur = 0
        sent_cl = ''
        anchor_boundry = []
        for s, e in cleaner.findBalanced(sent):
            sent_cl += sent[cur:s]
            tmp_anchor = sent[s:e]
            # extract title and label
            tmp_vbar = tmp_anchor.find('|')
            tmp_ent = ''
            tmp_ment = ''
            if tmp_vbar > 0:
                tmp_ent = tmp_anchor[2:tmp_vbar]
                tmp_ment = tmp_anchor[tmp_vbar + 1:-2]
            else:
                tmp_ent = tmp_anchor[2:-2]
                tmp_ment = tmp_ent

            if len(tmp_ment) > 0:
                if not isinstance(redirects,type(None)) and tmp_ent in redirects:
                    tmp_ent = redirects[tmp_ent]
                if not isinstance(entity_id, type(None)) and tmp_ent in entity_id:
                    tmp_title_id = entity_id[tmp_ent]
                    anchor_boundry.append([len(sent_cl), len(sent_cl) + len(tmp_ment), tmp_title_id])
            sent_cl += tmp_ment
            cur = e
        sent_cl += sent[cur:]
        seg_sent = self.tokenize(sent_cl.lower())

        res = ''
        anchor_index = 0
        tmp_ment = ''
        i = 0
        while i < len(seg_sent):
            token = seg_sent[i]
            i += 1
            token[0] = token[0].strip()
            if len(token[0]) < 1 : continue
            num_m = numRE2.match(token[0])
            if num_m:
                token[3] = 'dddddd'
            punc_m = punc.match(token[0])
            if punc_m:
                continue
            if anchor_index >= len(anchor_boundry) or token[2] < anchor_boundry[anchor_index][0]:
                res += token[3] + ' '
            elif token[1] >= anchor_boundry[anchor_index][1] :
                res += '[['+ anchor_boundry[anchor_index][2] +'|'+tmp_ment.strip()+']]' + ' '
                tmp_ment = ''
                anchor_index += 1
                i = i-1 if i-1 >= 0 else 0
            else:
                tmp_ment += token[3] + ' '
        if len(tmp_ment) > 0:
            res += '[['+ anchor_boundry[anchor_index][2] +'|'+tmp_ment.strip()+']]'
        return res.strip()

    # no anchor
    @staticmethod
    def removeAnchorSent(sent, lang):
        anchor_count = 0
        cur = 0
        res = ''
        openDelim = ['[[']
        closeDelim = [']]']
        boundary = 1
        if lang == 'zh':
            seg_list = jieba.cut(sent.strip(), cut_all=False)
            # some chinese entities contain whitespace
            seg_line = "_".join(seg_list)
            openDelim = ['[_[']
            closeDelim = [']_]']
            boundary = 2
        else:
            seg_line = sent
        for s, e in cleaner.findBalanced(seg_line, openDelim, closeDelim):
            # remove postfix of an anchor
            if lang == 'zh':
                tmp_line = re.sub(r'_', ' ', seg_line[cur:s])
            else:
                tmp_line = seg_line[cur:s]
            tmp_line = cleaner.regularize(tmp_line, lang)
            if len(tmp_line) > 0:
                res += tmp_line + ' '
            tmp_anchor = seg_line[s:e]
            # extract title and label
            # [_[_word_word_|_word_word_]_] or [_[_word_word_]_]
            tmp_vbar = tmp_anchor.find('|')
            tmp_title = ''
            tmp_label = ''
            tmp_title_id = ''
            if tmp_vbar > 0:
                tmp_title = tmp_anchor[2 * boundary:tmp_vbar]
                tmp_label = tmp_anchor[tmp_vbar + 1 * boundary:-2 * boundary]
            else:
                tmp_title = tmp_anchor[2 * boundary:-2 * boundary]
                tmp_label = tmp_title
            # map the right title
            if lang == 'zh':
                tmp_title = re.sub(r'_', '', tmp_title)
                tmp_label = re.sub(r'_', ' ', tmp_label)
            tmp_label = cleaner.regularize(tmp_label, lang)
            # remove prefix of anchor
            if len(tmp_label) > 0:
                res += tmp_label + ' '
            cur = e
        if lang == 'zh':
            tmp_line = re.sub(r'_', ' ', seg_line[cur:])
        else:
            tmp_line = seg_line[cur:]
        tmp_line = cleaner.regularize(tmp_line, lang)
        if len(tmp_line) > 0:
            res += tmp_line
        else:
            res = res.strip()
        return res

    @staticmethod
    def cleanAnchorSent(sent, lang, isReplaceId = True, entity_id = None, redirects = None, mentions = None):
        anchor_count = 0
        cur = 0
        res = ''
        openDelim = ['[[']
        closeDelim = [']]']
        boundary = 1
        if lang == 'zh':
            seg_list = jieba.cut(sent.strip(), cut_all=False)
            # some chinese entities contain whitespace
            seg_line = "_".join(seg_list)
            openDelim = ['[_[']
            closeDelim = [']_]']
            boundary = 2
        else:
            seg_line = sent
        for s, e in cleaner.findBalanced(seg_line, openDelim, closeDelim):
            # remove postfix of an anchor
            if lang == 'zh':
                tmp_line = re.sub(r'_', ' ', seg_line[cur:s])
            else:
                tmp_line = seg_line[cur:s]
            tmp_line = cleaner.regularize(tmp_line, lang)
            if len(tmp_line) > 0:
                res += tmp_line + ' '
            tmp_anchor = seg_line[s:e]
            # extract title and label
            # [_[_word_word_|_word_word_]_] or [_[_word_word_]_]
            tmp_vbar = tmp_anchor.find('|')
            tmp_title = ''
            tmp_label = ''
            tmp_title_id = ''
            if tmp_vbar > 0:
                tmp_title = tmp_anchor[2*boundary:tmp_vbar]
                tmp_label = tmp_anchor[tmp_vbar + 1*boundary:-2*boundary]
            else:
                tmp_title = tmp_anchor[2*boundary:-2*boundary]
                tmp_label = tmp_title
            # map the right title
            if lang == 'zh':
                tmp_title = re.sub(r'_', '', tmp_title)
                tmp_label = re.sub(r'_', ' ', tmp_label)
            tmp_label = cleaner.regularize(tmp_label, lang)
            tmp_anchor = tmp_label
            if len(tmp_label) > 0 :
                if redirects and tmp_title in redirects:
                    tmp_title = redirects[tmp_title]
                if isinstance(entity_id, type(None)):
                    tmp_anchor = '[[' + tmp_title + '|' + tmp_label + ']]'
                elif tmp_title in entity_id:
                    if isReplaceId:
                        tmp_title_id = entity_id[tmp_title]
                        tmp_anchor = '[[' + tmp_title_id + '|' + tmp_label + ']]'
                    else:
                        tmp_anchor = '[[' + tmp_title + '|' + tmp_label + ']]'

                    # count the mentions
                    if mentions:
                        tmp_mention = {} if tmp_title not in mentions else mentions[tmp_title]
                        if tmp_label in tmp_mention:
                            tmp_mention[tmp_label] += 1
                        else:
                            tmp_mention[tmp_label] = 1
                        mentions[tmp_title] = tmp_mention
                # remove prefix of anchor
                if len(tmp_anchor) > 0:
                    res += tmp_anchor + ' '
            cur = e
        if lang == 'zh':
            tmp_line = re.sub(r'_', ' ', seg_line[cur:])
        else:
            tmp_line = seg_line[cur:]
        tmp_line = cleaner.regularize(tmp_line, lang)
        if len(tmp_line) > 0:
            res += tmp_line
        else:
            res = res.strip()
        return res

    def cleanWiki(self, raw_anchor_file, anchor_file, mention_file = None):
        with codecs.open(raw_anchor_file, 'rb', 'utf-8') as fin:
            with codecs.open(anchor_file, 'w', 'utf-8') as fout:
                for line in fin:
                    cur = 0
                    res = ''
                    # isReplaceId = True, entity_id = None, redirects = None, mentions = None
                    # res = cleaner.cleanAnchorSent(line.strip(), self.lang, isReplaceId = True, entity_id = self.entity_id, redirects = self.redirects, mentions = self.mentions)
                    res = self.processSent(line.strip(),entity_id = self.entity_id, redirects = self.redirects, mentions = self.mentions)
                    if len(res) > 11:
                        fout.write("{0}\n".format(res))
        print('process train text finished! start count anchors ...')
        if not mention_file:
            with codecs.open(mention_file, 'w', 'utf-8') as fout:
                out_list = []
                for t in self.mentions:
                    out_list.append(self.entity_id[t] + '\t' + t + "\t" + "\t".join(
                        ["%s::=%s" % (k, v) for k, v in self.mentions[t].items()]) + "\n")
                    if len(out_list) >= 10000:
                        fout.writelines(out_list)
                        del out_list[:]
                if len(out_list) > 0:
                    fout.writelines(out_list)
            print('count mentions finished!')

def addClinks(clink, clink_dict):
    num_lang = len(clink)
    if num_lang != len(languages): return
    for i in xrange(num_lang-1):
        if len(clink[i]) > 0:
            tmp_dict = clink_dict[i]
            if clink[i] in tmp_dict:
                tmp_list = tmp_dict[clink[i]]
                for j in xrange(len(clink[i+1:])):
                    if len(tmp_list[j]) < 1 and len(clink[i+1+j]) > 0:
                        tmp_list[j] = clink[i+1+j]
            else:
                tmp_list = clink[i+1:]
            tmp_dict[clink[i]] = tmp_list
            break

# input several files with the same format
# languages
def mergeCrossLinks(files):
    ops = []
    entity_dics = []
    redirects_dics = []
    total_clinks = []
    num_lang = len(languages)
    for i in xrange(len(languages)):
        ops.append(options(i))

    for i in xrange(num_lang):
        entity_dics.append(Preprocessor.loadEntityDic(ops[i].vocab_entity_file))
        redirects_dics.append(Preprocessor.loadRedirects(ops[i].redirect_file))

    # each dict stores the crosslinks for one language except the last one
    total_clinks = []
    for i in xrange(num_lang-1):
        total_clinks.append({})

    for file in files:
        with codecs.open(file, 'rb', 'utf-8') as fin:
            for line in fin:
                items = re.split(r'\t', line.strip('\n'))
                if len(items) != num_lang : continue
                addClinks(items, total_clinks)
        out = ''
        for i in xrange(len(total_clinks)):
            out += "{0} links to {1} lang! ".format(len(total_clinks[i]), languages[i])
        print("successfully merged {0}".format(out))

    out_clinks = []
    for i in xrange(len(total_clinks)):
        tmp_dict = total_clinks[i]
        for tcl in tmp_dict:
            if len(tcl) < 1 : continue
            out_link = ['' for k in xrange(len(languages))]
            isAdded = False
            out_link[i] = tcl
            tmp_cl = tmp_dict[tcl]
            for j in xrange(len(tmp_cl)):
                if len(tmp_cl[j]) > 0:
                    out_link[i+1+j] = tmp_cl[j]
                    isAdded = True
            if isAdded:
                out_clinks.append(out_link)

    out_clinks_id = []
    for cl in out_clinks:
        out_link_id = ['' for k in xrange(len(languages))]
        isAdded = False
        for i in xrange(num_lang):
            tmp_title = cl[i]
            tmp_title = redirects_dics[i][cl[i]] if cl[i] in redirects_dics[i] else cl[i]
            if tmp_title in entity_dics[i]:
                out_link_id[i] = entity_dics[i][tmp_title]
                isAdded = True
        if isAdded:
            out_clinks_id.append(out_link_id)

    with codecs.open(ops[0].dump_path+'cross_links_all.dat', 'w', 'utf-8') as fout:
        fout.write("{0}\n".format(len(out_clinks)))
        fout.write("{0}\n".format(' '.join(languages)))
        for cl in out_clinks:
            fout.write("{0}\n".format('\t'.join(cl)))

    with codecs.open(ops[0].dump_path + 'cross_links_all_id.dat', 'w', 'utf-8') as fout:
        fout.write("{0}\n".format(len(out_clinks)))
        fout.write("{0}\n".format(' '.join(languages)))
        for cl_id in out_clinks_id:
            fout.write("{0}\n".format('\t'.join(cl_id)))

# clean into plain text
def cleanT(lang):
    op = options(lang)

    cl = cleaner()
    cl.init(lang)
    cl.cleanText(op.raw_text_file, op.text_file)

# clean anchor text symbols, convert [[entity|label]] to [[entity_id|label]]
def clean(lang):
    op = options(lang)

    cl = cleaner()
    cl.init(lang)
    if lang == languages.index('zh'):
        cl.formatRawWiki(op.raw_anchor_file)
    if lang == languages.index('es'):
        cl.initNlpTool('http://localhost:9002','es')
    if lang == languages.index('en'):
        cl.initNlpTool('http://localhost:9001','en')
    cl.entity_id = Preprocessor.loadEntityDic(op.vocab_entity_file)
    cl.redirects = Preprocessor.loadRedirects(op.redirect_file)
    cl.cleanWiki(op.raw_anchor_file, op.anchor_file)

class MonoKGBuilder():

    def __init__(self, lang):
        self.op = options(lang)
        self.preprocessor = None

    def buildMonoKG(self):
        # build entity dic and redirect dic
        self.preprocessor.total_entity_id, self.preprocessor.total_id_entity = Preprocessor.loadWikiIndex(self.op.entity_index_dump)
        self.preprocessor.buildEntityDic(self.op.title_file)
        self.preprocessor.parseRedirects(self.op.redirect_dump)
        self.preprocessor.lowerTitleToRedirects()
        # self.preprocessor.saveEntityDic(self.op.raw_vocab_entity_file)
        self.preprocessor.saveRedirects(self.op.redirect_file)
        # extract outlinks
        self.preprocessor.parsePageLinks(self.op.pagelink_dump)
        self.preprocessor.saveOutlinks(self.op.mono_outlink_idfile)
        self.preprocessor.saveOutlinks(self.op.mono_outlink_file, False)
        self.preprocessor.saveLinkedEntity(self.op.vocab_entity_file)

    def extractLanglinks(self):
        if not self.preprocessor: return
        if not self.preprocessor.total_entity_id:
            self.preprocessor.total_entity_id, self.preprocessor.total_id_entity = Preprocessor.loadWikiIndex(self.op.entity_index_dump)
        if not self.preprocessor.entity_id:
            self.preprocessor.entity_id = Preprocessor.loadEntityDic(self.op.vocab_entity_file)
        if not self.preprocessor.redirects:
            self.preprocessor.redirects = Preprocessor.loadRedirects(self.op.redirect_file)

        self.preprocessor.parseLangLinks(self.op.langlink_dump)
        self.preprocessor.saveLangLink(self.op.cross_link_file)

    def process(self):
        self.preprocessor = Preprocessor()
        self.buildMonoKG()
        self.extractLanglinks()

def merge():
    files = []
    for i in xrange(len(languages)):
        op = options(i)
        files.append(op.cross_link_file)

    mergeCrossLinks(files)

def subCrossLinks(filename, outputfile, lang):
    with codecs.open(filename, 'rb', 'utf-8') as fin:
        out_clinks = []
        count_line = 0
        indexes = []
        for line in fin:
            count_line += 1
            if count_line == 2:
                items = re.split(r' ', line.strip('\n'))
                if len(items) != len(languages):
                    print('out of languages!')
                    return
                indexes = [languages.index(lang[i]) for i in xrange(len(lang))]
                continue
            if len(indexes) < 1: continue
            tmp_ids = []
            id_count = 0
            items = re.split(r'\t', line.strip('\n'))
            for i in indexes:
                tmp_ids.append(items[i])
                if len(items[i]) > 0 :
                    id_count += 1
            if id_count > 1:
                out_clinks.append(tmp_ids)
    with codecs.open(outputfile, 'w', 'utf-8') as fout:
        fout.write("{0}\n".format(len(out_clinks)))
        for clink in out_clinks:
            fout.write("{0}\n".format('\t'.join(clink)))

def mentionCount(filename, ment_count_file):
    ent_prior = {}
    ent_count = {}
    count = 0
    with codecs.open(filename, 'rb') as fin:
        for line in fin:
            line = line.strip().decode('utf-8', 'ignore')
            for s, e in cleaner.findBalanced(line):
                tmp_anchor = line[s:e]
                # extract title and label
                # [_[_word_word_|_word_word_]_] or [_[_word_word_]_]
                tmp_vbar = tmp_anchor.find('|')
                if tmp_vbar <= 0: continue
                tmp_id = tmp_anchor[2 :tmp_vbar]
                tmp_label = tmp_anchor[tmp_vbar + 1:-2]
                #tmp_label = re.sub(r'\s+', '', tmp_label)
                tmp_mentions = {} if tmp_id not in ent_prior else ent_prior[tmp_id]
                if tmp_label in tmp_mentions:
                    tmp_mentions[tmp_label] += 1
                else:
                    tmp_mentions[tmp_label] = 1
                tmp_count = 0 if tmp_id not in ent_count else ent_count[tmp_id]
                tmp_count += 1
                ent_count[tmp_id] = tmp_count
                count += 1
                if count%100000 == 0:
                    print("has processed {0} mentions!".format(count))
                ent_prior[tmp_id] = tmp_mentions
    print("totally {0} mentions for {1} entities!".format(count, len(ent_prior)))
    with codecs.open(ment_count_file, 'w') as fout:
        for id in ent_prior:
            mentions = ent_prior[id]
            prior = 0 if id not in ent_count else float(ent_count[id])/float(count)*1000
            ment_str = "\t".join(["%s::=%s" % (k, mentions[k]) for k in mentions]).encode('utf8')
            fout.write("{0}\t{1}\t{2}\n".format(id, prior,ment_str))


if __name__ == '__main__':
    # if zhwiki, please format zhwiki.xml first
    # fead zhwiki.xml into WikiExtractor, output <wiki_anchor_text> and <wiki_ariticle_title>
    # specify language 'eswiki', 'enwiki' or 'zhwiki'
    lang_index = languages.index('zh')
    # mkb = MonoKGBuilder(lang_index)
    # mkb.process()
    # when processed all the languge monokg, merge each cross lingual links into one
    # merge()
    # clean wiki anchor text, for chinese, better using opencc to convert to simplied chinese
    # clean(lang_index)
    # cleanT(lang_index)
    # lang = ['en', 'zh']
    # cross_file = '/home/caoyx/data/paradata/cross_links_all_id.dat'
    # sub_file = '/home/caoyx/data/paradata/cross_links.'+ lang[0] + '_' + lang[1]
    # subCrossLinks(cross_file, sub_file, lang)
    # anchor_text_file = '/home/caoyx/data/dump20170401/eswiki_cl/anchor_text_cl.dat'
    # op = options(lang_index)
    # mentionCount(op.anchor_file,op.mention_file)
    cl = cleaner()
    op = options(lang_index)

    cl.init(lang_index)
    cl.entity_id = Preprocessor.loadEntityDic(op.vocab_entity_file)
    cl.redirects = Preprocessor.loadRedirects(op.redirect_file)

    output = '/home/caoyx/data/dump20170401/zhwiki_cl/linked_pages.tw'
    cl.formatZhDoc(op.cross_corpus_file,output)
