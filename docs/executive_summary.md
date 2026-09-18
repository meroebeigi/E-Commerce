# Executive summary

## E-Commerce Decision Intelligence
Growth, Customer Value, Product Performance & Operational Risk

All findings below were generated from the public Olist source files after validation. Values are historical BRL, not current market forecasts or Olist accounting revenue. See `metric_dictionary.md` for populations and `output/` for evidence.

### Six findings

1. Delivered merchandise value was **BRL 13,221,498.11**, across **96,478 orders** and **93,358 unique customers**; AOV was **BRL 137.04**.
2. **3.00%** of customers placed multiple observed eligible orders. Subsequent orders contributed **2.90%** of GMV. Among customers with 90 days of observation, **2.28%** bought again within 90 days. These are observation-window measures, not churn.
3. The highest-spending **45.00%** of customers contributed 80% of GMV. An automatic 80/20 claim is therefore inappropriate; use the measured concentration curves.
4. **6.78%** of delivery-eligible orders arrived after the promised calendar day. Low-review rates were **62.42%** for late orders and **9.26%** for on-time orders. This association does not identify a causal effect.
5. **health beauty** has **BRL 1,233,132** GMV, **7.52%** late deliveries and **8,629** delivery-eligible orders. Its classification is **Improvement priority** under the documented volume, confidence and contribution rules.
6. The selected **Random forest** achieved temporal holdout average precision **0.061** against a prevalence baseline of **0.035**, with recall **36.40%** and precision **6.22%** at threshold **0.48**. Low precision limits practical use: most alerts are false positives. Customer clustering selected **K=2**, with silhouette **0.676** and seed-stability ARI **1.000**. Inspect the profiles: strong separation can simply recover the rare repeat-buyer group, adding little beyond a frequency rule. Intervention value has not been tested.

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
