#-*- coding: ISO-8859-1 -*-
import sys
reload(sys)
sys.setdefaultencoding('ISO-8859-1')
import codecs
import re
import HTMLParser

htmlparser = HTMLParser.HTMLParser()
ENCODE = 'ISO-8859-1'

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
        with codecs.open(filename, 'r', 'ISO-8859-1') as fin:
            for line in fin:
                m = self.nsidRE.match(line.strip())
                if m != None:
                    id = m.group(2)
                    title = m.group(3)
                    self.tmp_entity_id[title] = id
                    self.tmp_id_entity[id] = title
        print "successfully load %d title index!" % len(self.tmp_entity_id)

    def buildEntityDic(self, filename):
        with codecs.open(filename, 'r', 'ISO-8859-1') as fin:
            for line in fin:
                title = line.strip()
                if title in self.tmp_entity_id:
                    self.entity_id[title] = self.tmp_entity_id[title]
                    self.id_entity[self.tmp_entity_id[title]] = title
        print "successfully build %d entities!" % len(self.entity_id)

    def parseRedirects(self, filename):
        with codecs.open(filename, 'rb', 'ISO-8859-1') as fin:
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
        with codecs.open(filename, 'w', 'ISO-8859-1') as fout:
            for ent in self.entity_id:
                fout.write('%s\t%s\n' % (htmlparser.unescape(self.entity_id[ent]), htmlparser.unescape(ent)))

    def saveRedirects(self, filename):
        with codecs.open(filename, 'w', 'ISO-8859-1') as fout:
            for r in self.redirects:
                # r_id \t r_title \t title
                fout.write('%s\t%s\t%s\n' % (self.redirects_id[r], htmlparser.unescape(r), htmlparser.unescape(self.redirects[r])))

    def loadEntityDic(self, filename):
        with codecs.open(filename, 'rb', 'ISO-8859-1') as fin:
            for line in fin:
                items = re.split(r'\t', line.strip())
                if len(items) != 2 : continue
                self.entity_id[items[1]] = items[0]
                self.id_entity[items[0]] = items[1]
        print "successfully load %d entities!" % len(self.entity_id)

    def loadRedirects(self, filename):
        with codecs.open(filename, 'rb', 'ISO-8859-1') as fin:
            for line in fin:
                items = re.split(r'\t', line.strip())
                if len(items) != 3 : continue
                self.redirects_id[items[1]] = items[0]
                self.id_redirects[items[0]] = items[1]
                self.redirects[items[1]] = items[2]
        print "successfully load %d redirects!" % len(self.redirects)

    def parseLinks(self, filename):
        with codecs.open(filename, 'rb', 'ISO-8859-1') as fin:
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
        with codecs.open(filename, 'w', 'ISO-8859-1') as fout:
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
        with codecs.open(filename, 'w', 'ISO-8859-1') as fout:
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
        print "processing %d language!" % self.cur_lang

    def parseLangLinks(self, filename):
        with codecs.open(filename, 'rb', 'ISO-8859-1') as fin:
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
                        self.addLangLink(cur_title, target_lang, target_title)
        print "successfully parsed %d links to %s lang, %d links to %s lang!" % (len(self.lang1), self.lang1_label, len(self.lang2), self.lang2_label)

    def addLangLink(self, cur_title, tar_lang, tar_title):
        if tar_lang == self.cur_lang : return
        if self.lang1_label == '':
            self.lang1_label = tar_lang
        elif self.lang2_label == '':
            self.lang2_label = tar_lang

        if tar_lang == self.lang1_label:
            self.lang1[cur_title] = tar_title
        elif tar_lang == self.lang2_label:
            self.lang2[cur_title] = tar_title

    def saveLangLink(self, filename):
        if self.lang2_label == '' and self.lang1_label == '' : return
        # list: english \t chinese \t Spanish
        multilinguallinks = []
        for ct in self.lang1:
            if ct in self.lang2:
                tmp_ml = self.mergeLangLinks([ct, self.cur_lang, self.lang1[ct], self.lang1_label, self.lang2, self.lang2_label])
                del self.lang2[ct]
            else:
                tmp_ml = self.mergeLangLinks([ct, self.cur_lang, self.lang1[ct], self.lang1_label, '', self.lang2_label])
            if tmp_ml:
                multilinguallinks.append(tmp_ml)
        for ct in self.lang2:
            tmp_ml = self.mergeLangLinks([ct, self.cur_lang, '', self.lang1_label, self.lang2[ct], self.lang2_label])
            if tmp_ml:
                multilinguallinks.append(tmp_ml)
        with codecs.open(filename, 'w', 'ISO-8859-1') as fout:
            fout.write("%d\n" % len(multilinguallinks))
            for links in multilinguallinks:
                fout.write("%s\n" % '\t'.join(links))

    def mergeLangLinks(self, links):
        if len(links) != 6 : return None
        mergedlinks = ['', '', '']
        for i in xrange(0, 6, 2):
            self.processLangs(mergedlinks, links[i], links[i+1])
        return mergedlinks

    def processLangs(self, mergedlinks, lang, title):
        if lang == 'en':
            mergedlinks[0] = title
        elif lang == 'zh':
            mergedlinks[1] = title
        elif lang == 'es':
            mergedlinks[2] = title

dump_path = '/data/m1/cyx/MultiMPME/data/dumps20170401/'
lang = 'eswiki'
redirect_dump = dump_path + lang + '/' + lang + '-20170401-redirect.sql'
title_dump = dump_path + lang + '/' + lang + '-20170401-all-titles-in-ns0'
entity_index_dump = dump_path + lang + '/' + lang + '-20170401-pages-articles-multistream-index.txt'
pagelink_dump = dump_path + lang + '/' + lang + '-20170401-pagelinks.sql'
langlink_dump = dump_path + lang + '/' + lang + '-20170401-langlinks.sql'
# output
output_path = lang + '_cl'
title_file = dump_path + output_path + '/wiki_article_title'
redirect_file = dump_path + output_path + '/vocab_redirects.dat'
raw_vocab_entity_file = dump_path + output_path + '/vocab_entity_all.dat'
mono_outlink_file = dump_path + output_path + '/mono_kg.dat'
vocab_entity_file = dump_path + output_path + '/vocab_entity.dat'
cross_link_file = dump_path + output_path + '/cross_links.dat'

def buildMonoKG():
    preprocessor = Preprocessor()
    # build entity dic and redirect dic
    preprocessor.loadTitleIndex(entity_index_dump)
    preprocessor.buildEntityDic(title_file)
    preprocessor.parseRedirects(redirect_dump)
    preprocessor.saveEntityDic(raw_vocab_entity_file)
    preprocessor.saveRedirects(redirect_file)
    # extract outlinks
    preprocessor.parseLinks(pagelink_dump)
    preprocessor.saveOutlinks(mono_outlink_file)
    preprocessor.saveLinkedEntity(vocab_entity_file)

def extractLanglinks():
    preprocessor = Preprocessor()
    preprocessor.setCurLang(lang)
    preprocessor.loadEntityDic(vocab_entity_file)
    preprocessor.loadRedirects(redirect_file)

    preprocessor.parseLangLinks(langlink_dump)
    preprocessor.saveLangLink(cross_link_file)

if __name__ == '__main__':
    buildMonoKG()

