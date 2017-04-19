# -*- coding: utf-8 -*-

import codecs
import re


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
        self.redirect_file = self.dump_path + self.output_path + '/vocab_redirects.dat'
        self.raw_vocab_entity_file = self.dump_path + self.output_path + '/vocab_entity_all.dat'
        self.mono_outlink_file = self.dump_path + self.output_path + '/mono_kg.dat'
        self.vocab_entity_file = self.dump_path + self.output_path + '/vocab_entity.dat'
        self.cross_link_file = self.dump_path + self.output_path + '/cross_links.dat'
        self.raw_anchor_file = self.dump_path + self.output_path + '/wiki_anchor_text'
        self.anchor_file = self.dump_path + self.output_path + '/anchor_text_cl.dat'
        self.mention_file = self.dump_path + self.output_path + '/mention_count.dat'

nsidRE = re.compile(r'(\d{1,}):(\d{1,}):(.*)')

titles = set()

def loadTitleIndex(filename):
    with codecs.open(filename, 'r', 'utf-8') as fin:
        for line in fin:
            m = nsidRE.match(line.strip())
            if m != None:
                id = m.group(2)
                title = m.group(3)
                if title in titles:
                    print title.encode('utf-8')
                else:
                    titles.add(title)

formatRE = re.compile(r'-\{.*?(zh-hans|zh-cn):(?P<label>[^;]*?)(;.*?\}|\})-')
# format zh-cn and zh-tw
def zhwikiReplacefj(zhwiki_file, zhwiki_format_file):
    with codecs.open(zhwiki_file, 'r') as fin:
        with codecs.open(zhwiki_format_file, 'w', 'utf-8') as fout:
            for line in fin:
                line = line.decode('utf-8', 'ignore')
                line = formatRE.sub('\g<label>', line)
                fout.write(line)



op = options('zhwiki')

zhwikiReplacefj(op.wiki_dump, op.wiki_cleaned_file)