"""Reproducible customer clustering and a temporally evaluated risk model."""
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler,OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier,HistGradientBoostingClassifier
from sklearn.metrics import (silhouette_score,adjusted_rand_score,average_precision_score,
    roc_auc_score,precision_score,recall_score,f1_score,confusion_matrix)
from sklearn.inspection import permutation_importance
from .feature_engineering import prediction_features

SEED=42

def cluster_customers(customers):
    cols=['recency','frequency','monetary','items_per_order']
    x=customers[cols].copy()
    # Monetary and AOV are strongly related with mostly one-time buyers: do not double-weight them.
    cap=x.quantile(.99)
    treatment=pd.DataFrame({'feature':cols,'skew_before':x.skew().values,
        'upper_cap_99pct':cap.values,'capped_customers':x.gt(cap).sum().values})
    transformed=np.log1p(x.clip(upper=cap,axis=1))
    z=StandardScaler().fit_transform(transformed)
    scores=[];fits={}
    for k in range(2,7):
        fit=KMeans(n_clusters=k,n_init=10,random_state=SEED).fit(z)
        other=KMeans(n_clusters=k,n_init=10,random_state=SEED+1).fit(z)
        fits[k]=fit
        scores.append({'k':k,'inertia':fit.inertia_,
            'silhouette':silhouette_score(z,fit.labels_,sample_size=min(4000,len(z)),random_state=SEED),
            'seed_stability_ari':adjusted_rand_score(fit.labels_,other.labels_),
            'smallest_cluster_share':pd.Series(fit.labels_).value_counts(normalize=True).min()})
    scores=pd.DataFrame(scores)
    eligible=scores[(scores.smallest_cluster_share>=.02)&(scores.seed_stability_ari>=.8)]
    chosen=int((eligible if len(eligible) else scores).sort_values('silhouette',ascending=False).iloc[0].k)
    fit=fits[chosen]; labeled=customers.copy();labeled['cluster']=fit.labels_
    profile=labeled.groupby('cluster').agg(customers=('customer_unique_id','size'),recency=('recency','mean'),
        frequency=('frequency','mean'),monetary=('monetary','mean'),aov=('aov','mean'),items_per_order=('items_per_order','mean'))
    # Names derived from measured features; cluster ID suffix only disambiguates similar profiles.
    reference=customers[['recency','frequency','monetary','items_per_order']].mean()
    def name(row):
        time='More recent' if row.recency<=reference.recency else 'Less recent'
        value='above-average value' if row.monetary>=reference.monetary else 'below-average value'
        behavior='repeat-oriented' if row.frequency>=1.5 else ('larger baskets' if row.items_per_order>=1.5 else 'single-purchase dominated')
        return f'{time}, {value}, {behavior} ({row.name+1})'
    profile['business_name']=profile.apply(name,axis=1)
    labeled['cluster_name']=labeled.cluster.map(profile.business_name)
    scores['selected']=scores.k.eq(chosen)
    return labeled,profile.reset_index(),scores,treatment

