import re
import codecs

qa_file = '/Users/ethan/Downloads/mlmpme/questions-words.txt'
par_file = '/Users/ethan/Downloads/mlmpme/para_data.dat'
enword_vocab_file = '/Users/ethan/Downloads/mlmpme/enwiki_cl/vocab_word.txt'
zhword_vocab_file = '/Users/ethan/Downloads/mlmpme/zhwiki_cl/vocab_word.txt'
par_vocabs = [{}, {}]
word_vocab = [{}, {}]
par_vocab_files = ['/Users/ethan/Downloads/mlmpme/enwiki_cl/par_vocab_word.txt', '/Users/ethan/Downloads/mlmpme/zhwiki_cl/par_vocab_word.txt']
qa_vocab_file = '/Users/ethan/Downloads/mlmpme/qa_vocab.txt'

def loadVocab(file, vocab):
    with codecs.open(file, 'r','utf-8') as fin:
        for line in fin:
            items = re.split(r'\t', line.strip('\n'))
            if len(items)!=2 : continue
            vocab[items[0]] = int(items[1])
    print "load %d words!" % len(vocab)

def saveVocab(file, vocab):
    with codecs.open(file, 'w','utf-8') as fout:
        for w in vocab:
            fout.write("%s\t%d\n" % (w[0], w[1]))

loadVocab(enword_vocab_file, word_vocab[0])
loadVocab(zhword_vocab_file, word_vocab[1])

with codecs.open(par_file, 'r', 'utf-8') as fin:
    for line in fin:
        par_lines = re.split(r'\t', line.strip())
        if len(par_lines)!= 2: continue
        for i in xrange(2):
            items = re.split(r' ', par_lines[i])
            for item in items:
                if item in word_vocab[i]:
                    par_vocabs[i][item] = word_vocab[i][item]
    sorted_vocab = [None, None]
    for i in xrange(2):
        sorted_vocab[i] = sorted(par_vocabs[i].items(), key=lambda x:x[1], reverse=True)
        saveVocab(par_vocab_files[i], sorted_vocab[i])
    print "totally %d en words and %d zh words!" % (len(par_vocabs[0]), len(par_vocabs[1]))

# count question words vocab
qa_vocab = {}
with codecs.open(qa_file, 'r', 'utf-8') as fin:
    for line in fin:
        if line.startswith(':'): continue
        items = re.split(r' ', line.lower().strip())
        if len(items) != 4: continue
        for it in items:
            if it in word_vocab[0] and it not in qa_vocab:
                qa_vocab[it] = word_vocab[0][it]
    sorted_qa_vocab = sorted(qa_vocab.items(), key=lambda x:x[1], reverse=True)
    print "there %d words in qa file!" % len(sorted_qa_vocab)
saveVocab(qa_vocab_file, sorted_qa_vocab)

