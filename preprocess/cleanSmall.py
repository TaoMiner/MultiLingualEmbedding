import codecs
import re
import preprocess

options = preprocess.options
cleaner = preprocess.cleaner

containerRE = re.compile(r'^<(.*)>')

lang = 'es'

path = '/home/caoyx/data/dump20170401/' + lang + 'wiki_cl/'
page_file = path + 'linked_wiki_pages.dat'
clean_file = path + 'anchor_text_cl_small.dat'
mention_file = path + 'mention_count_small.dat'

op = options(lang)
cl = cleaner()
cl.init(lang)
with codecs.open(page_file, 'r', 'utf8') as fin:
    with codecs.open(clean_file, 'w', 'utf8') as fout:
        for line in fin:
            m = containerRE.match(line.strip())
            if m : continue

            cl.entity_id = preprocess.Preprocessor.loadEntityDic(op.vocab_entity_file)
            cl.redirects = preprocess.Preprocessor.loadRedirects(op.redirect_file)
            cl.cleanWiki(op.raw_anchor_file, op.anchor_file, mention_file=op.mention_file)