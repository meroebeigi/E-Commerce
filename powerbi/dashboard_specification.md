# Four-page decision dashboard

Canvas: 16:9, off-white background, navy text, blue/teal for commercial measures, orange for operational concerns. Use BRL labels, percentages to one decimal and counts with separators. Show the selected period and population on every page. Place high-level cards above trends, comparisons and a short action panel. Static previews in `dashboard_preview/` contain actual computed results; the instructions below define intended interactive behavior.

## 1. Executive Overview

**Decision:** Is growth accompanied by healthy customer and fulfillment outcomes?

Top cards: GMV, orders, customers, AOV, repeat-customer rate, late-delivery rate. Main row: monthly GMV and monthly customer trend. Lower row: category GMV contribution and customer-state performance. Footer: current selection, delivered-only commerce definition and boundary-period flag.

Slicers: purchase date, customer state on FactOrders. Category and seller filters are optional and must use matching item/order measures. Clicking a month filters detail visuals. Tooltip: GMV, orders, customers, AOV, eligible delivery denominator, missing-review coverage. Drill through to commercial or operations page by category/state. Avoid displaying a headline cancellation card under product filters.

## 2. Customer & Growth Intelligence

**Decision:** How much growth depends on first-time buyers, and which customer hypotheses are worth testing?

Cards: new customers, returning customers, returning-order GMV share, GMV/customer and matured 90-day second-purchase rate. Visuals: new/subsequent GMV stack, monthly customers and AOV, RFM shares, concentration curve and cohort retention heatmap. Month 0 should be displayed separately as structural 100%; blank cells mean unobservable, not zero. Show cohort size alongside every row.

Slicers: acquisition cohort for the disconnected retention snapshot; purchase period for transaction visuals; full-window RFM segment if merged into DimCustomer. Do not imply that a daily date slicer recalculates the precomputed cohort table. Tooltips define first/subsequent orders and observation eligibility. Drill through from a segment to aggregate customer profile and candidate actions, avoiding an unnecessarily exposed personal-level table. Show the exact growth bridge in a tooltip or supporting table; it does not assign causal credit to marketing.

## 3. Commercial Performance

**Decision:** Which categories and sellers combine commercial scale with reliable performance?

Cards: selected GMV, contribution, distinct orders and units. Visuals: category scorecard, seller scorecard, contribution/Pareto curves, comparable-window category growth and seller Volume × Rate × GMV bubble chart. Include the 95% rate interval, reviewed/delivery denominators, sample-eligibility label, low-review rate and priority group in the tables. Use a log volume axis for the bubble chart and explain its scale.

Slicers: category, seller state, customer state, purchase date. Sample-size parameter defaults to 50 and should be accompanied by a sensitivity view at 30/50/100. Python snapshot priorities use 50; a changed interactive parameter must not relabel them without recalculation. Seller drill-through: category mix, monthly volume, late rate, review coverage. Tooltip warns that multi-seller orders share an order-level delivery label. Never add category distinct-order counts to make a marketplace total.

## 4. Customer Experience & Operations

**Decision:** Where should the operations team investigate, and can a risk model support triage?

Cards: late rate, median/mean delivery days, low-review rate and reviewed-order coverage. Visuals: duration distribution, on-time/late review comparison, high-volume risk sellers, category priority table and state delivery performance. Include an optional model panel with temporal holdout period, prevalence, average precision, precision, recall and alert volume. Clearly label experimental model results; the current pipeline does not validate intervention effectiveness or probability calibration.

Slicers: date, category, seller, order destination state. Use matched populations for comparisons. Tooltips expose eligible denominator, missing dates, interval, associated GMV and low-review rate. Drill through to an operational diagnostic page with order chronology, selected review and payment reconciliation if needed for analyst audit. Show no fabricated returns or return reasons.

## Interaction and accessibility requirements

- Keep visible metric definitions and population labels; never use color as the sole encoding of risk.
- Keep monetary axes at zero for bars, label log axes and avoid 3-D graphics.
- Retain readable labels and short business titles; table drill-through handles detailed IDs.
- Default to the full validated observation window, with incomplete-period context visible.
- Exported static page images document visual hierarchy, not interactive Power BI functionality.
