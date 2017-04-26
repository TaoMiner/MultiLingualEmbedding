import codecs
import re
import preprocess

languages = preprocess.languages
cleaner = preprocess.cleaner

class Sampler():
    def __init__(self, lang1, lang2):
        self.lang_indices = [languages.index(lang1), languages.index(lang2)]
        self.ids = [set() for i in xrange(len(languages))]
        self.num_sample = 1000

    def readCrosslinksId(self, filename):
        with codecs.open(filename, 'rb', 'utf-8') as fin:
            for line in fin:
                items = re.split(r'\t', line.strip('\n'))
                if len(items) != len(languages) : continue
                for i in xrange(len(self.lang_indices)):
                    if len(items[self.lang_indices[i]]) > 0:
                        self.ids[self.lang_indices[i]].add(items[self.lang_indices[i]])
        out = ''
        for i in xrange(len(self.lang_indices)):
            out += "read %d entities of %s lang!" % (len(self.ids[self.lang_indices[i]]), languages[self.lang_indices[i]])
        print out

    def sampleKG(self, filename, lang_index, outputfile):
        with codecs.open(filename, 'rb', 'utf-8') as fin:
            with codecs.open(outputfile, 'w', 'utf-8') as fout:
                output_count = 0
                for line in fin:
                    items = re.split('\t', line.strip())
                    tmp_head = items[0]
                    tmp_others = []
                    if tmp_head not in self.ids[lang_index]: continue
                    for ent in items[1:]:
                        if ent in self.ids[lang_index]:
                            tmp_others.append(ent)
                    if len(tmp_others) > 0:
                        fout.write("%s\t%s\n" % (tmp_head, '\t'.join(tmp_others)))
                        output_count += 1
                        if output_count >= self.num_sample:
                            break

    def sampleAnchor(self, filename, lang_index, outputfile):
        with codecs.open(filename, 'rb', 'utf-8') as fin:
            with codecs.open(outputfile, 'w', 'utf-8') as fout:
                output_count = 0
                for line in fin:
                    line = line.strip()
                    cur = 0
                    for s, e in cleaner.findBalanced(line):
                        tmp_anchor = line[s:e]
                        tmp_vbar = tmp_anchor.find('|')
                        tmp_label = ''
                        tmp_title = ''
                        if tmp_vbar > 0:
                            tmp_title = tmp_anchor[2:tmp_vbar]
                            tmp_label = tmp_anchor[tmp_vbar + 1:-2]
                        else:
                            tmp_label = tmp_anchor[2:-2]
                            tmp_title = tmp_label
                        if tmp_title in self.ids[lang_index]:
                            fout.write("%s\n" % line)
                            output_count += 1
                            if output_count >= self.num_sample:
                                break
                            continue
                        cur = e

if __name__ == '__main__':
    dump_path = '/data/m1/cyx/MultiMPME/data/dumps20170401/'
    cross_file = dump_path + 'cross_links_all.dat'
    lang1 = 'en'
    lang2 = 'zh'
    an_file1 = dump_path + lang1 +'wiki_cl/anchor_text_cl.dat'
    sample_an_file1 = dump_path + lang1 + 'wiki_cl/anchor_text_sample.dat'
    kg_file1 = dump_path + lang1 + 'wiki_cl/mono_kg_id.dat'
    sample_kg_file1 = dump_path + lang1 + 'wiki_cl/sample_kg.dat'

    # for simplified chinese
    an_file2 = dump_path + lang2 +'wiki_cl/anchor_text_chs.dat'
    sample_an_file2 = dump_path + lang2 + 'wiki_cl/anchor_text_sample.dat'
    kg_file2 = dump_path + lang2 + 'wiki_cl/mono_kg_id.dat'
    sample_kg_file2 = dump_path + lang2 + 'wiki_cl/sample_kg.dat'

    sp = Sampler('en', 'zh')
    sp.readCrosslinksId(cross_file)
    sp.sampleKG(kg_file1, sp.lang_indices[0], sample_kg_file1)
    sp.sampleKG(kg_file2, sp.lang_indices[1], sample_kg_file2)
    sp.sampleAnchor(an_file1, sp.lang_indices[0], sample_an_file1)
    sp.sampleAnchor(an_file2, sp.lang_indices[1], sample_an_file2)