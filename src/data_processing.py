"""Grain-safe Olist model. No payment-to-item expansion is permitted."""
from pathlib import Path
import hashlib
import numpy as np
import pandas as pd

FILES = {
    'orders': 'olist_orders_dataset.csv',
    'customers': 'olist_customers_dataset.csv',
    'items': 'olist_order_items_dataset.csv',
    'payments': 'olist_order_payments_dataset.csv',
    'products': 'olist_products_dataset.csv',
    'sellers': 'olist_sellers_dataset.csv',
    'reviews': 'olist_order_reviews_dataset.csv',
    'translation': 'product_category_name_translation.csv',
}
KEYS = {'orders':['order_id'], 'customers':['customer_id'],
        'items':['order_id','order_item_id'], 'payments':['order_id','payment_sequential'],
        'products':['product_id'], 'sellers':['seller_id'],
        'reviews':['review_id','order_id'], 'translation':['product_category_name']}

def load_raw(folder):
    folder = Path(folder)
    missing = [f for f in FILES.values() if not (folder / f).exists()]
    if missing:
        raise FileNotFoundError('Missing public Olist files in '+str(folder)+':\n'+'\n'.join(missing))
    raw = {k:pd.read_csv(folder/f, dtype={c:'string' for c in
           ['order_id','customer_id','customer_unique_id','product_id','seller_id','review_id',
            'customer_zip_code_prefix','seller_zip_code_prefix']}) for k,f in FILES.items()}
    manifest = pd.DataFrame([{'file':f, 'bytes':(folder/f).stat().st_size,
        'sha256':hashlib.sha256((folder/f).read_bytes()).hexdigest()} for f in FILES.values()])
    return raw, manifest

def audit(raw):
    return pd.DataFrame([{
        'dataset':name,'rows':len(df),'columns':len(df.columns),
        'duplicate_rows':int(df.duplicated().sum()),'missing_cells':int(df.isna().sum().sum()),
        'missing_pct':100*df.isna().sum().sum()/max(df.size,1),
        'expected_key':'+'.join(KEYS[name]),
        'key_unique':not df.duplicated(KEYS[name]).any(),
        'null_key_rows':int(df[KEYS[name]].isna().any(axis=1).sum())
    } for name,df in raw.items()])

