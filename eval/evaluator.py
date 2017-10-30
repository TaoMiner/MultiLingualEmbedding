import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
import datetime
import codecs
from options import Options

class Evaluator:
    def __init__(self):
        self.log_file = ''
        self.feature_list = ['kb_cand_size', 'kb_pem', 'kb_pe','kb_largest_pe',\
                             'trans_str_sim1', 'trans_str_sim2','trans_str_sim3','trans_str_sim4','trans_str_sim5',\
                             'cur_str_sim1', 'cur_str_sim2', 'cur_str_sim3','cur_str_sim4', 'cur_str_sim5', \
                             'esim1', 'erank1', 'esim2', 'erank2', 'esim3', 'erank3', 'esim4', 'erank4', \
                             'csim1', 'crank1','csim2', 'crank2','csim3', 'crank3']

    def loadFeatures(self, filename):
        features = pd.read_csv(filename, header = None, names = ['doc_id', 'mention_id', 'wiki_id', 'kb_cand_id',\
                                              'kb_cand_size', 'kb_pem', 'kb_pe','kb_largest_pe', \
                                                'cur_pem', 'cur_pe', 'cur_largest_pe', \
                                                 'trans_str_sim1', 'trans_str_sim2','trans_str_sim3','trans_str_sim4','trans_str_sim5', \
                                                'cur_str_sim1', 'cur_str_sim2', 'cur_str_sim3','cur_str_sim4', 'cur_str_sim5', \
                                                'esim1', 'erank1', 'esim2', 'erank2','esim3', 'erank3', 'esim4', 'erank4',\
                                                'csim1', 'crank1','csim2', 'crank2','csim3', 'crank3'])
        print('load finished!')
        features = features.fillna(0)
        label = []
        for row in features.loc[:, ['wiki_id', 'kb_cand_id']].itertuples():
            label.append(1 if row[1] == row[2] else 0)
        features.insert(0, 'label', label)
        return features

    def gbdt(self, train_feature_file, test_feature_file, predict_file = None, ans_file = None, learning_rate=0.02, n_estimators=10000, max_depth=4):
        train_feature = self.loadFeatures(train_feature_file)
        test_feature = self.loadFeatures(test_feature_file)
        gbdt=GradientBoostingRegressor(
                                          loss='ls'
                                        , learning_rate=learning_rate
                                        , n_estimators=n_estimators
                                        , subsample=1
                                        , min_samples_split=2
                                        , min_samples_leaf=1
                                        , max_depth=max_depth
                                        , init=None
                                        , random_state=None
                                        , max_features=None
                                        , alpha=0.9
                                        , verbose=0
                                        , max_leaf_nodes=None
                                        , warm_start=False
                                        )
        #self.train_x = self.train.loc[:, 'cand_size':'crank5'].values
        train_x = train_feature.loc[:, self.feature_list].values
        train_y = train_feature.loc[:, 'label'].values

        test_x = test_feature.loc[:, self.feature_list].values
        test_y = test_feature.loc[:, 'label'].values

        gbdt.fit(train_x, train_y)
        print("train finished!")
        pred=gbdt.predict(test_x)
        test_feature.insert(0,'score', pred)

        #testa's doc_id 947-1162
        total_p = 0.0
        total_mention_tp = 0
        total_doc_num = 0
        total_mention_num = 0
        # for test set
        grouped = test_feature.groupby('doc_id')
        for doc_id, df_doc in grouped:
            if df_doc.shape[0]==0:continue
            d_mention_num = df_doc['mention_id'].iloc[-1]+1
            #max score's index of mention's candidates
            idx = df_doc.groupby('mention_id')['score'].idxmax()
            # restore predicted result
            tmp_res = df_doc.loc[idx]
            if not isinstance(predict_file, type(None)):
                tmp_res.to_csv(predict_file, mode='a', header=False, index=False)
            # record answers
            if not isinstance(ans_file, type(None)):
                ans = df_doc.loc[df_doc[df_doc.label == 1].index]
                ans.to_csv(ans_file, mode='a', header=False, index=False)

            #num of label with 1 with max score
            d_tp = tmp_res[tmp_res.label == 1].shape[0]
            total_p += float(d_tp)/d_mention_num
            total_mention_tp += d_tp
            total_doc_num += 1
            total_mention_num += d_mention_num
        micro_p = float(total_mention_tp)/total_mention_num
        macro_p = total_p/total_doc_num
        print("micro precision : %f(%d/%d), macro precision : %f" % (micro_p, total_mention_tp, total_mention_num, macro_p))
        if len(self.log_file) > 0:
            with codecs.open(self.log_file, 'a', encoding='UTF-8') as fout:
                fout.write('*******************************************************************************************\n')
                fout.write('train feature file:{0}, test feature file:{1}, answer file:{2}, predicted file:{3}\n'.format(train_feature_file, test_feature_file, predict_file, ans_file))
                fout.write('total {0} candidates! use features:{1} \n'.format(len(test_feature), ','.join(self.feature_list)))
                fout.write("micro precision : {0}({1}/{2}), macro precision : {3}\n".format(micro_p, total_mention_tp, total_mention_num, macro_p))
                fout.write("*******************************************************************************************\n")

if __name__ == '__main__':
    cur_lang = Options.en
    doc_type = Options.doc_type[0]
    corpus_year = 2015
    exp = 'exp9'

    eval = Evaluator()
    eval.log_file = Options.getLogFile('eval1.log')
    starttime = datetime.datetime.now()
    eval.gbdt(Options.getFeatureFile(corpus_year,False,cur_lang, doc_type, exp), Options.getFeatureFile(corpus_year,True,cur_lang, doc_type, exp), predict_file = Options.getLogFile('eval_predict.log'), ans_file = Options.getLogFile('eval_ans.log'))
    endtime = datetime.datetime.now()
    print("{0}".format((endtime - starttime).seconds))
