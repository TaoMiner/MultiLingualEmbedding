from options import Options
from candidate import Candidate
from DataReader import DataReader
from DataReader import Doc
from Entity import Entity
from Sense import Sense

def isInCand(cand, lang, ment_name, wiki_id):
    cand_set = cand.getCandidates(ment_name.lower(), lang)
    for c in cand_set:
        if c[0] == wiki_id:
            return True
    return False

dr = DataReader()
idmap = dr.loadKbidMap(Options.kbid_map_file)
total_mentions = dr.loadKbpMentions(Options.getKBPAnsFile(2015, False), id_map=idmap)

cand = Candidate()
cand.loadCandidates()
cand.loadTranslations()
cand.loadCrossLinks(Options.cross_links_file)

en_entity = Entity()
en_entity.loadVocab(Options.getExpVocabFile('exp9', Options.en, Options.entity_type) )
zh_entity = Entity()
zh_entity.loadVector(Options.getExpVocabFile('exp9', Options.zh, Options.entity_type) )
es_entity = Entity()
es_entity.loadVector(Options.getExpVocabFile('exp10', Options.es, Options.entity_type) )

en_sense = Sense()
en_sense.loadVector(Options.getExpVocabFile('exp9', Options.en, Options.sense_type) )
zh_sense = Sense()
zh_sense.loadVector(Options.getExpVocabFile('exp9', Options.zh, Options.sense_type) )
es_sense = Sense()
es_sense.loadVector(Options.getExpVocabFile('exp10', Options.es, Options.sense_type) )

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
                if isInCand(cand, Options.en, m[3], m[2]) and m[2] in en_entity.vocab:
                    en_nw_cand_count += 1
        elif doc_id[4:6] == 'DF':
            for m in total_mentions[doc_id]:
                if isInCand(cand, Options.en, m[3], m[2]) and m[2] in en_entity.vocab:
                    en_df_cand_count += 1
    if doc_id.startswith("SPA"):
        if doc_id[4:6] == 'NW':
            for m in total_mentions[doc_id]:
                if isInCand(cand, Options.es, m[3], m[2]) and m[2] in es_entity.vocab:
                    es_nw_cand_count += 1
        elif doc_id[4:6] == 'DF':
            for m in total_mentions[doc_id]:
                if isInCand(cand, Options.es, m[3], m[2]) and m[2] in es_entity.vocab:
                    es_df_cand_count += 1
    if doc_id.startswith("CMN"):
        if doc_id[4:6] == 'NW':
            for m in total_mentions[doc_id]:
                if isInCand(cand, Options.zh, m[3], m[2]) and m[2] in zh_entity.vocab:
                    zh_nw_cand_count += 1
        elif doc_id[4:6] == 'DF':
            for m in total_mentions[doc_id]:
                if isInCand(cand, Options.zh, m[3], m[2]) and m[2] in zh_entity.vocab:
                    zh_df_cand_count += 1
print("ENG: totally {0} nw mentions has embedding! {1} df mentions has embedding!".format(en_nw_cand_count, en_df_cand_count))
print("SPA: totally {0} nw mentions has embedding! {1} df mentions has embedding!".format(es_nw_cand_count, es_df_cand_count))
print("CMN: totally {0} nw mentions has embedding! {1} df mentions has embedding!".format(zh_nw_cand_count, zh_df_cand_count))