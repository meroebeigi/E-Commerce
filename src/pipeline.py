"""Stage functions shared by command line and executable notebooks."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from .data_processing import load_raw,audit,build_model
from .kpi_functions import executive_kpis,monthly_growth,scorecard,pareto,payment_analysis
from .feature_engineering import customer_features,cohorts,second_purchase

def export_table(df,path):
    path.parent.mkdir(parents=True,exist_ok=True);df.to_csv(path,index=False)

def quality(root):
    root=Path(root);out=root/'output';out.mkdir(exist_ok=True)
    raw,manifest=load_raw(root/'data/raw')
    export_table(audit(raw),out/'data_quality_audit.csv')
    export_table(manifest,out/'source_checksums.csv')
    model,reconciliation,coverage,dates=build_model(raw)
    for name,df in model.items():export_table(df,out/(name+'.csv'))
    export_table(pd.DataFrame([{'table':name,'rows':len(df),'columns':len(df.columns),
        'fields':', '.join(df.columns)} for name,df in model.items()]),out/'model_inventory.csv')
    for name,df in [('reconciliation',reconciliation),('coverage_audit',coverage),('date_audit',dates)]:export_table(df,out/(name+'.csv'))
    # Quantify the original join defect; never use the expanded frame for actual KPIs.
    naive=raw['orders'][['order_id']].merge(raw['items'],on='order_id',how='left').merge(raw['payments'],on='order_id',how='left')
    defect=pd.DataFrame([{'measure':'Payment value','correct':raw['payments'].payment_value.sum(),'original_join':naive.payment_value.sum()},
                        {'measure':'Merchandise value','correct':raw['items'].price.sum(),'original_join':naive.price.sum()}])
    defect['overstatement']=defect.original_join-defect.correct
    defect['overstatement_pct']=defect.overstatement/defect.correct
    export_table(defect,out/'original_join_impact.csv')
    return model

def load_model(root):
    names=['FactOrders','FactOrderItems','DimCustomer','DimProduct','DimSeller','DimDate','FactPayments','FactReviews']
    model={n:pd.read_csv(Path(root)/'output'/(n+'.csv'),dtype={c:'string' for c in ['order_id','customer_id','customer_unique_id','product_id','seller_id','review_id']}) for n in names}
    f=model['FactOrders']
    for col in ['order_purchase_timestamp','order_approved_at','order_delivered_carrier_date','order_delivered_customer_date','order_estimated_delivery_date','purchase_date','first_purchase_date']:
        f[col]=pd.to_datetime(f[col],errors='coerce')
    for col in ['is_late','low_review']:f[col]=f[col].astype('boolean')
    return model

def business(root,model=None):
    root=Path(root);model=model if model is not None else load_model(root);f=model['FactOrders']
    a={'kpis':executive_kpis(f),'monthly':monthly_growth(f),
       'categories':scorecard(model,'category'),'sellers':scorecard(model,'seller_id'),
       'geography':scorecard(model,'customer_state')}
    customer,segment=customer_features(model)
    a.update(customers=customer,segments=segment,cohorts=cohorts(f),second_purchase=second_purchase(f))
    c=f[f.commercial_eligible].copy();c['order_type']=np.where(c.is_returning,'Returning customer order','New customer order')
    ac=c.groupby(['purchase_month','order_type']).agg(customers=('customer_unique_id','nunique'),orders=('order_id','size'),gmv=('merchandise_value','sum'))
    ac['aov']=ac.gmv/ac.orders;ac['monthly_gmv_share']=ac.gmv/ac.groupby(level=0).gmv.transform('sum')
    a['acquisition']=ac.reset_index()
    d=f[f.delivery_eligible&f.review_eligible].copy();d['delivery_status']=np.where(d.is_late,'Late','On time')
    a['delivery_reviews']=d.groupby('delivery_status').agg(orders=('order_id','size'),average_review_score=('review_score','mean'),low_review_rate=('low_review','mean')).reset_index()
    d=f[f.delivery_eligible].copy();d['delivery_band']=pd.cut(d.delivery_days,[-.001,7,14,21,30,60,np.inf],labels=['0–7','7–14','14–21','21–30','30–60','60+'])
    a['delivery_distribution']=d.groupby('delivery_band',observed=False).agg(orders=('order_id','size')).reset_index()
    a['payment_types'],a['payment_behavior']=payment_analysis(model)
    # Supporting commercial, payment and experience drill-through tables.
    item=model['FactOrderItems'].merge(model['DimProduct'][['product_id','category']],on='product_id',validate='many_to_one')
    item=item.merge(c[['order_id','purchase_month']],on='order_id',validate='many_to_one')
    mix=item.groupby(['seller_id','category']).agg(gmv=('price','sum'),orders=('order_id','nunique'),units=('order_item_id','size'))
    mix['seller_gmv_share']=mix.gmv/mix.groupby(level=0).gmv.transform('sum')
    a['seller_category_mix']=mix.reset_index()
    cm=item.groupby(['category','purchase_month']).price.sum().unstack(fill_value=0)
    cm=cm.reindex(columns=a['monthly'].purchase_month,fill_value=0)
    cg=cm.T.pct_change(fill_method=None).replace([np.inf,-np.inf],np.nan).T
    a['category_monthly']=cm.stack().rename('gmv').reset_index().merge(
        cg.stack().rename('gmv_mom').reset_index(),on=['category','purchase_month'],how='left',validate='one_to_one')
    a['state_status']=f.groupby('customer_state').agg(recorded_orders=('order_id','size'),
        cancellations=('is_canceled','sum'),unavailable=('is_unavailable','sum')).reset_index()
    a['state_status']['cancellation_rate']=a['state_status'].cancellations/a['state_status'].recorded_orders
    a['review_distribution']=f[f.review_eligible].groupby('review_score').agg(orders=('order_id','size')).reset_index()
    a['installment_distribution']=c.groupby('installment_count',dropna=False).agg(orders=('order_id','size'),
        gmv=('merchandise_value','sum'),aov=('merchandise_value','mean')).reset_index()
    for name,values in [('customer',c.groupby('customer_unique_id').merchandise_value.sum()),('category',a['categories'].set_index('category').gmv),('seller',a['sellers'].set_index('seller_id').gmv)]:
        a[name+'_pareto']=pareto(values)
    concentrations=[]
    for name in ['customer','category','seller']:
        p=a[name+'_pareto']
        for target in [.5,.8]:
            row=p[p.cumulative_gmv_share.ge(target)].iloc[0]
            concentrations.append({'entity':name,'target_gmv_share':target,'entities_required':int(row['rank']),
                'total_entities':len(p),'entity_share':row.entity_share})
    a['concentration_summary']=pd.DataFrame(concentrations)
    # Demonstrate threshold sensitivity instead of treating 50 as a universal truth.
    sensitivity=[]
    for name in ['categories','sellers','geography']:
        for minimum in [30,50,100]:
            x=a[name];valid=x.delivery_orders.ge(minimum)&x.reviewed_orders.ge(minimum)
            sensitivity.append({'entity':name,'minimum_orders':minimum,'rate_eligible_entities':int(valid.sum()),
                'high_value_weak_experience_entities':int((valid&x.high_commercial_value&x.weak_experience).sum())})
    a['priority_sensitivity']=pd.DataFrame(sensitivity)
    # Explicit analysis population report.
    a['populations']=pd.DataFrame([{'population':col,'orders':int(f[col].sum())} for col in ['commercial_eligible','delivery_eligible','review_eligible']])
    for name,df in a.items():export_table(df,root/'output'/(name+'.csv'))
    from .sql_layer import export_and_verify
    a['sql_reconciliation']=export_and_verify(model,root,a)
    export_table(a['sql_reconciliation'],root/'output/sql_reconciliation.csv')
    from .visualization import charts
    charts(a,root)
    return a

def data_science(root,model=None):
    root=Path(root);model=model if model is not None else load_model(root)
    from .models import cluster_customers,classify_late_delivery,statistical_tests
    from .visualization import model_charts
    customer=pd.read_csv(root/'output/customers.csv')
    print('Clustering customers...',flush=True)
    labeled,profile,scores,treatment=cluster_customers(customer)
    print('Training and evaluating temporal late-delivery models...',flush=True)
    metrics,comparison,thresholds,importance,scored=classify_late_delivery(model)
    tests=statistical_tests(model['FactOrders'])
    tables={'customer_clusters':labeled,'cluster_profiles':profile,'cluster_diagnostics':scores,
        'cluster_treatment':treatment,'model_comparison':comparison,'model_thresholds':thresholds,
        'model_importance':importance,'test_predictions':scored,'statistical_tests':tests}
    for name,df in tables.items():export_table(df,root/'output'/(name+'.csv'))
    (root/'output/model_metrics.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
    model_charts(scores,importance,metrics,root)
    return metrics

def executive_report(root):
    root=Path(root);out=root/'output'
    read=lambda n:pd.read_csv(out/(n+'.csv'))
    k=read('kpis').set_index('metric').value
    m=json.loads((out/'model_metrics.json').read_text())
    c=read('customer_pareto'); share80=c.loc[c.cumulative_gmv_share.ge(.8),'entity_share'].iloc[0]
    d=read('delivery_reviews').set_index('delivery_status')
    categories=read('categories');priorities=categories[categories.priority_group.eq('Improvement priority')].sort_values('excess_late_orders',ascending=False)
    top=priorities.iloc[0] if len(priorities) else categories.iloc[0]
    sp=read('second_purchase');rate90=sp.second_buyers.sum()/sp.eligible_customers.sum()
    cluster=read('cluster_diagnostics').query('selected == True').iloc[0]
    summary=f'''# Executive summary

## E-Commerce Decision Intelligence
Growth, Customer Value, Product Performance & Operational Risk

All findings below were generated from the public Olist source files after validation. Values are historical BRL, not current market forecasts or Olist accounting revenue. See `metric_dictionary.md` for populations and `output/` for evidence.

### Six findings

1. Delivered merchandise value was **BRL {k['GMV']:,.2f}**, across **{k['Orders']:,.0f} orders** and **{k['Customers']:,.0f} unique customers**; AOV was **BRL {k['AOV']:,.2f}**.
2. **{k['Repeat customer rate']:.2%}** of customers placed multiple observed eligible orders. Subsequent orders contributed **{k['Returning order GMV share']:.2%}** of GMV. Among customers with 90 days of observation, **{rate90:.2%}** bought again within 90 days. These are observation-window measures, not churn.
3. The highest-spending **{share80:.2%}** of customers contributed 80% of GMV. An automatic 80/20 claim is therefore inappropriate; use the measured concentration curves.
4. **{k['Late delivery rate']:.2%}** of delivery-eligible orders arrived after the promised calendar day. Low-review rates were **{d.loc['Late','low_review_rate']:.2%}** for late orders and **{d.loc['On time','low_review_rate']:.2%}** for on-time orders. This association does not identify a causal effect.
5. **{top['category'].replace('_',' ')}** has **BRL {top['gmv']:,.0f}** GMV, **{top['late_delivery_rate']:.2%}** late deliveries and **{top['delivery_orders']:,.0f}** delivery-eligible orders. Its classification is **{top['priority_group']}** under the documented volume, confidence and contribution rules.
6. The selected **{m['selected_model']}** achieved temporal holdout average precision **{m['test_average_precision']:.3f}** against a prevalence baseline of **{m['test_prevalence']:.3f}**, with recall **{m['test_recall']:.2%}** and precision **{m['test_precision']:.2%}** at threshold **{m['threshold']:.2f}**. Low precision limits practical use: most alerts are false positives. Customer clustering selected **K={int(cluster.k)}**, with silhouette **{cluster.silhouette:.3f}** and seed-stability ARI **{cluster.seed_stability_ari:.3f}**. Inspect the profiles: strong separation can simply recover the rare repeat-buyer group, adding little beyond a frequency rule. Intervention value has not been tested.

### Six priorities to test

| Evidence | Proposed action | KPI and evaluation |
|---|---|---|
| Sparse repeat purchasing and unequal observation windows | Randomize an opt-in second-purchase journey among newly acquired customers; use equal 90-day follow-up | Incremental 90-day second-purchase rate and GMV per eligible customer; record incentive costs separately |
| High-volume seller and category delay exposure | Review the highest-priority seller/category pairs in the scorecards; investigate promise accuracy and dispatch processes | Late rate with interval, excess late-order count, low-review rate; compare against a suitable control |
| Large review gap by delivery status | Test proactive delay communication for eligible at-risk orders | Low-review rate, contact rate, satisfaction; verify that operational performance improves as well |
| Model ranking above the reported baseline, if confirmed in a deployment-like test | Shadow-score future orders before any automated intervention; select alert volume against team capacity | Precision/recall at capacity, calibration and drift; establish false-alert and missed-delay costs |
| Measured concentration across customers, categories and sellers | Monitor contribution and performance together; investigate overdependence where exposure is material | Top-N contribution and cumulative GMV share, paired with experience KPIs |
| Accounting and join risks in the original analysis | Use the reconciled order/item model as the shared reporting source | Reconciliation failures, missing payment coverage and SQL/Python agreement |

### Interpretation boundaries

The dataset is historical and observational. No channel spend, acquisition cost, profit margin, returns, market size or experimental interventions are observed. The last eligible month is conservatively censored in retention reporting. Delivered-only commercial results exclude unresolved and canceled orders. Seller/category experience uses order-level outcomes, including shared multi-seller orders; this cannot establish seller-level responsibility. Cluster separation, model metrics and correlations do not prove commercial benefit.

Native Power BI execution is not part of the Python run. Dashboard previews are rendered from real calculated data; DAX, Power Query, relationships and a four-page specification are supplied for Power BI Desktop implementation.
'''
    (root/'docs/executive_summary.md').write_text(summary,encoding='utf-8')
    return summary

def run(root):
    print('Auditing source and building dimensional model...',flush=True)
    model=quality(root)
    print('Calculating business and customer analytics; verifying SQL...',flush=True)
    business(root,model)
    metrics=data_science(root,model)
    executive_report(root)
    print(json.dumps(metrics,indent=2),flush=True)
