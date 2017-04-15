#-*- coding: ISO-8859-1 -*-
import sys
reload(sys)
sys.setdefaultencoding('ISO-8859-1')
import codecs
import re
import HTMLParser
from itertools import izip, izip_longest
import string
import jieba

htmlparser = HTMLParser.HTMLParser()
ENCODE = 'ISO-8859-1'

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
        self.title_file = self.dump_path + self.output_path + '/wiki_article_title'
        self.redirect_file = self.dump_path + self.output_path + '/vocab_redirects.dat'
        self.raw_vocab_entity_file = self.dump_path + self.output_path + '/vocab_entity_all.dat'
        self.mono_outlink_file = self.dump_path + self.output_path + '/mono_kg.dat'
        self.vocab_entity_file = self.dump_path + self.output_path + '/vocab_entity.dat'
        self.cross_link_file = self.dump_path + self.output_path + '/cross_links.dat'
        self.raw_anchor_file = self.dump_path + self.output_path + '/wiki_anchor_text'
        self.anchor_file = self.dump_path + self.output_path + '/anchor_text_cl.dat'
        self.mention_file = self.dump_path + self.output_path + '/mention_count.dat'

class Preprocessor():

    def __init__(self):
        self.tmp_entity_id = {}
        self.tmp_id_entity = {}
        self.entity_id = {}
        self.id_entity = {}
        self.redirects = {}
        self.id_redirects = {}
        self.redirects_id = {}
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

    def loadTitleIndex(self, filename):
        with codecs.open(filename, 'r', ENCODE) as fin:
            for line in fin:
                m = self.nsidRE.match(line.strip())
                if m != None:
                    id = m.group(2)
                    title = m.group(3)
                    self.tmp_entity_id[title] = id
                    self.tmp_id_entity[id] = title
        print "successfully load %d title index!" % len(self.tmp_entity_id)

    def buildEntityDic(self, filename):
        with codecs.open(filename, 'r', ENCODE) as fin:
            for line in fin:
                title = line.strip()
                if title in self.tmp_entity_id:
                    self.entity_id[title] = self.tmp_entity_id[title]
                    self.id_entity[self.tmp_entity_id[title]] = title
        print "successfully build %d entities!" % len(self.entity_id)

    def parseRedirects(self, filename):
        with codecs.open(filename, 'rb', ENCODE) as fin:
            for line in fin:
                line = line.replace('INSERT INTO `redirect` VALUES (', '')
                for i in line.strip().split('),('):
                    m = self.redirectRE.match(i)  # Only select namespace 0 (Main/Article) pages
                    if m != None:
                        rd_id = m.group(1)
                        rd_title = m.group(2)
                        rd_title = rd_title.replace('\\', '')
                        rd_title = rd_title.replace('_', ' ')

                        if rd_id not in self.tmp_id_entity or rd_title not in self.entity_id or self.tmp_id_entity[rd_id] == rd_title:
                            continue
                        self.id_redirects[rd_id] = self.tmp_id_entity[rd_id]
                        self.redirects_id[self.tmp_id_entity[rd_id]] = rd_id
                        self.redirects[self.tmp_id_entity[rd_id]] = rd_title
                        # remove redirect title in entity dic
                        if rd_id in self.id_entity:
                            del self.entity_id[self.id_entity[rd_id]]
                            del self.id_entity[rd_id]
        print "successfully parse %d redirects for %d entities!" % (len(self.redirects), len(self.entity_id))
        del self.tmp_id_entity
        del self.tmp_entity_id

    def saveEntityDic(self, filename):
        with codecs.open(filename, 'w', ENCODE) as fout:
            for ent in self.entity_id:
                fout.write('%s\t%s\n' % (htmlparser.unescape(self.entity_id[ent]), htmlparser.unescape(ent)))

    def saveRedirects(self, filename):
        with codecs.open(filename, 'w', ENCODE) as fout:
            for r in self.redirects:
                # r_id \t r_title \t title
                fout.write('%s\t%s\t%s\n' % (self.redirects_id[r], htmlparser.unescape(r), htmlparser.unescape(self.redirects[r])))

    def loadEntityDic(self, filename):
        with codecs.open(filename, 'rb', ENCODE) as fin:
            for line in fin:
                items = re.split(r'\t', line.strip())
                if len(items) != 2 : continue
                self.entity_id[items[1]] = items[0]
                self.id_entity[items[0]] = items[1]
        print "successfully load %d entities!" % len(self.entity_id)

    def loadRedirects(self, filename):
        with codecs.open(filename, 'rb', ENCODE) as fin:
            for line in fin:
                items = re.split(r'\t', line.strip())
                if len(items) != 3 : continue
                self.redirects_id[items[1]] = items[0]
                self.id_redirects[items[0]] = items[1]
                self.redirects[items[1]] = items[2]
        print "successfully load %d redirects!" % len(self.redirects)

    def parseLinks(self, filename):
        with codecs.open(filename, 'rb', ENCODE) as fin:
            for line in fin:
                line = line.replace('INSERT INTO `pagelinks` VALUES (', '')
                for i in line.strip().split('),('):
                    m = self.linkRE.match(i)  # Only select namespace 0 (Main/Article) pages
                    if m != None:
                        from_title = None
                        target_title = None
                        tmp_target_title = m.group(2)
                        tmp_target_title = tmp_target_title.replace('\\', '')
                        tmp_target_title = tmp_target_title.replace('_', ' ')
                        tmp_from_id = m.group(1)
                        if tmp_target_title in self.redirects:
                            target_title = self.redirects[tmp_target_title]
                        elif tmp_target_title in self.entity_id:
                            target_title = tmp_target_title
                        if tmp_from_id in self.id_redirects:
                            from_title = self.redirects[self.id_redirects[tmp_from_id]]
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

    def saveOutlinks(self,filename):
        with codecs.open(filename, 'w', ENCODE) as fout:
            for t in self.outlinks:
                fout.write('%s\t%s\n' % (htmlparser.unescape(t), htmlparser.unescape('\t'.join(self.outlinks[t]))))

    def saveLinkedEntity(self, filename):
        linked_entities = set()
        for t in self.outlinks:
            linked_entities.add(t)
            for lt in self.outlinks[t]:
                linked_entities.add(lt)
        print "totally %d linked entities!" % len(linked_entities)
        error_count = 0
        with codecs.open(filename, 'w', ENCODE) as fout:
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
        with codecs.open(filename, 'rb', ENCODE) as fin:
            for line in fin:
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
                        if cur_id in self.id_redirects:
                            cur_title = self.redirects[self.id_redirects[cur_id]]
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
        with codecs.open(filename, 'w', ENCODE) as fout:
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

