"""Business charts in a consistent accessible palette; all charts use calculated tables."""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter,PercentFormatter
import seaborn as sns

BLUE='#176B91';TEAL='#128C7E';ORANGE='#DB792E';RED='#B94749';INK='#142D40'

def style():
    sns.set_theme(style='whitegrid',palette=[BLUE,TEAL,ORANGE,RED],font_scale=1.05)
    plt.rcParams.update({'axes.spines.top':False,'axes.spines.right':False,'axes.titleweight':'bold',
        'axes.labelcolor':INK,'text.color':INK,'figure.facecolor':'#FAFCFD','axes.facecolor':'#FAFCFD',
        'savefig.facecolor':'#FAFCFD'})

def save(fig,path):
    fig.savefig(path,dpi=150,bbox_inches='tight');plt.close(fig)

def money_axis(ax,axis='y'):
    (ax.yaxis if axis=='y' else ax.xaxis).set_major_formatter(FuncFormatter(lambda x,p:f'{x/1e6:.1f}m' if abs(x)>=1e6 else f'{x/1000:,.0f}k' if abs(x)>=1000 else f'{x:,.0f}'))

def charts(a,root):
    style();dest=root/'images';dest.mkdir(exist_ok=True)
    m=a['monthly'];cat=a['categories'];sel=a['sellers'];co=a['cohorts'];seg=a['segments']
    fig,ax=plt.subplots(figsize=(11,4.8),layout='constrained')
    ax.plot(m.purchase_month,m.gmv,marker='o',color=BLUE,lw=2)
    ax.set(title='Marketplace growth: delivered merchandise value',ylabel='GMV (BRL)',xlabel='Purchase month')
    ax.tick_params(axis='x',rotation=60,labelsize=9);money_axis(ax)
    save(fig,dest/'monthly_growth.png')
    fig,ax=plt.subplots(figsize=(12,8),layout='constrained')
    matrix=co[co.cohort_size.ge(50)].pivot(index='cohort_month',columns='age_month',values='retention_rate')
    # Month 0 is structurally 100%; remove from color scale so repeat behavior stays readable.
    heat=matrix.drop(columns=0,errors='ignore')
    sns.heatmap(heat*100,mask=heat.isna(),cmap='Blues',ax=ax,cbar_kws={'label':'Active customer share (%)'},vmin=0)
    ax.set(title='Repeat purchasing · cohorts with at least 50 customers',xlabel='Months after first purchase (month 0 excluded)',ylabel='First eligible purchase month')
    save(fig,dest/'retention_cohort.png')
    fig,ax=plt.subplots(figsize=(10,5.5),layout='constrained')
    s=seg.sort_values('gmv_share');ax.barh(s.segment,s.gmv_share,color=TEAL)
    ax.xaxis.set_major_formatter(PercentFormatter(1));ax.set(title='Which behavioral segments contribute GMV?',xlabel='Share of delivered GMV',ylabel='Observed RFM segment')
    save(fig,dest/'customer_segments.png')
    fig,ax=plt.subplots(figsize=(10,6),layout='constrained')
    s=sel[sel.rate_rank_eligible]
    sc=ax.scatter(s.orders,s.late_delivery_rate,s=25+500*s.gmv/s.gmv.max(),c=s.average_review_score,cmap='viridis',alpha=.65,edgecolors='white')
    ax.axhline(s.late_rate_baseline.iloc[0],color=RED,ls='--',label='Marketplace late rate')
    ax.set(xscale='log',title='Seller priorities: scale, delay rate and commercial importance',xlabel='Distinct delivered orders (log scale)',ylabel='Late-delivery rate')
    ax.yaxis.set_major_formatter(PercentFormatter(1));ax.legend(loc='upper left')
    fig.colorbar(sc,ax=ax,label='Average review score');save(fig,dest/'seller_performance_matrix.png')
    fig,ax=plt.subplots(figsize=(10,5),layout='constrained')
    d=a['delivery_reviews'];ax.bar(d.delivery_status,d.low_review_rate,color=[ORANGE if s=='Late' else BLUE for s in d.delivery_status])
    ax.yaxis.set_major_formatter(PercentFormatter(1));ax.set(title='Is late delivery associated with poor reviews?',ylabel='Reviews scoring 1–2 / reviewed orders',xlabel='Delivery status')
    save(fig,dest/'delivery_reviews.png')
    fig,ax=plt.subplots(figsize=(10,5),layout='constrained')
    for name,color in [('customer_pareto',BLUE),('category_pareto',TEAL),('seller_pareto',ORANGE)]:
        d=a[name];ax.plot(np.r_[0,d.entity_share],np.r_[0,d.cumulative_gmv_share],label=name.replace('_pareto','').title(),color=color)
    ax.axhline(.8,color=INK,ls='--',lw=1);ax.xaxis.set_major_formatter(PercentFormatter(1));ax.yaxis.set_major_formatter(PercentFormatter(1))
    ax.set(title='Concentration is measured, not assumed',xlabel='Share of entities ranked by GMV',ylabel='Cumulative GMV share');ax.legend()
    save(fig,dest/'pareto.png')
    # Four dashboard previews, filled with real results. These are static design artifacts, not PBIX files.
    k=a['kpis'].set_index('metric').value
    for page in range(1,5):
        fig,axes=plt.subplots(2,2,figsize=(15,9),layout='constrained')
        titles=['Executive overview','Customer & growth intelligence','Commercial performance','Customer experience & operations']
        fig.suptitle('OLIST  /  '+titles[page-1],fontsize=22,fontweight='bold')
        ax,bx,cx,dx=axes.flat
        if page==1:
            ax.axis('off');ax.text(0,.95,f'BRL {k["GMV"]/1e6:.2f}m GMV\n{k["Orders"]:,.0f} delivered orders\n{k["Customers"]:,.0f} customers\nBRL {k["AOV"]:,.2f} AOV\n{k["Repeat customer rate"]:.1%} repeat customers\n{k["Late delivery rate"]:.1%} late deliveries',fontsize=21,va='top',linespacing=1.6)
            bx.plot(m.purchase_month,m.gmv,color=BLUE);bx.set_title('Monthly GMV (BRL)');money_axis(bx)
            top=cat.head(8).sort_values('gmv');cx.barh(top.category.str.replace('_',' '),top.gmv,color=TEAL);cx.set_title('Leading categories · GMV (BRL)');money_axis(cx,'x')
            g=a['geography'].head(8);dx.bar(g.customer_state,g.gmv,color=BLUE);dx.set_title('Leading states · GMV (BRL)');money_axis(dx)
        elif page==2:
            n=a['acquisition'].pivot(index='purchase_month',columns='order_type',values='gmv').fillna(0)
            n.plot.area(ax=ax,color=[BLUE,ORANGE],alpha=.85);ax.set_title('First vs subsequent order GMV');money_axis(ax)
            ss=seg.sort_values('customer_share');bx.barh(ss.segment,ss.customer_share,color=TEAL);bx.xaxis.set_major_formatter(PercentFormatter(1));bx.set_title('Customer segments')
            cp=a['customer_pareto'];cx.plot(cp.entity_share,cp.cumulative_gmv_share);cx.set_title('Customer GMV concentration');cx.xaxis.set_major_formatter(PercentFormatter(1));cx.yaxis.set_major_formatter(PercentFormatter(1))
            sp=a['second_purchase'].query('eligible_customers >= 50');dx.plot(sp.first_month,sp.second_purchase_rate,marker='o');dx.yaxis.set_major_formatter(PercentFormatter(1));dx.set_title('90-day second purchase · cohorts ≥50 customers')
        elif page==3:
            top=cat.head(10).sort_values('gmv');ax.barh(top.category.str.replace('_',' '),top.gmv,color=TEAL);ax.set_title('Category GMV (BRL)');money_axis(ax,'x')
            ss=sel[sel.rate_rank_eligible];bx.scatter(ss.orders,ss.late_delivery_rate,s=20+200*ss.gmv/ss.gmv.max(),color=BLUE,alpha=.6);bx.set_xscale('log');bx.yaxis.set_major_formatter(PercentFormatter(1));bx.set_title('Seller volume × late rate · size = GMV')
            pp=a['seller_pareto'];cx.plot(pp.entity_share,pp.cumulative_gmv_share);cx.set_title('Seller concentration');cx.xaxis.set_major_formatter(PercentFormatter(1));cx.yaxis.set_major_formatter(PercentFormatter(1))
            top=cat[cat.rate_rank_eligible].nlargest(8,'excess_late_orders').sort_values('excess_late_orders');dx.barh(top.category.str.replace('_',' '),top.excess_late_orders,color=ORANGE);dx.set_title('Late-order excess vs marketplace benchmark')
        else:
            dr=a['delivery_reviews'];colors=[ORANGE if s=='Late' else BLUE for s in dr.delivery_status];ax.bar(dr.delivery_status,dr.average_review_score,color=colors);ax.set_ylim(0,5);ax.set_title('Review score by delivery status')
            bx.bar(dr.delivery_status,dr.low_review_rate,color=colors);bx.yaxis.set_major_formatter(PercentFormatter(1));bx.set_title('Low-review rate')
            geo=a['geography'].sort_values('gmv',ascending=False).head(10);cx.bar(geo.customer_state,geo.late_delivery_rate,color=ORANGE);cx.yaxis.set_major_formatter(PercentFormatter(1));cx.set_title('Late rate · ten largest state markets')
            dd=a['delivery_distribution'];dx.bar(dd.delivery_band,dd.orders,color=TEAL);dx.set_title('Delivery duration · order count');dx.tick_params(axis='x',rotation=30)
        for aa in axes.flat:
            if len(aa.get_xticklabels())>12:
                aa.tick_params(axis='x',rotation=60,labelsize=8)
                for tick in aa.get_xticklabels()[1::2]:tick.set_visible(False)
        save(fig,root/'powerbi/dashboard_preview'/f'page_{page}.png')

