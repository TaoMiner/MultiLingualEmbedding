#!/usr/bin/env python
# -*- coding: utf-8 -*-
import codecs
import re
import HTMLParser
from itertools import izip
import string
import jieba

htmlparser = HTMLParser.HTMLParser()
jieba.set_dictionary('/data/m1/cyx/MultiMPME/data/dict.txt.big')

# wiki dump encoding as latin-1, we convert them to utf-8


# parameters
class options():
    def __init__(self, lang):
        self.dump_path = '/data/m1/cyx/MultiMPME/data/dumps20170401/'
        self.lang = lang
        self.redirect_dump = self.dump_path + self.lang + '/' + self.lang + '-20170401-redirect.sql'
        self.title_dump = self.dump_path + self.lang + '/' + self.lang + '-20170401-all-titles-in-ns0'
        self.entity_index_dump = self.dump_path + self.lang + '/' + self.lang + '-20170401-pages-articles-multistream-index.txt'
        self.pagelink_dump = self.dump_path + self.lang + '/' + self.lang + '-20170401-pagelinks.sql'
        self.langlink_dump = self.dump_path + self.lang + '/' + self.lang + '-20170401-langlinks.sql'
        # output
        self.output_path = self.lang + '_cl'
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
        self.lang1 = {}
        self.lang2 = {}
        self.lang1_label = ''
        self.lang2_label = ''
        self.cur_lang = ''
        self.nsidRE = re.compile(r'(\d{1,}):(\d{1,}):(.*)')
        # pagelink: (pl_from_id, pl_namespace, pl_title, pl_from_namespace),
        # only for main namespace 0
        self.linkRE = re.compile(r'(\d{1,}),0,\'(.*?)\',0')
        # redirect: (rd_from_id, rd_namespace_id, rd_title, rd_interwiki, rd_fragment),
        # only for main namespace 0
        self.redirectRE = re.compile(r'(\d{1,}),0,\'(.*?)\',\'(.*?)\',\'(.*?)\'')
        # langlinks: (cur_id, target_lang, target_title),
        # only considering english, chinese and Spanish
        self.langlinkRE = re.compile(r'(\d{1,}),\'(en|zh|es)\',\'(.*?)\'')
        # -{zh-cn:xxx1;zh-cn:xxx2}-
        self.formatRE = re.compile(r'-\{.*?(zh-hans|zh-cn):(?P<label>[^;]*?)([;].*?\}|\})-')

    # format -{zh-cn:xxx1;zh-cn:xxx2}- to xxx1
    def formatRawWiki(self, zhwiki_file, zhwiki_format_file):
        line_count = 0
        with codecs.open(zhwiki_file, 'r') as fin:
            with codecs.open(zhwiki_format_file, 'w', 'utf-8') as fout:
                for line in fin:
                    line_count += 1
                    if line_count % 1000000 == 0: print "has processed %d lines!" % line_count
                    line = line.decode('utf-8', 'ignore')
                    line = self.formatRE.sub('\g<label>', line)
                    fout.write(line)

    def loadTotalIndex(self, filename):
        with codecs.open(filename, 'r', 'utf-8') as fin:
            for line in fin:
                m = self.nsidRE.match(line.strip())
                if m != None:
                    id = m.group(2)
                    title = m.group(3)
                    self.total_entity_id[title] = id
                    self.total_id_entity[id] = title
        print "successfully load %d wiki index!" % len(self.total_entity_id)

    # build wiki_aritle_title dict that doesnt contain any redirects
    def buildEntityDic(self, filename):
        with codecs.open(filename, 'r', 'utf-8') as fin:
            for line in fin:
                title = line.strip()
                if title in self.total_entity_id:
                    self.entity_id[title] = self.total_entity_id[title]
                    self.id_entity[self.total_entity_id[title]] = title
        print "successfully build %d entities!" % len(self.entity_id)


    def parseRedirects(self, filename):
        with codecs.open(filename, 'rb') as fin:
            for line in fin:
                line = line.decode('utf-8', 'ignore')
                line = line.replace('INSERT INTO `redirect` VALUES (', '')
                for i in line.strip().split('),('):
                    m = self.redirectRE.match(i)  # Only select namespace 0 (Main/Article) pages
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
        print "successfully parse %d redirects for %d entities!" % (len(self.redirects), len(self.entity_id))

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
        print "lowered %d new redirects!" % len(tmp_redirects)
        self.redirects.update(tmp_redirects)
        del tmp_redirects

    def saveEntityDic(self, filename):
        with codecs.open(filename, 'w', 'utf-8') as fout:
            for ent in self.entity_id:
                fout.write('%s\t%s\n' % (htmlparser.unescape(self.entity_id[ent]), htmlparser.unescape(ent)))

    def saveRedirects(self, filename):
        with codecs.open(filename, 'w', 'utf-8') as fout:
            for r in self.redirects:
                # r_title \t title
                fout.write('%s\t%s\n' % (htmlparser.unescape(r), htmlparser.unescape(self.redirects[r])))

    def loadEntityDic(self, filename):
        with codecs.open(filename, 'rb', 'utf-8') as fin:
            for line in fin:
                items = re.split(r'\t', line.strip())
                if len(items) != 2 : continue
                self.entity_id[items[1]] = items[0]
                self.id_entity[items[0]] = items[1]
        print "successfully load %d entities!" % len(self.entity_id)

    def loadRedirects(self, filename):
        with codecs.open(filename, 'rb', 'utf-8') as fin:
            for line in fin:
                items = re.split(r'\t', line.strip())
                if len(items) != 2 : continue
                self.redirects[items[0]] = items[1]
        print "successfully load %d redirects!" % len(self.redirects)

    def parseLinks(self, filename):
        with codecs.open(filename, 'rb') as fin:
            for line in fin:
                line = line.decode('utf-8', 'ignore')
                line = line.replace(u'INSERT INTO `pagelinks` VALUES (', '')
                for i in line.strip().split(u'),('):
                    m = self.linkRE.match(i)  # Only select namespace 0 (Main/Article) pages
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
        print "successfully extract %d outlinks for %d entities!" % (outlink_num, len(self.outlinks))

    def saveOutlinks(self,filename,idfilename):
        with codecs.open(filename, 'w', 'utf-8') as fout:
            with codecs.open(idfilename, 'w', 'utf-8') as fout_id:
                tmp_line = []
                for t in self.outlinks:
                    if t not in self.entity_id or len(self.entity_id[t]) < 1: continue
                    fout.write('%s\t%s\n' % (htmlparser.unescape(t), htmlparser.unescape('\t'.join(self.outlinks[t]))))
                    tmp_line.append(self.entity_id[t])
                    for tt in self.outlinks[t]:
                        if tt in self.entity_id:
                            tmp_line.append(self.entity_id[tt])
                    if len(tmp_line) > 1:
                        fout_id.write('%s\n' % '\t'.join(tmp_line))
                    del tmp_line[:]


    def saveLinkedEntity(self, filename):
        linked_entities = set()
        for t in self.outlinks:
            linked_entities.add(t)
            for lt in self.outlinks[t]:
                linked_entities.add(lt)
        print "totally %d linked entities!" % len(linked_entities)
        error_count = 0
        with codecs.open(filename, 'w', 'utf-8') as fout:
            for t in linked_entities:
                if t not in self.entity_id:
                    error_count += 1
                    continue
                fout.write('%s\t%s\n' % (htmlparser.unescape(self.entity_id[t]), htmlparser.unescape(t)))
        print "%d linked entities not in vocab!" % error_count

    def setCurLang(self, lang):
        if lang == 'enwiki':
            self.cur_lang = 'en'
        elif lang == 'eswiki':
            self.cur_lang = 'es'
        elif lang == 'zhwiki':
            self.cur_lang = 'zh'
        print "processing %s language!" % self.cur_lang

    def parseLangLinks(self, filename):
        with codecs.open(filename, 'rb') as fin:
            for line in fin:
                line = line.decode('utf-8', 'ignore')
                line = line.replace('INSERT INTO `langlinks` VALUES (', '')
                for i in line.strip().split('),('):
                    m = self.langlinkRE.match(i)
                    if m != None:
                        cur_title = None
                        cur_id = m.group(1)
                        target_lang = m.group(2)
                        target_title = m.group(3)
                        if target_lang == self.cur_lang : continue
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
                            self.addLangLink(cur_title, target_lang, target_title)
        print "successfully parsed %d links to %s lang, %d links to %s lang!" % (len(self.lang1), self.lang1_label, len(self.lang2), self.lang2_label)

    def addLangLink(self, cur_title, tar_lang, tar_title):
        if tar_lang == self.cur_lang : return

        if self.lang1_label == '':
            self.lang1_label = tar_lang
        if tar_lang == self.lang1_label:
            self.lang1[cur_title] = tar_title
            return
        if self.lang2_label == '':
            self.lang2_label = tar_lang
        if tar_lang == self.lang2_label:
            self.lang2[cur_title] = tar_title

    def saveLangLink(self, filename):
        if self.lang2_label == '' and self.lang1_label == '' : return
        # list: english \t chinese \t Spanish
        multilinguallinks = []
        overlapped_set = set()
        for ct in self.lang1:
            if ct in self.lang2:
                overlapped_set.add(ct)
                tmp_ml = self.mergeLangLinks([ct, self.cur_lang, self.lang1[ct], self.lang1_label, self.lang2[ct], self.lang2_label])
            else:
                tmp_ml = self.mergeLangLinks([ct, self.cur_lang, self.lang1[ct], self.lang1_label, '', self.lang2_label])
            if tmp_ml:
                multilinguallinks.append(tmp_ml)
        for ct in self.lang2:
            if ct in overlapped_set : continue
            tmp_ml = self.mergeLangLinks([ct, self.cur_lang, '', self.lang1_label, self.lang2[ct], self.lang2_label])
            if tmp_ml:
                multilinguallinks.append(tmp_ml)
        with codecs.open(filename, 'w', 'utf-8') as fout:
            fout.write("%d\n" % len(multilinguallinks))
            for links in multilinguallinks:
                fout.write("%s\n" % '\t'.join(links))

    def mergeLangLinks(self, links):
        if len(links) != 6 : return None
        mergedlinks = ['', '', '']
        for i in xrange(0, 6, 2):
            self.processLangs(mergedlinks, links[i], links[i+1])
        return mergedlinks

    def processLangs(self, mergedlinks, title, lang):
        if lang == 'en':
            mergedlinks[0] = title
        elif lang == 'zh':
            mergedlinks[1] = title
        elif lang == 'es':
            mergedlinks[2] = title

    def loadCrossLinks(self, filename):
        with codecs.open(filename, 'rb', 'utf-8') as fin:
            line_count = 0
            link_set = set()
            for line in fin:
                line_count += 1
                if line_count < 2 : continue
                items = re.split(r'\t', line.strip())
                if len(items) != 3: continue
                for i in items:
                    if len(i) < 1: continue
                    link_set.add(i)
        print "successfully load %d cross lingual entities!" % len(link_set)
        return link_set

