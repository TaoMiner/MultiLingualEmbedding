//
//  mlmpme.cpp
//  MLMPME
//
//  Created by 曹艺馨 on 17/3/16.
//  Copyright © 2017年 ethan. All rights reserved.
//

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <pthread.h>


#define inf 1000000000
#define _clr(x, len) memset(x,-1,sizeof(int)*len)

#define MAX_STRING 1100          //>longest entity + longest mention + 1
#define NUM_LANG 2
#define NUM_MODEL 3
#define EXP_TABLE_SIZE 1000
#define MAX_EXP 6
#define TEXT_VOCAB 0
#define KG_VOCAB 1
#define SENSE_VOCAB 2
#define MAX_NUM_MENTION 135
#define MAX_SENTENCE_LENGTH 1000
#define MAX_PAR_SENT 10
#define CLIP_UPDATES 0.1               // biggest update per parameter per step

typedef float real;                    // Precision of float numbers

struct KM_var {
    int m,n;
    real *matrix;
    int match1[MAX_PAR_SENT*MAX_SENTENCE_LENGTH], match2[MAX_PAR_SENT*MAX_SENTENCE_LENGTH];
    int s[MAX_PAR_SENT*MAX_SENTENCE_LENGTH], t[MAX_PAR_SENT*MAX_SENTENCE_LENGTH];
    real l1[MAX_PAR_SENT*MAX_SENTENCE_LENGTH];
    real l2[MAX_PAR_SENT*MAX_SENTENCE_LENGTH];
};

struct anchor_item {
    long long start_pos;
    long long length;
    int entity_index;
    int sense_index;
};

struct vocab_item {
    long long cn;                   //for words, text counts; for sense, anchor counts; for entity, outlink counts.
    int index;                     //for words, sense indexes; for entity, cross links index; for sense, context cluster num.
    int entity_index;               // only for sense, corresponding entity index.
    char *item;
};

struct vocab {
    char train_file[MAX_STRING], output_file[MAX_STRING];
    char save_vocab_file[MAX_STRING], read_vocab_file[MAX_STRING];
    int vocab_type, lang;
    struct vocab_item *vocab;
    int *vocab_hash, vocab_hash_size;
    long long vocab_max_size, vocab_size;
    long long train_items, file_size;
    long long lang_updates, dump_iters, epoch;
    real *syn0, *syn1neg;
    real *syn0Grad, *syn1negGrad;
    real *syn0Delta, *syn1negDelta;
    int *table;
    int min_count;
};

// NUM_MODEL: words, entities, senses vocab; NUM_LANG: different languages
struct vocab model[NUM_MODEL][NUM_LANG];

// cross links dictionary
int *cross_links[NUM_LANG];

int local_iter=0, debug_mode = 2, window = 5, num_threads = 12, min_reduce = 1, negative = 5, binary=1, shareSyn0 = 1, min_count = 5, is_normal = 0, sgd_mode=0, has_sense=1,has_kg_att = 1, has_w_att = 1, sim_mode = 0;
long long layer_size = 100, max_train_words = 0, entity_count_actual=0, word_count_actual=0, NUM_EPOCHS = 1, EARLY_STOP = 0, dump_every=0;

const int table_size = 1e8;
real starting_alpha, alpha = 0.025, sample = 1e-3, cross_model_weight = 1, rho = 1.0, xling=0.9;
real *expTable;
char multi_context_file[NUM_LANG-1][MAX_STRING], output_path[NUM_LANG][MAX_STRING], read_mono_vocab_path[NUM_LANG][MAX_STRING], save_mono_vocab_path[NUM_LANG][MAX_STRING], cross_link_file[NUM_LANG-1][MAX_STRING];
clock_t start;
long long par_actual_line[NUM_LANG-1];
int par_line_num[NUM_LANG-1], par_epoch[NUM_LANG-1], max_num_clink=0, MONO_DONE_TRAINING = 0;
real par_err[NUM_LANG-1];
unsigned long long g_next_random = 0;

bool isequal(real a,real b)
{
    if(fabs(a-b)<0.000001)
        return 1;
    return 0;
}

//return the num of mention words
//split_pos indicates word start position in mention, range from 0 to mention length -1
int SplitMention(int *split_pos, char *mention) {
    int a = 0, b = 0, ch;
    if(mention[b]!=0){
        split_pos[a] = 0;
        a++;
        b++;
    }
    while (mention[b]!=0) {
        ch = mention[b];
        b++;
        if (ch == ' ')
            if(mention[b]!=0){
                split_pos[a] = b;
                a++;
                if(a>=MAX_NUM_MENTION){
                    a = -1;
                    break;
                }
            }
    }
    return a;
}

//return negative if that's not anchor, the int indicates how many words should be offset.
//return the word's start pos
int ReadAnchor(char *item, FILE *fin){
    int a = 0, ch, is_anchor = 0, prev_brace = 0, post_brace = 0, word_num=0, anchor_pos=0;
    while (!feof(fin)) {
        ch = fgetc(fin);
        if( prev_brace==0 ){
            if(ch == '['){
                prev_brace = 1;
                continue;
            }
            else{
                a=0;
                is_anchor --;
                break;
            }
        }
        is_anchor--;
        if(ch == ' ') word_num ++;
        if (ch == '\n' || word_num>MAX_NUM_MENTION) {
            a = 0;
            break;
        }
        if (ch == '|')
            anchor_pos = a+1;
        if ( (ch == ']') && (post_brace==0)){
            post_brace = 1;
            continue;
        }
        if(post_brace==1){
            if(ch == ']')
                is_anchor = anchor_pos;
            break;
        }
        item[a] = ch;
        a++;
        if (a >= MAX_STRING - 1){a--;break;}
    }
    item[a] = 0;
    return is_anchor;
}


//return negative if that's not anchor, the int indicates the offset.
//return 0 if read correctly
int ReadMention(char *item, FILE *fin){
    int a = 0, ch, is_anchor = 0, prev_brace = 0, post_brace = 0, word_num=0;
    while (!feof(fin)) {
        ch = fgetc(fin);
        if( prev_brace==0 ){
            if(ch == '{'){
                prev_brace = 1;
                continue;
            }
            else{
                a=0;
                is_anchor --;
                break;
            }
        }
        is_anchor--;
        if(ch == ' ') word_num ++;
        if (ch == '\n' || word_num>MAX_NUM_MENTION) {
            a = 0;
            break;
        }
        if ( (ch == '}') && (post_brace==0)){
            post_brace = 1;
            continue;
        }
        if(post_brace==1){
            if(ch == '}')
                is_anchor = 0;
            break;
        }
        item[a] = ch;
        a++;
        if (a >= MAX_STRING - 1){a--;break;}
    }
    item[a] = 0;
    return is_anchor;
}

// Reads a single word or anchor from an annotated text file, assuming space + tab + EOL to be word boundaries, [[anchor]]
//return -1 if read a word, 0 if [[anchor]], '|''s pos(1-length) if [[entity|mention]]
//return -2 if read a mention
int ReadText(char *item, FILE *fin) {
    int a = 0, ch, is_anchor=-1;
    
    while (!feof(fin)) {
        ch = fgetc(fin);
        if (ch == 13) continue;
        if ((ch == ' ') || (ch == '\t') || (ch == '\n') || (ch == ']') || (ch == '[') || (ch == '{') || (ch == '}')) {
            if (a > 0) {
                if (ch == '\n') ungetc(ch, fin);
                if (ch == '[') ungetc(ch, fin);
                if (ch == '{') ungetc(ch, fin);
                break;
            }
            if (ch == '\n') {
                strcpy(item, (char *)"</s>");
                return -1;
            }
            else if (ch == '['){
                is_anchor = ReadAnchor(item, fin);
                if (is_anchor<0){
                    fseek(fin, is_anchor, SEEK_CUR);
                    continue;
                }
                else return is_anchor;
            }
            else if(ch == '{'){
                is_anchor = ReadMention(item, fin);
                if (is_anchor<0){
                    fseek(fin, is_anchor, SEEK_CUR);
                    continue;
                }
                else return -2;
            }
            else continue;
        }
        item[a] = ch;
        a++;
        if (a >= MAX_STRING - 1) a--;   // Truncate too long words
    }
    item[a] = 0;
    return -1;
}

void ReadItem(char *item, FILE *fin) {
    int a = 0, ch;
    while (!feof(fin)) {
        ch = fgetc(fin);
        if (ch == 13) continue;
        if ((ch == '\t') || (ch == ' ') || (ch == '\n')) {
            if (a > 0) {
                if (ch == '\n') ungetc(ch, fin);
                else if (ch == '\t') ungetc(ch, fin);
                break;
            }
            if (ch == '\n') {
                strcpy(item, (char *)"</s>");
                return;
            } else if (ch == '\t'){
                strcpy(item, (char *)"</t>");
                return;
            } else continue;
        }
        item[a] = ch;
        a++;
        if (a >= MAX_STRING - 1) a--;   // Truncate too long words
    }
    item[a] = 0;
}

// Returns hash value of an item
int GetItemHash(char *item, int vocab_hash_size) {
    unsigned long long a, hash = 0;
    for (a = 0; a < strlen(item); a++) hash = hash * 257 + item[a];
    hash = hash % vocab_hash_size;
    return hash;
}

// Returns position of an item in the vocabulary; if the item is not found, returns -1
int SearchVocab(char *item, struct vocab *mono_vocab) {
    unsigned int hash = GetItemHash(item, mono_vocab->vocab_hash_size);
    while (1) {
        if (mono_vocab->vocab_hash[hash] == -1) return -1;
        if (!strcmp(item, mono_vocab->vocab[mono_vocab->vocab_hash[hash]].item)) return mono_vocab->vocab_hash[hash];
        hash = (hash + 1) % mono_vocab->vocab_hash_size;
    }
    return -1;
}

// Reduces the vocabulary by removing infrequent tokens
void ReduceVocab(struct vocab *mono_vocab) {
    int a, b = 0;
    unsigned int hash;
    for (a = 0; a < mono_vocab->vocab_size; a++) if (mono_vocab->vocab[a].cn > min_reduce) {
        mono_vocab->vocab[b].cn = mono_vocab->vocab[a].cn;
        mono_vocab->vocab[b].item = mono_vocab->vocab[a].item;
        b++;
    } else free(mono_vocab->vocab[a].item);
    mono_vocab->vocab_size = b;
    for (a = 0; a < mono_vocab->vocab_hash_size; a++) mono_vocab->vocab_hash[a] = -1;
    for (a = 0; a < mono_vocab->vocab_size; a++) {
        // Hash will be re-computed, as it is not actual
        hash = GetItemHash(mono_vocab->vocab[a].item, mono_vocab->vocab_hash_size);
        while (mono_vocab->vocab_hash[hash] != -1) hash = (hash + 1) % mono_vocab->vocab_hash_size;
        mono_vocab->vocab_hash[hash] = a;
    }
    fflush(stdout);
    min_reduce++;
}

// Adds an item to its vocabulary
int AddItemToVocab(char *item, struct vocab *mono_vocab) {
    unsigned int hash, length = strlen(item) + 1;
    if (length > MAX_STRING) length = MAX_STRING;
    mono_vocab->vocab[mono_vocab->vocab_size].item = (char *)calloc(length, sizeof(char));
    strcpy(mono_vocab->vocab[mono_vocab->vocab_size].item, item);
    mono_vocab->vocab[mono_vocab->vocab_size].cn = 0;
    mono_vocab->vocab[mono_vocab->vocab_size].index = -1;
    mono_vocab->vocab[mono_vocab->vocab_size].entity_index = -1;
    mono_vocab->vocab_size++;
    // Reallocate memory if needed
    if (mono_vocab->vocab_size + 2 >= mono_vocab->vocab_max_size) {
        mono_vocab->vocab_max_size += 100000;
        mono_vocab->vocab = (struct vocab_item *)realloc(mono_vocab->vocab, mono_vocab->vocab_max_size * sizeof(struct vocab_item));
    }
    hash = GetItemHash(item, mono_vocab->vocab_hash_size);
    while (mono_vocab->vocab_hash[hash] != -1) hash = (hash + 1) % mono_vocab->vocab_hash_size;
    mono_vocab->vocab_hash[hash] = mono_vocab->vocab_size - 1;
    return mono_vocab->vocab_size - 1;
}

// Used later for sorting by item counts
int VocabCompare( const void *a, const void *b) {
    return ((struct vocab_item *)b)->cn - ((struct vocab_item *)a)->cn;
}

