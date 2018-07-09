import os

class Options:
    en = 'eng'
    zh = 'cmn'
    es = 'spa'
    entity_type = 'entity'
    word_type = 'word'
    sense_type = 'sense'

    doc_type = ['nw','df','all']

    root_path = '/home/caoyx/data/'
    ppr_candidate_file = '/home/caoyx/data/conll/ppr_candidate'
    yago_candidate_file = '/home/caoyx/JTextKgForEL/data/conll/yago_candidates'

    cross_links_file = '/home/caoyx/data/paradata/cross_links_all_id.dat'
    entity_relatedness_file = '/home/caoyx/data/test_relatedness_id.dat'
    aida_file = '/home/caoyx/data/conll/AIDA-YAGO2-dataset.tsv'
    train_feature_file = '/home/caoyx/data/train15_file.csv'
    eval_feature_file = '/home/caoyx/data/eval15_file.csv'
    res_file = '/home/caoyx/data/log/conll_pred.mpme'
    kbid_map_file = '/home/caoyx/data/kbp/id.key'

    output_file = '../etc/output_senselink'

    wordsim353_file = root_path+'wordsim353_agreed.txt'

    @staticmethod
    def getFeatureFile(year, isEval, lang, docType, exp, round=0):
        tmp = 'eval' if isEval else 'training'
        if round>0:
            return Options.root_path + 'features/' + str(year) + '_' + tmp + '_' + lang + '_' + docType + '.feature'+str(round) +'_' + exp
        return Options.root_path + 'features/' + str(year) + '_' + tmp + '_' + lang + '_' + docType + '.feature_' + exp

    @staticmethod
    # type = {'train','testa','testb'}
    def getParFile(lang):
        return Options.root_path + 'paradata/para_contexts.en-' + Options.getLangStr(lang)

    @staticmethod
    # type = {'train','testa','testb'}
    def getConllFeatureFile(exp, type):
        return Options.root_path + 'features/conll_'+type+'.feature_' + exp

    @staticmethod
    def getNlpToolUrl(lang):
        url = ''
        if lang == Options.en:
            url = 'http://localhost:9001'
        elif lang == Options.es:
            url = 'http://localhost:9002'
        elif lang == Options.zh:
            url = '/home/caoyx/data/dict.txt.big'
        return url

    @staticmethod
    def getLogPath():
        return Options.root_path + 'log/'

    @staticmethod
    def getLogFile(filename):
        return Options.getLogPath() + filename

    @staticmethod
    def getKBPRootPath():
        return Options.root_path + 'kbp/LDC2017E03_TAC_KBP_Entity_Discovery_and_Linking_Comprehensive_Training_and_Evaluation_Data_2014-2016/data/'

    @staticmethod
    def getKBPAnsFile(year, isEval):
        tmp_path = '/eval' if isEval else '/training'
        tmp_type = 'evaluation' if isEval else 'training'
        tmp_edl = '_tedl_' if year == 2015 else '_edl_'
        return Options.getKBPRootPath() + str(year) + tmp_path + '/tac_kbp_' + str(year) + tmp_edl + tmp_type + '_gold_standard_entity_mentions.tab'

    # languages = ['eng', 'cmn', 'spa']
    # doc_type = ['nw', 'df', 'newswire', 'discussion_forum']
    @staticmethod
    def getKBPDataPath(year, isEval, lang, docType):
        if year == 2015:
            tmp_path = '/eval' if isEval else '/training'
            docTypePath = '/newswire/' if docType == Options.doc_type[0] else '/discussion_forum/'
        else:
            tmp_path = '/eval/'
            docTypePath = '/nw/' if docType == Options.doc_type[0] else '/df/'
        tmp_source = '/source_documents/' if isEval else '/source_docs/'

        return Options.getKBPRootPath() + str(year) + tmp_path + tmp_source + lang + docTypePath

    @staticmethod
    def getTransFile(lang):
        return Options.root_path + 'kbp/' + Options.getLangStr(lang) +'-en'

    @staticmethod
    def getLangStr(lang):
        tmp_lang = 'en'
        if lang == 'eng' :
            tmp_lang = 'en'
        elif lang == 'spa':
            tmp_lang = 'es'
        elif lang == 'cmn':
            tmp_lang = 'zh'
        return tmp_lang

    @staticmethod
    def getLangName(lang):
        tmp_lang = ''
        if lang == Options.en:
            tmp_lang = 'English'
        elif lang == Options.es:
            tmp_lang = 'Spanish'
        elif lang == Options.zh:
            tmp_lang = 'Chinese'
        return tmp_lang

    @staticmethod
    def getLangType(lang):
        if lang == 'en':
            return Options.en
        if lang == 'es':
            return Options.es
        if lang == 'zh':
            return Options.zh
        return ''

    @staticmethod
    def getEntityIdFile(lang = 'eng'):
        return Options.root_path + 'dump20170401/' + Options.getLangStr(lang) + 'wiki_cl/vocab_entity.dat'

    @staticmethod
    def getMentionCountFile(lang):
        return Options.root_path + 'dump20170401/' + Options.getLangStr(lang) + 'wiki_cl/entity_prior'

    @staticmethod
    def getEvalMentionVocabFile(lang):
        return Options.root_path + 'eval_mention_dic.' + Options.getLangStr(lang)

    @staticmethod
    def getEvalCandidatesFile(lang):
        return Options.root_path + 'candidates.' + Options.getLangStr(lang)

    @staticmethod
    def getExpPath(exp):
        return Options.root_path + 'etc/' + exp + '/'

    @staticmethod
    # type: 'w': word, 'e' : entity, 's' : sense
    def getExpVecFile(exp, lang, type, it):
        return Options.getExpPath(exp) + Options.getLangStr(lang) + 'vec/vectors_' + type + str(it)

    @staticmethod
    # type: 'w': word, 'e' : entity, 's' : sense
    def getExpVocabFile(lang, type):
        return Options.root_path + 'etc/vocab/'+ Options.getLangStr(lang) +'vocab/vocab_' + type + '.txt'

    @staticmethod
    def getRedirectFile(lang):
        return Options.root_path + 'dump20170401/' + Options.getLangStr(lang) + 'wiki_cl/redirect_article_title'

    @staticmethod
    def getBiLexFile(lang):
        if lang == Options.zh:
            return Options.root_path + 'wordTranslation/all.zh-en.lex'
        elif lang == Options.es:
            return Options.root_path + 'wordTranslation/all.es-en.lex'
        return ''
if __name__ == '__main__':
    print(Options.getKBPAnsFile(2015,False))