#-*- coding: utf-8 -*-
import sys
reload(sys)
sys.setdefaultencoding('utf8')
import codecs
import re

class Preprocessor():

    def __init__(self):
        self.titles = set()
        self.entity_id = {}
        self.id_entity = {}
        self.redirects = {}
        self.outlinks = {}
        self.nsidRE = re.compile(r'(\d{1,}):(\d{1,}):(.*)')
        self.linkRE = re.compile(r'\((\d{1,}),\d{1,},\'(.*?)\',\d{1,}\)')

    def loadTitles(self, filename):
        with codecs.open(filename, 'r', 'utf-8') as fin:
            for line in fin:
                title = line.strip()
                if title.startswith('Anexo:') or title.startswith('Categor') or title.startswith('Wikipedia:') :
                    continue
                if title.startswith('Category:') or title.startswith('Template:') or title.startswith('File:') or title.startswith('Wikipedia') or title.startswith('Portal'):
                    continue
                self.titles.add(line.strip())
        print "successfully load %d titles!" % len(self.titles)

    def buildEntityDic(self, filename):
        with codecs.open(filename, 'r', 'utf-8') as fin:
            for line in fin:
                m = self.nsidRE.search(line.strip())
                if m.group(3) in self.titles:
                    self.entity_id[m.group(3)] = m.group(2)
                    self.id_entity[m.group(2)] = m.group(3)
        print "successfully build %d entities!" % len(self.entity_id)

    def loadRedirects(self, filename):
        with codecs.open(filename, 'r', 'utf-8') as fin:
            for line in fin:
                items = re.split(r'\t', line.strip())
                if len(items) != 2: continue
                if items[1] in self.titles:
                    self.redirects[items[0]] = items[1]
        print "successfully load %d redirects!" % len(self.redirects)

    def saveEntityDic(self, filename):
        with codecs.open(filename, 'w', 'utf-8') as fout:
            for ent in self.entity_id:
                fout.write('%s\t%s\n' % (self.entity_id[ent], ent))

    def linkExtract(self, filename):
        with codecs.open(filename, 'rb') as fin:
            isValue = False
            for line in fin:
                if line.startswith('INSERT INTO'):
                    isValue = True
                if isValue:
                    for m in self.linkRE.finditer(line.strip()):
                        title = None
                        outlink = None
                        tmp_title = m.group(2).decode('ISO-8859-1')
                        tmp_outlink = m.group(1).decode('ISO-8859-1')
                        if tmp_title in self.redirects:
                            title = self.redirects[tmp_title]
                        elif tmp_title in self.entity_id:
                            title = tmp_title
                        if tmp_outlink in self.id_entity:
                            outlink = self.id_entity[tmp_outlink]
                        if title and outlink:
                            tmp_set = set() if title not in self.outlinks else self.outlinks[title]
                            tmp_set.add(outlink)
                            self.outlinks[title] = tmp_set
        outlink_num = 0
        for t in self.outlinks:
            outlink_num += len(self.outlinks[t])
        print "successfully extract %d outlinks for %d entities!" % (outlink_num, len(self.outlinks))

    def saveOutlinks(self,filename):
        with codecs.open(filename, 'w', 'utf-8') as fout:
            for t in self.outlinks:
                fout.write('%s\t%s\n' % (t, '\t'.join(self.outlinks[t])))

    def saveLinkedEntity(self, filename):
        linked_entities = set()
        for t in self.outlinks:
            linked_entities.add(t)
            for lt in self.outlinks[t]:
                linked_entities.add(lt)
        print "totally %d linked entities!" % len(linked_entities)
        with codecs.open(filename, 'w', 'utf-8') as fout:
            for t in linked_entities:
                fout.write('%s\t%s\n' % (t, self.entity_id[t]))

def main():
    dump_path = '/data/m1/cyx/MultiMPME/data/dumps20170401/'
    lang = 'eswiki'
    redirect_file = dump_path + lang + '/redirect_title'
    title_file = dump_path + lang + '/wiki_title'
    entity_index_file = dump_path + lang + '/' + lang + '-20170401-pages-articles-multistream-index.txt'
    pagelink_file = dump_path + lang + '/' + lang + '-20170401-pagelinks.sql'
    # output
    raw_vocab_entity_file = dump_path + lang + '/raw_vocab_entity.dat'
    mono_outlink_file = dump_path + lang + '/mono_kg.dat'
    vocab_entity_file = dump_path + lang + '/vocab_entity.dat'

    preprocessor = Preprocessor()
    preprocessor.loadTitles(title_file)
    preprocessor.loadRedirects(redirect_file)
    preprocessor.buildEntityDic(entity_index_file)
    preprocessor.saveEntityDic(raw_vocab_entity_file)
    preprocessor.linkExtract(pagelink_file)
    preprocessor.saveOutlinks(mono_outlink_file)
    preprocessor.saveLinkedEntity(vocab_entity_file)

if __name__ == '__main__':
    main()