class cleaner():

    def __init__(self, options, preprocessor):
        self.op = options
        self.entity_id = preprocessor.entity_id
        self.redirects = preprocessor.redirects
        self.mentions = {}
        print "cleaning %s language!" % self.op.lang

        self.punc = re.compile(ur'[%s]' % re.escape(string.punctuation))
        zh_punctuation = "！？｡。·＂＃＄％＆＇（）＊＋，－／：；＜＝＞＠［＼］＾＿｀｛｜｝～｟｠｢｣､、〃》「」『』【】〔〕〖〗〘〙〚〛〜〝〞〟〰〾〿–—‘’‛“”„‟…‧﹏."
        self.zhpunc = re.compile(ur'[%s]' % re.escape(zh_punctuation.decode('utf-8')))

        self.numRE1 = re.compile(r'(?<=\s)[\d\s]+(?=($|\s))')
        self.numRE2 = re.compile(r'(?<=^)[\d\s]+(?=($|\s))')
        self.spaceRE = re.compile(r'[\s]+')

    def regularize(self, str):
        # possessive case 's
        # tmp_line = re.sub(r' s |\'s', ' ', str)
        # following clean wiki xml, punctuation, numbers, and lower case

        tmp_line = self.punc.sub('', str)
        if self.op.lang == 'zhwiki':
            tmp_line = self.zhpunc.sub('', tmp_line)
        tmp_line = self.spaceRE.sub(' ', tmp_line)
        tmp_line = self.numRE1.sub('dddddd', tmp_line)
        tmp_line = self.numRE2.sub('dddddd', tmp_line).lower().strip()
        return tmp_line

    def findBalanced(self, text, openDelim=['[['], closeDelim=[']]']):
        """
        Assuming that text contains a properly balanced expression using
        :param openDelim: as opening delimiters and
        :param closeDelim: as closing delimiters.
        :return: an iterator producing pairs (start, end) of start and end
        positions in text containing a balanced expression.
        """
        openPat = '|'.join([re.escape(x) for x in openDelim])
        afterPat = dict()
        for o, c in izip(openDelim, closeDelim):
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

    def clean(self):
        # clean wiki_anchor_text
        if self.op.lang == 'zhwiki':
            self.cleanZHWiki()
        else:
            self.cleanOtherWiki()
        print " clean wiki anchor text finished!"
        # replace mono_kg with id


    def cleanZHWiki(self):
        anchor_count = 0
        with codecs.open(self.op.raw_anchor_file, 'rb', 'utf-8') as fin:
            with codecs.open(self.op.anchor_file, 'w', 'utf-8') as fout:
                for line in fin:
                    cur = 0
                    res = ''
                    line = line.strip()
                    seg_list = jieba.cut(line, cut_all=False)
                    # some chinese entities contain whitespace
                    seg_line = "_".join(seg_list)
                    for s, e in self.findBalanced(seg_line,  ['[_['], [']_]']):
                        # remove postfix of an anchor
                        tmp_line = re.sub(r'_', ' ', seg_line[cur:s])
                        tmp_line = self.regularize(tmp_line)
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
                            tmp_title = tmp_anchor[4:tmp_vbar]
                            tmp_label = tmp_anchor[tmp_vbar + 2:-4]
                        else:
                            tmp_title = tmp_anchor[4:-4]
                            tmp_label = tmp_title
                        # map the right title
                        tmp_title = re.sub(r'_', '', tmp_title)

                        tmp_label = re.sub(r'_', ' ', tmp_label)
                        tmp_label = self.regularize(tmp_label)
                        mention_label = tmp_label
                        if tmp_title not in self.entity_id and tmp_title not in self.redirects:
                            tmp_anchor = tmp_label
                        else:
                            if tmp_title in self.redirects:
                                tmp_title = self.redirects[tmp_title]
                            tmp_title_id = self.entity_id[tmp_title]

                            tmp_anchor = '[[' + tmp_title_id + '|' + tmp_label + ']]'
                            anchor_count += 1
                            # count the mentions
                            tmp_mention = {} if tmp_title not in self.mentions else self.mentions[tmp_title]
                            if mention_label in tmp_mention:
                                tmp_mention[mention_label] += 1
                            else:
                                tmp_mention[mention_label] = 1
                            self.mentions[tmp_title] = tmp_mention
                        # remove prefix of anchor
                        if len(tmp_anchor) > 0:
                            res += tmp_anchor + ' '
                        cur = e
                    tmp_line = re.sub(r'_', ' ', seg_line[cur:])
                    tmp_line = self.regularize(tmp_line)
                    if len(tmp_line) > 0:
                        res += tmp_line + '\n'
                    else:
                        res = res.strip() + '\n'
                    if len(res) > 11:
                        fout.write(res)
        print 'process train text finished! start count %d anchors ...' % anchor_count
        with codecs.open(self.op.mention_file, 'w', 'utf-8') as fout:
            fout.write("%d\n" % anchor_count)
            out_list = []
            for t in self.mentions:
                out_list.append(self.entity_id[t] + '\t' + t + "\t" + "\t".join(
                    ["%s::=%s" % (k, v) for k, v in self.mentions[t].items()]) + "\n")
                if len(out_list) >= 10000:
                    fout.writelines(out_list)
                    del out_list[:]
            if len(out_list) > 0:
                fout.writelines(out_list)
        print 'count mentions finished!'

    def cleanOtherWiki(self):
        anchor_count = 0
        with codecs.open(self.op.raw_anchor_file, 'rb', 'utf-8') as fin:
            with codecs.open(self.op.anchor_file, 'w', 'utf-8') as fout:
                for line in fin:
                    cur = 0
                    res = ''
                    line = line.strip()
                    for s, e in self.findBalanced(line):
                        # remove postfix of an anchor
                        tmp_line = self.regularize(line[cur:s])
                        if len(tmp_line) > 0:
                            res += tmp_line + ' '

                        tmp_anchor = line[s:e]
                        # extract title and label
                        tmp_vbar = tmp_anchor.find('|')
                        tmp_title = ''
                        tmp_label = ''
                        tmp_title_id = ''
                        if tmp_vbar > 0:
                            tmp_title = tmp_anchor[2:tmp_vbar]
                            tmp_label = tmp_anchor[tmp_vbar + 1:-2]
                        else:
                            tmp_title = tmp_anchor[2:-2]
                            tmp_label = tmp_title
                        # map the right title
                        tmp_label = self.regularize(tmp_label)
                        if len(tmp_label) < 1: continue
                        if tmp_title not in self.entity_id and tmp_title not in self.redirects:
                            tmp_anchor = tmp_label
                        else:
                            if tmp_title in self.redirects:
                                tmp_title = self.redirects[tmp_title]
                            if tmp_title in self.entity_id:
                                tmp_title_id = self.entity_id[tmp_title]

                                tmp_anchor = '[[' + tmp_title_id + '|' + tmp_label + ']]'
                                anchor_count += 1
                                # count the mentions
                                tmp_mention = {} if tmp_title not in self.mentions else self.mentions[tmp_title]
                                if tmp_label in tmp_mention:
                                    tmp_mention[tmp_label] += 1
                                else:
                                    tmp_mention[tmp_label] = 1
                                self.mentions[tmp_title] = tmp_mention
                            else:
                                tmp_anchor = tmp_label
                        # remove prefix of anchor
                        if len(tmp_anchor)>0:
                            res += tmp_anchor + ' '
                        cur = e
                    tmp_line = self.regularize(line[cur:])
                    if len(tmp_line) > 0:
                        res += self.regularize(line[cur:]) + '\n'
                    else:
                        res = res.strip() + '\n'
                    if len(res) > 11:
                        fout.write(res)
        print 'process train text finished! start count %d anchors ...' % anchor_count
        with codecs.open(self.op.mention_file, 'w', 'utf-8') as fout:
            fout.write("%d\n" % anchor_count)
            out_list = []
            for t in self.mentions:
                out_list.append(self.entity_id[t] + '\t' + t + "\t" + "\t".join(
                    ["%s::=%s" % (k, v) for k, v in self.mentions[t].items()]) + "\n")
                if len(out_list) >= 10000:
                    fout.writelines(out_list)
                    del out_list[:]
            if len(out_list) > 0:
                fout.writelines(out_list)
        print 'count mentions finished!'