def model_charts(cluster_scores,importance,metrics,root):
    style()
    fig,axes=plt.subplots(1,2,figsize=(11,4),layout='constrained')
    axes[0].plot(cluster_scores.k,cluster_scores.inertia,marker='o');axes[0].set(title='Elbow diagnostic',xlabel='Clusters (K)',ylabel='Within-cluster squared distance')
    axes[1].plot(cluster_scores.k,cluster_scores.silhouette,marker='o',color=TEAL);axes[1].set(title='Separation diagnostic',xlabel='Clusters (K)',ylabel='Silhouette score')
    save(fig,root/'images/cluster_diagnostics.png')
    fig,ax=plt.subplots(figsize=(10,5),layout='constrained')
    q=importance.head(10).sort_values('ap_drop_mean');ax.barh(q.feature,q.ap_drop_mean,xerr=q.ap_drop_std,color=BLUE)
    ax.set(title='Which inputs support late-delivery risk ranking?',xlabel='Holdout average-precision decrease after permutation',ylabel='Input feature')
    save(fig,root/'images/risk_feature_importance.png')
    fig,ax=plt.subplots(figsize=(5,4),layout='constrained')
    sns.heatmap([[metrics['true_negatives'],metrics['false_positives']],[metrics['false_negatives'],metrics['true_positives']]],annot=True,fmt='d',cmap='Blues',cbar=False,ax=ax,xticklabels=['On time','Late'],yticklabels=['On time','Late'])
    ax.set(title='Final temporal holdout',xlabel='Predicted',ylabel='Observed');save(fig,root/'images/risk_confusion_matrix.png')
