CC = g++
#Using -Ofast instead of -O3 might result in faster code, but is supported only by newer GCC versions
CFLAGS = -lm -pthread -O3 -march=native -Wall -funroll-loops -Wno-unused-result

all: mlmpme

mlmpme : mlmpme.cpp
	$(CC) mlmpme.cpp -o mlmpme $(CFLAGS)
	chmod +x *.sh

clean:
	rm -rf mlmpme