// Sorts the vocabulary by frequency using vocab cn
void SortVocab(struct vocab *mono_vocab) {
    int a;
    long long size;
    unsigned int hash;
    // Sort the vocabulary and keep </s> at the first position
    qsort(&mono_vocab->vocab[1], mono_vocab->vocab_size - 1, sizeof(struct vocab_item), VocabCompare);
    for (a = 0; a < mono_vocab->vocab_hash_size; a++) mono_vocab->vocab_hash[a] = -1;
    size = mono_vocab->vocab_size;
    mono_vocab->train_items = 0;
    for (a = 0; a < size; a++) {
        // items occuring less than min_count times will be discarded from the vocab
        if ((mono_vocab->vocab[a].cn < mono_vocab->min_count) && (a != 0)) {
            mono_vocab->vocab_size--;
            free(mono_vocab->vocab[a].item);
        } else {
            // Hash will be re-computed, as after the sorting it is not actual
            hash=GetItemHash(mono_vocab->vocab[a].item, mono_vocab->vocab_hash_size);
            while (mono_vocab->vocab_hash[hash] != -1) hash = (hash + 1) % mono_vocab->vocab_hash_size;
            mono_vocab->vocab_hash[hash] = a;
            mono_vocab->train_items += mono_vocab->vocab[a].cn;
        }
    }
    mono_vocab->vocab = (struct vocab_item *)realloc(mono_vocab->vocab, (mono_vocab->vocab_size + 1) * sizeof(struct vocab_item));
}

void ReadVocab(struct vocab *mono_vocab) {
    long long a;
    char c;
    char item[MAX_STRING];
    FILE *fin = fopen(mono_vocab->read_vocab_file, "rb");
    if (fin == NULL) {
        printf("Vocabulary file not found\n");
        exit(1);
    }
    //initialize hash map and set vocab size
    for (a = 0; a < mono_vocab->vocab_hash_size; a++) mono_vocab->vocab_hash[a] = -1;
    mono_vocab->vocab_size = 0;
    while (1) {
        ReadItem(item, fin);
        if (feof(fin)) break;
        if (!strcmp(item, "</t>")) continue;
        a = AddItemToVocab(item, mono_vocab);
        if (mono_vocab->vocab_type==SENSE_VOCAB )
            mono_vocab->vocab[a].entity_index = SearchVocab(item, &model[KG_VOCAB][mono_vocab->lang]);
        fscanf(fin, "%lld%c", &mono_vocab->vocab[a].cn, &c);
    }
    SortVocab(mono_vocab);
    if (debug_mode > 0) {
        printf("Size of Vocab %d for lang %d: %lld\n", mono_vocab->vocab_type, mono_vocab->lang, mono_vocab->vocab_size);
        printf("Items in train file: %lld\n", mono_vocab->train_items);
    }
    fin = fopen(mono_vocab->train_file, "rb");
    if (fin == NULL) {
        printf("ERROR: training data file not found!\n");
        exit(1);
    }
    fseek(fin, 0, SEEK_END);
    mono_vocab->file_size = ftell(fin);
    fclose(fin);
}

void LearnWordVocabFromTrainFile(int lang_id) {
    char word[MAX_STRING], tmp_word[MAX_STRING];
    FILE *fin;
    long long a, i, b;
    size_t tmp_word_len = 0;
    int anchor_pos = -1, word_begin[MAX_NUM_MENTION], words_in_mention = 1;
    struct vocab *mono_vocab = &model[TEXT_VOCAB][lang_id];
    for(a=0;a<MAX_NUM_MENTION;a++) word_begin[a] = 0;;
    for (a = 0; a < mono_vocab->vocab_hash_size; a++) mono_vocab->vocab_hash[a] = -1;
    fin = fopen(mono_vocab->train_file, "rb");
    if (fin == NULL) {
        printf("ERROR: training data file not found!\n");
        exit(1);
    }
    mono_vocab->vocab_size = 0;
    AddItemToVocab((char *)"</s>", mono_vocab);
    while (1) {
        anchor_pos = ReadText(word, fin);
        if (feof(fin)) break;
        
        if(anchor_pos > 0){
            tmp_word_len = strlen(word)-anchor_pos;
            strncpy(tmp_word, &word[anchor_pos], sizeof(char)*tmp_word_len);
        }
        else{
            tmp_word_len = strlen(word);
            strncpy(tmp_word, word, sizeof(char)*tmp_word_len);
        }
        tmp_word[tmp_word_len] = 0;
        //get the words start pos in the mention. or return 1 for a word
        words_in_mention = SplitMention(word_begin, tmp_word);
        for(b=0;b<words_in_mention;b++){
            if (anchor_pos == -1){
                tmp_word_len = strlen(tmp_word);
                strncpy(word, tmp_word, sizeof(char)*tmp_word_len);
            }
            else if(b+1<words_in_mention){
                tmp_word_len = word_begin[b+1]-1-word_begin[b];
                strncpy(word, &tmp_word[word_begin[b]], sizeof(char)*tmp_word_len);
            }
            else{
                tmp_word_len = strlen(&tmp_word[word_begin[b]]);
                strncpy(word, &tmp_word[word_begin[b]], sizeof(char)*tmp_word_len);
            }
            word[tmp_word_len]=0;
            mono_vocab->train_items++;
            if ((debug_mode > 1) && (mono_vocab->train_items % 100000 == 0)) {
                printf("%lldK%c", mono_vocab->train_items / 1000, 13);
                fflush(stdout);
            }
            i = SearchVocab(word, mono_vocab);
            if (i == -1) {
                a = AddItemToVocab(word, mono_vocab);
                mono_vocab->vocab[a].cn = 1;
            } else mono_vocab->vocab[i].cn++;
            if (mono_vocab->vocab_size > mono_vocab->vocab_hash_size * 0.7) ReduceVocab(mono_vocab);
        }
        
    }
    SortVocab(mono_vocab);
    if (debug_mode > 0) {
        printf("lang %d: Word Vocab size: %lld\n", lang_id, mono_vocab->vocab_size);
        printf("lang %d: Words in train file: %lld\n", lang_id, mono_vocab->train_items);
    }
    mono_vocab->file_size = ftell(fin);
    fclose(fin);
}

void LearnEntityVocabFromTrainFile(int lang_id) {
    char entity[MAX_STRING];
    FILE *fin;
    long long a, i;
    
    //initial entity vocab
    struct vocab *entity_vocab = &model[KG_VOCAB][lang_id];
    for (a = 0; a < entity_vocab->vocab_hash_size; a++) entity_vocab->vocab_hash[a] = -1;
    fin = fopen(entity_vocab->train_file, "rb");
    if (fin == NULL) {
        printf("ERROR: training data file not found!\n");
        exit(1);
    }
    entity_vocab->vocab_size = 0;
    AddItemToVocab((char *)"</s>", entity_vocab);
    
    while (1) {
        ReadItem(entity, fin);
        if (feof(fin)) break;
        if (!strcmp(entity, "</t>")) continue;
        entity_vocab->train_items++;
        if ((debug_mode > 1) && (entity_vocab->train_items % 100000 == 0)) {
            printf("%lldK%c", entity_vocab->train_items / 1000, 13);
            fflush(stdout);
        }
        //add entity into entity vocab
        i = SearchVocab(entity, entity_vocab);
        if (i == -1) {
            a = AddItemToVocab(entity, entity_vocab);
            entity_vocab->vocab[a].cn = 1;
        } else entity_vocab->vocab[i].cn++;
        if (entity_vocab->vocab_size > entity_vocab->vocab_hash_size * 0.7) ReduceVocab(entity_vocab);
    }
    SortVocab(entity_vocab);
    if (debug_mode > 0) {
        printf("lang %d: Entity vocab size: %lld\n", lang_id, entity_vocab->vocab_size);
        printf("lang %d: Entities in train file: %lld\n", lang_id, entity_vocab->train_items);
    }
    entity_vocab->file_size = ftell(fin);
    fclose(fin);
}

// return the pos of the left brace, -1 indicate there isn't.
int lengthOfMention(char *entity_title){
    int i;
    int length = strlen(entity_title);
    for (i=length-1;i>=0;i--)
        if (entity_title[i] == '('){
            if (i>0 && entity_title[i-1] == ' ') i--;
            break;
        }
    length = i;
    return length;
}

// read anchors to add sense mention into word vocab and count them
void LearnSenseVocabFromTrainFile(int lang_id) {
    char ent_str[MAX_STRING], item[MAX_STRING];
    FILE *fin;
    long long i,a;
    int anchor_pos = -1;
    struct vocab *entity_vocab = &model[KG_VOCAB][lang_id];
    //initial sense vocab
    struct vocab *sense_vocab = &model[SENSE_VOCAB][lang_id];
    for (a = 0; a < sense_vocab->vocab_hash_size; a++) sense_vocab->vocab_hash[a] = -1;
    sense_vocab->vocab_size = 0;
    
    //add entity into sense vocab for initialization
    for(i=0;i<entity_vocab->vocab_size;i++){
        a = AddItemToVocab(entity_vocab->vocab[i].item, sense_vocab);
        sense_vocab->vocab[a].entity_index = i;
    }
    sense_vocab->vocab[0].cn = entity_vocab->vocab[0].cn;
    fin = fopen(sense_vocab->train_file, "rb");
    if (fin == NULL) {
        printf("ERROR: training data file not found!\n");
        exit(1);
    }
    while (1) {
        anchor_pos = ReadText(item, fin);
        if (feof(fin)) break;
        // skip words
        if (anchor_pos < 0) continue;
        
        if (anchor_pos == 0){
            strcpy(ent_str, item);
            ent_str[strlen(item)] = 0;
        }
        else{
            strncpy(ent_str, item, sizeof(char)*(anchor_pos-1));
            ent_str[anchor_pos-1] = 0;
        }
        //count anchors for sense
        i = SearchVocab(ent_str, sense_vocab);
        if (i != -1) sense_vocab->vocab[i].cn++;
        sense_vocab->train_items++;
        if ((debug_mode > 1) && (sense_vocab->train_items % 100000 == 0)) {
            printf("%lldK%c", sense_vocab->train_items / 1000, 13);
            fflush(stdout);
        }
    }
    SortVocab(sense_vocab);
    if (debug_mode > 0) {
        printf("Lang %d: Sense Vocab size: %lld\n", lang_id, sense_vocab->vocab_size);
        printf("Lang %d: Anchors in train file: %lld\n", lang_id, sense_vocab->train_items);
    }
    sense_vocab->file_size = ftell(fin);
    fclose(fin);
}

void SaveVocab(struct vocab *mono_vocab) {
    long long i;
    FILE *fo = fopen(mono_vocab->save_vocab_file, "wb");
    for (i = 0; i < mono_vocab->vocab_size; i++) fprintf(fo, "%s\t%lld\n", mono_vocab->vocab[i].item, mono_vocab->vocab[i].cn);
    fclose(fo);
}

void SaveVector(struct vocab *mono_vocab, int id){
    long a, b, tmp_a;
    char output_file[MAX_STRING];
    sprintf(output_file, "%s%d", mono_vocab->output_file, id);
    FILE *fo = fopen(output_file, "wb");
    fprintf(fo, "%lld %lld\n", mono_vocab->vocab_size, layer_size);
    // Save the item vectors
    for (a = 0; a < mono_vocab->vocab_size; a++) {
        
        if (mono_vocab->vocab_type==SENSE_VOCAB && shareSyn0==1){
            tmp_a = mono_vocab->vocab[a].entity_index;
            if (tmp_a == -1) continue;
        }
        else
            tmp_a = a;
        fprintf(fo, "%s\t", mono_vocab->vocab[a].item);
        if (binary) for (b = 0; b < layer_size; b++) fwrite(&(mono_vocab->syn0[tmp_a * layer_size + b]), sizeof(real), 1, fo);
        else for (b = 0; b < layer_size; b++) fprintf(fo, "%lf ", mono_vocab->syn0[tmp_a * layer_size + b]);
        
        if(mono_vocab->vocab_type==SENSE_VOCAB){
            if (binary) for (b = 0; b < layer_size; b++) fwrite(&(mono_vocab->syn1neg[a * layer_size + b]), sizeof(real), 1, fo);
            else{
                fprintf(fo, "\n");
                for (b = 0; b < layer_size; b++) fprintf(fo, "%lf ", mono_vocab->syn1neg[a * layer_size + b]);
            }
        }
        
        fprintf(fo, "\n");
    }
    fclose(fo);
}

