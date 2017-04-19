# -*- coding: utf-8 -*-
import codecs
import re
import HTMLParser
from itertools import izip
import string
import jieba

htmlparser = HTMLParser.HTMLParser()


# parameters
class options():
    def __init__(self, lang):
        self.dump_path = '/data/m1/cyx/MultiMPME/data/dumps20170401/'
        self.lang = lang
        self.wiki_dump = self.dump_path + self.lang + '/' + self.lang + '-20170401-pages-articles-multistream.xml'
        self.redirect_dump = self.dump_path + self.lang + '/' + self.lang + '-20170401-redirect.sql'
        self.title_dump = self.dump_path + self.lang + '/' + self.lang + '-20170401-all-titles-in-ns0'
        self.entity_index_dump = self.dump_path + self.lang + '/' + self.lang + '-20170401-pages-articles-multistream-index.txt'
        self.pagelink_dump = self.dump_path + self.lang + '/' + self.lang + '-20170401-pagelinks.sql'
        self.langlink_dump = self.dump_path + self.lang + '/' + self.lang + '-20170401-langlinks.sql'
        # output
        self.output_path = self.lang + '_cl'

        self.wiki_cleaned_file = self.dump_path + self.output_path + '/wiki_article_cl.xml'
        self.title_file = self.dump_path + self.output_path + '/wiki_article_title'
        self.raw_entity_file = self.dump_path + self.output_path + '/raw_vocab_entity.dat'
        # the simplified chinese wiki anchor file from wiki_anchor_text extracted by WikiExtractor
        self.raw_anchor_file = self.dump_path + self.output_path + '/wiki_anchor_chs'

        self.redirect_file = self.dump_path + self.output_path + '/vocab_redirects.dat'
        self.raw_vocab_entity_file = self.dump_path + self.output_path + '/vocab_entity_all.dat'
        self.mono_outlink_file = self.dump_path + self.output_path + '/mono_kg.dat'
        self.vocab_entity_file = self.dump_path + self.output_path + '/vocab_entity.dat'
        self.cross_link_file = self.dump_path + self.output_path + '/cross_links.dat'
        self.anchor_file = self.dump_path + self.output_path + '/anchor_text_cl.dat'
        self.mention_file = self.dump_path + self.output_path + '/mention_count.dat'

class ZhPreprocessor():
    def __init__(self):
        self.nsidRE = re.compile(r'(\d{1,}):(\d{1,}):(.*)')
        self.formatRE = re.compile(r'-\{.*?(zh-hans|zh-cn):(?P<label>[^;]*?)([;].*?\}|\})-')
        self.total_entity_id = {}
        self.total_id_entity = {}
        self.entity_id = {}
        self.id_entity = {}

    # format zh-cn and zh-tw
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

    def loadTitleIndex(self, filename):
        with codecs.open(filename, 'r', 'utf-8') as fin:
            for line in fin:
                m = self.nsidRE.match(line.strip())
                if m != None:
                    id = m.group(2)
                    title = m.group(3)
                    self.total_entity_id[title] = id
                    self.total_id_entity[id] = title
        print "successfully load %d title index!" % len(self.total_entity_id)

    def buildEntityDic(self, filename):
        with codecs.open(filename, 'r', 'utf-8') as fin:
            for line in fin:
                title = line.strip()
                if title in self.total_entity_id:
                    self.entity_id[title] = self.total_entity_id[title]
                    self.id_entity[self.total_entity_id[title]] = title
        print "successfully build %d entities!" % len(self.entity_id)

    def saveEntityDic(self, filename):
        with codecs.open(filename, 'w', 'utf-8') as fout:
            for ent in self.entity_id:
                fout.write('%s\t%s\n' % (htmlparser.unescape(self.entity_id[ent]), htmlparser.unescape(ent)))

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

if __name__ == '__main__':
    op = options('zhwiki')
    zhPre = ZhPreprocessor()
    # replace -{zh-cn:xxx;zh-tw:xxx;}-
    # zhPre.formatRawWiki(op.wiki_dump, op.wiki_cleaned_file)
    # opencc: convert wiki_cleaned_file to simplified chinese
    zhPre.loadTitleIndex(op.entity_index_dump)
    zhPre.buildEntityDic(op.title_file)
    zhPre.saveEntityDic(op.raw_entity_file)