def build_model(raw):
    """Return model, reconciliation, coverage and exceptions. Raw input is never mutated."""
    r = {k:v.copy() for k,v in raw.items()}
    for name in r:
        if name != 'reviews':
            if r[name].duplicated(KEYS[name]).any() or r[name][KEYS[name]].isna().any().any():
                raise ValueError(f'{name}: primary key violation; inspect source audit')
    dates = {'orders':['order_purchase_timestamp','order_approved_at','order_delivered_carrier_date',
                       'order_delivered_customer_date','order_estimated_delivery_date'],
             'items':['shipping_limit_date'], 'reviews':['review_creation_date','review_answer_timestamp']}
    date_audit=[]
    for name,cols in dates.items():
        for col in cols:
            old=r[name][col]
            parsed=pd.to_datetime(old,errors='coerce')
            date_audit.append({'dataset':name,'field':col,'missing':int(old.isna().sum()),
                               'unparseable':int((old.notna() & parsed.isna()).sum())})
            r[name][col]=parsed
    links=[('orders','customer_id','customers','customer_id'),('items','order_id','orders','order_id'),
           ('items','product_id','products','product_id'),('items','seller_id','sellers','seller_id'),
           ('payments','order_id','orders','order_id'),('reviews','order_id','orders','order_id')]
    coverage=[]
    for child,fk,parent,pk in links:
        bad=~r[child][fk].isin(r[parent][pk])
        coverage.append({'relationship':f'{child}.{fk} -> {parent}.{pk}',
                         'child_rows':len(r[child]),'unmatched_rows':int(bad.sum())})
    # Required references fail loudly; report available via validate_inputs before building.
    if any(x['unmatched_rows'] for x in coverage):
        raise ValueError('Foreign-key violations: '+str([x for x in coverage if x['unmatched_rows']]))
    o,c,i,p,pr,s,rv = [r[k] for k in ['orders','customers','items','payments','products','sellers','reviews']]
    for name,df,cols in [('items',i,['price','freight_value']),('payments',p,['payment_value'])]:
        if df[cols].isna().any().any() or (df[cols]<0).any().any():
            raise ValueError(f'{name}: missing or negative monetary values')
    ia=i.groupby('order_id').agg(merchandise_value=('price','sum'),freight_value=('freight_value','sum'),
            number_of_items=('order_item_id','size'),seller_count=('seller_id','nunique'))
    pa=p.groupby('order_id').agg(payment_value=('payment_value','sum'),
        payment_type_count=('payment_type','nunique'),payment_record_count=('payment_value','size'),
        installment_count=('payment_installments','max'))
    # Keep full reviews separately; select latest completed response deterministically for descriptive reporting.
    rv=rv.sort_values(['order_id','review_answer_timestamp','review_creation_date','review_id'],na_position='first')
    review=rv.drop_duplicates('order_id',keep='last')[['order_id','review_score']]
    review['review_score']=review.review_score.where(review.review_score.between(1,5))
    f=o.merge(c,on='customer_id',how='left',validate='many_to_one')
    f=f.merge(ia,on='order_id',how='left',validate='one_to_one')
    f=f.merge(pa,on='order_id',how='left',validate='one_to_one')
    f=f.merge(review,on='order_id',how='left',validate='one_to_one')
    f['has_items']=f.number_of_items.notna()
    f['has_payments']=f.payment_record_count.notna()
    f['has_review']=f.review_score.notna()
    f['purchase_date']=f.order_purchase_timestamp.dt.normalize()
    f['purchase_month']=f.order_purchase_timestamp.dt.strftime('%Y-%m')
    f['delivery_days']=(f.order_delivered_customer_date-f.order_purchase_timestamp).dt.total_seconds()/86400
    # Promise is treated as a calendar date: delivery on the promised day is on time.
    f['delay_days']=(f.order_delivered_customer_date.dt.normalize()-f.order_estimated_delivery_date.dt.normalize()).dt.days
    f['invalid_chronology']=(f.delivery_days.lt(0) |
        (f.order_estimated_delivery_date < f.order_purchase_timestamp.dt.normalize()) |
        (f.order_delivered_carrier_date < f.order_purchase_timestamp) |
        (f.order_delivered_customer_date < f.order_delivered_carrier_date) |
        (f.order_approved_at < f.order_purchase_timestamp))
    f['commercial_eligible']=(f.order_status.eq('delivered') & f.has_items & f.order_purchase_timestamp.notna())
    f['delivery_eligible']=(f.order_status.eq('delivered') & f.delivery_days.notna() &
                           f.delay_days.notna() & ~f.invalid_chronology)
    f['review_eligible']=f.order_status.eq('delivered') & f.has_review
    f['is_late']=f.delay_days.gt(0).astype('boolean').where(f.delivery_eligible)
    f['low_review']=f.review_score.le(2).astype('boolean').where(f.review_eligible)
    f['is_canceled']=f.order_status.eq('canceled')
    f['is_unavailable']=f.order_status.eq('unavailable')
    f['payment_difference']=f.payment_value-f.merchandise_value-f.freight_value
    # New/returning refers to observed eligible order sequence, with order_id breaking timestamp ties.
    eligible=f.loc[f.commercial_eligible].sort_values(['order_purchase_timestamp','order_id'])
    seq=eligible.groupby('customer_unique_id').cumcount()
    f['customer_order_number']=pd.Series(seq.to_numpy()+1,index=eligible.index).reindex(f.index).astype('Int64')
    f['is_returning']=f.customer_order_number.gt(1).fillna(False)
    first=eligible.groupby('customer_unique_id').order_purchase_timestamp.min()
    f['first_purchase_date']=f.customer_unique_id.map(first).dt.normalize()
    f['cohort_month']=f.first_purchase_date.dt.strftime('%Y-%m')
    dc=f.sort_values(['order_purchase_timestamp','order_id']).drop_duplicates('customer_unique_id')[[
        'customer_unique_id','customer_city','customer_state','customer_zip_code_prefix','first_purchase_date']].copy()
    dc=dc.rename(columns={'customer_city':'first_observed_city','customer_state':'first_observed_state',
                         'customer_zip_code_prefix':'first_observed_zip_prefix'})
    dp=pr.merge(r['translation'],on='product_category_name',how='left',validate='many_to_one')
    dp['category']=dp.product_category_name_english.fillna(dp.product_category_name).fillna('unknown')
    dd=pd.DataFrame({'date':pd.date_range(f.purchase_date.min(),f.purchase_date.max(),freq='D')})
    for col,values in {'year':dd.date.dt.year,'quarter':dd.date.dt.quarter,'month_number':dd.date.dt.month,
        'month_name':dd.date.dt.month_name(),'year_month':dd.date.dt.strftime('%Y-%m'),
        'week':dd.date.dt.isocalendar().week,'weekday_number':dd.date.dt.dayofweek+1,
        'weekday_name':dd.date.dt.day_name(),'is_weekend':dd.date.dt.dayofweek.ge(5)}.items(): dd[col]=values
    checks=[]
    def check(label,a,b):
        ok=bool(np.isclose(float(a),float(b),rtol=1e-10,atol=1e-6))
        checks.append({'check':label,'source':float(a),'model':float(b),'passed':ok})
        if not ok: raise AssertionError(f'{label}: {a} != {b}')
    check('unique orders',o.order_id.nunique(),f.order_id.nunique())
    check('item merchandise',i.price.sum(),f.merchandise_value.sum())
    check('item freight',i.freight_value.sum(),f.freight_value.sum())
    check('payments',p.payment_value.sum(),f.payment_value.sum())
    for status in ['delivered','canceled','unavailable']:
        check(status,o.order_status.eq(status).sum(),f.order_status.eq(status).sum())
    for label,mask in {'orders without items':~f.has_items,'orders without payments':~f.has_payments,
        'orders without valid review':~f.has_review,'invalid chronology':f.invalid_chronology,
        'multiple payment records':f.payment_record_count.gt(1),
        'payment difference over BRL 0.01':f.payment_difference.abs().gt(.01)}.items():
        coverage.append({'relationship':label,'child_rows':len(f),'unmatched_rows':int(mask.sum())})
    coverage.extend([
        {'relationship':'orders with multiple review records','child_rows':len(o),'unmatched_rows':int(rv.groupby('order_id').size().gt(1).sum())},
        {'relationship':'products without original category','child_rows':len(dp),'unmatched_rows':int(dp.product_category_name.isna().sum())},
        {'relationship':'products without English translation','child_rows':len(dp),'unmatched_rows':int(dp.product_category_name_english.isna().sum())}])
    model={'FactOrders':f,'FactOrderItems':i,'DimCustomer':dc,'DimProduct':dp,'DimSeller':s,'DimDate':dd,
           'FactPayments':p,'FactReviews':rv}
    for name,key in [('FactOrders','order_id'),('DimCustomer','customer_unique_id'),('DimProduct','product_id'),('DimSeller','seller_id'),('DimDate','date')]:
        assert model[name][key].is_unique, name
    return model,pd.DataFrame(checks),pd.DataFrame(coverage),pd.DataFrame(date_audit)