class cleaner():

    def __init__(self):
        self.cur_lang = None
        self.entity_id = {}
        self.redirects = {}
        self.mentions = {}

        self.punc = re.compile('[%s]' % re.escape(string.punctuation))
        self.numRE1 = re.compile(r'(?<=\s)[\d\s]+(?=($|\s))')
        self.numRE2 = re.compile(r'(?<=^)[\d\s]+(?=($|\s))')
        self.spaceRE = re.compile(r'[\s]+')

    def setCurLang(self, lang):
        if lang == 'enwiki':
            self.cur_lang = 'en'
        elif lang == 'eswiki':
            self.cur_lang = 'es'
        elif lang == 'zhwiki':
            self.cur_lang = 'zh'
        print "cleaning %s language!" % self.cur_lang

    def regularize(self, str):
        # possessive case 's
        # tmp_line = re.sub(r' s |\'s', ' ', str)
        # following clean wiki xml, punctuation, numbers, and lower case
        tmp_line = self.punc.sub('', str)
        tmp_line = self.spaceRE.sub(' ', tmp_line)
        tmp_line = self.numRE1.sub('dddddd', tmp_line)
        tmp_line = self.numRE2.sub('dddddd', tmp_line).lower()
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

    def clean(self, wiki_anchor_file, output_file, mention_file):
        if isinstance(self.cur_lang, type(None)):
            print "don't know what language!"
            return
        if self.cur_lang == 'zh':
            self.cleanZHWiki(wiki_anchor_file, output_file, mention_file)
        else:
            self.cleanOtherWiki(wiki_anchor_file, output_file, mention_file)

    def cleanZHWiki(self, wiki_anchor_file, output_file, mention_file):
        anchor_count = 0
        with codecs.open(wiki_anchor_file, 'rb', ENCODE) as fin:
            with codecs.open(output_file, 'w', ENCODE) as fout:
                for line in fin:
                    cur = 0
                    res = ''
                    res_anchor = ''
                    line = line.strip()
                    for s, e in self.findBalanced(line):
                        res += self.regularize(line[cur:s])
                        res_anchor += line[cur:s]
                        tmp_anchor = line[s:e]
                        # extract title and label
                        tmp_vbar = tmp_anchor.find('|')
                        tmp_title = ''
                        tmp_label = ''
                        if tmp_vbar > 0:
                            tmp_title = tmp_anchor[2:tmp_vbar]
                            tmp_label = tmp_anchor[tmp_vbar + 1:-2]
                        else:
                            tmp_title = tmp_anchor[2:-2]
                            tmp_label = tmp_title
                        # map the right title
                        tmp_label = self.regularize(tmp_label)
                        if tmp_title not in self.entity_id and tmp_title not in self.redirects:
                            tmp_anchor = tmp_label
                        else:
                            if tmp_title in self.redirects:
                                tmp_title = self.redirects[tmp_title]
                            if tmp_title == tmp_label:
                                tmp_anchor = '[[' + tmp_title + ']]'
                            else:
                                tmp_anchor = '[[' + tmp_title + '|' + tmp_label + ']]'
                            anchor_count += 1
                            if anchor_count % 100000 == 0:
                                print 'has processed %d anchors!' % anchor_count
                            # count the mentions
                            tmp_mention = {} if tmp_title not in self.mentions else self.mentions[tmp_title]
                            if tmp_label in tmp_mention:
                                tmp_mention[tmp_label] += 1
                            else:
                                tmp_mention[tmp_label] = 1
                            self.mentions[tmp_title] = tmp_mention

                        res += tmp_anchor
                        cur = e
                    res += self.regularize(line[cur:]) + '\n'
                    if len(res) > 10:
                        fout.write(res)
        print 'process train text finished! start count %d anchors ...' % anchor_count
        with codecs.open(mention_file, 'w', ENCODE) as fout:
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

    def cleanOtherWiki(self, wiki_anchor_file, output_file, mention_file):
        anchor_count = 0
        with codecs.open(wiki_anchor_file, 'rb', ENCODE) as fin:
            with codecs.open(output_file, 'w', ENCODE) as fout:
                for line in fin:
                    cur = 0
                    res = ''
                    line = line.strip()
                    for s, e in self.findBalanced(line):
                        # remove postfix of an anchor
                        tmp_line = self.regularize(line[cur:s])
                        if len(res)>0:
                            tmp_pos = tmp_line.find(' ')
                            tmp_line = tmp_line[tmp_pos:] if tmp_pos != -1 else ''
                        print line[cur:s]
                        print tmp_line
                        res += tmp_line

                        tmp_anchor = line[s:e]
                        # extract title and label
                        tmp_vbar = tmp_anchor.find('|')
                        tmp_title = ''
                        tmp_label = ''
                        if tmp_vbar > 0:
                            tmp_title = tmp_anchor[2:tmp_vbar]
                            tmp_label = tmp_anchor[tmp_vbar + 1:-2]
                        else:
                            tmp_title = tmp_anchor[2:-2]
                            tmp_label = tmp_title
                        # map the right title
                        tmp_label = self.regularize(tmp_label)
                        if tmp_title not in self.entity_id and tmp_title not in self.redirects:
                            tmp_anchor = tmp_label
                        else:
                            if tmp_title in self.redirects:
                                tmp_title = self.redirects[tmp_title]
                            if tmp_title == tmp_label:
                                tmp_anchor = '[[' + tmp_title + ']]'
                            else:
                                tmp_anchor = '[[' + tmp_title + '|' + tmp_label + ']]'
                            anchor_count += 1
                            if anchor_count % 100000 == 0:
                                print 'has processed %d anchors!' % anchor_count
                            # count the mentions
                            tmp_mention = {} if tmp_title not in self.mentions else self.mentions[tmp_title]
                            if tmp_label in tmp_mention:
                                tmp_mention[tmp_label] += 1
                            else:
                                tmp_mention[tmp_label] = 1
                            self.mentions[tmp_title] = tmp_mention
                        # remove prefix of anchor
                        tmp_pos = res.rfind(' ')
                        print res
                        res = res[:tmp_pos] if tmp_pos != -1 else ''
                        print res
                        res += tmp_anchor
                        cur = e
                    tmp_line = self.regularize(line[cur:])
                    if len(res) > 0:
                        tmp_pos = tmp_line.find(' ')
                        tmp_line = tmp_line[tmp_pos:] if tmp_pos != -1 else ''
                    print line[cur:]
                    print tmp_line
                    res += tmp_line + '\n'
                    if len(res) > 11:
                        fout.write(res)
        print 'process train text finished! start count %d anchors ...' % anchor_count
        with codecs.open(mention_file, 'w', ENCODE) as fout:
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

