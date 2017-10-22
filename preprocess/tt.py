import codecs
import re


cross_link_file1 = '/home/caoyx/data/paradata/cross_links_labels.en_zh'
cross_link_file2 = '/home/caoyx/data/paradata/cross_links_labels.en_es'
para_sent_file = '/home/caoyx/data/paradata/para_data.en-es'
input_files = [cross_link_file1, cross_link_file2, para_sent_file]

output_file1 = '/home/caoyx/data/paradata/para_links.en_zh'
output_file2 = '/home/caoyx/data/paradata/para_links.en_es'
output_file3 = '/home/caoyx/data/paradata/para_sents.en_es'
output_files = [output_file1, output_file2, output_file3]

spaceRE = re.compile(r'[ ]+')
ddRE = re.compile(r'dddddd')
for i in range(3):
    with codecs.open(input_files[i], 'r') as fin:
        with codecs.open(output_files[i], 'w') as fout:
            for line in fin:
                line = ddRE.sub('', line.strip())
                line = spaceRE.sub(' ', line)
                items = re.split(r'\t', line.strip())
                if len(items) != 2 or len(items[0])<0 or len(items[1])<0 : continue
                fout.write("1\tid1\tid2\t{0}\n".format(items[0]))
                fout.write("2\tid1\tid2\t{0}\n".format(items[1]))
