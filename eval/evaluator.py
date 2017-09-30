import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
import datetime
import codecs

class Evaluator:
    def __init__(self):
        self.log_file = ''
        self.feature_list = ['cand_size', 'pem', 'pe','largest_pe','str_sim1', 'str_sim2','str_sim3','str_sim4','str_sim5','csim1', 'crank1','csim2', 'crank2','csim3', 'crank3', 'csim4', 'crank4']

    def loadFeatures(self, filename):
        features = pd.read_csv(filename, header = None, names = ['doc_id', 'mention_id', 'wiki_id', 'cand_id',\
                                              'cand_size', 'pem', 'pe','largest_pe',\
                                                'str_sim1', 'str_sim2','str_sim3','str_sim4','str_sim5',\
                                                'esim1', 'erank1', 'esim2', 'erank2','esim3', 'erank3',\
                                                'csim1', 'crank1','csim2', 'crank2','csim3', 'crank3','csim4', 'crank4','csim5', 'crank5'])
        print 'load finished!'
        features = features.fillna(0)
        label = []
        for row in features.loc[:, ['wiki_id', 'cand_id']].itertuples():
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
        test_x.insert(0,'score', pred)

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
                fout.write('{0}\n'.format(','.join(self.feature_list)))
                fout.write("micro precision : {0}({1}/{2}), macro precision : {3}\n".format(micro_p, total_mention_tp, total_mention_num, macro_p))
                fout.write("*******************************************************************************************\n")

if __name__ == '__main__':
    output_path = '/home/caoyx/data/log/'
    train_feature_file = '/home/caoyx/data/train15_file.csv'
    test_feature_file = '/home/caoyx/data/eval15_file.csv'
    ans_file = output_path + 'conll_ans.mpme'
    predict_file = output_path + 'conll_pred.mpme'
    log_file = output_path + 'conll_log'
    eval = Evaluator()
    eval.log_file = log_file
    starttime = datetime.datetime.now()
    eval.gbdt(train_feature_file, test_feature_file, predict_file = predict_file, ans_file = ans_file)
    endtime = datetime.datetime.now()
    print (endtime - starttime).seconds