void LearnVocabFromTrainFile(int model_type, int lang_id){
    if(TEXT_VOCAB == model_type) LearnWordVocabFromTrainFile(lang_id);
    else if(KG_VOCAB == model_type) LearnEntityVocabFromTrainFile(lang_id);
    else if(SENSE_VOCAB == model_type) LearnSenseVocabFromTrainFile(lang_id);
    else printf("no such model type!");
}

void InitNet(struct vocab *mono_vocab) {
    long long a, b;
    unsigned long long next_random = 1;
    real *syn0grad, *syn1negGrad, *syn0delta, *syn1negdelta;
    if (shareSyn0==1 && mono_vocab->vocab_type==SENSE_VOCAB)
        mono_vocab->syn0 = model[KG_VOCAB][mono_vocab->lang].syn0;
    else
        a = posix_memalign((void **)&(mono_vocab->syn0), 128, (long long)mono_vocab->vocab_size * layer_size * sizeof(real));
    if (mono_vocab->syn0 == NULL) {printf("Memory allocation failed\n"); exit(1);}
    if (sgd_mode>0) {
        a = posix_memalign((void **)&syn0grad, 128, (long long)mono_vocab->vocab_size *
                           layer_size * sizeof(real));
        if (syn0grad == NULL) {printf("Memory allocation failed\n"); exit(1);}
        else mono_vocab->syn0Grad = syn0grad;
        a = posix_memalign((void **)&syn1negGrad, 128, (long long)mono_vocab->vocab_size *
                           layer_size * sizeof(real));
        if (syn1negGrad == NULL) {printf("Memory allocation failed\n"); exit(1);}
        else mono_vocab->syn1negGrad= syn1negGrad;
    }
    if (sgd_mode>2){
        a = posix_memalign((void **)&syn0delta, 128, (long long)mono_vocab->vocab_size *
                           layer_size * sizeof(real));
        if (syn0delta == NULL) {printf("Memory allocation failed\n"); exit(1);}
        else mono_vocab->syn0Delta = syn0delta;
        a = posix_memalign((void **)&syn1negdelta, 128, (long long)mono_vocab->vocab_size *
                           layer_size * sizeof(real));
        if (syn1negdelta == NULL) {printf("Memory allocation failed\n"); exit(1);}
        else mono_vocab->syn1negDelta= syn1negdelta;
    }
    if (negative>0) {
        a = posix_memalign((void **)&(mono_vocab->syn1neg), 128, (long long)mono_vocab->vocab_size * layer_size * sizeof(real));
        if (mono_vocab->syn1neg == NULL) {printf("Memory allocation failed\n"); exit(1);}
        for (a = 0; a < mono_vocab->vocab_size; a++) for (b = 0; b < layer_size; b++){
            mono_vocab->syn1neg[a * layer_size + b] = 0;
            if (sgd_mode>0) mono_vocab->syn1negGrad[a * layer_size + b] = 0;
            if (sgd_mode>2) mono_vocab->syn1negDelta[a * layer_size + b] = 0;
        }
    }
    if (shareSyn0!=1 || mono_vocab->vocab_type!=SENSE_VOCAB){
        for (a = 0; a < mono_vocab->vocab_size; a++) for (b = 0; b < layer_size; b++) {
            next_random = next_random * (unsigned long long)25214903917 + 11;
            mono_vocab->syn0[a * layer_size + b] = (((next_random & 0xFFFF) / (real)65536) - 0.5) / layer_size;
            if (sgd_mode>0) mono_vocab->syn0Grad[a * layer_size + b] = 0;
            if (sgd_mode>2) mono_vocab->syn0Delta[a * layer_size + b] = 0;
        }
    }
}

void InitUnigramTable(struct vocab *mono_vocab) {
    int a, i;
    double train_items_pow = 0;
    double d1, power = 0.75;
    mono_vocab->table = (int *)malloc(table_size * sizeof(int));
    for (a = 0; a < mono_vocab->vocab_size; a++) train_items_pow += pow(mono_vocab->vocab[a].cn, power);
    i = 0;
    d1 = pow(mono_vocab->vocab[i].cn, power) / train_items_pow;
    for (a = 0; a < table_size; a++) {
        mono_vocab->table[a] = i;
        if (a / (double)table_size > d1) {
            i++;
            d1 += pow(mono_vocab->vocab[i].cn, power) / train_items_pow;
        }
        if (i >= mono_vocab->vocab_size) i = mono_vocab->vocab_size - 1;
    }
}

void InitModel(int model_type, int lang_id){
    struct vocab *mono_vocab = &model[model_type][lang_id];
    // initialize vocab type
    mono_vocab->vocab_type = model_type;
    mono_vocab->lang = lang_id;
    mono_vocab->min_count = min_count;
    
    mono_vocab->vocab_max_size = 2500000;      //vocab word size is 2.7m
    mono_vocab->vocab_size = 0;
    mono_vocab->train_items = 0;
    mono_vocab->file_size = 0;
    mono_vocab->lang_updates = 0;
    mono_vocab->dump_iters = 0;
    mono_vocab->epoch = 0;
    mono_vocab->vocab_hash_size = 30000000;  // Maximum items in the vocabulary 30m*0.7=21m
    
    mono_vocab->vocab = (struct vocab_item *)calloc(mono_vocab->vocab_max_size, sizeof(struct vocab_item));
    mono_vocab->vocab_hash = (int *)calloc(mono_vocab->vocab_hash_size, sizeof(int));
    
    if (read_mono_vocab_path[lang_id][0]!= 0) ReadVocab(mono_vocab);
    else LearnVocabFromTrainFile(model_type, lang_id);
    if (save_mono_vocab_path[lang_id][0]!= 0) SaveVocab(mono_vocab);
    if (output_path[lang_id][0] == 0) return;
    InitNet(mono_vocab);
    if (negative > 0) InitUnigramTable(mono_vocab);
}

// return 1 or 2 if success, -1 false
int ReadParLine(FILE *fi, long long sen[MAX_PAR_SENT*MAX_SENTENCE_LENGTH], long long entity_index[2], int lang_id[2]) {
    long long index = -1;
    char word[MAX_STRING];
    int sentence_length = 0, cur_lang=-1, par_lang = -1, item_count=0;
    int VOCAB = KG_VOCAB;
    if (shareSyn0!=1) VOCAB = SENSE_VOCAB;
    while (1) {
        ReadItem(word, fi);
        if (feof(fi) || !strcmp(word, "</s>")){
            sen[sentence_length] = -1;
            if (par_lang != -1 && (item_count < 3 || sen[0] <=0) ) par_lang = -1;
            break;
        }
        if (!strcmp(word, "1") || !strcmp(word, "2")) par_lang = atoi(word);
        if (par_lang==-1) continue;
        
        if (item_count<3+MAX_PAR_SENT){
            if (!strcmp(word, "</t>")) {
                if (item_count>=3 && sentence_length>0 && sen[sentence_length-1]>0) {
                    sen[sentence_length++] = 0;
                    if (sentence_length >= MAX_PAR_SENT*MAX_SENTENCE_LENGTH)
                        sentence_length = MAX_PAR_SENT*MAX_SENTENCE_LENGTH - 1;
                }
                item_count++;
                continue;
            }
            
            if (item_count == 0)
                cur_lang = lang_id[par_lang-1];
            else if (item_count == 1 || item_count == 2)
                entity_index[item_count-1] = SearchVocab(word, &model[VOCAB][cur_lang]);
            else{
                index = SearchVocab(word, &model[TEXT_VOCAB][cur_lang]);
                if (index == -1 || index == 0) continue;
                if (sample > 0) {
                    real ran = (sqrt(model[TEXT_VOCAB][cur_lang].vocab[index].cn / (sample * model[TEXT_VOCAB][cur_lang].train_items)) + 1) * (sample * model[TEXT_VOCAB][cur_lang].train_items) / model[TEXT_VOCAB][cur_lang].vocab[index].cn;
                    g_next_random = g_next_random * (unsigned long long)25214903917 + 11;
                    if (ran < (g_next_random & 0xFFFF) / (real)65536) continue;
                }
                sen[sentence_length] = index;
                sentence_length++;
                if (sentence_length >= MAX_PAR_SENT*MAX_SENTENCE_LENGTH)
                    sentence_length = MAX_PAR_SENT*MAX_SENTENCE_LENGTH - 1;
            }
        }
    }
    return par_lang;
}

// cross lingual alignment
/* Read parallel sentences into *sen for all languages from fi
 * fi point to the file: each two line contains 2 language sentences separated by tab
 1 \t ent0_id \t ent1_id \t sent ...
 2 \t ent2_id \t ent3_id \t sent ...
 *sen separated by 0, end by -1
 *entity_index, could be -1
 return n>0 if read n lines success, -n false*/
int ReadSent(FILE *fi, long long sen[2][MAX_PAR_SENT*MAX_SENTENCE_LENGTH], long long entity_index[4], int lang_id[2]) {

    int par_lang=-1,res = -1, line_count = 0;

    while (1) {
        par_lang = ReadParLine(fi, sen[0], entity_index, lang_id);
        if (feof(fi)) break;
        line_count ++;
        if (par_lang == 1) break;
    }
    par_lang = ReadParLine(fi, sen[1], &entity_index[2], lang_id);
    line_count ++;
    if (par_lang == 2) res = 1;
    return res * line_count;
}

// cross links between 2 languages
void readCrossLinks(char *cross_link_file, int lang_id[2]){
    int a, item_count=0, clink[2], entity_index, num_clink, line_count=0, tmp_clink_idx, tmp_clink, total_num = 0;
    char item[MAX_STRING];
    bool hasInvalidEntity = false;
    FILE *fin = fopen(cross_link_file, "rb");
    if (fin == NULL) {
        printf("ERROR: training data file not found!\n");
        exit(1);
    }
    fscanf(fin, "%d", &num_clink);
    num_clink += 1;
    for(a=0;a<2;a++) clink[a] = -1;
    while (1) {
        ReadItem(item, fin);
        if (feof(fin)) break;
        if (!strcmp(item, "</t>")) continue;
        if (!strcmp(item, "</s>")) {
            if (item_count == 2 && !hasInvalidEntity){
                tmp_clink_idx = model[KG_VOCAB][lang_id[0]].vocab[clink[0]].index;
                if (tmp_clink_idx!=-1){
                    tmp_clink = cross_links[lang_id[0]][tmp_clink_idx];
                    if (tmp_clink == clink[0]){
                        cross_links[lang_id[1]][tmp_clink_idx] = clink[1];
                        model[KG_VOCAB][lang_id[1]].vocab[clink[1]].index = tmp_clink_idx;
                        total_num ++;
                    }
                }
                else{
                    cross_links[lang_id[0]][line_count] = clink[0];
                    model[KG_VOCAB][lang_id[0]].vocab[clink[0]].index = line_count;
                    cross_links[lang_id[1]][line_count] = clink[1];
                    model[KG_VOCAB][lang_id[1]].vocab[clink[1]].index = line_count;
                    line_count++;
                    total_num ++;
                }
            }
            item_count = 0;
            hasInvalidEntity = false;
            continue;
        }
        if (item_count < 2){
            entity_index = SearchVocab(item, &model[KG_VOCAB][lang_id[item_count]]);
            clink[item_count] = entity_index;
            if (entity_index==-1) hasInvalidEntity = true;
        }
        item_count++;
    }
    fclose(fin);
    max_num_clink += line_count;
    if (debug_mode > 0) {
        printf("Totally %d cross links! Read %d cross links from lang %d to lang %d from file: %s!\n",max_num_clink, total_num, lang_id[0], lang_id[1], cross_link_file);
    }
}

int readContextLines(char *multi_context_file, int lang_id[2]){
    int line_count = 0, res;
    long long par_sen[2][MAX_PAR_SENT*MAX_SENTENCE_LENGTH];
    long long par_entity[4];
    // initialize the parallel context number
    FILE *fin = fopen(multi_context_file, "rb");
    while(1){
        res = ReadSent(fin, par_sen, par_entity, lang_id);
        if (feof(fin)) break;
        if (res < 0) continue;
        line_count += res;
    }
    fclose(fin);
    if (debug_mode > 0) {
        printf("Read %d parallel sents from lang %d to lang %d from file: %s!\n", line_count, lang_id[0], lang_id[1], multi_context_file);
    }
    return line_count;
}