# pre: [enpre, zhpre, espre]
# en_dict: {'entitle':[zhtitle, estitle]}
# non_en_dict: {zhtitle: estitle}
def merge(pre, en_dict, non_en_dict, dict_file):
    with codecs.open(dict_file, 'rb', 'utf-8') as fin:
        for line in fin:
            items = re.split(r'\t', line.strip())
            if len(items) != 3 : continue
            # en_title, zh_title, es_title
            titles = [u'', u'', u'']
            for i in xrange(3):
                if items[i] in pre[i].redirects:
                    items[i] = pre[i].redirects[items[i]]
                if items[i] in pre[i].entity_id:
                    titles[i] = items[i]
            # differiate if there is english title
            if len(titles[0]) > 0:
                if titles[0] not in en_dict:
                    en_dict[titles[0]] = titles[1:]
                else:
                    tmp_list = en_dict[titles[0]]
                    for i in xrange(2):
                        if len(tmp_list[i]) <= 0 and len(titles[i+1]) > 0:
                            tmp_list[i] = titles[i+1]
                    en_dict[titles[0]] = tmp_list
            else:
                if len(titles[1]) > 0 and len(titles[2]) > 0:
                    non_en_dict[titles[1]] = titles[2]
    print 'successfully merged %d enlink tuples and %d non-enlink tuples!' % (len(en_dict), len(non_en_dict))

