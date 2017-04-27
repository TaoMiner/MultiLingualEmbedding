ulimit -s unlimited
ulimit -c unlimited
make
time ./mlmpme -mono_anchor1 /data/m1/cyx/MultiMPME/data/dumps20170401/enwiki_cl/anchor_text_cl.dat -mono_kg1 /data/m1/cyx/MultiMPME/data/dumps20170401/enwiki_cl/mono_kg_id.dat -output1 /data/m1/cyx/MultiMPME/etc/test/envec/ -save_mono_vocab1 /data/m1/cyx/MultiMPME/etc/test/envec/ -size 200 -window 5 -sample 1e-4 -negative 5 -threads 63  -save_iter 5 -iter 5 -has_sense 0
