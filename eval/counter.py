from options import Options
from candidate import Candidate
from DataReader import DataReader
from DataReader import Doc
from Entity import Entity
from Sense import Sense
from preprocess import Preprocessor

def isInCand(cand, lang, ment_name, wiki_id):
    cand_set = cand.getCandidates(ment_name.lower(), lang)
    for c in cand_set:
        if c[0] == wiki_id:
            return True
    return False
entity_index_dump = '/home/caoyx/data/dump20170401/enwiki/enwiki-20170401-pages-articles-multistream-index.txt'
total_entity_id, total_id_entity = Preprocessor.loadWikiIndex(entity_index_dump)
redirects_id = Preprocessor.loadRedirectsId('/home/caoyx/data/dump20170401/enwiki_cl/vocab_redirects.dat', total_entity_id)

dr = DataReader()
idmap = dr.loadKbidMap(Options.kbid_map_file)
total_mentions = dr.loadKbpMentions(Options.getKBPAnsFile(2015, False), id_map=idmap, redirectsId=redirects_id)

cand = Candidate()
cand.loadCandidates()
cand.loadTranslations()
cand.loadCrossLinks(Options.cross_links_file)

en_entity = Entity()
en_entity.loadVocab(Options.getExpVocabFile(Options.en, Options.entity_type) )

en_sense = Sense()
en_sense.loadVocab(Options.getExpVocabFile(Options.en, Options.sense_type) )

en_nw_entity_count = 0
en_df_entity_count = 0
es_nw_entity_count = 0
es_df_entity_count = 0
zh_nw_entity_count = 0
zh_df_entity_count = 0

en_nw_sense_count = 0
en_df_sense_count = 0
es_nw_sense_count = 0
es_df_sense_count = 0
zh_nw_sense_count = 0
zh_df_sense_count = 0

en_nw_cand_count = 0
en_df_cand_count = 0
es_nw_cand_count = 0
es_df_cand_count = 0
zh_nw_cand_count = 0
zh_df_cand_count = 0

for doc_id in total_mentions:
    if doc_id.startswith("ENG") :
        if doc_id[4:6] == 'NW':
            for m in total_mentions[doc_id]:
                if isInCand(cand, Options.en, m[3], m[2]):
                    en_nw_cand_count += 1
                    if m[2] in en_entity.vocab:
                        en_nw_entity_count += 1
                    if m[2] in en_sense.vocab:
                        en_nw_sense_count += 1
        elif doc_id[4:6] == 'DF':
            for m in total_mentions[doc_id]:
                if isInCand(cand, Options.en, m[3], m[2]):
                    en_df_cand_count += 1
                    if m[2] in en_entity.vocab:
                        en_df_entity_count += 1
                    if m[2] in en_sense.vocab:
                        en_df_sense_count += 1
    if doc_id.startswith("SPA"):
        if doc_id[4:6] == 'NW':
            for m in total_mentions[doc_id]:
                if isInCand(cand, Options.es, m[3], m[2]):
                    es_nw_cand_count += 1
                    if m[2] in en_entity.vocab:
                        es_nw_entity_count += 1
                    if m[2] in en_sense.vocab:
                        es_nw_sense_count += 1
        elif doc_id[4:6] == 'DF':
            for m in total_mentions[doc_id]:
                if isInCand(cand, Options.es, m[3], m[2]):
                    es_df_cand_count += 1
                    if m[2] in en_entity.vocab:
                        es_df_entity_count += 1
                    if m[2] in en_sense.vocab:
                        es_df_sense_count += 1
    if doc_id.startswith("CMN"):
        if doc_id[4:6] == 'NW':
            for m in total_mentions[doc_id]:
                if isInCand(cand, Options.zh, m[3], m[2]):
                    zh_nw_cand_count += 1
                    if m[2] in en_entity.vocab:
                        zh_nw_entity_count += 1
                    if m[2] in en_sense.vocab:
                        zh_nw_sense_count += 1
        elif doc_id[4:6] == 'DF':
            for m in total_mentions[doc_id]:
                if isInCand(cand, Options.zh, m[3], m[2]):
                    zh_df_cand_count += 1
                    if m[2] in en_entity.vocab:
                        zh_df_entity_count += 1
                    if m[2] in en_sense.vocab:
                        zh_df_sense_count += 1
print("ENG: nw {0}/{1}/{2} ! df {3}/{4}/{5}".format(en_nw_sense_count, en_nw_entity_count, en_nw_cand_count,en_df_sense_count, en_df_entity_count, en_df_cand_count))
print("SPA: nw {0}/{1}/{2} ! df {3}/{4}/{5}".format(es_nw_sense_count, es_nw_entity_count, es_nw_cand_count,es_df_sense_count, es_df_entity_count, es_df_cand_count))
print("CMN: nw {0}/{1}/{2} ! df {3}/{4}/{5}".format(zh_nw_sense_count, zh_nw_entity_count, zh_nw_cand_count,zh_df_sense_count, zh_df_entity_count, zh_df_cand_count))