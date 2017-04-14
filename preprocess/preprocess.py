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
        self.outlinks = {}
        self.nsidRE = re.compile(r'(\d{1,}):(\d{1,}):(.*)')
        # (pl_from_id, pl_namespace, pl_title, pl_from_namespace),
        # only for main namespace 0
        self.linkRE = re.compile(r'(\d{1,}),0,\'(.*?)\',0')
        # (rd_from_id, rd_namespace_id, rd_title, rd_interwiki, rd_fragment),
        # only for main namespace 0
        self.redirectRE = re.compile(r'(\d{1,}),0,\'(.*?)\',\'(.*?)\',\'(.*?)\'')

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
                        self.id_redirects[rd_id] = rd_title
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
                fout.write('%s\t%s\n' % (htmlparser.unescape(r), htmlparser.unescape(self.redirects[r])))

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
                            from_title = self.id_redirects[tmp_from_id]
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
        with codecs.open(filename, 'w', 'ISO-8859-1') as fout:
            for t in linked_entities:
                if t not in self.entity_id:
                    print "error!%s" % t.encode('ISO-8859-1')
                    continue
                fout.write('%s\t%s\n' % (htmlparser.unescape(self.entity_id[t]), htmlparser.unescape(t)))

def main():
    dump_path = '/data/m1/cyx/MultiMPME/data/dumps20170401/'
    lang = 'zhwiki'
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
    preprocessor.loadTitleIndex(entity_index_dump)
    preprocessor.buildEntityDic(title_file)
    preprocessor.parseRedirects(redirect_dump)
    preprocessor.saveEntityDic(raw_vocab_entity_file)
    preprocessor.saveRedirects(redirect_file)
    # extract outlinks
    preprocessor.parseLinks(pagelink_dump)
    preprocessor.saveOutlinks(mono_outlink_file)
    preprocessor.saveLinkedEntity(vocab_entity_file)

if __name__ == '__main__':
    main()

