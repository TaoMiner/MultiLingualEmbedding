ulimit -s unlimited
ulimit -c unlimited
make
time ./mlmpme -mono_anchor1 /data/m1/cyx/MultiMPME/data/dumps20170401/enwiki_cl/anchor_text_cl.dat -mono_anchor2 /data/m1/cyx/MultiMPME/data/dumps20170401/zhwiki_cl/anchor_text_chs.dat -mono_kg1 /data/m1/cyx/MultiMPME/data/dumps20170401/enwiki_cl/mono_kg_id.dat -mono_kg2 /data/m1/cyx/MultiMPME/data/dumps20170401/enwiki_cl/mono_kg_id.dat -multi_context /data/m1/cyx/MultiMPME/data/dumps20170401/para_data.dat -output1 /data/m1/cyx/MultiMPME/etc/test/envec/ -output2 /data/m1/cyx/MultiMPME/etc/test/zhvec/ -save_mono_vocab1 /data/m1/cyx/MultiMPME/etc/test/envec/ -save_mono_vocab2 /data/m1/cyx/MultiMPME/etc/test/zhvec/ -read_cross_link /data/m1/cyx/MultiMPME/data/dumps20170401/cross_links_all_id.dat -size 200 -window 5 -sample 1e-4 -negative 5 -threads 63  -save_iter 1 -iter 1
