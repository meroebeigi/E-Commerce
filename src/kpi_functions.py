"""Metric definitions and matched populations, with additive amounts separated from rates."""
import numpy as np
import pandas as pd

def ratio(a,b):
    return float(a)/float(b) if b else np.nan

def executive_kpis(f):
    c=f[f.commercial_eligible]; d=f[f.delivery_eligible]; r=f[f.review_eligible]
    customers=c.groupby('customer_unique_id').agg(orders=('order_id','size'),gmv=('merchandise_value','sum'))
    repeat_ids=customers.index[customers.orders.gt(1)]
    specs=[
      ('GMV',c.merchandise_value.sum(),'BRL','Delivered item merchandise; excludes freight','commercial'),
      ('Payment value',c.payment_value.sum(),'BRL','Recorded payments on commercial orders; missing payments excluded from sum','commercial'),
      ('Orders',len(c),'count','Delivered orders with items and a purchase timestamp','commercial'),
      ('Units sold',c.number_of_items.sum(),'count','Item rows on commercial orders','commercial'),
      ('Customers',len(customers),'count','Distinct customer_unique_id on commercial orders','commercial'),
      ('AOV',ratio(c.merchandise_value.sum(),len(c)),'BRL','GMV / commercial orders','commercial'),
      ('Average item value',ratio(c.merchandise_value.sum(),c.number_of_items.sum()),'BRL','GMV / units','commercial'),
      ('Items per order',c.number_of_items.mean(),'decimal','Units / commercial orders','commercial'),
      ('Freight / merchandise',ratio(c.freight_value.sum(),c.merchandise_value.sum()),'percent','Freight divided by merchandise, not total payment','commercial'),
      ('Repeat customer rate',customers.orders.gt(1).mean(),'percent','Customers with >1 eligible orders / customers over full window','commercial'),
      ('Orders per customer',ratio(len(c),len(customers)),'decimal','Eligible orders / customers','commercial'),
      ('GMV per customer',ratio(c.merchandise_value.sum(),len(customers)),'BRL','GMV / customers','commercial'),
      ('Returning order GMV share',ratio(c.loc[c.is_returning,'merchandise_value'].sum(),c.merchandise_value.sum()),'percent','GMV after a customer first eligible order / all GMV','commercial'),
      ('Repeat customer lifetime GMV share',ratio(c.loc[c.customer_unique_id.isin(repeat_ids),'merchandise_value'].sum(),c.merchandise_value.sum()),'percent','All GMV of observed repeat customers, including their first order','commercial'),
      ('New customers',c.loc[~c.is_returning,'customer_unique_id'].nunique(),'count','First observed eligible purchase in reporting window','commercial'),
      ('Returning customers',c.loc[c.is_returning,'customer_unique_id'].nunique(),'count','At least one eligible order after first; overlaps new customers','commercial'),
      ('Average delivery days',d.delivery_days.mean(),'days','Purchase to actual delivery, valid delivered orders','delivery'),
      ('Median delivery days',d.delivery_days.median(),'days','Median purchase-to-delivery duration','delivery'),
      ('Late delivery rate',d.is_late.mean(),'percent','Delivered after promised calendar day / delivery-eligible orders','delivery'),
      ('Average delay among late orders',d.loc[d.is_late.fillna(False),'delay_days'].mean(),'days','Calendar-day delay only among late orders','delivery'),
      ('Cancellation rate',f.is_canceled.mean(),'percent','Canceled orders / every recorded order, separate from unavailable','all'),
      ('Unavailable rate',f.is_unavailable.mean(),'percent','Unavailable orders / every recorded order','all'),
      ('Average review score',r.review_score.mean(),'score','Latest valid selected review for delivered orders','review'),
      ('Low review rate',r.low_review.mean(),'percent','Selected review <=2 / delivered reviewed orders','review'),
      ('Five star rate',r.review_score.eq(5).mean(),'percent','Selected review ==5 / delivered reviewed orders','review')]
    populations={'commercial':len(c),'delivery':len(d),'review':len(r),'all':len(f)}
    out=pd.DataFrame(specs,columns=['metric','value','unit','definition','population'])
    out['population_orders']=out.population.map(populations)
    bounded=out.unit.eq('percent') & out.metric.ne('Freight / merchandise')
    assert out.loc[bounded,'value'].dropna().between(0,1).all()
    return out

