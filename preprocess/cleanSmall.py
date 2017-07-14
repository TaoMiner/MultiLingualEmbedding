import codecs
import re
import preprocess

options = preprocess.options
cleaner = preprocess.cleaner
languages = preprocess.languages

containerRE = re.compile(r'^<(.*)>')

lang = 'es'
lang_index = languages.index(lang)

path = '/home/caoyx/data/dump20170401/' + lang + 'wiki_cl/'
page_file = path + 'linked_wiki_pages.dat'
clean_file = path + 'anchor_text_cl_small.dat'
mention_file = path + 'mention_count_small.dat'

op = options(lang_index)
cl = cleaner()
cl.init(lang_index)
cl.entity_id = preprocess.Preprocessor.loadEntityDic(op.vocab_entity_file)
cl.redirects = preprocess.Preprocessor.loadRedirects(op.redirect_file)
with codecs.open(page_file, 'r', 'utf8') as fin:
    with codecs.open(clean_file, 'w', 'utf8') as fout:
        for line in fin:
            m = containerRE.match(line.strip())
            if m : continue
            res = cl.cleanAnchorSent(line.strip(), cl.lang, isReplaceId=True, entity_id=cl.entity_id,
                                          redirects=cl.redirects, mentions=cl.mentions)
            if len(res) > 11:
                fout.write("%s\n" % res)
        print 'process train text finished! start count anchors ...'
        if not mention_file:
            with codecs.open(mention_file, 'w', 'utf-8') as fout:
                out_list = []
                for t in cl.mentions:
                    out_list.append(cl.entity_id[t] + '\t' + t + "\t" + "\t".join(
                        ["%s::=%s" % (k, v) for k, v in cl.mentions[t].items()]) + "\n")
                    if len(out_list) >= 10000:
                        fout.writelines(out_list)
                        del out_list[:]
                if len(out_list) > 0:
                    fout.writelines(out_list)
            print 'count mentions finished!'