void InitMultiModel(){
    int max_num = 1500000, lang_id[2];            // 1m, max num clinks
    for(int i = 0; i < NUM_LANG; i++){
        cross_links[i] = (int *)malloc(max_num * sizeof(int));
        _clr(cross_links[i],max_num);
    }
    lang_id[0] = 0;
    for (int i=0;i<NUM_LANG-1;i++){
        lang_id[1] = i+1;
        if(cross_link_file[i][0]!=0)
            readCrossLinks(cross_link_file[i], lang_id);
        if(multi_context_file[i][0]!=0){
            par_line_num[i] = readContextLines(multi_context_file[i], lang_id);
            par_actual_line[i] = 0;
        }
    }
    for (int i=0;i<NUM_LANG;i++)
        cross_links[i] = (int *)realloc(cross_links[i], max_num_clink * sizeof(int));
}

void UpdateEmbeddings(real *embeddings, real *rms_grads, real *rms_delta, int offset, int num_updates, real *deltas, real weight) {
    int a;
    real step, epsilon = 1e-6, xling2 = 0.999;
    for (a = 0; a < num_updates; a++) {
        // sgd_mode: 0:sgd; 1:adagrad; 2:rmsprop; 3:adadelta; 4: adam
        
        if (sgd_mode==4){
            rms_grads[offset + a] = xling * rms_grads[offset + a] + (1-xling) * deltas[a];
            rms_delta[offset + a] = xling2 * rms_delta[offset + a] + (1-xling2) * deltas[a] * deltas[a];
            step = (alpha / fmax(epsilon, sqrt(rms_delta[offset + a]))) * rms_grads[offset + a];
        }
        else if (sgd_mode==2 || sgd_mode == 3) {
            rms_grads[offset + a] = xling * rms_grads[offset + a] + (1-xling) * deltas[a] * deltas[a];
            // Use Adadelta for automatic learning rate selection
            if (sgd_mode==2)
                //rms prop
                step = (alpha / fmax(epsilon, sqrt(rms_grads[offset + a]))) * deltas[a];
            else{
                step = fmax(epsilon, rms_delta[offset + a])/fmax(epsilon, sqrt(rms_grads[offset + a])) * deltas[a];
                rms_delta[offset + a] = xling * rms_delta[offset + a] + (1-xling) * step * step;
            }
        }
        else if (sgd_mode==1){
            // Use Adagrad for automatic learning rate selection
            rms_grads[offset + a] += (deltas[a] * deltas[a]);
            step = (alpha / fmax(epsilon, sqrt(rms_grads[offset + a]))) * deltas[a];
        }
        else {
            // Regular SGD
            step = alpha * deltas[a];
        }
        if (step != step) {
            printf("ERROR: step == NaN");
        }
        step = step * weight;
        if (CLIP_UPDATES != 0) {
            if (step > CLIP_UPDATES) step = CLIP_UPDATES;
            if (step < -CLIP_UPDATES) step = -CLIP_UPDATES;
        }
        embeddings[offset + a] += step;
    }
}

void resetSenseCluster(int lang_id){
    long long a,c;
    struct vocab *tmp_model = &model[SENSE_VOCAB][lang_id];
    for (a = 0; a < tmp_model->vocab_size; a++){
        //sense cluster
        if (tmp_model->vocab[a].index > 0){
            for (c=0;c<layer_size;c++)
                tmp_model->syn1neg[a*layer_size+c] /= tmp_model->vocab[a].index;
            tmp_model->vocab[a].index = 1;
        }
    }
}

void *TrainTextModelThread(void *id) {
    long long a, b, d, cw, word_index=-1, last_word_index, sentence_length = 0, sentence_position = 0;
    long long word_count = 0, anchor_count = 0, anchor_position=0, last_word_count = 0, sen[MAX_SENTENCE_LENGTH + 1], all_train_words;
    long long l1, l2, c, target, label = 0;
    int lang_id = (long long)id / num_threads-NUM_LANG, thread_id = (long long)id % num_threads;
    unsigned long long next_random = (long long)thread_id;
    int anchor_pos = -1, word_begin[MAX_NUM_MENTION], mention_length = 1;
    char item[MAX_STRING], tmp_word[MAX_STRING], word[MAX_STRING], entity[MAX_STRING], out_str[MAX_STRING];
    size_t tmp_word_len = 0;
    
    real f, g;
    clock_t now;
    real *neu1 = (real *)calloc(layer_size, sizeof(real));
    real *neu1e = (real *)calloc(layer_size, sizeof(real));
    real *syn1negDelta = (real *)calloc(layer_size, sizeof(real));
    
    //context vector
    real *tmp_context_vec = (real *)calloc(layer_size, sizeof(real));
    struct anchor_item *anchors = (struct anchor_item *)calloc(MAX_SENTENCE_LENGTH, sizeof(struct anchor_item));
    
    struct vocab *mono_words = &model[TEXT_VOCAB][lang_id];
    struct vocab *mono_entities = &model[KG_VOCAB][lang_id];
    struct vocab *mono_senses = &model[SENSE_VOCAB][lang_id];
    
    FILE *fi = fopen(mono_words->train_file, "rb");
    if (!EARLY_STOP)
        // If two languages have different amounts of training data,
        // recycle the smaller language data while there is more data
        // for the other language
        all_train_words = max_train_words * NUM_EPOCHS * NUM_LANG;
    else {
        all_train_words = EARLY_STOP;
    }
    if (dump_every < 0) {
        dump_every = max_train_words / abs(dump_every);
    }
    fseek(fi, mono_words->file_size / (long long)num_threads * (long long)thread_id, SEEK_SET);
    for(a=0;a<MAX_NUM_MENTION;a++) word_begin[a] = 0;
    while (1) {
        if (word_count - last_word_count > 10000) {
            word_count_actual += word_count - last_word_count;
            last_word_count = word_count;
            if ((debug_mode > 1)) {
                now = clock();
                sprintf(out_str, "Alpha: %f (%d)  Progress: %.2f%% (", alpha, sgd_mode, word_count_actual / (real)(all_train_words + 1) * 100);
                for (int l = 0;l <NUM_LANG;l++)
                    sprintf(out_str, "%sKG%d: %.2fM (%lld), ", out_str, l+1, model[KG_VOCAB][l].lang_updates / (real)1000000, model[KG_VOCAB][l].epoch);
                for (int l=0;l<NUM_LANG;l++)
                    sprintf(out_str, "%sL%d: %.2fM (%lld), ",out_str, l+1, model[TEXT_VOCAB][l].lang_updates / (real)1000000, model[TEXT_VOCAB][l].epoch);
                for (int l=0;l<NUM_LANG-1;l++)
                    sprintf(out_str, "%sL1L%d: %.2fM (%d) err: %.4f ", out_str,l+2, par_actual_line[l] / (real)1000000, par_epoch[l], par_err[l]);
                printf("%c%sWords/sec: %.2fK  ", 13, out_str,
                       word_count_actual / ((real)(now - start + 1) /
                                            (real)CLOCKS_PER_SEC * 1000));
                fflush(stdout);
            }
            if (sgd_mode==0) {
                if (word_count_actual < (all_train_words + 1)) {
                    alpha = starting_alpha *
                    (1.0 - word_count_actual / (real)(all_train_words + 1));
                } else alpha = starting_alpha * 0.0001;
                //if (alpha < starting_alpha * 0.0001) alpha = starting_alpha * 0.0001;
            }
        }
        if (sentence_length == 0) {
            anchor_count = 0;
            while(1){
                anchor_pos = ReadText(item, fi);
                if (feof(fi)) break;
                
                if (anchor_pos>=0){
                    anchors[anchor_count].start_pos = sentence_length;
                }
                
                if(anchor_pos > 0){
                    tmp_word_len = strlen(item)-anchor_pos;
                    strncpy(word, &item[anchor_pos], sizeof(char)*tmp_word_len);
                    strncpy(entity, item, sizeof(char)*(anchor_pos-1));
                    entity[anchor_pos-1] = 0;
                }
                else{
                    tmp_word_len = strlen(item);
                    strncpy(word, item, sizeof(char)*tmp_word_len);
                }
                word[tmp_word_len] = 0;
                if (anchor_pos==0) strcpy(entity, word);
                
                mention_length = 1;
                if (anchor_pos != -1){
                    mention_length = SplitMention(word_begin, word);
                }
                if (mention_length<=0) continue;
                for(b=0;b<mention_length;b++){
                    if (mention_length > 1){
                        if (b+1 < mention_length)
                            tmp_word_len = word_begin[b+1]-1-word_begin[b];
                        else
                            tmp_word_len = strlen(&word[word_begin[b]]);
                        strncpy(tmp_word, &word[word_begin[b]], sizeof(char)*tmp_word_len);
                        tmp_word[tmp_word_len]=0;
                        word_index = SearchVocab(tmp_word, mono_words);
                    }
                    else
                        word_index = SearchVocab(word, mono_words);
                    if (word_index == -1) continue;
                    word_count++;
                    
                    mono_words->lang_updates ++;
                    
                    if (mono_words->lang_updates > 0 &&
                        mono_words->lang_updates % mono_words->train_items == 0) {
                        mono_words->epoch++;
                        resetSenseCluster(lang_id);
                    }
                    
                    if (dump_every > 0)
                        if (mono_words->lang_updates % dump_every == 0){
                            SaveVector(mono_words,mono_words->dump_iters++);
                            SaveVector(mono_senses,mono_senses->dump_iters++);
                            SaveVector(mono_entities,mono_entities->dump_iters++);
                        }
                    if (word_index == 0) break;
                    
                    // The subsampling randomly discards frequent words while keeping the ranking same
                    if (sample > 0) {
                        real ran = (sqrt(mono_words->vocab[word_index].cn / (sample * mono_words->train_items)) + 1) * (sample * mono_words->train_items) / mono_words->vocab[word_index].cn;
                        next_random = next_random * (unsigned long long)25214903917 + 11;
                        if (ran < (next_random & 0xFFFF) / (real)65536) continue;
                    }
                    sen[sentence_length] = word_index;
                    sentence_length++;
                    if (sentence_length >= MAX_SENTENCE_LENGTH) break;
                }
                if(anchor_pos>=0 && b >= mention_length-1){
                    anchors[anchor_count].length = sentence_length - anchors[anchor_count].start_pos;
                    if(anchors[anchor_count].length>0){
                        anchors[anchor_count].entity_index = SearchVocab(entity, &model[KG_VOCAB][lang_id]);
                        anchors[anchor_count].sense_index = SearchVocab(entity, &model[SENSE_VOCAB][lang_id]);
                        if(anchors[anchor_count].entity_index!=-1 && anchors[anchor_count].sense_index!=-1){
                            anchor_count++;
                            if(anchor_count >= MAX_SENTENCE_LENGTH) anchor_count--;
                        }
                    }
                }
                if(word_index == 0 || sentence_length >= MAX_SENTENCE_LENGTH) break;
            }
            sentence_position = 0;
        }
        if (mono_words->lang_updates > all_train_words/ NUM_LANG) break;
        if (feof(fi) || (word_count > mono_words->train_items / num_threads)) {
            word_count_actual += word_count - last_word_count;
            word_count = 0;
            last_word_count = 0;
            sentence_length = 0;
            for(a=0;a<MAX_NUM_MENTION;a++) word_begin[a] = 0;
            fseek(fi, mono_words->file_size / (long long)num_threads * (long long)thread_id, SEEK_SET);
            continue;
        }
        if (EARLY_STOP) {
            if (word_count_actual > EARLY_STOP) {
                printf("EARLY STOP point reached (thread %lld)\n", (long long)id);
                break;
            }
        }
        
        word_index = sen[sentence_position];
        if (word_index == -1) continue;
        for (c = 0; c < layer_size; c++) neu1[c] = 0;
        for (c = 0; c < layer_size; c++) neu1e[c] = 0;
        next_random = next_random * (unsigned long long)25214903917 + 11;
        b = next_random % window;
        //train skip-gram
        for (a = b; a < window * 2 + 1 - b; a++) if (a != window) {
            c = sentence_position - window + a;
            if (c < 0) continue;
            if (c >= sentence_length) continue;
            last_word_index = sen[c];
            if (last_word_index == -1) continue;
            l1 = last_word_index * layer_size;
            for (c = 0; c < layer_size; c++) neu1e[c] = 0;
            // NEGATIVE SAMPLING
            if (negative > 0) for (d = 0; d < negative + 1; d++) {
                if (d == 0) {
                    target = word_index;
                    label = 1;
                } else {
                    next_random = next_random * (unsigned long long)25214903917 + 11;
                    target = mono_words->table[(next_random >> 16) % table_size];
                    if (target == 0) target = next_random % (mono_words->vocab_size - 1) + 1;
                    if (target == word_index) continue;
                    label = 0;
                }
                l2 = target * layer_size;
                f = 0;
                for (c = 0; c < layer_size; c++) f += mono_words->syn0[c + l1] * mono_words->syn1neg[c + l2];
                if (f > MAX_EXP) g = (label - 1);
                else if (f < -MAX_EXP) g = (label - 0);
                else g = (label - expTable[(int)((f + MAX_EXP) * (EXP_TABLE_SIZE / MAX_EXP / 2))]);
                for (c = 0; c < layer_size; c++) neu1e[c] += g * mono_words->syn1neg[c + l2];
                // for (c = 0; c < layer_size; c++) mono_words->syn1neg[c + l2] += g * mono_words->syn0[c + l1];
                for (c = 0; c < layer_size; c++) syn1negDelta[c] = g * mono_words->syn0[c + l1];
                UpdateEmbeddings(mono_words->syn1neg, mono_words->syn1negGrad, mono_words->syn1negDelta, l2, layer_size,syn1negDelta, +1);
            }
            // Learn weights input -> hidden
            // for (c = 0; c < layer_size; c++) mono_words->syn0[c + l1] += neu1e[c];
            UpdateEmbeddings(mono_words->syn0, mono_words->syn0Grad, mono_words->syn0Delta, l1, layer_size, neu1e, +1);
        }
        
        sentence_position++;
            
        if (sentence_position >= sentence_length) {
            // train word embedding finished! start train mention sense embedding ...
            if (anchor_count > 0 && has_sense){
                for(anchor_position=0;anchor_position<anchor_count;anchor_position++){
                    //reset context vec
                    for (c = 0; c < layer_size; c++) tmp_context_vec[c] = 0;
                    cw = 0;
                    
                    // use context words and mention sense to predict entity
                    for (c = 0; c < layer_size; c++) neu1[c] = 0;
                    for (c = 0; c < layer_size; c++) neu1e[c] = 0;
                    next_random = next_random * (unsigned long long)25214903917 + 11;
                    b = next_random % window;
                    sentence_position = anchors[anchor_position].start_pos;
                    word_index = anchors[anchor_position].entity_index;
                    if (word_index == -1) continue;
                    
                    //train skip-gram
                    for (a = b; a < window * 2 + 1 - b; a++)
                        if(a == window)
                            sentence_position = anchors[anchor_position].start_pos + anchors[anchor_position].length-1;
                        else {
                            c = sentence_position - window + a;
                            if (c < 0) continue;
                            if (c >= sentence_length) continue;
                            last_word_index = sen[c];
                            if (last_word_index == -1) continue;
                            for (c = 0; c < layer_size; c++) tmp_context_vec[c] += mono_words->syn0[last_word_index * layer_size + c];
                            cw ++;
                            l1 = last_word_index * layer_size;
                            for (c = 0; c < layer_size; c++) neu1e[c] = 0;
                            // NEGATIVE SAMPLING
                            if (negative > 0) for (d = 0; d < negative + 1; d++) {
                                if (d == 0) {
                                    target = word_index;
                                    label = 1;
                                } else {
                                    next_random = next_random * (unsigned long long)25214903917 + 11;
                                    target = mono_entities->table[(next_random >> 16) % table_size];
                                    if (target == 0) target = next_random % (mono_entities->vocab_size - 1) + 1;
                                    if (target == word_index) continue;
                                    label = 0;
                                }
                                l2 = target * layer_size;
                                f = 0;
                                for (c = 0; c < layer_size; c++) f += mono_words->syn0[c + l1] * mono_entities->syn0[c + l2];
                                if (f > MAX_EXP) g = (label - 1);
                                else if (f < -MAX_EXP) g = (label - 0);
                                else g = (label - expTable[(int)((f + MAX_EXP) * (EXP_TABLE_SIZE / MAX_EXP / 2))]);
                                for (c = 0; c < layer_size; c++) neu1e[c] += g * mono_entities->syn0[c + l2];
                                // for (c = 0; c < layer_size; c++) mono_entities->syn1neg[c + l2] += g * mono_words->syn0[c + l1];
                                for (c = 0; c < layer_size; c++) syn1negDelta[c] = g * mono_words->syn0[c + l1];
                                UpdateEmbeddings(mono_entities->syn0, mono_entities->syn0Grad, mono_entities->syn0Delta, l2, layer_size,syn1negDelta, +1);
                            }
                            // Learn weights input -> hidden
                            //for (c = 0; c < layer_size; c++) mono_words->syn0[c + l1] += neu1e[c];
                            UpdateEmbeddings(mono_words->syn0, mono_words->syn0Grad, mono_words->syn0Delta, l1, layer_size, neu1e, +1);
                        }
                    //also use sense embedding to predict the entity
                    last_word_index = anchors[anchor_position].sense_index;
                    if (last_word_index == -1) continue;
                    //update cluster center mu and cluster size
                    if(cw>0){
                        for (c = 0; c < layer_size; c++) mono_senses->syn1neg[last_word_index * layer_size + c] += (tmp_context_vec[c]/cw);
                        mono_senses->vocab[last_word_index].index += 1;
                    }
                    if (shareSyn0 != 1){
                        l1 = last_word_index * layer_size;
                        for (c = 0; c < layer_size; c++) neu1e[c] = 0;
                        // NEGATIVE SAMPLING
                        if (negative > 0) for (d = 0; d < negative + 1; d++) {
                            if (d == 0) {
                                target = word_index;
                                label = 1;
                            } else {
                                next_random = next_random * (unsigned long long)25214903917 + 11;
                                target = mono_entities->table[(next_random >> 16) % table_size];
                                if (target == 0) target = next_random % (mono_entities->vocab_size - 1) + 1;
                                if (target == word_index) continue;
                                label = 0;
                            }
                            l2 = target * layer_size;
                            f = 0;
                            for (c = 0; c < layer_size; c++) f += mono_senses->syn0[c + l1] * mono_entities->syn1neg[c + l2];
                            if (f > MAX_EXP) g = (label - 1);
                            else if (f < -MAX_EXP) g = (label - 0);
                            else g = (label - expTable[(int)((f + MAX_EXP) * (EXP_TABLE_SIZE / MAX_EXP / 2))]);
                            for (c = 0; c < layer_size; c++) neu1e[c] += g * mono_entities->syn1neg[c + l2];
                            //for (c = 0; c < layer_size; c++) mono_entities->syn1neg[c + l2] += g * mono_senses->syn0[c + l1];
                            for (c = 0; c < layer_size; c++) syn1negDelta[c] = g * mono_senses->syn0[c + l1];
                            UpdateEmbeddings(mono_entities->syn1neg, mono_entities->syn1negGrad, mono_entities->syn1negDelta, l2, layer_size,syn1negDelta, +1);
                        }
                        // Learn weights input -> hidden
                        // for (c = 0; c < layer_size; c++) mono_senses->syn0[c + l1] += neu1e[c];
                        UpdateEmbeddings(mono_senses->syn0, mono_senses->syn0Grad, mono_senses->syn0Delta, l1, layer_size, neu1e, +1);
                    }
                    
                }
            }
            
            sentence_length = 0;
            continue;
        }
    }
    fclose(fi);
    free(neu1);
    free(neu1e);
    MONO_DONE_TRAINING++;
    pthread_exit(NULL);
}

