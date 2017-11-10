import codecs
import re

str_lang1 = 'en'
str_lang2 = 'es'
para_file = '/home/caoyx/data/paradata/para_contexts.' + str_lang1 + '-' + str_lang2
max_par_count = 0
avg_par_count = 0
par_count = [0,0,0,0,0,0]
line_count = 0
with codecs.open(para_file, 'r') as fin:
    for line in fin:
        items = re.split(r'\t', line.strip())
        if len(items) < 4 : continue
        par_num = len(items) - 3
        if par_num > max_par_count : max_par_count = par_num
        avg_par_count += par_num
        line_count += 1
        if par_num>0 and par_num<=10: par_count[0] += 1
        elif par_num>10 and par_num<=20: par_count[1] += 1
        elif par_num>20 and par_num<=30: par_count[2] += 1
        elif par_num>30 and par_num<=40: par_count[3] += 1
        elif par_num>40 and par_num<=50: par_count[4] += 1
        else: par_count[5] += 1

print("max:{0}, avg:{1}, step:{2}\n".format(max_par_count,float(avg_par_count)/line_count, ",".join(par_count)))