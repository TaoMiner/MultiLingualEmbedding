//
//  mlmpme.cpp
//  MLMPME
//
//  Created by 曹艺馨 on 17/3/16.
//  Copyright © 2017年 ethan. All rights reserved.
//

#include "mlmpme.hpp"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <pthread.h>

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

typedef float real;                    // Precision of float numbers

struct anchor_item {
    long long start_pos;
    long long length;
    int entity_index;
    int sense_index;
};

struct vocab_item {
    long long cn;                   //for words, text counts; for sense, anchor counts; for entity, outlink counts.
    int index;                     //for words, sense indexes; for entity, cross links index; for sense, context cluster num.
    char *item;
};

struct vocab {
    char train_file[MAX_STRING], output_file[MAX_STRING];
    char save_vocab_file[MAX_STRING], read_vocab_file[MAX_STRING];
    int vocab_type;
    struct vocab_item *vocab;
    int *vocab_hash, vocab_hash_size;
    long long vocab_max_size, vocab_size;
    long long train_items, item_count_actual, file_size;
    real starting_alpha, alpha;
    real *syn0, *syn1neg;
    int *table;
};

// NUM_MODEL: words, entities, senses vocab; NUM_LANG: different languages
struct vocab *model[NUM_MODEL][NUM_LANG];

// cross links dictionary
int *cross_links[NUM_LANG];

int local_iter=0, debug_mode = 2, window = 5, min_count = 5, num_threads = 12, min_reduce = 1,save_iter = 1, negative = 5, iter = 5;
long long layer_size = 100;
const int table_size = 1e8;
real alpha = 0.025, sample = 1e-3, bilbowa_grad=0;
real *expTable;
char multi_context_file[MAX_STRING], output_path[NUM_LANG][MAX_STRING], read_mono_vocab_path[NUM_LANG][MAX_STRING], save_mono_vocab_path[NUM_LANG][MAX_STRING], cross_link_file[MAX_STRING];

int cur_lang_id = -1, par_line_num = 0;       //indicator for the thread processing language.

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
                    printf("error! anchor's mention length is larger than %d!\n", MAX_NUM_MENTION);
                    printf("%s\n",mention);
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
        if (a >= MAX_STRING - 1){printf("error! too long string:\n %s\n",item); a--;break;}
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
        if (a >= MAX_STRING - 1){printf("error! too long string:\n %s\n",item); a--;break;}
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