void *TrainKgModelThread(void *id) {
    long long d, entity_index, head_entity_index = -1, tmp_head_entity_index=-1, cross_index=-1, line_entity_count = 0, is_read_head = 1, sentence_length = 0, sentence_position = 0;
    long long entity_count = 0, last_entity_count = 0, sen[MAX_SENTENCE_LENGTH + 1];
    long long l1, l2, c, target, label;
    int lang_id = (long long)id / num_threads, thread_id = (long long)id % num_threads;
    
    unsigned long long next_random = (long long)thread_id;
    char entity[MAX_STRING];
    real f, g;
    real *neu1 = (real *)calloc(layer_size, sizeof(real));
    real *neu1e = (real *)calloc(layer_size, sizeof(real));
    real *syn1negDelta = (real *)calloc(layer_size, sizeof(real));
    
    struct vocab *mono_entities = &model[KG_VOCAB][lang_id];
    struct vocab *tmp_mono_entities;
    FILE *fi = fopen(mono_entities->train_file, "rb");
    
    fseek(fi, mono_entities->file_size / (long long)num_threads * (long long)thread_id, SEEK_SET);
    head_entity_index = -1;
    is_read_head = 1;
    line_entity_count = 0;
    while (MONO_DONE_TRAINING < NUM_LANG * num_threads) {
        if (entity_count - last_entity_count > 10000) {
            entity_count_actual += entity_count - last_entity_count;
            last_entity_count = entity_count;
            
        }
        if (sentence_length == 0) {
            while(1){
                ReadItem(entity, fi);
                if (feof(fi)) break;
                if (!strcmp(entity, "</t>")) continue;
                entity_count ++;
                mono_entities->lang_updates ++;
                
                if (mono_entities->lang_updates > 0 &&
                    mono_entities->lang_updates % mono_entities->train_items == 0) {
                    mono_entities->epoch++;
                }
                
                line_entity_count++;
                if(is_read_head==1){
                    head_entity_index = SearchVocab(entity, mono_entities);
                    if(head_entity_index==0) line_entity_count = 0;
                    if(head_entity_index>0 && line_entity_count==1) is_read_head=0;
                    else head_entity_index = -1;
                    continue;
                }
                else if(head_entity_index!=-1){
                    entity_index = SearchVocab(entity, mono_entities);
                    if (entity_index == -1) continue;
                    if (entity_index == 0) {
                        line_entity_count = 0;
                        is_read_head=1;
                        break;
                    }
                }
                else {is_read_head=1;continue;}
                if (sample > 0) {
                    real ran = (sqrt(mono_entities->vocab[entity_index].cn / (sample * mono_entities->train_items)) + 1) * (sample * mono_entities->train_items) / mono_entities->vocab[entity_index].cn;
                    next_random = next_random * (unsigned long long)25214903917 + 11;
                    if (ran < (next_random & 0xFFFF) / (real)65536) continue;
                }
                sen[sentence_length] = entity_index;
                sentence_length++;
                if (sentence_length >= MAX_SENTENCE_LENGTH) break;
            }
            sentence_position = 0;
        }
        // kg training is almost 6 times faster than text
        // if (mono_entities->lang_updates/6 > all_train_items/(NUM_MODEL-1) / NUM_LANG) break;
        if (feof(fi) || (entity_count > mono_entities->train_items / num_threads)) {
            entity_count_actual += entity_count - last_entity_count;
            fseek(fi, mono_entities->file_size / (long long)num_threads * (long long)thread_id, SEEK_SET);
            head_entity_index = -1;
            is_read_head = 1;
            line_entity_count = 0;
            sentence_length = 0;
            entity_count = 0;
            last_entity_count = 0;
            continue;
        }
        for (c = 0; c < layer_size; c++) neu1[c] = 0;
        for (c = 0; c < layer_size; c++) neu1e[c] = 0;
        //train skip-gram
        for (; sentence_position<sentence_length; sentence_position++){
            entity_index = sen[sentence_position];
            if (entity_index == -1) continue;
            l1 = entity_index * layer_size;
            for (c = 0; c < layer_size; c++) neu1e[c] = 0;
            // NEGATIVE SAMPLING
            if (negative > 0) for (d = 0; d < negative + 1; d++) {
                if (d == 0) {
                    target = head_entity_index;
                    label = 1;
                } else {
                    next_random = next_random * (unsigned long long)25214903917 + 11;
                    target = mono_entities->table[(next_random >> 16) % table_size];
                    if (target == 0) target = next_random % (mono_entities->vocab_size - 1) + 1;
                    if (target == head_entity_index) continue;
                    label = 0;
                }
                l2 = target * layer_size;
                f = 0;
                for (c = 0; c < layer_size; c++) f += mono_entities->syn0[c + l1] * mono_entities->syn1neg[c + l2];
                // We multiply with the learning rate in UpdateEmbeddings()
                if (f > MAX_EXP) g = (label - 1);
                else if (f < -MAX_EXP) g = (label - 0);
                else g = (label - expTable[(int)((f + MAX_EXP) * (EXP_TABLE_SIZE / MAX_EXP / 2))]);
                for (c = 0; c < layer_size; c++) neu1e[c] += g * mono_entities->syn1neg[c + l2];
                //for (c = 0; c < layer_size; c++) mono_entities->syn1neg[c + l2] += g * mono_entities->syn0[c + l1];
                for (c = 0; c < layer_size; c++) syn1negDelta[c] = g * mono_entities->syn0[c + l1];
                UpdateEmbeddings(mono_entities->syn1neg, mono_entities->syn1negGrad, mono_entities->syn1negDelta, l2, layer_size, syn1negDelta, +1);
            }
            // Learn weights input -> hidden
            // for (c = 0; c < layer_size; c++) mono_entities->syn0[c + l1] += neu1e[c];
            UpdateEmbeddings(mono_entities->syn0, mono_entities->syn0Grad, mono_entities->syn0Delta, l1, layer_size, neu1e, +1);
        }
        //train cross lingual links
        cross_index = mono_entities->vocab[head_entity_index].index;
        if (NUM_LANG >=2 && cross_model_weight>0 && cross_index>=0){
            for (c = 0; c < layer_size; c++) neu1e[c] = 0;
            for (int k=0;k<NUM_LANG;k++){
                if (k==lang_id) continue;
                tmp_head_entity_index = cross_links[k][cross_index];
                if (tmp_head_entity_index==-1) continue;
                tmp_mono_entities = &model[KG_VOCAB][k];
                //train skip-gram
                for (; sentence_position<sentence_length; sentence_position++){
                    entity_index = sen[sentence_position];
                    if (entity_index == -1) continue;
                    l1 = entity_index * layer_size;
                    for (c = 0; c < layer_size; c++) neu1e[c] = 0;
                    // NEGATIVE SAMPLING
                    if (negative > 0) for (d = 0; d < negative + 1; d++) {
                        if (d == 0) {
                            target = tmp_head_entity_index;
                            label = 1;
                        } else {
                            next_random = next_random * (unsigned long long)25214903917 + 11;
                            target = tmp_mono_entities->table[(next_random >> 16) % table_size];
                            if (target == 0) target = next_random % (tmp_mono_entities->vocab_size - 1) + 1;
                            if (target == tmp_head_entity_index) continue;
                            label = 0;
                        }
                        l2 = target * layer_size;
                        f = 0;
                        for (c = 0; c < layer_size; c++) f += mono_entities->syn0[c + l1] * tmp_mono_entities->syn1neg[c + l2];
                        if (f > MAX_EXP) g = (label - 1);
                        else if (f < -MAX_EXP) g = (label - 0);
                        else g = (label - expTable[(int)((f + MAX_EXP) * (EXP_TABLE_SIZE / MAX_EXP / 2))]);
                        for (c = 0; c < layer_size; c++) neu1e[c] += g * tmp_mono_entities->syn1neg[c + l2];
                        // for (c = 0; c < layer_size; c++) tmp_mono_entities->syn1neg[c + l2] += g * mono_entities->syn0[c + l1];
                        for (c = 0; c < layer_size; c++) syn1negDelta[c] = g * mono_entities->syn0[c + l1];
                        UpdateEmbeddings(tmp_mono_entities->syn1neg, tmp_mono_entities->syn1negGrad, tmp_mono_entities->syn1negDelta, l2, layer_size, syn1negDelta, +1);
                    }
                    // Learn weights input -> hidden
                    // for (c = 0; c < layer_size; c++) mono_entities->syn0[c + l1] += neu1e[c];
                    UpdateEmbeddings(mono_entities->syn0, mono_entities->syn0Grad, mono_entities->syn0Delta, l1, layer_size, neu1e, +1);
                }   // end train
            }   // end lang
        }
        
        sentence_length = 0;
    }
    fclose(fi);
    free(neu1);
    free(neu1e);
    pthread_exit(NULL);
}

