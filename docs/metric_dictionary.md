# Metric and population contract

All currency amounts are nominal historical Brazilian reais (BRL). GMV is merchandise value, not marketplace accounting revenue. Freight is separate. Payment value is the amount in recorded payment rows and can differ from merchandise plus freight. This dataset cannot supply profit, take rate, CAC, marketing ROI, returns or churn labels.

| Population | Inclusion | Intended use |
|---|---|---|
| All recorded orders | Every unique source order | Status counts, cancellations and unavailable rates |
| Commercial | Delivered, at least one item, valid purchase timestamp | GMV, AOV, customers, cohorts, segments and commercial scorecards |
| Delivery | Delivered, valid purchase/promise/actual delivery, no detected chronology defect | Duration and late rates |
| Reviews | Delivered, selected review score between 1 and 5 | Review score and low/five-star rates |
| Delivery versus review | Intersection of delivery and review populations | Association comparisons |

`output/populations.csv` records population sizes; `output/kpis.csv` contains each calculation, value, unit, definition and order-population count. A row's population count is not necessarily its denominator: customer rates use customers, and delay severity uses only late orders.

### Core definitions

- **GMV**: sum item `price` on eligible commercial orders. All-status merchandise totals are reconciled separately and are not headline GMV.
- **Orders**: unique eligible `order_id`; at order grain this equals row count. **Units**: item rows, not distinct product IDs.
- **Customers**: unique `customer_unique_id`. `customer_id` links an order to its customer record and is not the persistent identity.
- **AOV**: GMV / eligible orders. Category AOV is category merchandise / distinct orders containing that category, not the total basket value of those orders.
- **Freight ratio**: sum freight / sum merchandise. Ratios of totals are used instead of unweighted order ratios.
- **Repeat customer**: more than one observed eligible order. Repeat customer rate uses the full selected observation window and is not a churn measure.
- **Returning order**: any eligible order after the first eligible order; timestamp then order ID breaks ties. First and subsequent orders on the same day remain distinct.
- **Returning-order GMV share**: only subsequent order GMV / GMV. **Repeat-customer lifetime GMV share** also includes those customers' first order. They answer different questions.
- **New/returning monthly customers**: customers with first/subsequent orders in that month. A customer can be counted in both, so do not add those customer counts.
- **Late**: actual delivery calendar date is after estimated delivery calendar date. A late-afternoon delivery on the promised date is on time. Duration uses elapsed fractional days; delay severity uses calendar days.
- **Low review**: score 1 or 2, among review-eligible orders. Orders with no valid review are absent from the denominator, not classified as satisfied.
- **Cancellation rate**: canceled / all source orders. Unavailable is reported separately; neither is a return.
- **90-day second-purchase rate**: customers with an eligible second purchase within 90 elapsed days / customers whose first observed purchase leaves at least 90 days until the last observed eligible purchase. This is a conservative observation cutoff, not a verified business extraction date.

### Grain and allocation

Payments and items are aggregated independently before they join orders, with validated cardinalities. Reviews are sorted by answer timestamp, creation timestamp and review ID; the latest row per order is selected for descriptive metrics. Missing dates sort first. The original review records remain available in `FactReviews` for audit. No review enters prediction features.

An order can contain several categories or sellers. Item GMV is allocated naturally by item; experience is attributed once to each order/category or order/seller pair. Consequently category/seller order counts and issue counts are not additive across groups. Delivery and review outcomes describe the whole order and cannot determine which seller caused a problem.

Customer-state analysis uses the state on the order record. The unique customer dimension keeps first-observed geography, explicitly labeled; it does not overwrite subsequent order destinations.

### Growth and exposure

The identity GMV = customers × orders/customer × GMV/order is validated monthly. The exact sequential bridge first changes customers, then purchase frequency, then AOV. Attribution depends on this ordering and is accounting decomposition, not causality. Growth tables include empty months and flag dataset boundaries; percentage changes from zero are unavailable. Scorecard growth compares the last two equal three-month windows after removing the first and last eligible months. No claim about marketing impact or robust annual seasonality is made.

The retention grid includes zero-activity observable periods and leaves the latest eligible month and future periods unavailable. Month 0 is 100% by construction. The heatmap excludes month 0 and cohorts smaller than 50 customers so a one-customer cohort cannot dominate its color scale; all cohorts remain in the exported table. The 90-day dashboard chart also requires at least 50 eligible customers per cohort. Cohort retention is activity in a specific month, not cumulative survival.

### RFM and prioritization

Snapshot = last eligible purchase date + one day. R/M scores use tied percentile ranks; frequency scores are 1, 2, 3 and 4+ orders. No arbitrary tie-breaking forces one-time buyers into different frequency quantiles. Segment precedence is documented directly in `src/feature_engineering.py`; inactive labels describe recency, never proven churn. Marketing actions are test hypotheses.

Commercial importance = top GMV quartile among entities. Rate comparison requires at least 50 delivery-eligible and 50 reviewed orders. Weak experience = the lower 95% Wilson late-rate bound exceeds the marketplace delivery rate. Improvement priorities combine high commercial importance and weak experience. Remaining high-value entities are labeled strong commercial performers, which does not establish operational equivalence. A growth candidate has positive comparable-window growth without this high-rate signal; external market potential is unknown.

Priority rank orders eligible entities by positive excess late orders over the marketplace benchmark. GMV, GMV on late orders, low-review rate, growth and confidence bounds are exposed alongside the rank. GMV on late orders is **exposure**, not lost revenue. Thresholds are analytical defaults and should be sensitivity-tested before operational use.

### Machine learning

Clustering uses log-transformed recency, frequency, monetary value and items/order after transparent upper-99th-percentile winsorization, then standardization. AOV is omitted to avoid doubling monetary weighting when frequency is one. K=2–6 is assessed with inertia, sample silhouette, minimum cluster share and seed stability. Highest silhouette among stable candidates with >=2% smallest cluster is preferred. Stability across random seeds is weaker evidence than stability across future populations. Clusters with modest separation should be treated as exploratory descriptions.

Late prediction uses order-placement/early-approval features only: basket characteristics, origin/destination state, category, calendar and promised duration. Product fields and promises are assumed available then; the public extract lacks field version history. The primary item is highest price, then lowest sequence number. Seller history is intentionally excluded because a reliable as-of history requires outcome-availability tracking.

Purchase-date 60/20/20 boundaries define train/validation/test. Training outcomes must have been delivered before validation starts; validation outcomes must be delivered before test starts. This purges labels not yet known at each boundary. Fit transformations on training only. Select model by validation average precision, then threshold by validation F1. The holdout is not used for selection. Average precision summarizes the precision-recall ranking; it is not trapezoidal PR area. Always compare it against holdout prevalence.

F1 is an illustrative threshold policy because intervention costs are absent. False negatives miss risky orders; false positives consume capacity and may unnecessarily worry customers. Validate calibration and cost/capacity policy before using probabilities in production. Predictions are conditional on eventually delivered orders with valid labels: canceled, unresolved and invalid orders are excluded, so deployment drift and selection bias remain.

Mann–Whitney tests compare distributions of tied/ordinal reviews and skewed order values. H0: the two sampled distributions are equal; H1: they differ. Report U, two-sided p, sample sizes, medians and rank-biserial effect. A median-only interpretation requires comparable distribution shapes. Orders may cluster by customer or seller, weakening independence. Bonferroni-adjusted p-values cover the two comparisons; these are exploratory association checks, not causal inference.
