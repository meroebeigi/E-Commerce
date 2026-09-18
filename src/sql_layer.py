"""Execute every SQL file and reconcile independently against Python aggregates."""
import sqlite3
import numpy as np
import pandas as pd

def export_and_verify(model,root,analytics):
    out=root/'output'; results={}; checks=[]
    with sqlite3.connect(out/'olist.sqlite') as db:
        for name,df in model.items():
            x=df.copy()
            for col in x:
                if str(x[col].dtype)=='boolean':x[col]=x[col].astype('Int64')
                if pd.api.types.is_datetime64_any_dtype(x[col]):x[col]=x[col].dt.strftime('%Y-%m-%d %H:%M:%S')
            x.to_sql(name,db,if_exists='replace',index=False,chunksize=5000)
        for path in sorted((root/'sql').glob('*.sql')):
            result=pd.read_sql_query(path.read_text(encoding='utf-8'),db)
            result.to_csv(out/(path.stem+'.csv'),index=False);results[path.stem]=result
    def check(label,a,b):
        passed=bool(np.allclose(np.asarray(a,dtype=float),np.asarray(b,dtype=float),rtol=1e-9,atol=1e-6,equal_nan=True))
        checks.append({'check':label,'passed':passed})
        if not passed:raise AssertionError(label)
    k=analytics['kpis'].set_index('metric').value
    q=results['01_executive_kpis'].iloc[0]
    for col,name in [('gmv','GMV'),('orders','Orders'),('customers','Customers'),('aov','AOV'),('repeat_customer_rate','Repeat customer rate'),('late_delivery_rate','Late delivery rate')]:
        check('SQL '+col,q[col],k[name])
    q=results['02_monthly_growth'].set_index('purchase_month')
    p=analytics['monthly'].set_index('purchase_month').reindex(q.index)
    for col in ['gmv','orders','customers','aov']:check('SQL monthly '+col,q[col],p[col])
    for prefix,key,label in [('04_product_performance','category','categories'),('05_seller_performance','seller_id','sellers')]:
        q=results[prefix].set_index(key);p=analytics[label].set_index(key).reindex(q.index)
        for col in ['gmv','orders','late_delivery_rate']:check('SQL '+label+' '+col,q[col],p[col])
    q=results['03_customer_analysis'].set_index('customer_unique_id');p=analytics['customers'].set_index('customer_unique_id').reindex(q.index)
    check('SQL customer GMV',q.gmv,p.monetary)
    q=results['06_retention_analysis'].set_index(['cohort_month','age_month'])
    p=analytics['cohorts'].set_index(['cohort_month','age_month']).reindex(q.index)
    check('SQL cohort retention',q.retention_rate,p.retention_rate)
    return pd.DataFrame(checks)