int ReadParText(char *item, FILE *fin) {
    int a = 0, ch, is_anchor=-1;
    
    while (!feof(fin)) {
        ch = fgetc(fin);
        if (ch == 13) continue;
        if ((ch == ' ') || (ch == '\t') || (ch == '\n') || (ch == ']') || (ch == '[') || (ch == '{') || (ch == '}')) {
            if (a > 0) {
                if (ch == '\n') ungetc(ch, fin);
                if (ch == '\t') ungetc(ch, fin);
                if (ch == '[') ungetc(ch, fin);
                if (ch == '{') ungetc(ch, fin);
                break;
            }
            if (ch == '\n') {
                strcpy(item, (char *)"</s>");
                return -1;
            }
            else if(ch == '\t'){
                strcpy(item, (char *)"</t>");
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


// splite by tab
void ReadItem(char *item, FILE *fin) {
    int a = 0, ch;
    while (!feof(fin)) {
        ch = fgetc(fin);
        if (ch == 13) continue;
        if ((ch == '\t') || (ch == '\n')) {
            if (a > 0) {
                if (ch == '\n') ungetc(ch, fin);
                break;
            }
            if (ch == '\n') {
                strcpy(item, (char *)"</s>");
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
    mono_vocab->vocab[mono_vocab->vocab_size].index = 0;
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
        if ((mono_vocab->vocab[a].cn < min_count) && (a != 0)) {
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
        a = AddItemToVocab(item, mono_vocab);
        fscanf(fin, "%lld%c", &mono_vocab->vocab[a].cn, &c);
    }
    SortVocab(mono_vocab);
    if (debug_mode > 0) {
        printf("Vocab size: %lld\n", mono_vocab->vocab_size);
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
    
    struct vocab *mono_vocab = model[TEXT_VOCAB][lang_id];
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
    struct vocab *entity_vocab = model[KG_VOCAB][lang_id];
    for (a = 0; a < entity_vocab->vocab_hash_size; a++) entity_vocab->vocab_hash[a] = -1;
    fin = fopen(entity_vocab->train_file, "rb");
    if (fin == NULL) {
        printf("ERROR: training data file not found!\n");
        exit(1);
    }
    entity_vocab->vocab_size = 0;
    AddItemToVocab((char *)"</s>", entity_vocab);
    
    //initial sense vocab
    struct vocab *sense_vocab = model[KG_VOCAB][lang_id];
    for (a = 0; a < sense_vocab->vocab_hash_size; a++) sense_vocab->vocab_hash[a] = -1;
    sense_vocab->vocab_size = 0;
    
    while (1) {
        ReadItem(entity, fin);
        if (feof(fin)) break;
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
    //add entity into sense vocab for initialization
    for(i=0;i<entity_vocab->vocab_size;i++)
        AddItemToVocab(entity_vocab->vocab[i].item, sense_vocab);
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
    long long a, i, b;
    int anchor_pos = -1, tmp_mention_len = 0;
    
    struct vocab *word_vocab = model[TEXT_VOCAB][lang_id];
    struct vocab *sense_vocab = model[SENSE_VOCAB][lang_id];
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
            strncpy(ent_str, item, sizeof(char)*anchor_pos);
            ent_str[anchor_pos] = 0;
        }
        //count anchors for sense
        i = SearchVocab(ent_str, sense_vocab);
        if (i != -1) sense_vocab->vocab[i].cn++;
    }
    SortVocab(sense_vocab);
    if (debug_mode > 0) {
        printf("Lang %d: Sense Vocab size: %lld\n", lang_id, sense_vocab->vocab_size);
        printf("Lang %d: Anchors in train file: %lld\n", lang_id, sense_vocab->train_items);
    }
    sense_vocab->file_size = ftell(fin);
    fclose(fin);
    //add sense mention into word vocab
    /*
    for(i=0;i<sense_vocab->vocab_size;i++){
        tmp_mention_len = lengthOfMention(sense_vocab->vocab[i].item);
        strncpy(ent_str, sense_vocab->vocab[i].item, tmp_mention_len);
        ent_str[tmp_mention_len] = 0;
        a = SearchVocab(ent_str, word_vocab);
        if (a == -1) {
            a = AddItemToVocab(ent_str, word_vocab);
            word_vocab->vocab[a].cn = sense_vocab->vocab[i].cn;
            word_vocab->train_items += word_vocab->vocab[a].cn;
        }
    }
    SortVocab(word_vocab);
     */
}

void SaveVocab(struct vocab *mono_vocab) {
    long long i;
    FILE *fo = fopen(mono_vocab->save_vocab_file, "wb");
    for (i = 0; i < mono_vocab->vocab_size; i++) fprintf(fo, "%s\t%lld\n", mono_vocab->vocab[i].item, mono_vocab->vocab[i].cn);
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
    a = posix_memalign((void **)&(mono_vocab->syn0), 128, (long long)mono_vocab->vocab_size * layer_size * sizeof(real));
    if (mono_vocab->syn0 == NULL) {printf("Memory allocation failed\n"); exit(1);}
    if (negative>0) {
        a = posix_memalign((void **)&(mono_vocab->syn1neg), 128, (long long)mono_vocab->vocab_size * layer_size * sizeof(real));
        if (mono_vocab->syn1neg == NULL) {printf("Memory allocation failed\n"); exit(1);}
        for (a = 0; a < mono_vocab->vocab_size; a++) for (b = 0; b < layer_size; b++)
            mono_vocab->syn1neg[a * layer_size + b] = 0;
    }
    for (a = 0; a < mono_vocab->vocab_size; a++) for (b = 0; b < layer_size; b++) {
        next_random = next_random * (unsigned long long)25214903917 + 11;
        mono_vocab->syn0[a * layer_size + b] = (((next_random & 0xFFFF) / (real)65536) - 0.5) / layer_size;
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
    struct vocab *mono_vocab = model[model_type][lang_id];
    mono_vocab->vocab_max_size = 2500000;      //vocab word size is 2.7m
    mono_vocab->vocab_size = 0;
    mono_vocab->train_items = 0;
    mono_vocab->item_count_actual = 0;
    mono_vocab->file_size = 0;
    mono_vocab->alpha = alpha;
    mono_vocab->vocab_hash_size = 30000000;  // Maximum items in the vocabulary 30m*0.7=21m
    
    mono_vocab->vocab = (struct vocab_item *)calloc(mono_vocab->vocab_max_size, sizeof(struct vocab_item));
    mono_vocab->vocab_hash = (int *)calloc(mono_vocab->vocab_hash_size, sizeof(int));
    
    if (read_mono_vocab_path[lang_id][0]!= 0) ReadVocab(mono_vocab);
    else LearnVocabFromTrainFile(model_type, lang_id);
    if (read_mono_vocab_path[lang_id][0] != 0) SaveVocab(mono_vocab);
    if (output_path[lang_id][0] == 0) return;
    InitNet(mono_vocab);
    if (negative > 0) InitUnigramTable(mono_vocab);
}

void InitMultiModel(char *cross_link_file){
    int a, i, j, num_link=0;
    char item[MAX_STRING];
    FILE *fin = fopen(cross_link_file, "rb");
    if (fin == NULL) {
        printf("ERROR: training data file not found!\n");
        exit(1);
    }
    fscanf(fin, "%d", &num_link);
    num_link += 1;
    for(i = 0; i < NUM_LANG; i++)
        cross_links[i] = (int *)malloc(num_link * sizeof(int));
    i = 0;
    // skip 0 column to keep vocab.index=0 meaningful for sense context cluster size.
    j = 1;
    while (1) {
        ReadItem(item, fin);
        if (!strcmp(item, "</s>")) {
            i = 0;
            j++;
        }
        if (i>2) continue;
        a = SearchVocab(item, model[KG_VOCAB][i]);
        cross_links[i][j] = a;
        if (a!=-1)
            model[KG_VOCAB][i]->vocab[a].index = j;
        i++;
        if (feof(fin)) break;
    }
    fclose(fin);
}

void *TrainTextModelThread(void *id) {
    long long a, b, d, cw, word_index=-1, last_word_index, sentence_length = 0, sentence_position = 0;
    long long word_count = 0, anchor_count = 0, anchor_position=0, last_word_count = 0, sen[MAX_SENTENCE_LENGTH + 1];
    long long l1, l2, c, target, label = 0;
    unsigned long long next_random = (long long)id;
    int anchor_pos = -1, word_begin[MAX_MENTION], mention_length = 1;
    char item[MAX_STRING], tmp_word[MAX_STRING], word[MAX_STRING], entity[MAX_STRING];
    size_t tmp_word_len = 0;
    real f, g;
    clock_t now;
    real *neu1 = (real *)calloc(layer1_size, sizeof(real));
    real *neu1e = (real *)calloc(layer1_size, sizeof(real));
    //context vector
    real *tmp_context_vec = (real *)calloc(layer1_size, sizeof(real));
    struct anchor_item *anchors = (struct anchor_item *)calloc(MAX_SENTENCE_LENGTH, sizeof(struct anchor_item));
    
    struct vocab *mono_words = model[TEXT_VOCAB][cur_lang_id];
    struct vocab *mono_entities = model[KG_VOCAB][cur_lang_id];
    struct vocab *mono_senses = model[SENSE_VOCAB][cur_lang_id];
    
    FILE *fi = fopen(mono_words->train_file, "rb");
    fseek(fi, mono_words->file_size / (long long)num_threads * (long long)id, SEEK_SET);
    for(a=0;a<MAX_NUM_MENTION;a++) word_begin[a] = 0;
    while (1) {
        if (word_count - last_word_count > 10000) {
            mono_words->item_count_actual += word_count - last_word_count;
            last_word_count = word_count;
            if ((debug_mode > 1)) {
                now=clock();
                printf("%cModel %d: Alpha: %f  Progress: %.2f%%  Words/thread/sec: %.2fk  ", 13, mono_words->vocab_type, mono_words->alpha,
                       mono_words->item_count_actual / (real)(mono_words->train_items + 1) * 100,
                       mono_words->item_count_actual / ((real)(now - start + 1) / (real)CLOCKS_PER_SEC * 1000));
                fflush(stdout);
            }
            mono_words->alpha = mono_words->starting_alpha * (1 - mono_words->item_count_actual / (real)(iter * mono_words->train_items + 1));
            if (mono_words->alpha < mono_words->starting_alpha * 0.0001) mono_words->alpha = mono_words->starting_alpha * 0.0001;
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
                    strncpy(entity, item, sizeof(char)*anchor_pos);
                    entity[anchor_pos] = 0;
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
                    word_count++;
                    if (word_index == -1) continue;
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
                        anchors[anchor_count].entity_index = SearchVocab(entity, model[KG_VOCAB][cur_lang_id]);
                        anchors[anchor_count].sense_index = SearchVocab(entity, model[SENSE_VOCAB][cur_lang_id]);
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
        if (feof(fi) || (word_count > mono_words->train_items / num_threads)) {
            mono_words->item_count_actual += word_count - last_word_count;
            break;
        }
        
        word_index = sen[sentence_position];
        if (word_index == -1) continue;
        for (c = 0; c < layer1_size; c++) neu1[c] = 0;
        for (c = 0; c < layer1_size; c++) neu1e[c] = 0;
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
                if (f > MAX_EXP) g = (label - 1) * mono_words->alpha;
                else if (f < -MAX_EXP) g = (label - 0) * mono_words->alpha;
                else g = (label - expTable[(int)((f + MAX_EXP) * (EXP_TABLE_SIZE / MAX_EXP / 2))]) * mono_words->alpha;
                for (c = 0; c < layer_size; c++) neu1e[c] += g * mono_words->syn1neg[c + l2];
                for (c = 0; c < layer_size; c++) mono_words->syn1neg[c + l2] += g * mono_words->syn0[c + l1];
            }
            // Learn weights input -> hidden
            for (c = 0; c < layer_size; c++) mono_words->syn0[c + l1] += neu1e[c];
        }
        
        sentence_position++;
        if (sentence_position >= sentence_length) {
            // train word embedding finished! start train mention sense embedding ...
            if (anchor_count > 0){
                for(anchor_position=0;anchor_position<anchor_count;anchor_position++){
                    for (c = 0; c < layer_size; c++) neu1[c] = 0;
                    for (c = 0; c < layer_size; c++) neu1e[c] = 0;
                    //reset context vec
                    for (c = 0; c < layer_size; c++) tmp_context_vec[c] = 0;
                    cw = 0;
                    next_random = next_random * (unsigned long long)25214903917 + 11;
                    b = next_random % window;
                    sentence_position = anchors[anchor_position].start_pos;
                    l1 = anchors[anchor_position].sense_index * layer_size;
                    // mention sense to predict context words
                    for (a = b; a < window * 2 + 1 - b; a++)
                        if(a == window)
                            sentence_position = anchors[anchor_position].start_pos + anchors[anchor_position].length-1;
                        else {
                            c = sentence_position - window + a;
                            if (c < 0) continue;
                            if (c >= sentence_length) continue;
                            word_index = sen[c];
                            if (word_index == -1) continue;
                            // compute context vec
                            for (c = 0; c < layer_size; c++) tmp_context_vec[c] += mono_words->syn0[word_index * layer_size + c];
                            cw ++;
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
                                for (c = 0; c < layer_size; c++) f += mono_senses->syn0[c + l1] * mono_words->syn1neg[c + l2];
                                if (f > MAX_EXP) g = (label - 1) * mono_words->alpha;
                                else if (f < -MAX_EXP) g = (label - 0) * mono_words->alpha;
                                else g = (label - expTable[(int)((f + MAX_EXP) * (EXP_TABLE_SIZE / MAX_EXP / 2))]) * mono_words->alpha;
                                for (c = 0; c < layer_size; c++) neu1e[c] += g * mono_words->syn1neg[c + l2];
                                for (c = 0; c < layer_size; c++) mono_words->syn1neg[c + l2] += g * mono_senses->syn0[c + l1];
                            }
                            // Learn weights input -> hidden
                            for (c = 0; c < layer_size; c++) mono_senses->syn0[c + l1] += neu1e[c];
                        }
                    
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
                                for (c = 0; c < layer_size; c++) f += mono_words->syn0[c + l1] * mono_entities->syn1neg[c + l2];
                                if (f > MAX_EXP) g = (label - 1) * mono_words->alpha;
                                else if (f < -MAX_EXP) g = (label - 0) * mono_words->alpha;
                                else g = (label - expTable[(int)((f + MAX_EXP) * (EXP_TABLE_SIZE / MAX_EXP / 2))]) * mono_words->alpha;
                                for (c = 0; c < layer_size; c++) neu1e[c] += g * mono_entities->syn1neg[c + l2];
                                for (c = 0; c < layer_size; c++) mono_entities->syn1neg[c + l2] += g * mono_words->syn0[c + l1];
                            }
                            // Learn weights input -> hidden
                            for (c = 0; c < layer_size; c++) mono_words->syn0[c + l1] += neu1e[c];
                        }
                    //also use sense embedding to predict the entity
                    last_word_index = anchors[anchor_position].sense_index;
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
                            target = mono_entities->table[(next_random >> 16) % table_size];
                            if (target == 0) target = next_random % (mono_entities->vocab_size - 1) + 1;
                            if (target == word_index) continue;
                            label = 0;
                        }
                        l2 = target * layer_size;
                        f = 0;
                        for (c = 0; c < layer_size; c++) f += mono_senses->syn0[c + l1] * mono_entities->syn1neg[c + l2];
                        if (f > MAX_EXP) g = (label - 1) * mono_words->alpha;
                        else if (f < -MAX_EXP) g = (label - 0) * mono_words->alpha;
                        else g = (label - expTable[(int)((f + MAX_EXP) * (EXP_TABLE_SIZE / MAX_EXP / 2))]) * mono_words->alpha;
                        for (c = 0; c < layer_size; c++) neu1e[c] += g * mono_entities->syn1neg[c + l2];
                        for (c = 0; c < layer_size; c++) mono_entities->syn1neg[c + l2] += g * mono_senses->syn0[c + l1];
                    }
                    // Learn weights input -> hidden
                    for (c = 0; c < layer_size; c++) mono_senses->syn0[c + l1] += neu1e[c];
                    
                    
                    //update cluster center mu and cluster size
                    if(cw>0){
                        for (c = 0; c < layer_size; c++) mono_senses->syn1neg[l1 + c] += (tmp_context_vec[c]/cw);
                        mono_senses->vocab[last_word_index].index += 1;
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
    pthread_exit(NULL);
}

void *TrainKgModelThread(void *id) {
    long long d, entity_index, head_entity_index = -1, tmp_head_entity_index=-1, cross_index=-1, line_entity_count = 0, is_read_head = 1, sentence_length = 0, sentence_position = 0;
    long long entity_count = 0, last_entity_count = 0, sen[MAX_SENTENCE_LENGTH + 1];
    long long l1, l2, c, target, label;
    unsigned long long next_random = (long long)id;
    char entity[MAX_STRING];
    real f, g;
    clock_t now;
    real *neu1 = (real *)calloc(layer_size, sizeof(real));
    real *neu1e = (real *)calloc(layer_size, sizeof(real));
    
    struct vocab *mono_entities = model[KG_VOCAB][cur_lang_id];
    struct vocab *tmp_mono_entities;
    FILE *fi = fopen(mono_entities->train_file, "rb");
    fseek(fi, mono_entities->file_size / (long long)num_threads * (long long)id, SEEK_SET);
    if((long long)id!=0)
        while(1){
            ReadItem(entity, fi);
            entity_index = SearchVocab(entity, mono_entities);
            entity_count ++;
            if (feof(fi) || (entity_index==0)) break;
        }
    head_entity_index = -1;
    is_read_head = 1;
    line_entity_count = 0;
    while (1) {
        if (entity_count - last_entity_count > 10000) {
            mono_entities->item_count_actual += entity_count - last_entity_count;
            last_entity_count = entity_count;
            if ((debug_mode > 1)) {
                now=clock();
                printf("%cModel %d: Alpha: %f  Progress: %.2f%%  entities/thread/sec: %.2fk  ", 13, mono_entities->vocab_type, mono_entities->alpha,
                       mono_entities->item_count_actual / (real)(mono_entities->train_items + 1) * 100,
                       mono_entities->item_count_actual / ((real)(now - start + 1) / (real)CLOCKS_PER_SEC * 1000));
                fflush(stdout);
            }
            mono_entities->alpha = mono_entities->starting_alpha * (1 - mono_entities->item_count_actual / (real)(iter * mono_entities->train_items + 1));
            if (mono_entities->alpha < mono_entities->starting_alpha * 0.0001) mono_entities->alpha = mono_entities->starting_alpha * 0.0001;
        }
        if (sentence_length == 0) {
            while(1){
                ReadItem(entity, fi);
                if (feof(fi)) break;
                entity_count ++;
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
                sen[sentence_length] = entity_index;
                sentence_length++;
                if (sentence_length >= MAX_SENTENCE_LENGTH) break;
            }
            sentence_position = 0;
        }
        if (feof(fi) || (entity_count > mono_entities->train_items / num_threads)) {
            mono_entities->item_count_actual += entity_count - last_entity_count;
            break;
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
                if (f > MAX_EXP) g = (label - 1) * mono_entities->alpha;
                else if (f < -MAX_EXP) g = (label - 0) * mono_entities->alpha;
                else g = (label - expTable[(int)((f + MAX_EXP) * (EXP_TABLE_SIZE / MAX_EXP / 2))]) * mono_entities->alpha;
                for (c = 0; c < layer_size; c++) neu1e[c] += g * mono_entities->syn1neg[c + l2];
                for (c = 0; c < layer_size; c++) mono_entities->syn1neg[c + l2] += g * mono_entities->syn0[c + l1];
            }
            // Learn weights input -> hidden
            for (c = 0; c < layer_size; c++) mono_entities->syn0[c + l1] += neu1e[c];
        }
        //train cross lingual links
        cross_index = mono_entities->vocab[head_entity_index].index;
        if (cross_index>0){
            for (c = 0; c < layer_size; c++) neu1[c] = 0;
            for (c = 0; c < layer_size; c++) neu1e[c] = 0;
            for (int k=0;k<NUM_LANG;k++){
                if (k==cur_lang_id) continue;
                tmp_head_entity_index = cross_links[k][cross_index];
                tmp_mono_entities = model[KG_VOCAB][k];
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
                        if (f > MAX_EXP) g = (label - 1) * mono_entities->alpha;
                        else if (f < -MAX_EXP) g = (label - 0) * mono_entities->alpha;
                        else g = (label - expTable[(int)((f + MAX_EXP) * (EXP_TABLE_SIZE / MAX_EXP / 2))]) * mono_entities->alpha;
                        for (c = 0; c < layer_size; c++) neu1e[c] += g * tmp_mono_entities->syn1neg[c + l2];
                        for (c = 0; c < layer_size; c++) tmp_mono_entities->syn1neg[c + l2] += g * mono_entities->syn0[c + l1];
                    }
                    // Learn weights input -> hidden
                    for (c = 0; c < layer_size; c++) mono_entities->syn0[c + l1] += neu1e[c];
                }
            }
            
        }
        sentence_length = 0;
    }
    fclose(fi);
    free(neu1);
    free(neu1e);
    pthread_exit(NULL);
}

void setMonoLangId(int lang_id){
    cur_lang_id = lang_id;
}

void TrainModel(int model_type, int lang_id){
    long a, b, c;
    pthread_t *pt = (pthread_t *)malloc(num_threads * sizeof(pthread_t));
    real len;
    struct vocab *model = model[model_type][lang_id];
    setMonoLangId(lang_id);
    start = clock();
    printf("\nStarting training model %d using file %s\n", model_type, model->train_file);
    model->item_count_actual = 0;
    model->starting_alpha = model->alpha;
    
    if (TEXT_VOCAB==model_type)
        for (a = 0; a < num_threads; a++) pthread_create(&pt[a], NULL, TrainTextModelThread, (void *)a);
    if (KG_VOCAB==model_type)
        for (a = 0; a < num_threads; a++) pthread_create(&pt[a], NULL, TrainKgModelThread, (void *)a);
    for (a = 0; a < num_threads; a++) pthread_join(pt[a], NULL);
    if (TEXT_VOCAB==model_type)
        resetSenseCluster(lang_id);
}

void resetSenseCluster(int lang_id){
    long long a,c;
    struct vocab *model = model[SENSE_VOCAB][lang_id];
    for (a = 0; a < model->vocab_size; a++){
        //sense cluster
        if (model->vocab[a].index > 0){
            for (c=0;c<layer_size;c++)
                model->syn1neg[a*layer_size+c] /= model->vocab[a].index;
            model->vocab[a].index = 1;
        }
    }
}

// cross lingual alignment
/* Read parallel sentences into *sen for all languages from fi
 * fi point to the file: each line contains NUM_LANG sentences separated by tab */
void ReadSent(FILE *fi, long long sen[NUM_LANG][MAX_SENTENCE_LENGTH]) {
    long long word_index;
    char word[MAX_STRING];
    int sentence_length = 0, anchor_pos, cur_lang=0, i;
    struct vocab *word_model;
    while (1) {
        anchor_pos = ReadParText(word, fi);
        if (feof(fi) || !strcmp(word, (char *)"</s>")){
            sen[cur_lang][sentence_length] = 0;
            break;
        }
        if (!strcmp(word, (char *)"</t>")){
            sen[cur_lang][sentence_length] = 0;
            sentence_length = 0;
            cur_lang = (cur_lang + 1) % NUM_LANG;
            continue;
        }
        //only for words
        if (anchor_pos==-1 && sentence_length < MAX_SEN_LEN-1){
            word_model = model[TEXT_VOCAB][cur_lang];
            word_index = SearchVocab(word, word_model);
            if (word == -1) continue;
            // The subsampling randomly discards frequent words while keeping the ranking same
            if (sample > 0) {
                real ran = (sqrt(word_model->vocab[word_index].cn / (sample * word_model->train_items)) + 1) * (sample * word_model->train_items) / word_model->vocab[word_index].cn;
                next_random = next_random * (unsigned long long)25214903917 + 11;
                if (ran < (next_random & 0xFFFF) / (real)65536) continue;
            }
            sen[cur_lang][sentence_length] = word_index;
            sentence_length++;
            if (sentence_length >= MAX_SEN_LEN){
                sentence_length = MAX_SEN_LEN - 1;
                continue;
            }
        }
        
    }
}

void UpdateEmbeddings(real *embeddings, int offset, int num_updates, real *deltas, real weight) {
    int a;
    real step, epsilon = 1e-6;
    for (a = 0; a < num_updates; a++) {
        // Regular SGD
        step = alpha * deltas[a];
        if (step != step) {
            fprintf(stderr, "ERROR: step == NaN\n");
        }
        step = step * weight;
        embeddings[offset + a] += step;
    }
}

void UpdateSquaredError(long long sen1[MAX_SENTENCE_LENGTH], long long sen2[MAX_SENTENCE_LENGTH], real *delta, real *syn0_1, real *syn0_2) {
    int d, offset;
    // To minimize squared error:
    // delta = d .5*|| e - f ||^2 = ±(e - f)
    // d/den = +delta
    for (d = 0; d < MAX_SENTENCE_LENGTH; d++) {
        if (sen1[d]==0) break;
        offset = layer_size * sen1[d];
        // update in -d/den = -delta direction
        UpdateEmbeddings(syn0_1, offset, layer_size, delta, -1);
    }
    // d/df = -delta
    for (d = 0; d < MAX_SENTENCE_LENGTH; d++) {
        if (sen2[d]==0) break;
        offset = layer_size * sen2[d];
        // update in -d/df = +delta direction
        UpdateEmbeddings(syn0_2, offset, layer_size, delta, 1);
    }
}

real FpropSent(long long sen[MAX_SENTENCE_LENGTH], real *deltas, real *syn, real sign) {
    real sumSquares = 0;
    long long c, d, offset;
    for (d = 0; d < MAX_SENTENCE_LENGTH; d++) {
        if (sen[d]==0) break;
        offset = layer_size * sen[d];
        for (c = 0; c < layer_size; c++) {
            // We compute the MEAN sentence vector
            deltas[c] += sign * syn[offset + c] / (real)len;
            if (d == len - 1) sumSquares += deltas[c] * deltas[c];
        }
    }
    return sumSquares;
}


/* BilBOWA bag-of-words sentence update */
void BilBOWASentenceUpdate(long long sen[NUM_LANG][MAX_SENTENCE_LENGTH], real *deltas) {
    int a;
    real grad_norm;
    real *syn0_1, *syn0_2;
    // FPROP
    // RESET DELTAS
    for (a = 0; a < layer_size; a++) deltas[a] = 0;
    // ACCUMULATE L2 LOSS DELTA for each pair of languages, which should be improved
    for (int i=0;i<NUM_LANG;i++)
        for (int j=i+1;j<NUM_LANG;j++){
            syn0_1 = model[TEXT_VOCAB][i].syn0;
            syn0_2 = model[TEXT_VOCAB][j].syn0;
            FpropSent(sen[i], deltas, syn0_1, +1);
            grad_norm = FpropSent(sen[j], deltas, syn0_2, -1);
            bilbowa_grad = 0.9*bilbowa_grad + 0.1*grad_norm;
            UpdateSquaredError(sen[i], sen[j], deltas, syn0_1, syn0_2);
        }
}

/* Thread for performing the cross-lingual learning */
void *BilbowaThread(void *id) {
    int par_sen_len[NUM_LANG];
    
    // Each thread should work on both languages, so we do not need to obtain the lang_idX based on the thread_number
    // TODO: Change this for more than two languages
    int lang_id[NUM_LANG];
    // Each thread will be responsible for reading a portion of both lang_id1 and lang_id2 files. portion size is: file_size/num_threads
    int thread_id = (int)id % num_threads; // total_sampled;
    long long par_sen[NUM_LANG][MAX_SENTENCE_LENGTH];
    long long fi_size;
    int line_num = 0, cur_line = 0;
    
    real *syn0_e = syn0s[lang_id1], *syn0_f = syn0s[lang_id2];
    real deltas[layer_size];
    
    //seek for the position of the current thread
    FILE *fi_par = fopen(multi_context_file, "rb");
    fseek(fi_par, 0, SEEK_END);
    fi_size = ftell(fi_par);
    fseek(fi_par, fi_size / (long long)num_threads * (long long)id, SEEK_SET);
    line_num = par_line_num / (long long)num_threads;
    
    //skip the current line
    if((long long)id!=0) ReadSent(fi_par, par_sen);
    
    // Continue training while monolingual models are still training
    while (cur_line < line_num) {
        ReadSent(fi_par, par_sen);
        cur_line ++;
        BilBOWASentenceUpdate(par_sen, deltas);
    } // while training loop
    fclose(fi_par);
    pthread_exit(NULL);
}

void TrainMultiModel(){
    long a, b, c;
    pthread_t *pt = (pthread_t *)malloc(num_threads * sizeof(pthread_t));
    real len;
    start = clock();
    printf("\nStarting training multilingual text model using file %s\n", multi_context_file);
    
    for (a = 0; a < num_threads; a++) pthread_create(&pt[a], NULL, BilbowaThread, (void *)a);
    for (a = 0; a < num_threads; a++) pthread_join(pt[a], NULL);
}

void TrainModel(){
    long long i;
    
    for (i=0;i<NUM_LANG;i++)
        TrainModel(KG_VOCAB, i);
    
    for (i=0;i<NUM_LANG;i++)
        TrainModel(TEXT_VOCAB, i);
    
    //align cross lingual words
    TrainMultiModel();
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
    int i, j;
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
        printf("\nExamples:\n");
        printf("./mlmpme -mono_anchor1 en_anchor.txt -mono_anchor2 zh_anchor.txt -mono_kg1 en_kg.txt -mono_kg2 zh_kg.txt -multi_kg multi_kg.txt -multi_context multi_context.txt -output1 ./en_vec/ -output2 ./zh_vec/ -save_mono_vocab1 ./en_vocab/ -save_mono_vocab2 ./zh_vocab/ -read_cross_link cross_links.txt -size 200 -window 5 -sample 1e-4 -negative 5 -threads 63  -save_iter 1 -iter 3\n\n");
        return 0;
    }
    
    multi_context_file[0]=0;
    cross_link_file[0]=0;
    for(i=0;i<NUM_LANG;i++){
        output_path[i][0]=0;
        read_mono_vocab_path[i][0]=0;
        save_mono_vocab_path[i][0]=0;
    }
    
    if ((i = ArgPos((char *)"-multi_context", argc, argv)) > 0) strcpy(multi_context_file, argv[i + 1]);
    if ((i = ArgPos((char *)"-read_cross_link", argc, argv)) > 0) strcpy(cross_link_file, argv[i + 1]);
    
    for(i=0;i<NUM_LANG;i++){
        sprintf(temp_arg, "-mono_anchor%d", i);
        if ((i = ArgPos(temp_arg, argc, argv)) > 0) strcpy(model[TEXT_VOCAB][i]->train_file, argv[i + 1]);
        sprintf(temp_arg, "-mono_kg%d", i);
        if ((i = ArgPos(temp_arg, argc, argv)) > 0) strcpy(model[KG_VOCAB][i]->train_file, argv[i + 1]);
        sprintf(temp_arg, "-output%d", i);
        if ((i = ArgPos(temp_arg, argc, argv)) > 0) strcpy(output_path[i], argv[i + 1]);
        sprintf(temp_arg, "-save_mono_vocab%d", i);
        if ((i = ArgPos(temp_arg, argc, argv)) > 0) strcpy(save_mono_vocab_path[i], argv[i + 1]);
        sprintf(temp_arg, "-read_mono_vocab%d", i);
        if ((i = ArgPos(temp_arg, argc, argv)) > 0) strcpy(read_mono_vocab_path[i], argv[i + 1]);
    }
    
    if ((i = ArgPos((char *)"-size", argc, argv)) > 0) layer_size = atoi(argv[i + 1]);
    if ((i = ArgPos((char *)"-debug", argc, argv)) > 0) debug_mode = atoi(argv[i + 1]);
    if ((i = ArgPos((char *)"-alpha", argc, argv)) > 0) alpha = atof(argv[i + 1]);
    if ((i = ArgPos((char *)"-window", argc, argv)) > 0) window = atoi(argv[i + 1]);
    if ((i = ArgPos((char *)"-sample", argc, argv)) > 0) sample = atof(argv[i + 1]);
    if ((i = ArgPos((char *)"-negative", argc, argv)) > 0) negative = atoi(argv[i + 1]);
    if ((i = ArgPos((char *)"-threads", argc, argv)) > 0) num_threads = atoi(argv[i + 1]);
    if ((i = ArgPos((char *)"-iter", argc, argv)) > 0) iter = atoi(argv[i + 1]);
    if ((i = ArgPos((char *)"-min_count", argc, argv)) > 0) min_count = atoi(argv[i + 1]);
    if ((i = ArgPos((char *)"-save_iter", argc, argv)) > 0) save_iter = atoi(argv[i + 1]);
    
    expTable = (real *)malloc((EXP_TABLE_SIZE + 1) * sizeof(real));
    for (i = 0; i < EXP_TABLE_SIZE; i++) {
        expTable[i] = exp((i / (real)EXP_TABLE_SIZE * 2 - 1) * MAX_EXP); // Precompute the exp() table
        expTable[i] = expTable[i] / (expTable[i] + 1);                   // Precompute f(x) = x / (x + 1)
    }
    
    for (i=0; i< NUM_LANG; i++){
        // training senses also using anchors
        strcpy(model[SENSE_VOCAB][i]->train_file, model[TEXT_VOCAB][i]->train_file);
        
        // initialize output file
        if(output_path[i][0]!=0){
            sprintf(model[TEXT_VOCAB][i]->output_file, "%svectors%d_word.dat", output_path[i], i);
            sprintf(model[KG_VOCAB][i]->output_file, "%svectors%d_entity.dat", output_path[i], i);
            sprintf(model[SENSE_VOCAB][i]->output_file, "%svectors%d_senses.dat", output_path[i], i);
        }
        
        //initialize save vocab file
        if(save_mono_vocab_path[i][0]!=0){
            sprintf(model[TEXT_VOCAB][i]->save_vocab_file, "%svocab%d_word.txt", save_mono_vocab_path[i], i);
            sprintf(model[KG_VOCAB][i]->save_vocab_file, "%svocab%d_entity.txt", save_mono_vocab_path[i], i);
            sprintf(model[SENSE_VOCAB][i]->save_vocab_file, "%svocab%d_sense.txt", save_mono_vocab_path[i], i);
        }
        
        // read vocab
        if(read_mono_vocab_path[i][0]!=0){
            sprintf(model[TEXT_VOCAB][i]->read_vocab_file, "%svocab%d_word.txt", read_mono_vocab_path[i], i);
            sprintf(model[KG_VOCAB][i]->read_vocab_file, "%svocab%d_entity.txt", read_mono_vocab_path[i], i);
            sprintf(model[SENSE_VOCAB][i]->read_vocab_file, "%svocab%d_sense.txt", read_mono_vocab_path[i], i);
        }
        
        // initialize vocab type
        model[TEXT_VOCAB][i]->vocab_type = TEXT_VOCAB;
        model[KG_VOCAB][i]->vocab_type = KG_VOCAB;
        model[SENSE_VOCAB][i]->vocab_type = SENSE_VOCAB;
        
        //read vocab & initilize text model and kg model，//use read_xx_path to decide whether use pre-trained xx model
        //the init order is necessary, words->entity->senses
        InitModel(0, i);
        InitModel(1, i);
        InitModel(2, i);
    }
    if(cross_link_file[0]!=0)
        InitMultiModel(cross_link_file);
    
    //start training
    local_iter = 0;
    if (save_iter <=0 || save_iter > iter) save_iter = iter;
    while(local_iter<iter){
        local_iter++;
        printf("Start jointly training the %d time... ", local_iter);
        TrainModel();
        if (local_iter%save_iter==0){
            printf("saving results...\n");
            for (i=0;i<NUM_LANG;i++){
                SaveVocab(model[TEXT_VOCAB][i]);
                SaveVocab(model[KG_VOCAB][i]);
                SaveVocab(model[SENSE_VOCAB][i]);
            }
        }
    }
    return 0;
}