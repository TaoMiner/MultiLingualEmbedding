import os

class Options:
    en = 'eng'
    zh = 'cmn'
    es = 'spa'
    entity_type = 'entity'
    word_type = 'word'
    sense_type = 'sense'

    doc_type = ['nw','df']

    root_path = '/home/caoyx/data/'
    ppr_candidate_file = '/home/caoyx/data/conll/ppr_candidate'
    yago_candidate_file = '/home/caoyx/JTextKgForEL/data/conll/yago_candidates'

    cross_links_file = '/home/caoyx/data/paradata/cross_links_all_id.dat'

    aida_file = '/home/caoyx/data/conll/AIDA-YAGO2-dataset.tsv'
    train_feature_file = '/home/caoyx/data/train15_file.csv'
    eval_feature_file = '/home/caoyx/data/eval15_file.csv'
    res_file = '/home/caoyx/data/log/conll_pred.mpme'
    kbid_map_file = '/home/caoyx/data/kbp/id.key'

    output_file = '../etc/output_senselink'

    @staticmethod
    def getFeatureFile(year, isEval, lang, docType):
        tmp = 'eval' if isEval else 'training'
        return Options.root_path + 'kbp/' + str(year) + '_' + tmp + '_' + lang + '_' + docType + '.feature'

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
        return Options.getKBPRootPath() + str(year) + tmp_path + '/tac_kbp_2015_tedl_' + tmp_type + '_gold_standard_entity_mentions.tab'

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
        vocab_index = '1' if Options.getLangStr(lang) == 'en' else '2'
        return Options.getExpPath(exp) + Options.getLangStr(lang) + 'vec/vectors' + vocab_index + '_' + type + str(it)

    @staticmethod
    # type: 'w': word, 'e' : entity, 's' : sense
    def getExpVocabFile(exp, lang, type):
        vocab_index = '1' if Options.getLangStr(lang) == 'en' else '2'
        return Options.getExpPath(exp) + Options.getLangStr(lang) + 'vec/vocab' + vocab_index + '_' + type + '.txt'

    @staticmethod
    def getRedirectFile(lang):
        return Options.root_path + 'dump20170401/' + Options.getLangStr(lang) + 'wiki_cl/redirect_article_title'

if __name__ == '__main__':
    print(Options.getKBPAnsFile(2015,False))