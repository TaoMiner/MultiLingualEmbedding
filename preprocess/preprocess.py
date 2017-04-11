import codecs
import re

class Preprocessor():

    def __init__(self):
        self.titles = set()
        self.entity_id = {}
        self.redirects = {}
        self.nsidRE = re.compile(r'(\d{1,}):(\d{1,}):(.*)')

    def loadTitles(self, filename):
        with codecs.open(filename, 'r', 'utf-8') as fin:
            for line in fin:
                self.titles.add(line.strip())
        print "successfully load %d titles!" % len(self.titles)

    def buildEntityDic(self, filename):
        with codecs.open(filename, 'r', 'utf-8') as fin:
            for line in fin:
                m = self.nsidRE.search(line.strip())
                if m.group(3) in self.titles:
                    self.entity_id[m.group(3)] = m.group(2)
        print "successfully build %d entities!" % len(self.entity_id)

    def loadRedirects(self, filename):
        with codecs.open(filename, 'r', 'utf-8') as fin:
            for line in fin:
