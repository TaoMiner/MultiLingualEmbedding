ulimit -s unlimited
ulimit -c unlimited
make
time ./align -train_text /data/m1/cyx/MultiMPME/data/dumps20170401/enwiki_cl/anchor_text_cl.dat -train_kg /data/m1/cyx/MultiMPME/data/dumps20170401/enwiki_cl/mono_kg_id.dat -train_anchor /data/m1/cyx/MultiMPME/data/dumps20170401/enwiki_cl/anchor_text_cl.dat -save_vocab_path /data/m1/cyx/MultiMPME/etc/exp5/envec/ -output_path /data/m1/cyx/MultiMPME/etc/exp5/envec/ -binary 1 -min-count 5 -cw 0 -sg 1 -size 200 -negative 5 -sample 1e-4 -threads 63 -iter 5 -window 5
