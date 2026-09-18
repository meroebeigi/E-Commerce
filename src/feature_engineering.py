"""Customer features and censoring-aware retention."""
import numpy as np
import pandas as pd

def customer_features(model):
    f=model['FactOrders']; c=f[f.commercial_eligible].copy()
    snapshot=c.order_purchase_timestamp.max().normalize()+pd.Timedelta(days=1)
    x=c.groupby('customer_unique_id').agg(last_purchase=('order_purchase_timestamp','max'),
        first_purchase=('order_purchase_timestamp','min'),frequency=('order_id','nunique'),
        monetary=('merchandise_value','sum'),aov=('merchandise_value','mean'),
        items_per_order=('number_of_items','mean'),average_freight=('freight_value','mean'))
    x['recency']=(snapshot-x.last_purchase.dt.normalize()).dt.days
    x['snapshot_date']=snapshot
    # Percentile ranks preserve ties. Frequency is discrete to avoid artificial splitting of one-time buyers.
    x['r_score']=np.ceil(x.recency.rank(method='average',pct=True,ascending=False)*4).clip(1,4).astype(int)
    x['m_score']=np.ceil(x.monetary.rank(method='average',pct=True)*4).clip(1,4).astype(int)
    x['f_score']=np.select([x.frequency.eq(1),x.frequency.eq(2),x.frequency.eq(3)],[1,2,3],default=4)
    x['segment']=np.select([
        x.frequency.ge(2)&x.r_score.ge(3)&x.m_score.ge(3),
        x.m_score.eq(4)&x.r_score.le(2),
        x.m_score.eq(4),x.frequency.ge(2),x.r_score.eq(4),x.r_score.ge(3)],
        ['Champions','Previously high value / inactive','High value','Repeat buyers','Recent','Potential second purchase'],
        default='Low recent engagement')
    summary=x.groupby('segment').agg(customers=('frequency','size'),gmv=('monetary','sum'),orders=('frequency','sum'),
        average_recency=('recency','mean'),average_frequency=('frequency','mean'),average_monetary=('monetary','mean'))
    summary['aov']=summary.gmv/summary.orders;summary['customer_share']=summary.customers/len(x);summary['gmv_share']=summary.gmv/summary.gmv.sum()
    return x.reset_index(),summary.reset_index()

def cohorts(f):
    c=f[f.commercial_eligible].copy()
    c['cohort']=c.first_purchase_date.dt.to_period('M')
    c['month']=c.order_purchase_timestamp.dt.to_period('M')
    c['age']=c.month.astype('int64')-c.cohort.astype('int64')
    sizes=c.groupby('cohort').customer_unique_id.nunique()
    observed_end=c.month.max()
    # Last observed eligible month is conservatively excluded as possibly incomplete.
    last_complete=observed_end-1
    rows=[]
    for cohort,size in sizes.items():
        for age in range(int(observed_end.ordinal-cohort.ordinal)+1):
            observable=(cohort+age)<=last_complete
            active=c.loc[(c.cohort==cohort)&(c.age==age),'customer_unique_id'].nunique()
            rows.append({'cohort_month':str(cohort),'age_month':age,'cohort_size':int(size),
                'active_customers':int(active) if observable else np.nan,
                'retention_rate':active/size if observable else np.nan,'fully_observed':observable})
    return pd.DataFrame(rows)

def second_purchase(f,horizon=90):
    c=f[f.commercial_eligible].sort_values(['order_purchase_timestamp','order_id'])
    end=c.order_purchase_timestamp.max()
    first=c.groupby('customer_unique_id').order_purchase_timestamp.min()
    second=c[c.customer_order_number.eq(2)].set_index('customer_unique_id').order_purchase_timestamp
    x=first.to_frame('first_purchase').join(second.rename('second_purchase'))
    x['eligible']=x.first_purchase.le(end-pd.Timedelta(days=horizon))
    x['second_within_horizon']=(x.second_purchase-x.first_purchase).dt.total_seconds().div(86400).le(horizon)
    x['first_month']=x.first_purchase.dt.strftime('%Y-%m')
    result=x[x.eligible].groupby('first_month').agg(eligible_customers=('eligible','size'),second_buyers=('second_within_horizon','sum'))
    result['second_purchase_rate']=result.second_buyers/result.eligible_customers
    result['horizon_days']=horizon
    return result.reset_index()

def prediction_features(model):
    """Features available just after approval; no realized delivery or review fields in X."""
    f=model['FactOrders'];i=model['FactOrderItems']
    p=model['DimProduct'];s=model['DimSeller']
    x=i.merge(p[['product_id','category','product_weight_g','product_length_cm','product_height_cm','product_width_cm']],on='product_id',validate='many_to_one')
    x=x.merge(s[['seller_id','seller_state']],on='seller_id',validate='many_to_one')
    x=x.merge(f[['order_id','customer_state']],on='order_id',validate='many_to_one')
    x['same_state']=x.seller_state.eq(x.customer_state).astype(int)
    x['volume_cm3']=x.product_length_cm*x.product_height_cm*x.product_width_cm
    a=x.groupby('order_id').agg(mean_weight=('product_weight_g','mean'),mean_volume=('volume_cm3','mean'),same_state_share=('same_state','mean'))
    # Deterministic primary item: largest merchandise value then smallest item sequence.
    primary=x.sort_values(['order_id','price','order_item_id'],ascending=[True,False,True]).drop_duplicates('order_id')[['order_id','seller_state','category']]
    out=f[f.delivery_eligible & f.has_items].merge(a,on='order_id',validate='one_to_one').merge(primary,on='order_id',validate='one_to_one')
    out['month']=out.order_purchase_timestamp.dt.month
    out['weekday']=out.order_purchase_timestamp.dt.dayofweek
    out['promised_days']=(out.order_estimated_delivery_date-out.order_purchase_timestamp.dt.normalize()).dt.days
    out['label_available_at']=out.order_delivered_customer_date
    features=['merchandise_value','freight_value','number_of_items','seller_count','mean_weight','mean_volume',
              'same_state_share','month','weekday','promised_days','customer_state','seller_state','category']
    assert not set(features)&{'review_score','delivery_days','delay_days','order_delivered_customer_date','is_late'}
    return out,features