def classify_late_delivery(model):
    data,features=prediction_features(model)
    data=data.sort_values(['order_purchase_timestamp','order_id']).reset_index(drop=True)
    # Boundaries on date prevent same-day splitting. Purge outcomes not yet known at the next boundary.
    a=data.order_purchase_timestamp.quantile(.6).normalize()
    b=data.order_purchase_timestamp.quantile(.8).normalize()
    train=data[(data.order_purchase_timestamp<a)&(data.label_available_at<a)]
    valid=data[(data.order_purchase_timestamp>=a)&(data.order_purchase_timestamp<b)&(data.label_available_at<b)]
    test=data[data.order_purchase_timestamp>=b]
    if min(len(train),len(valid),len(test))<100:
        raise ValueError('Insufficient temporal sample for model evaluation')
    numeric=[c for c in features if c not in ['customer_state','seller_state','category']]
    categorical=[c for c in features if c not in numeric]
    def preprocessing():
        return ColumnTransformer([
            ('numeric',Pipeline([('impute',SimpleImputer(strategy='median')),('scale',StandardScaler())]),numeric),
            ('categorical',Pipeline([('impute',SimpleImputer(strategy='most_frequent')),
             ('encode',OneHotEncoder(handle_unknown='ignore',sparse_output=False,min_frequency=30))]),categorical)])
    estimators={
        'Logistic regression':LogisticRegression(class_weight='balanced',max_iter=1000,random_state=SEED),
        'Random forest':RandomForestClassifier(n_estimators=180,max_depth=12,min_samples_leaf=15,class_weight='balanced',n_jobs=2,random_state=SEED),
        'Gradient boosting':HistGradientBoostingClassifier(max_iter=150,max_leaf_nodes=15,learning_rate=.07,random_state=SEED)}
    ytrain=train.is_late.astype(int); yval=valid.is_late.astype(int);ytest=test.is_late.astype(int)
    candidates=[];pipelines={};threshold_rows=[]
    for name,est in estimators.items():
        pipe=Pipeline([('preprocess',preprocessing()),('model',est)])
        pipe.fit(train[features],ytrain)
        prob=pipe.predict_proba(valid[features])[:,1]
        for threshold in np.linspace(.02,.98,49):
            pred=prob>=threshold
            threshold_rows.append({'model':name,'threshold':threshold,'precision':precision_score(yval,pred,zero_division=0),
                'recall':recall_score(yval,pred,zero_division=0),'f1':f1_score(yval,pred,zero_division=0),
                'alert_share':float(pred.mean())})
        candidates.append({'model':name,'validation_ap':average_precision_score(yval,prob),'validation_roc_auc':roc_auc_score(yval,prob)})
        pipelines[name]=pipe
    comparison=pd.DataFrame(candidates).sort_values('validation_ap',ascending=False)
    chosen=comparison.iloc[0]['model'];thresholds=pd.DataFrame(threshold_rows)
    threshold=float(thresholds[thresholds.model.eq(chosen)].sort_values(['f1','threshold'],ascending=[False,False]).iloc[0].threshold)
    # Final holdout is evaluated once, after model and threshold selection using validation only.
    pipe=pipelines[chosen];prob=pipe.predict_proba(test[features])[:,1];pred=prob>=threshold
    tn,fp,fn,tp=confusion_matrix(ytest,pred,labels=[0,1]).ravel()
    metrics={'selected_model':chosen,'threshold':threshold,'train_orders':len(train),'validation_orders':len(valid),'test_orders':len(test),
        'validation_start':str(a),'test_start':str(b),'test_prevalence':float(ytest.mean()),
        'test_average_precision':float(average_precision_score(ytest,prob)),
        'test_roc_auc':float(roc_auc_score(ytest,prob)),'test_precision':float(precision_score(ytest,pred,zero_division=0)),
        'test_recall':float(recall_score(ytest,pred,zero_division=0)),'test_f1':float(f1_score(ytest,pred,zero_division=0)),
        'true_negatives':int(tn),'false_positives':int(fp),'false_negatives':int(fn),'true_positives':int(tp),
        'excluded_unmatured_labels':int(len(data)-len(train)-len(valid)-len(test))}
    sample=test.sample(min(2500,len(test)),random_state=SEED)
    imp=permutation_importance(pipe,sample[features],sample.is_late.astype(int),scoring='average_precision',n_repeats=3,random_state=SEED,n_jobs=1)
    importance=pd.DataFrame({'feature':features,'ap_drop_mean':imp.importances_mean,'ap_drop_std':imp.importances_std}).sort_values('ap_drop_mean',ascending=False)
    scored=test[['order_id','order_purchase_timestamp','is_late']].copy()
    scored['risk_probability']=prob;scored['alert']=pred
    return metrics,comparison,thresholds,importance,scored

def statistical_tests(f):
    from scipy.stats import mannwhitneyu
    d=f[f.delivery_eligible&f.review_eligible]
    c=f[f.commercial_eligible]
    comparisons=[('Review scores: late versus on-time',d.loc[d.is_late.fillna(False),'review_score'],d.loc[~d.is_late.fillna(False),'review_score']),
                 ('Order GMV: returning versus first',c.loc[c.is_returning,'merchandise_value'],c.loc[~c.is_returning,'merchandise_value'])]
    rows=[]
    for label,a,b in comparisons:
        test=mannwhitneyu(a,b,alternative='two-sided',method='asymptotic')
        rows.append({'comparison':label,'n_a':len(a),'n_b':len(b),'median_a':a.median(),'median_b':b.median(),
            'u_statistic':test.statistic,'p_value':test.pvalue,
            'rank_biserial_a_over_b':2*test.statistic/(len(a)*len(b))-1,
            'assumption_caveat':'Order observations may cluster within customer or seller; p-values are descriptive, not causal.'})
    out=pd.DataFrame(rows)
    out['p_bonferroni']=np.minimum(out.p_value*len(out),1)
    return out