void normalizeVec(real *syn, long long vocab_size){
    real len=0;
    for (int i=0;i<vocab_size;i++){
        for (int j=0;j<layer_size;j++)
            len += syn[i*layer_size+j] * syn[i*layer_size+j];
        len = sqrtf(len);
        if (len > 0)
            for (int j=0;j<layer_size;j++)
                syn[i*layer_size+j] /= len;
    }
}

//batch normalization
void normalize(){
    
    for (int i=0;i<NUM_MODEL;i++){
        if (i == SENSE_VOCAB && shareSyn0==1) continue;
        for (int j=0;j<NUM_LANG;j++){
            normalizeVec(model[i][j].syn0, model[i][j].vocab_size);
            if (i != SENSE_VOCAB)
                normalizeVec(model[i][j].syn1neg, model[i][j].vocab_size);
        }
    }
}

// compute similarity
real similarity(real *vec1, real *vec2){
    real dist = 0.0;
    real len_v1 = 0, len_v2 = 0, len_v = 0;
    long a;
    // cosine similarity
    if (sim_mode==0){
        for (a = 0; a < layer_size; a++){
            len_v1 += vec1[a] * vec1[a];
            len_v2 += vec2[a] * vec2[a];
        }
        len_v1 = sqrt(len_v1);
        len_v2 = sqrt(len_v2);
        len_v = len_v1 * len_v2;
        if (len_v > 0) {
            for (a = 0; a < layer_size; a++)
                dist += vec1[a] * vec2[a] / len_v;
            dist = (dist*rho+1)/2;      // (-1,1) --> (0,1), rho for smooth
        }
    }
    else{
        // inner product similarity
        for (int a = 0; a < layer_size; a++)
            dist += vec1[a] * vec2[a];
        dist *= rho;
        if (dist>MAX_EXP) dist = MAX_EXP;
        if (dist<-MAX_EXP) dist = -MAX_EXP;
        dist = expTable[(int)((dist + MAX_EXP) * (EXP_TABLE_SIZE / MAX_EXP / 2))];
    }
    return dist;
}

void UpdateSquaredError(long long sen[2][MAX_PAR_SENT*MAX_SENTENCE_LENGTH],real attention[2][MAX_PAR_SENT*MAX_SENTENCE_LENGTH],int w_count[2], int lang_id[2], real *delta, real weight) {
    int d, offset;
    
    // To minimize squared error:
    // delta = d .5*|| e - f ||^2 = ±(e - f)
    // d/den = +delta
    for (d = 0; d < MAX_PAR_SENT*MAX_SENTENCE_LENGTH; d++) {
        if (sen[0][d]==-1) break;
        if (sen[0][d]==0) continue;
        offset = layer_size * sen[0][d];
        // update in -d/den = -delta direction
        if (attention[0][0] < 0)
            UpdateEmbeddings(model[TEXT_VOCAB][lang_id[0]].syn0, model[TEXT_VOCAB][lang_id[0]].syn0Grad, model[TEXT_VOCAB][lang_id[0]].syn0Delta, offset, layer_size, delta, -weight);
        else
            UpdateEmbeddings(model[TEXT_VOCAB][lang_id[0]].syn0, model[TEXT_VOCAB][lang_id[0]].syn0Grad, model[TEXT_VOCAB][lang_id[0]].syn0Delta, offset, layer_size, delta, -attention[0][d]*w_count[0]*weight);
    }
    // d/df = -delta
    for (d = 0; d < MAX_PAR_SENT*MAX_SENTENCE_LENGTH; d++) {
        if (sen[1][d]==-1) break;
        if (sen[1][d]==0) continue;
        offset = layer_size * sen[1][d];
        // update in -d/df = +delta direction
        if (attention[1][0] < 0)
            UpdateEmbeddings(model[TEXT_VOCAB][lang_id[1]].syn0,model[TEXT_VOCAB][lang_id[1]].syn0Grad, model[TEXT_VOCAB][lang_id[1]].syn0Delta, offset, layer_size, delta, weight);
        else
            UpdateEmbeddings(model[TEXT_VOCAB][lang_id[1]].syn0,model[TEXT_VOCAB][lang_id[1]].syn0Grad, model[TEXT_VOCAB][lang_id[1]].syn0Delta, offset, layer_size, delta, attention[1][d]*w_count[1]*weight);
    }
}

real FpropSent(long long sen[MAX_PAR_SENT*MAX_SENTENCE_LENGTH], real attention[MAX_PAR_SENT*MAX_SENTENCE_LENGTH], real *deltas, real *syn, real sign) {
    real sumSquares = 0;
    long long c, d, offset;
    int len = 0, w_count = 0;
    for (len = 0;len<MAX_PAR_SENT*MAX_SENTENCE_LENGTH;len++){
        if (sen[len] == -1) break;
        if (sen[len] == 0) continue;
        w_count ++;
    }
    for (d = 0; d < len; d++) {
        if (sen[d]==0) continue;
        offset = layer_size * sen[d];
        for (c = 0; c < layer_size; c++) {
            // We compute the attentive sentence vector
            if (attention[0] < 0)
                deltas[c] += sign * syn[offset + c] / (real)w_count;
            else
                deltas[c] += sign * attention[d] * syn[offset + c];
            if (d == len - 1) sumSquares += deltas[c] * deltas[c];
        }
    }
    return sumSquares;
}


/* BilBOWA bag-of-words sentence update */
void BilBOWASentenceUpdate(long long sen[2][MAX_PAR_SENT*MAX_SENTENCE_LENGTH],real attention[2][MAX_PAR_SENT*MAX_SENTENCE_LENGTH], int lang_id[2], real *deltas) {
    int a,i;
    int w_count[2];
    // FPROP
    // length of sen
    for (i=0;i<2;i++){
        w_count[i] = 0;
        for(a=0;a<MAX_PAR_SENT*MAX_SENTENCE_LENGTH;a++){
            if (sen[i][a]==-1) break;
            if (sen[i][a]==0) continue;
            w_count[i]++;
        }
    }
    for (a = 0; a < layer_size; a++) deltas[a] = 0;
    // ACCUMULATE L2 LOSS DELTA for each pair of languages, which should be improved
    FpropSent(sen[0], attention[0], deltas, model[TEXT_VOCAB][lang_id[0]].syn0, +1);
    par_err[lang_id[1]-1] = FpropSent(sen[1], attention[1], deltas, model[TEXT_VOCAB][lang_id[1]].syn0, -1);
    UpdateSquaredError(sen, attention, w_count, lang_id, deltas, cross_model_weight);
}

real km_match(struct KM_var *km_var)
{
    int p,q,i,j,k;
    int m = km_var->m;
    int n = km_var->n;
    real res=0;
    int *s = km_var->s;
    int *t = km_var->t;
    real *l1 = km_var->l1;
    real *l2 = km_var->l2;
    for(i=0;i<m;i++)
    {
        l1[i]=-10000000;
        
        for(j=0;j<n;j++)
            l1[i]=km_var->matrix[i*n+j]>l1[i]?km_var->matrix[i*n+j]:l1[i];
        if(isequal(l1[i],-10000000))
            return -1;
    }
    
    for(i=0;i<n;i++)
        l2[i]=0;
    _clr(km_var->match1, MAX_PAR_SENT*MAX_SENTENCE_LENGTH);
    _clr(km_var->match2, MAX_PAR_SENT*MAX_SENTENCE_LENGTH);
    for(i=0;i<m;i++)
    {
        _clr(t, MAX_PAR_SENT*MAX_SENTENCE_LENGTH);
        p=0;q=0;
        for(s[0]=i;p<=q&&km_var->match1[i]<0;p++)
        {
            for(k=s[p],j=0;j<n&&km_var->match1[i]<0;j++)
            {
                if(isequal(l1[k]+l2[j],km_var->matrix[k*n+j])&&t[j]<0)
                {
                    s[++q]=km_var->match2[j];
                    t[j]=k;
                    if(s[q]<0)
                    {
                        for(p=j;p>=0;j=p)
                        {
                            km_var->match2[j]=k=t[j];
                            p=km_var->match1[k];
                            km_var->match1[k]=j;
                        }
                    }
                }
            }
        }
        
        if(km_var->match1[i]<0)
        {
            i--;
            real pp=10000000;
            for(k=0;k<=q;k++)
            {
                for(j=0;j<n;j++)
                {
                    if(t[j]<0&&l1[s[k]]+l2[j]-km_var->matrix[s[k]*n+j]<pp)
                        pp=l1[s[k]]+l2[j]-km_var->matrix[s[k]*n+j];
                }
            }
            for(j=0;j<n;j++)
                l2[j]+=t[j]<0?0:pp;
            for(k=0;k<=q;k++)
                l1[s[k]]-=pp;
        }
    }
    for(i=0;i<m;i++)
        res+=km_var->matrix[i*n+km_var->match1[i]];
    return res;
}