def mergeCrossLinks():
    enOp = options('enwiki')
    esOp = options('eswiki')
    zhOp = options('zhwiki')

    enPre = Preprocessor()
    enPre.setCurLang(enOp.lang)
    enPre.loadEntityDic(enOp.vocab_entity_file)
    enPre.loadRedirects(enOp.redirect_file)

    esPre = Preprocessor()
    esPre.setCurLang(esOp.lang)
    esPre.loadEntityDic(esOp.vocab_entity_file)
    esPre.loadRedirects(esOp.redirect_file)

    zhPre = Preprocessor()
    zhPre.setCurLang(zhOp.lang)
    zhPre.loadEntityDic(zhOp.vocab_entity_file)
    zhPre.loadRedirects(zhOp.redirect_file)

    en_dict = {}
    non_en_dict = {}
    merge([enPre, zhPre, esPre], en_dict, non_en_dict, enOp.cross_link_file)
    merge([enPre, zhPre, esPre], en_dict, non_en_dict, zhOp.cross_link_file)
    merge([enPre, zhPre, esPre], en_dict, non_en_dict, esOp.cross_link_file)

    with codecs.open(enOp.dump_path+'cross_links_all.dat', 'w', 'utf-8') as fout:
        fout.write("%d\n" % (len(en_dict) + len(non_en_dict)))
        fout.write("English\tChinese\tSpanish\n")
        for et in en_dict:
            fout.write("%s\t%s\n" % (et, '\t'.join(en_dict[et])))
        for zt in non_en_dict:
            fout.write("\t%s\t%s\n" % (zt, non_en_dict[zt]))

    with codecs.open(enOp.dump_path+'cross_links_all_id.dat', 'w', 'utf-8') as fout:
        fout.write("%d\n" % (len(en_dict) + len(non_en_dict)))
        fout.write("English\tChinese\tSpanish\n")
        tmp_line = ['','','']
        for et in en_dict:
            if et not in enPre.entity_id and en_dict[et][0] not in zhPre.entity_id and en_dict[et][1] not in esPre.entity_id :
                continue

            tmp_line[0] = enPre.entity_id[et] if et in enPre.entity_id else ''
            tmp_line[1] = zhPre.entity_id[en_dict[et][0]] if en_dict[et][0] in zhPre.entity_id else ''
            tmp_line[2] = esPre.entity_id[en_dict[et][1]] if en_dict[et][1] in esPre.entity_id else ''
            fout.write("%s\n" % '\t'.join(tmp_line))
        tmp_line = ['','']
        for zt in non_en_dict:
            if zt not in zhPre.entity_id and non_en_dict[zt] not in esPre.entity_id:
                continue

            tmp_line[0] = zhPre.entity_id[zt] if zt in zhPre.entity_id else ''
            tmp_line[1] = esPre.entity_id[non_en_dict[zt]] if non_en_dict[zt] in esPre.entity_id else ''
            fout.write("\t%s\n" % '\t'.join(tmp_line))