def buildMonoKG(options):
    preprocessor = Preprocessor()
    # build entity dic and redirect dic
    preprocessor.loadTitleIndex(options.entity_index_dump)
    preprocessor.buildEntityDic(options.title_file)
    preprocessor.parseRedirects(options.redirect_dump)
    preprocessor.saveEntityDic(options.raw_vocab_entity_file)
    preprocessor.saveRedirects(options.redirect_file)
    # extract outlinks
    preprocessor.parseLinks(options.pagelink_dump)
    preprocessor.saveOutlinks(options.mono_outlink_file)
    preprocessor.saveLinkedEntity(options.vocab_entity_file)

def extractLanglinks(options):
    preprocessor = Preprocessor()
    preprocessor.setCurLang(options.lang)
    preprocessor.loadEntityDic(options.vocab_entity_file)
    preprocessor.loadRedirects(options.redirect_file)

    preprocessor.parseLangLinks(options.langlink_dump)
    preprocessor.saveLangLink(options.cross_link_file)

# pre: [enpre, zhpre, espre]
# en_dict: {'entitle':[zhtitle, estitle]}
# non_en_dict: {zhtitle: estitle}
def merge(pre, en_dict, non_en_dict, dict_file):
    with codecs.open(dict_file, 'rb', ENCODE) as fin:
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

    with codecs.open(enOp.dump_path+'cross_links_all.dat', 'w', ENCODE) as fout:
        fout.write("%d\n" % (len(en_dict) + len(non_en_dict)))
        for et in en_dict:
            fout.write("%s\t%s\n" % (et, '\t'.join(en_dict[et])))
        for zt in non_en_dict:
            fout.write("\t%s\t%s\n" % (zt, non_en_dict[zt]))



def clean():
    op = options('eswiki')
    pre = Preprocessor()
    pre.setCurLang(op.lang)
    pre.loadEntityDic(op.vocab_entity_file)
    pre.loadRedirects(op.redirect_file)

    cl = cleaner()
    cl.cur_lang = op.lang
    cl.entity_id = pre.entity_id
    cl.redirects = pre.redirects
    cl.clean(op.raw_anchor_file, op.anchor_file, op.mention_file)

if __name__ == '__main__':
    # op = options('eswiki')
    # extractLanglinks(op)
    # mergeCrossLinks()
    clean()