void SetKGAttention(long long sen[MAX_PAR_SENT*MAX_SENTENCE_LENGTH],long long entity_index[2], real attention[MAX_PAR_SENT*MAX_SENTENCE_LENGTH], int lang_id){
    long j,k,tmp_pos=0;
    real sum = 0.0, tmp_sim;
    real rel_vec[layer_size];
    real sent_vec[layer_size];
    int VOCAB = KG_VOCAB;
    if (shareSyn0!=1) VOCAB = SENSE_VOCAB;
    
    for (j=0;j<layer_size;j++){
        //rel_vec[j] = model[VOCAB][lang_id].syn0[entity_index[0]*layer_size+j] - model[VOCAB][lang_id].syn0[entity_index[1]*layer_size+j];
        rel_vec[j] = model[VOCAB][lang_id].syn0[entity_index[0]*layer_size+j];
    }
    
    for (k=0;k<layer_size;k++) sent_vec[k] = 0;

    for (j=0;j<MAX_PAR_SENT*MAX_SENTENCE_LENGTH;j++){
        if (sen[j]==0 || sen[j]==-1){
            tmp_sim = similarity(sent_vec, rel_vec);
            for (k=0;k<layer_size;k++) sent_vec[k] = 0;
            sum += tmp_sim;
            for (k=tmp_pos;k<j;k++) attention[k] = tmp_sim;
            if (sen[j]==-1) break;
            tmp_pos = j+1;
            continue;
        }
        for (k=0;k<layer_size;k++)
            sent_vec[k] += model[TEXT_VOCAB][lang_id].syn0[sen[j]*layer_size+k];
    }
    if (sum>0){
        for (j=0;j<MAX_PAR_SENT*MAX_SENTENCE_LENGTH;j++){
            if (attention[j] == -1) break;
            attention[j] /= sum;
        }
    }
    else
        attention[0] = -1;
    
}

void SetWAttention(long long sen[2][MAX_PAR_SENT*MAX_SENTENCE_LENGTH], real attention[2][MAX_PAR_SENT*MAX_SENTENCE_LENGTH], struct KM_var *km_var, int lang_id[2]){
    long i,j;
    real sum = 0.0;
    int len[2], m,n;
    
    for (i=0;i<2;i++){
        for (j=0;j<MAX_PAR_SENT*MAX_SENTENCE_LENGTH;j++){
            if (sen[i][j] == -1){
                len[i] = j;
                break;
            }
        }
    }
    // word alignment attention
    m = len[0]<=len[1]?0:1;
    n = len[0]<=len[1]?1:0;
    km_var->m = len[m];
    km_var->n = len[n];
    km_var->matrix = (real *)calloc(km_var->m * km_var->n, sizeof(real));
    for (i=0;i<km_var->m;i++){
        for (j=0;j<km_var->n;j++){
            if (sen[m][i]==0 || sen[n][j]==0)
                km_var->matrix[i*km_var->n+j] = 0.0;
            else
                km_var->matrix[i*km_var->n+j] = similarity(&model[TEXT_VOCAB][lang_id[m]].syn0[sen[m][i]*layer_size], &model[TEXT_VOCAB][lang_id[n]].syn0[sen[n][j]*layer_size]);
        }
    }
    sum = km_match(km_var);
    if (sum>0){
        for (j=0;j<len[m];j++){
            attention[m][j] = 0;
            if (km_var->match1[j] != -1 && sen[m][j]>0)
                attention[m][j] = km_var->matrix[j*km_var->n+km_var->match1[j]];
        }
        
        for (j=0;j<len[n];j++){
            attention[n][j] = 0;
            if (km_var->match2[j] != -1 && sen[n][j]>0)
                attention[n][j] = km_var->matrix[km_var->match2[j]*km_var->n+j];
        }
        
        // assign the same words with same attention in the longer sentence
        for (j=0;j<len[n];j++){
            if (km_var->match2[j] != -1 && sen[n][j] > 0){
                for (i=0;i<len[n];i++){
                    if (sen[n][i]==sen[n][j])
                        attention[n][i]=attention[n][j];
                }
            }
        }
        
        // average
        for (i=0;i<2;i++){
            sum = 0.0;
            for (j=0;j<len[i];j++)
                sum += attention[i][j];
            if (sum > 0)
                for (j=0;j<len[i];j++)
                    attention[i][j] /= sum;
            else
                attention[i][0] = -1;
        }
    }
    else{
        attention[0][0] = -1;
        attention[1][0] = -1;
    }
    free(km_var->matrix);
}

/* Thread for performing the cross-lingual learning */
void *BilbowaThread(void *id) {
    
    // Each thread will be responsible for reading a portion of both lang_id1 and lang_id2 files. portion size is: file_size/num_threads
    long long par_sen[2][MAX_PAR_SENT*MAX_SENTENCE_LENGTH];
    long long par_entity[4];
    real kg_attention[2][MAX_PAR_SENT*MAX_SENTENCE_LENGTH];
    real w_attention[2][MAX_PAR_SENT*MAX_SENTENCE_LENGTH];
    real attention[2][MAX_PAR_SENT*MAX_SENTENCE_LENGTH];
    long long fi_size;
    int line_num = 0, cur_line = 0, res = 0, lang_id[2], sen_count[2];
    int cur_lang_id = (long long)id / num_threads-2*NUM_LANG+1, thread_id = (long long)id % num_threads;
    
    lang_id[0] = 0;
    lang_id[1] = cur_lang_id;
    //km parameter
    struct KM_var km_var;
    real sum = 0;
    real deltas[layer_size];
    //seek for the position of the current thread
    FILE *fi_par = fopen(multi_context_file[lang_id[1]-1], "rb");
    fseek(fi_par, 0, SEEK_END);
    fi_size = ftell(fi_par);
    fseek(fi_par, fi_size / (long long)num_threads * (long long)thread_id, SEEK_SET);
    line_num = par_line_num[lang_id[1]-1] / (long long)num_threads;
    
    while (MONO_DONE_TRAINING < NUM_LANG * num_threads) {
        for(int i=0;i<2;i++) {
            par_sen[i][0] = -1;
            attention[i][0] = -1;
        }
        for(int i=0;i<4;i++) par_entity[i] = -1;
        
        res = ReadSent(fi_par, par_sen, par_entity, lang_id);
        if (feof(fi_par) || cur_line>=line_num){
            cur_line = 0;
            fseek(fi_par, fi_size / (long long)num_threads * (long long)thread_id, SEEK_SET);
            continue;
        }
        if (res <= 0) continue;
        cur_line += res;
        for (int i=0;i<res;i++){
            par_actual_line[lang_id[1]-1] ++;
            if (par_actual_line[lang_id[1]-1] > 0 &&
                par_actual_line[lang_id[1]-1] % par_line_num[lang_id[1]-1] == 0) {
                par_epoch[lang_id[1]-1]++;
            }
        }
        if (has_w_att || has_kg_att){
                if (has_kg_att && (par_entity[0]<=0 || par_entity[1]<=0 || par_entity[2]<=0 || par_entity[3]<=0))
                    continue;
            //init attention
            for (int i=0;i<2;i++){
                sen_count[i] = 1;
                for (int j=0;j<MAX_PAR_SENT*MAX_SENTENCE_LENGTH;j++){
                    if (par_sen[i][j] == -1) {
                        kg_attention[i][j] = -1;
                        w_attention[i][j] = -1;
                        attention[i][j] = -1;
                        break;
                    }
                    if (par_sen[i][j] == 0) {
                        sen_count[i] ++;
                        kg_attention[i][j] = 0;
                        w_attention[i][j] = 0;
                        attention[i][j] = 0;
                        continue;
                    }
                    kg_attention[i][j] = 1.0;
                    w_attention[i][j] = 1.0;
                    
                    attention[i][j] = 1.0;
                }
            }
            //compute attention
            if (has_kg_att){
                for (int i=0;i<2;i++)
                    if (par_entity[2*i]>0 && par_entity[2*i+1]>0 && sen_count[i] > 1)
                        SetKGAttention(par_sen[i], &par_entity[2*i], kg_attention[i], lang_id[i]);
            }
            
            if (has_w_att) SetWAttention(par_sen, w_attention, &km_var, lang_id);
            
            for (int i=0;i<2;i++){
                if (isequal(kg_attention[i][0], -1) && isequal(w_attention[i][0], -1))
                    attention[i][0] = -1;
                else if (!isequal(kg_attention[i][0], -1) && isequal(w_attention[i][0], -1)){
                    for (int j=0;j<MAX_PAR_SENT*MAX_SENTENCE_LENGTH;j++){
                        if (isequal(attention[i][j], -1)) break;
                        attention[i][j] = kg_attention[i][j];
                    }   // end for j
                }
                else if (isequal(kg_attention[i][0], -1) && !isequal(w_attention[i][0], -1)){
                    for (int j=0;j<MAX_PAR_SENT*MAX_SENTENCE_LENGTH;j++){
                        if (isequal(attention[i][j], -1)) break;
                        attention[i][j] = w_attention[i][j];
                    }   // end for j
                }
                else{
                    for (int j=0;j<MAX_PAR_SENT*MAX_SENTENCE_LENGTH;j++){
                        if (isequal(attention[i][j], -1)) break;
                        attention[i][j] = w_attention[i][j] * kg_attention[i][j];
                    }   // end for j
                }
            }          // end for i
            // normalization
            for (int i=0;i<2;i++){
                sum = 0.0;
                for (int j=0;j<MAX_PAR_SENT*MAX_SENTENCE_LENGTH;j++){
                    if (isequal(attention[i][j], -1)) break;
                    sum += attention[i][j];
                }
                if (sum>0)
                    for (int j=0;j<MAX_PAR_SENT*MAX_SENTENCE_LENGTH;j++){
                        if (isequal(attention[i][j], -1)) break;
                        attention[i][j] /= sum;
                    }
                else
                    attention[i][0] = -1;
            }
            if ( attention[0][1] < 0 || attention[1][1] < 0)
                continue;
        }
        /*
        for(int i=0;i<2;i++){
            if (par_entity[2*i]>0 && par_entity[2*i+1]>0)
                printf("%d\t%s\t%s\t", i, model[KG_VOCAB][lang_id[i]].vocab[par_entity[2*i]].item, model[KG_VOCAB][lang_id[i]].vocab[par_entity[2*i+1]].item);
            else
                printf("%d\t%lld\t%lld\t", i, par_entity[2*i], par_entity[2*i+1]);
            for (int j=0;j<MAX_PAR_SENT*MAX_SENTENCE_LENGTH;j++){
                if (par_sen[i][j]==-1){printf("\n");break;}
                if (par_sen[i][j]==0) {printf("\t");continue;}
                printf("%s(%.4f, kg:%.4f, w:%.4f) ", model[TEXT_VOCAB][lang_id[i]].vocab[par_sen[i][j]].item, attention[i][j], kg_attention[i][j], w_attention[i][j]);
            }
        }
        */
        
        BilBOWASentenceUpdate(par_sen, attention, lang_id, deltas);
    } // while training loop
    fclose(fi_par);
    pthread_exit(NULL);
}

void TrainModel(){
    long long i, num_m = 0;
    long a;
    char out_str[MAX_STRING];
    starting_alpha = alpha;
    if (cross_model_weight>0) num_m = 3*NUM_LANG - 1;
    else num_m = 2*NUM_LANG;
    pthread_t *pt = (pthread_t *)malloc(num_m* num_threads * sizeof(pthread_t));
    start = clock();
    printf("Start training.\n");
    for (a = 0; a < NUM_LANG * num_threads; a++) {
        if (debug_mode > 2) printf("Spawning mono kg thread %ld\n", a);
        pthread_create(&pt[a], NULL, TrainKgModelThread, (void *)a);
    }
    
    for (a = NUM_LANG * num_threads; a < 2 * NUM_LANG * num_threads; a++) {
        if (debug_mode > 2) printf("Spawning mono text thread %ld\n", a);
        pthread_create(&pt[a], NULL, TrainTextModelThread, (void *)a);
    }
    if (cross_model_weight>0) {
        sprintf(out_str, "Starting training ");
        for (i=0;i<NUM_LANG-1;i++)
            sprintf(out_str, "%s%d lines using parallel file %s! ", out_str, par_line_num[i], multi_context_file[i]);
        printf("%s\n", out_str);
        for (a = 2 * NUM_LANG * num_threads; a < (3*NUM_LANG-1) * num_threads; a++) {
            if (debug_mode > 2) printf("Spawning mono parallel thread %ld\n", a);
            pthread_create(&pt[a], NULL, BilbowaThread, (void *)a);
        }
    }
    
    for (a = 0; a < num_m * num_threads; a++) pthread_join(pt[a], NULL);
    
    for (i=0;i<NUM_LANG;i++)
        resetSenseCluster(i);
    if (is_normal==1)
        normalize();
}