# clean anchor text symbols, convert [[entity|label]] to [[entity_id|label]]
def clean(lang):
    op = options(lang)

    pre = Preprocessor()
    pre.setCurLang(op.lang)
    pre.loadEntityDic(op.vocab_entity_file)
    pre.loadRedirects(op.redirect_file)

    cl = cleaner(op, pre)
    cl.clean()

class MonoKGBuilder():

    def __init__(self):
        self.lang = None
        self.options = None
        self.preprocessor = None

    def setCurLang(self, lang):
        self.lang = lang
        self.options = options(lang)
        self.preprocessor = Preprocessor()

    def buildMonoKG(self):
        # build entity dic and redirect dic
        self.preprocessor.loadTotalIndex(self.options.entity_index_dump)
        self.preprocessor.buildEntityDic(self.options.title_file)
        self.preprocessor.parseRedirects(self.options.redirect_dump)
        self.preprocessor.lowerTitleToRedirects()
        self.preprocessor.saveEntityDic(self.options.raw_vocab_entity_file)
        self.preprocessor.saveRedirects(self.options.redirect_file)
        # extract outlinks
        self.preprocessor.parseLinks(self.options.pagelink_dump)
        self.preprocessor.saveOutlinks(self.options.mono_outlink_file, self.options.mono_outlink_idfile)
        self.preprocessor.saveLinkedEntity(self.options.vocab_entity_file)

    def extractLanglinks(self):
        self.preprocessor.setCurLang(self.options.lang)
        self.preprocessor.loadTotalIndex(self.options.entity_index_dump)
        self.preprocessor.loadEntityDic(self.options.vocab_entity_file)
        self.preprocessor.loadRedirects(self.options.redirect_file)

        self.preprocessor.parseLangLinks(self.options.langlink_dump)
        self.preprocessor.saveLangLink(self.options.cross_link_file)

    def process(self):
        if self.lang:
            self.options = options(self.lang)
            self.buildMonoKG()
            self.extractLanglinks()

if __name__ == '__main__':
    # if zhwiki, please format zhwiki.xml first
    # fead zhwiki.xml into WikiExtractor, output <wiki_anchor_text> and <wiki_ariticle_title>
    # specify language 'eswiki', 'enwiki' or 'zhwiki'
    lang = 'enwiki'
    mkb = MonoKGBuilder()
    mkb.setCurLang(lang)
    mkb.process()
    # when processed all the languge monokg, merge each cross lingual links into one
    # mergeCrossLinks()
    # clean wiki anchor text, for chinese, better using opencc to convert to simplied chinese
    clean(lang)
