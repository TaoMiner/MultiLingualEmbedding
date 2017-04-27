import numpy as np
import regex as re
import codecs
import struct
import rank_metrics as rm
from Entity import Entity

base_path = '/Users/ethan/Downloads/mlmpme/envec/'
eval_file = base_path + 'test_relatedness_id.dat'
entity_dic_file = base_path + 'vocab_entity.dat'
entity_vec_file = base_path + 'vectors1_entity.dat'
log_file = base_path + 'log_entity'

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
        fout_log.write("eval %d(%d) entities with %d(%d) candidate entities for %s!\n" % (act_ent_count,len(eval_query),can_count/act_ent_count,relatedness_pair_num/len(eval_query), entity_vec_file))
        fout_log.write("ndcg1 : %f, ndcg5 : %f, ndcg10 : %f, map : %f\n" % (float(ndcg1_sum/act_ent_count),float(ndcg5_sum/act_ent_count),float(ndcg10_sum/act_ent_count),float(map_sum/act_ent_count)))
        fout_log.write("**********************************\n")
