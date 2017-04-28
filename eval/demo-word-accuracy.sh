ulimit -s unlimited
ulimit -c unlimited
make
time ./compute-accuracy /data/m1/cyx/MultiMPME/etc/exp2/envec/vectors1_word5 /data/m1/cyx/MultiMPME/etc/exp2/log_word 500000 < /data/m1/cyx/MultiMPME/expdata/questions-words.txt
