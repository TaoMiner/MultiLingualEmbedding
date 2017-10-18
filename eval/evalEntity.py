import numpy as np
import regex as re
import codecs
import struct
import rank_metrics as rm
from Entity import Entity
from options import Options

exp = 'exp18'
it = 5

eval_file = Options.entity_relatedness_file
entity_dic_file = Options.getExpVocabFile(Options.en, Options.entity_type)
entity_vec_file = Options.getExpVecFile(exp,Options.en, Options.entity_type, it)
log_file = Options.getLogFile('log_entity')

ent_id_dic = Entity.loadEntityDic(entity_dic_file)
id_ent_dic = Entity.loadEntityIdDic(entity_dic_file)
ent_vec = {}
eval_query = {}
relatedness_pair_num = 0
vocab_size = 0
layer_size = 0

def loadEvalFile():
    with codecs.open(eval_file, 'r', encoding='UTF-8') as fin_eval:
        global relatedness_pair_num
        for line in fin_eval:
            tmp_q = re.split(r'\t', line.strip())
            if len(tmp_q)==3:
                e_id = tmp_q[0]
                c_id = tmp_q[1]
                label = int(tmp_q[2])
                if e_id not in entity.vectors or c_id not in entity.vectors:
                    continue
                if e_id in eval_query and c_id not in eval_query[e_id]:
                    eval_query[e_id][c_id] = label
                else:
                    eval_query[e_id] = {c_id:label}
                relatedness_pair_num += 1
        print("successfully load %d entities with %d candidate entities on average from relatedness file!" % (len(eval_query), relatedness_pair_num/len(eval_query)))

entity = Entity()
entity.loadVector(entity_vec_file)
ent_vec = entity.vectors
loadEvalFile()
ent_skip_count = 0
can_count = 0
ndcg1_sum = 0
ndcg5_sum = 0
ndcg10_sum = 0
map_sum = 0
for ent in eval_query:
    sim = []
    if ent not in ent_vec:
        ent_skip_count += 1
    else:
        tmp_can_count = 0
        for can in eval_query[ent]:
            if can in ent_vec:
                tmp_can_count += 1
                a = ent_vec[ent]*ent_vec[can]
                sim.append((can, a.sum()))
        if tmp_can_count > 1:
            sim_rank = sorted(sim, key=lambda sim : sim[1], reverse=True)
            r = []
            for item in sim_rank:
                r.append(eval_query[ent][item[0]])
            if len(r) >1:
                tmp_n1 = rm.ndcg_at_k(r, 1, 1)
            else:
                tmp_n1 = rm.ndcg_at_k(r, len(r), 1)
            if len(r) >5:
                tmp_n5 = rm.ndcg_at_k(r, 5, 1)
            else:
                tmp_n5 = rm.ndcg_at_k(r, len(r), 1)
            if len(r) >10:
                tmp_n10 = rm.ndcg_at_k(r, 10, 1)
            else:
                tmp_n10 = rm.ndcg_at_k(r, len(r), 1)
            tmp_ap = rm.average_precision(r)
            ndcg1_sum += tmp_n1
            ndcg5_sum += tmp_n5
            ndcg10_sum += tmp_n10
            map_sum += tmp_ap
            can_count += tmp_can_count
        else:
            ent_skip_count +=1

if len(eval_query) > 0:
    act_ent_count = len(eval_query)-ent_skip_count
    with codecs.open(log_file, 'a', encoding='UTF-8') as fout_log:
        fout_log.write("**********************************\n")
        fout_log.write("{0}, eval {1}({2}) entities with {3}({4}) candidate entities!\n".format(exp, act_ent_count,len(eval_query),can_count/act_ent_count,relatedness_pair_num/len(eval_query)))
        fout_log.write("ndcg1 : {0}, ndcg5 : {1}, ndcg10 : {2}, map : {3}\n".format(float(ndcg1_sum/act_ent_count),float(ndcg5_sum/act_ent_count),float(ndcg10_sum/act_ent_count),float(map_sum/act_ent_count)))
        fout_log.write("**********************************\n")