int ArgPos(char *str, int argc, char **argv) {
    int a;
    for (a = 1; a < argc; a++) if (!strcmp(str, argv[a])) {
        if (a == argc - 1) {
            printf("Argument missing for %s\n", str);
            exit(1);
        }
        return a;
    }
    return -1;
}

int main(int argc, char **argv) {
    int i,j;
    char temp_arg[MAX_STRING];
    if (argc == 1) {
        printf("Cross-lingual Joint Word&Entity VECTOR Training Toolkit v 0.1c\n\n");
        printf("Options:\n");
        printf("Parameters for training:\n");
        printf("\t-mono_anchorN <file>\n");
        printf("\t\tUse monolingual annotated text data (including anchors) for language N from <file> to train text and joint model\n");
        printf("\t-mono_kgN <file>\n");
        printf("\t\tUse monolingual knowledge data from <file> to train the knowledge model\n");
        printf("\t-multi_kg <file>\n");
        printf("\t\tUse multilingual knowledge data from <file> to align entity in various languages\n");
        printf("\t-multi_context <file>\n");
        printf("\t\tUse multilingual entities' context words from <file> to align words in various languages\n");
        printf("\t-outputN <path>\n");
        printf("\t\tUse <path> to save the resulting vectors \n");
        printf("\t-read_mono_vocabN <path>\n");
        printf("\t\tUse <path> to read the word, entity and mention sense vocab.\n");
        printf("\t-save_mono_vocabN <path>\n");
        printf("\t\tUse <path> to save the word, entity and mention sense vocab.\n");
        printf("\t-read_cross_link <file>\n");
        printf("\t\tUse <file> to read the crosslingual entity links.\n");
        printf("\t-size <int>\n");
        printf("\t\tSet size of word  / entity vectors; default is 100\n");
        printf("\t-window <int>\n");
        printf("\t\tSet max skip length between (anchor) words; default is 5\n");
        printf("\t-sample <float>\n");
        printf("\t\tSet threshold for occurrence of (anchor) words. Those that appear with higher frequency in the training data\n");
        printf("\t\twill be randomly down-sampled; default is 1e-3, useful range is (0, 1e-5)\n");
        printf("\t-negative <int>\n");
        printf("\t\tNumber of negative examples; default is 5, common values are 3 - 10 (0 = not used)\n");
        printf("\t-threads <int>\n");
        printf("\t\tUse <int> threads (default 12)\n");
        printf("\t-iter <int>\n");
        printf("\t\tRun more training iterations (default 5)\n");
        printf("\t-min-count_word <int>\n");
        printf("\t\tThis will discard words that appear less than <int> times; default is 5\n");
        printf("\t-min-count_sense <int>\n");
        printf("\t\tThis will discard senses that appear less than <int> times; default is 5\n");
        printf("\t-alpha <float>\n");
        printf("\t\tSet the starting learning rate; default is 0.025 for skip-gram and 0.05 for CBOW\n");
        printf("\t-debug <int>\n");
        printf("\t\tSet the debug mode (default = 2 = more info during training)\n");
        printf("\t-share_syn <int>\n");
        printf("\t\tif sense embedding share entity embedding\n");
        printf("\t-has_kg_att <int>\n");
        printf("\t\tuse entity word similarity as attention to distant supervision\n");
        printf("\t-has_w_att <int>\n");
        printf("\t\tuse bilingual words alignment as attention\n");
        printf("\t-is_normal <int>\n");
        printf("\t\tif batch normalization\n");
        printf("\t-rho <int>\n");
        printf("\t\tsmooth attention (0-1), defautl is 1, 0 means attentions are the same \n");
        printf("\t-sgd_mode <int>\n");
        printf("\t\tdefault 0 is for sgd, 1 for adagrad, 2 for rms_prop, 3 for adadelta \n");
        printf("\t-sim_mode <int>\n");
        printf("\t\tsimilarity measurment, default 0 is for cosine, 1 for inner product \n");
        printf("\t-xling <int>\n");
        printf("\t\tthe decay parameter for adadelta\n");
        printf("\nExamples:\n");
        printf("./mlmpme -mono_anchor1 /enwiki/anchor_text_cl.dat -mono_anchor2 /eswiki/anchor_text_cl.dat -mono_kg1 /enwiki/mono_kg_id.dat -mono_kg2 /eswiki/mono_kg_id.dat -multi_context1 /paradata/para_contexts.en-es -output1 /data/etc/envec/ -output2 /data/etc/esvec/ -save_mono_vocab1 /data/envocab/ -save_mono_vocab2 /data/esvocab/ -read_cross_link1 /paradata/cross_links.en_es -size 200 -has_sense 1 -window 5 -sample 1e-4 -negative 5 -threads 50 -has_kg_att 1 -has_w_att 1 -cross_model_weight 1 -share_syn 1 -is_normal 0 -sgd_mode 1 -xling 0.9 -rho 1 -epochs 1 -sim_mode 0\n\n");
        return 0;
    }
    
    for(i=0;i<NUM_LANG;i++){
        output_path[i][0]=0;
        read_mono_vocab_path[i][0]=0;
        save_mono_vocab_path[i][0]=0;
        if (i == NUM_LANG-1) continue;
        multi_context_file[i][0]=0;
        cross_link_file[i][0]=0;
    }
    
    for(j=0;j<NUM_LANG;j++){
        sprintf(temp_arg, "-mono_anchor%d", j+1);
        if ((i = ArgPos(temp_arg, argc, argv)) > 0) strcpy(model[TEXT_VOCAB][j].train_file, argv[i + 1]);
        sprintf(temp_arg, "-mono_kg%d", j+1);
        if ((i = ArgPos(temp_arg, argc, argv)) > 0) strcpy(model[KG_VOCAB][j].train_file, argv[i + 1]);
        sprintf(temp_arg, "-output%d", j+1);
        if ((i = ArgPos(temp_arg, argc, argv)) > 0) strcpy(output_path[j], argv[i + 1]);
        sprintf(temp_arg, "-save_mono_vocab%d", j+1);
        if ((i = ArgPos(temp_arg, argc, argv)) > 0) strcpy(save_mono_vocab_path[j], argv[i + 1]);
        sprintf(temp_arg, "-read_mono_vocab%d", j+1);
        if ((i = ArgPos(temp_arg, argc, argv)) > 0) strcpy(read_mono_vocab_path[j], argv[i + 1]);
        if (j == NUM_LANG-1) continue;
        sprintf(temp_arg, "-multi_context%d", j+1);
        if ((i = ArgPos(temp_arg, argc, argv)) > 0) strcpy(multi_context_file[j], argv[i + 1]);
        sprintf(temp_arg, "-read_cross_link%d", j+1);
        if ((i = ArgPos(temp_arg, argc, argv)) > 0) strcpy(cross_link_file[j], argv[i + 1]);
    }
    
    if ((i = ArgPos((char *)"-size", argc, argv)) > 0) layer_size = atoi(argv[i + 1]);
    if ((i = ArgPos((char *)"-debug", argc, argv)) > 0) debug_mode = atoi(argv[i + 1]);
    if ((i = ArgPos((char *)"-alpha", argc, argv)) > 0) alpha = atof(argv[i + 1]);
    if ((i = ArgPos((char *)"-window", argc, argv)) > 0) window = atoi(argv[i + 1]);
    if ((i = ArgPos((char *)"-sample", argc, argv)) > 0) sample = atof(argv[i + 1]);
    if ((i = ArgPos((char *)"-negative", argc, argv)) > 0) negative = atoi(argv[i + 1]);
    if ((i = ArgPos((char *)"-threads", argc, argv)) > 0) num_threads = atoi(argv[i + 1]);
    if ((i = ArgPos((char *)"-early-stop", argc, argv)) > 0) EARLY_STOP = atoi(argv[i + 1]);
    if ((i = ArgPos((char *)"-epochs", argc, argv)) > 0) NUM_EPOCHS = atoi(argv[i + 1]);
    if ((i = ArgPos((char *)"-sgd_mode", argc, argv)) > 0) sgd_mode = atoi(argv[i + 1]);
    if ((i = ArgPos((char *)"-sim_mode", argc, argv)) > 0) sim_mode = atoi(argv[i + 1]);
    if ((i = ArgPos((char *)"-dump-every", argc, argv)) > 0) dump_every = atoi(argv[i + 1]);
    if ((i = ArgPos((char *)"-share_syn", argc, argv)) > 0) shareSyn0 = atoi(argv[i + 1]);
    if ((i = ArgPos((char *)"-min_count", argc, argv)) > 0) min_count = atoi(argv[i + 1]);
    if ((i = ArgPos((char *)"-has_kg_att", argc, argv)) > 0) has_kg_att = atoi(argv[i + 1]);
    if ((i = ArgPos((char *)"-has_w_att", argc, argv)) > 0) has_w_att = atoi(argv[i + 1]);
    if ((i = ArgPos((char *)"-is_normal", argc, argv)) > 0) is_normal = atoi(argv[i + 1]);
    if ((i = ArgPos((char *)"-has_sense", argc, argv)) > 0) has_sense = atoi(argv[i + 1]);
    if ((i = ArgPos((char *)"-cross_model_weight", argc, argv)) > 0) cross_model_weight = atof(argv[i + 1]);
    if ((i = ArgPos((char *)"-rho", argc, argv)) > 0) rho = atof(argv[i + 1]);
    if ((i = ArgPos((char *)"-xling", argc, argv)) > 0) xling = atof(argv[i + 1]);
    
    expTable = (real *)malloc((EXP_TABLE_SIZE + 1) * sizeof(real));
    for (i = 0; i <= EXP_TABLE_SIZE; i++) {
        expTable[i] = exp((i / (real)EXP_TABLE_SIZE * 2 - 1) * MAX_EXP); // Precompute the exp() table
        expTable[i] = expTable[i] / (expTable[i] + 1);                   // Precompute f(x) = x / (x + 1)
    }
    max_train_words = 0;
    for (i=0; i< NUM_LANG; i++){
        // training senses also using anchors
        strcpy(model[SENSE_VOCAB][i].train_file, model[TEXT_VOCAB][i].train_file);
        
        // initialize output file
        if(output_path[i][0]!=0){
            sprintf(model[TEXT_VOCAB][i].output_file, "%svectors_word", output_path[i]);
            sprintf(model[KG_VOCAB][i].output_file, "%svectors_entity", output_path[i]);
            sprintf(model[SENSE_VOCAB][i].output_file, "%svectors_sense", output_path[i]);
        }
        
        //initialize save vocab file
        if(save_mono_vocab_path[i][0]!=0){
            sprintf(model[TEXT_VOCAB][i].save_vocab_file, "%svocab_word.txt", save_mono_vocab_path[i]);
            sprintf(model[KG_VOCAB][i].save_vocab_file, "%svocab_entity.txt", save_mono_vocab_path[i]);
            sprintf(model[SENSE_VOCAB][i].save_vocab_file, "%svocab_sense.txt", save_mono_vocab_path[i]);
        }
        
        // read vocab
        if(read_mono_vocab_path[i][0]!=0){
            sprintf(model[TEXT_VOCAB][i].read_vocab_file, "%svocab_word.txt", read_mono_vocab_path[i]);
            sprintf(model[KG_VOCAB][i].read_vocab_file, "%svocab_entity.txt", read_mono_vocab_path[i]);
            sprintf(model[SENSE_VOCAB][i].read_vocab_file, "%svocab_sense.txt", read_mono_vocab_path[i]);
        }
        
        //read vocab & initilize text model and kg model，//use read_xx_path to decide whether use pre-trained xx model
        //the init order is necessary, words->entity->senses
        InitModel(TEXT_VOCAB, i);
        InitModel(KG_VOCAB, i);
        InitModel(SENSE_VOCAB, i);
        if (model[TEXT_VOCAB][i].train_items > max_train_words)
            max_train_words = model[TEXT_VOCAB][i].train_items;
    }
    printf("init model finished!");
    if (NUM_LANG >=2 && cross_model_weight>0)
        InitMultiModel();
    
    //start training
    TrainModel();
    for (i=0;i<NUM_MODEL;i++) for (int j=0;j<NUM_LANG;j++){
        if (model[i][j].dump_iters == 0)
            SaveVector(&model[i][j], model[i][j].dump_iters++);
    }
    
    return 0;
}
