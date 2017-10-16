from options import Options
from candidate import Candidate
from DataReader import DataReader
from DataReader import Doc
from Entity import Entity
from Sense import Sense
import codecs
import re

en_entity = Entity()
en_entity.loadVocab(Options.getExpVocabFile( Options.en, Options.entity_type) )
es_entity = Entity()
es_entity.loadVocab(Options.getExpVocabFile( Options.es, Options.entity_type) )

en_sense = Sense()
en_sense.loadVocab(Options.getExpVocabFile( Options.en, Options.sense_type) )

es_sense = Sense()
es_sense.loadVocab(Options.getExpVocabFile( Options.es, Options.sense_type) )

en_entity_count = 0
es_entity_count = 0

en_sense_count = 0
es_sense_count = 0
line_count = 0

with codecs.open('/home/caoyx/data/paradata/para_contexts.en-es', 'r', encoding='UTF-8') as fin:
    for line in fin:
        items = re.split(r'\t', line.strip())
        if len(items) < 4: continue
        line_count += 1
        if items[0] in en_entity.vocab:
            en_entity_count += 1
        if items[0] in en_sense.vocab:
            en_sense_count += 1
        if items[1] in es_entity.vocab:
            es_entity_count += 1
        if items[1] in es_sense.vocab:
            es_sense_count += 1
print("ENG: {0} entity {1} sense in {2} lines!".format(en_entity_count, en_sense_count, line_count))
print("SPA: {0} entity {1} sense in {2} lines!".format(es_entity_count, es_sense_count, line_count))