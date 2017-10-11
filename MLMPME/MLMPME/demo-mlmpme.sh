ulimit -s unlimited
ulimit -c unlimited
make
time ./mlmpme -mono_anchor1 /home/caoyx/data/dump20170401/enwiki_cl/anchor_text_cl.dat -mono_anchor2 /home/caoyx/data/dump20170401/eswiki_cl/anchor_text_cl.dat -mono_kg1 /home/caoyx/data/dump20170401/enwiki_cl/mono_kg_id.dat -mono_kg2 /home/caoyx/data/dump20170401/eswiki_cl/mono_kg_id.dat -multi_context /home/caoyx/data/paradata/para_contexts.en-es -output1 /home/caoyx/data/etc/exp10/envec/ -output2 /home/caoyx/data/etc/exp10/esvec/ -read_mono_vocab1 /home/caoyx/data/etc/exp10/envec/ -read_mono_vocab2 /home/caoyx/data/etc/exp10/esvec/ -read_cross_link /home/caoyx/data/paradata/cross_links.en_es -size 200 -has_sense 1 -window 5 -sample 1e-4 -negative 5 -threads 31 -save_iter 5 -iter 5