def monthly_growth(f):
    c=f[f.commercial_eligible].copy()
    m=c.groupby('purchase_month').agg(gmv=('merchandise_value','sum'),orders=('order_id','size'),
        customers=('customer_unique_id','nunique'),units=('number_of_items','sum'))
    full=pd.period_range(c.order_purchase_timestamp.min().to_period('M'),c.order_purchase_timestamp.max().to_period('M'),freq='M').astype(str)
    m=m.reindex(full,fill_value=0);m.index.name='purchase_month'
    m['aov']=m.gmv/m.orders.replace(0,np.nan)
    m['items_per_order']=m.units/m.orders.replace(0,np.nan)
    m['orders_per_customer']=m.orders/m.customers.replace(0,np.nan)
    m['gmv_per_customer']=m.gmv/m.customers.replace(0,np.nan)
    for col in ['gmv','orders','customers','aov','items_per_order','orders_per_customer','gmv_per_customer']:
        m[col+'_mom']=m[col].pct_change(fill_method=None).replace([np.inf,-np.inf],np.nan)
    # Exact sequential bridge; ordering is explicit and not a causal allocation.
    prev=m.shift()
    m['customer_effect']=(m.customers-prev.customers)*prev.orders_per_customer*prev.aov
    m['frequency_effect']=m.customers*(m.orders_per_customer-prev.orders_per_customer)*prev.aov
    m['aov_effect']=m.customers*m.orders_per_customer*(m.aov-prev.aov)
    bridge=m[['customer_effect','frequency_effect','aov_effect']].sum(axis=1,min_count=3)
    valid=bridge.notna()
    assert np.allclose(bridge[valid],m.gmv.diff()[valid])
    # First and last observed purchase months are coverage boundaries, not proven complete months.
    bounds=f.order_purchase_timestamp.dropna().dt.to_period('M')
    m['boundary_month']=m.index.isin([str(bounds.min()),str(bounds.max()),str(full[0]),str(full[-1])])
    return m.reset_index()

def pareto(values):
    x=values.sort_values(ascending=False).rename('gmv').reset_index()
    x['rank']=np.arange(1,len(x)+1)
    x['entity_share']=x['rank']/len(x)
    x['gmv_share']=x.gmv/x.gmv.sum()
    x['cumulative_gmv_share']=x.gmv_share.cumsum()
    return x

def wilson(success,n):
    n=n.astype(float); p=success/n.replace(0,np.nan); z=1.96
    center=(p+z*z/(2*n))/(1+z*z/n)
    half=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/(1+z*z/n)
    return (center-half).clip(0,1),(center+half).clip(0,1)

