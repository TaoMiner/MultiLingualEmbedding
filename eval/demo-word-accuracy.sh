ulimit -s unlimited
ulimit -c unlimited
make
time ./compute-accuracy /home/caoyx/data/etc/exp2/envec/vectors_word5 /home/caoyx/data/log/log_word 500000 < /home/caoyx/data/questions-words.txt
