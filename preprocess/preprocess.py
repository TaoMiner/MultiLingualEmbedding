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
        self.titles = set()
        self.entity_id = {}
        self.id_entity = {}
        self.redirects = {}
        self.tmp_redirects = {}
        self.outlinks = {}
        self.nsidRE = re.compile(r'(\d{1,}):(\d{1,}):(.*)')
        # (pl_from_id, pl_namespace, pl_title, pl_from_namespace),
        # only for main namespace 0
        self.linkRE = re.compile(r'(\d{1,}),0,\'(.*?)\',0')
        # (rd_from_id, rd_namespace_id, rd_title, rd_interwiki, rd_fragment),
        # only for main namespace 0
        self.redirectRE = re.compile(r'(\d{1,}),0,\'(.*?)\',\'(.*?)\',\'(.*?)\'')

    def loadTitles(self, filename):
        with codecs.open(filename, 'r', 'ISO-8859-1') as fin:
            for line in fin:
                title = line.strip()
                # filter non title such as Category:xxx
                if ':' not in title:
                    self.titles.add(title)
        print "successfully load %d titles!" % len(self.titles)

    def buildEntityDic(self, filename):
        with codecs.open(filename, 'r', 'ISO-8859-1') as fin:
            for line in fin:
                m = self.nsidRE.match(line.strip())
                if m!=None:
                    id = m.group(2)
                    title = m.group(3)
                    if title in self.titles:
                        self.entity_id[title] = id
                        self.id_entity[id] = title
                    elif id in self.tmp_redirects and self.tmp_redirects[id] in self.titles:
                        self.redirects[title] = self.tmp_redirects[id]
        self.tmp_redirects.clear()
        self.titles.clear()
        print "successfully build %d entities and %d redirects!" % (len(self.entity_id), len(self.redirects))

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
                        self.tmp_redirects[rd_id] = rd_title
        print "successfully parse %d redirects!" % len(self.tmp_redirects)

    def saveEntityDic(self, filename):
        with codecs.open(filename, 'w', 'ISO-8859-1') as fout:
            for ent in self.entity_id:
                fout.write('%s\t%s\n' % (htmlparser.unescape(self.entity_id[ent]), htmlparser.unescape(ent)))

    def saveRedirects(self, filename):
        with codecs.open(filename, 'w', 'ISO-8859-1') as fout:
            for r in self.redirects:
                fout.write('%s\t%s\n' % (htmlparser.unescape(r), htmlparser.unescape(self.redirects[r])))


    def parseLinks(self, filename):
        with codecs.open(filename, 'rb', 'ISO-8859-1') as fin:
            for line in fin:
                line = line.replace('INSERT INTO `pagelinks` VALUES (', '')
                for i in line.strip().split('),('):
                    m = self.linkRE.match(i)  # Only select namespace 0 (Main/Article) pages
                    if m != None:
                        title = None
                        outlink = None
                        tmp_title = m.group(2)
                        tmp_title = tmp_title.replace('\\', '')
                        tmp_title = tmp_title.replace('_', ' ')
                        tmp_outlink_id = m.group(1)
                        if tmp_title in self.redirects:
                            title = self.redirects[tmp_title]
                        elif tmp_title in self.entity_id:
                            title = tmp_title
                        if tmp_outlink_id in self.id_entity:
                            outlink = self.id_entity[tmp_outlink_id]
                        if title and outlink:
                            tmp_set = set() if title not in self.outlinks else self.outlinks[title]
                            tmp_set.add(outlink)
                            self.outlinks[title] = tmp_set
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
        with codecs.open(filename, 'w', 'ISO-8859-1') as fout:
            for t in linked_entities:
                fout.write('%s\t%s\n' % (htmlparser.unescape(self.linked_entities[t]), htmlparser.unescape(t)))

def main():
    dump_path = '/data/m1/cyx/MultiMPME/data/dumps20170401/'
    lang = 'eswiki'
    redirect_dump = dump_path + lang + '/' + lang + '-20170401-redirect.sql'
    title_dump = dump_path + lang + '/' + lang + '-20170401-all-titles-in-ns0'
    entity_index_dump = dump_path + lang + '/' + lang + '-20170401-pages-articles-multistream-index.txt'
    pagelink_dump = dump_path + lang + '/' + lang + '-20170401-pagelinks.sql'
    # output
    output_path = lang + '_cl'
    title_file = dump_path + output_path + '/wiki_article_title'
    redirect_file = dump_path + output_path + '/vocab_redirects.dat'
    raw_vocab_entity_file = dump_path + output_path + '/vocab_entity_all.dat'
    mono_outlink_file = dump_path + output_path + '/mono_kg.dat'
    vocab_entity_file = dump_path + output_path + '/vocab_entity.dat'

    preprocessor = Preprocessor()
    # build entity dic and redirect dic
    preprocessor.loadTitles(title_file)
    preprocessor.parseRedirects(redirect_dump)
    preprocessor.buildEntityDic(entity_index_dump)
    preprocessor.saveEntityDic(raw_vocab_entity_file)
    preprocessor.saveRedirects(redirect_file)
    # extract outlinks
    preprocessor.parseLinks(pagelink_dump)
    preprocessor.saveOutlinks(mono_outlink_file)
    preprocessor.saveLinkedEntity(vocab_entity_file)

if __name__ == '__main__':
    main()