def scorecard(model,key,min_orders=50):
    f=model['FactOrders']; c=f[f.commercial_eligible]
    i=model['FactOrderItems'].merge(model['DimProduct'][['product_id','category']],on='product_id',validate='many_to_one')
    cols=['order_id','customer_unique_id','customer_state','purchase_month','delivery_eligible','is_late','delivery_days','review_eligible','review_score','low_review']
    x=i.merge(c[cols],on='order_id',validate='many_to_one')
    # Money at item grain; experience once per order per entity. An order may span entities.
    money=x.groupby(key).agg(gmv=('price','sum'),units=('order_item_id','size'))
    y=x.drop_duplicates([key,'order_id'])
    volume=y.groupby(key).agg(orders=('order_id','size'),customers=('customer_unique_id','nunique'))
    delivery=y[y.delivery_eligible].groupby(key).agg(delivery_orders=('order_id','size'),late_orders=('is_late','sum'),average_delivery_days=('delivery_days','mean'))
    reviews=y[y.review_eligible].groupby(key).agg(reviewed_orders=('order_id','size'),low_reviews=('low_review','sum'),average_review_score=('review_score','mean'))
    out=money.join(volume).join(delivery).join(reviews)
    for col in ['delivery_orders','late_orders','reviewed_orders','low_reviews']:out[col]=out[col].fillna(0).astype(int)
    out['gmv_share']=out.gmv/out.gmv.sum();out['aov']=out.gmv/out.orders
    out['average_item_price']=out.gmv/out.units
    out['late_delivery_rate']=out.late_orders/out.delivery_orders.replace(0,np.nan)
    out['low_review_rate']=out.low_reviews/out.reviewed_orders.replace(0,np.nan)
    out['late_ci_low'],out['late_ci_high']=wilson(out.late_orders,out.delivery_orders)
    out['rate_rank_eligible']=out.delivery_orders.ge(min_orders)&out.reviewed_orders.ge(min_orders)
    baseline=float(f.loc[f.delivery_eligible,'is_late'].mean())
    out['late_rate_baseline']=baseline
    out['excess_late_orders']=(out.late_orders-baseline*out.delivery_orders).clip(lower=0)
    out['gmv_on_late_orders']=x[x.is_late.fillna(False)].groupby(key).price.sum().reindex(out.index,fill_value=0)
    out['high_commercial_value']=out.gmv.ge(out.gmv.quantile(.75))
    out['weak_experience']=out.late_ci_low.gt(baseline)
    complete=sorted(x.purchase_month.unique())
    # Exclude first/last observed eligible months conservatively; equal three-month windows.
    use=complete[1:-1]
    out['growth_rate']=np.nan
    if len(use)>=6:
        recent=x[x.purchase_month.isin(use[-3:])].groupby(key).price.sum().reindex(out.index,fill_value=0)
        prior=x[x.purchase_month.isin(use[-6:-3])].groupby(key).price.sum().reindex(out.index,fill_value=0)
        out['growth_rate']=recent/prior.replace(0,np.nan)-1
    out['priority_group']=np.select([
        ~out.rate_rank_eligible,
        out.high_commercial_value&out.weak_experience,
        out.high_commercial_value&~out.weak_experience,
        out.growth_rate.gt(0)&~out.weak_experience],
        ['Insufficient sample','Improvement priority','Strong commercial performer','Growth candidate'],default='Monitor')
    # Transparent ordinal components; no monetized causal loss or opaque weighted score.
    out['priority_rank']=out.excess_late_orders.where(out.rate_rank_eligible).rank(method='min',ascending=False)
    out=out.sort_values('gmv',ascending=False)
    out['cumulative_gmv_share']=out.gmv_share.cumsum()
    return out.reset_index()

def payment_analysis(model):
    f=model['FactOrders'];p=model['FactPayments']; c=f[f.commercial_eligible]
    records=p.merge(c[['order_id']],on='order_id',validate='many_to_one')
    summary=records.groupby('payment_type').agg(payment_value=('payment_value','sum'),payment_records=('order_id','size'),orders=('order_id','nunique'))
    summary['payment_value_share']=summary.payment_value/summary.payment_value.sum()
    types=records.groupby('order_id').payment_type.agg(lambda x: x.iloc[0] if x.nunique()==1 else 'mixed')
    orders=c.merge(types.rename('payment_group'),on='order_id',how='left',validate='one_to_one')
    orders['payment_group']=orders.payment_group.fillna('missing')
    orders['value_band']=pd.cut(orders.merchandise_value,[0,50,100,250,500,1000,np.inf],include_lowest=True).astype(str)
    behavior=orders.groupby(['payment_group','value_band']).agg(orders=('order_id','size'),aov=('merchandise_value','mean'),median_max_installments=('installment_count','median'))
    return summary.reset_index(),behavior.reset_index()
