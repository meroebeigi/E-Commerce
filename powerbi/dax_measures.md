# Proposed DAX measures

Create these measures individually. The CSV flags must be Boolean and dates must be Date. These measures are supplied for Desktop validation; they have not been executed in a DAX engine here.

Commercial measures use item-level GMV and explicitly propagate selected item IDs to orders when needed. This preserves category/seller slicers without global bidirectional relationships. Experience measures apply category/seller restrictions only when such a dimension is filtered; otherwise they retain delivery/review-eligible orders even if an item is absent.

```DAX
Total GMV =
CALCULATE(SUM(FactOrderItems[price]), FactOrders[commercial_eligible] = TRUE())

Total Orders =
CALCULATE(DISTINCTCOUNT(FactOrderItems[order_id]), FactOrders[commercial_eligible] = TRUE())

Unique Customers =
VAR OrderIDs = CALCULATETABLE(VALUES(FactOrderItems[order_id]), FactOrders[commercial_eligible] = TRUE())
RETURN CALCULATE(DISTINCTCOUNT(FactOrders[customer_unique_id]),
    FactOrders[commercial_eligible] = TRUE(), KEEPFILTERS(TREATAS(OrderIDs, FactOrders[order_id])))

AOV = DIVIDE([Total GMV], [Total Orders])

Units Sold = CALCULATE(COUNTROWS(FactOrderItems), FactOrders[commercial_eligible] = TRUE())

GMV per Customer = DIVIDE([Total GMV], [Unique Customers])

Items per Order = DIVIDE([Units Sold], [Total Orders])

New Customer GMV = CALCULATE([Total GMV], FactOrders[is_returning] = FALSE())

Returning Customer GMV = CALCULATE([Total GMV], FactOrders[is_returning] = TRUE())

Returning Order GMV Share = DIVIDE([Returning Customer GMV], [Total GMV])

Repeat Customer Rate =
VAR OrderIDs = CALCULATETABLE(VALUES(FactOrderItems[order_id]), FactOrders[commercial_eligible] = TRUE())
VAR CustomerCounts =
    CALCULATETABLE(
        SUMMARIZE(FactOrders, FactOrders[customer_unique_id], "N", COUNTROWS(FactOrders)),
        FactOrders[commercial_eligible] = TRUE(),
        KEEPFILTERS(TREATAS(OrderIDs, FactOrders[order_id])))
RETURN DIVIDE(COUNTROWS(FILTER(CustomerCounts, [N] > 1)), COUNTROWS(CustomerCounts))

Late Delivery Rate =
VAR HasItemFilter = ISCROSSFILTERED(DimProduct) || ISCROSSFILTERED(DimSeller)
VAR OrderIDs = VALUES(FactOrderItems[order_id])
VAR Eligible =
    FILTER(FactOrders, FactOrders[delivery_eligible] = TRUE() &&
        (NOT HasItemFilter || FactOrders[order_id] IN OrderIDs))
RETURN DIVIDE(COUNTROWS(FILTER(Eligible, FactOrders[is_late] = TRUE())), COUNTROWS(Eligible))

Average Delivery Days =
VAR HasItemFilter = ISCROSSFILTERED(DimProduct) || ISCROSSFILTERED(DimSeller)
VAR OrderIDs = VALUES(FactOrderItems[order_id])
RETURN AVERAGEX(FILTER(FactOrders, FactOrders[delivery_eligible] = TRUE() &&
    (NOT HasItemFilter || FactOrders[order_id] IN OrderIDs)), FactOrders[delivery_days])

Low Review Rate =
VAR HasItemFilter = ISCROSSFILTERED(DimProduct) || ISCROSSFILTERED(DimSeller)
VAR OrderIDs = VALUES(FactOrderItems[order_id])
VAR Eligible = FILTER(FactOrders, FactOrders[review_eligible] = TRUE() &&
    (NOT HasItemFilter || FactOrders[order_id] IN OrderIDs))
RETURN DIVIDE(COUNTROWS(FILTER(Eligible, FactOrders[low_review] = TRUE())), COUNTROWS(Eligible))

Average Review Score =
VAR HasItemFilter = ISCROSSFILTERED(DimProduct) || ISCROSSFILTERED(DimSeller)
VAR OrderIDs = VALUES(FactOrderItems[order_id])
RETURN AVERAGEX(FILTER(FactOrders, FactOrders[review_eligible] = TRUE() &&
    (NOT HasItemFilter || FactOrders[order_id] IN OrderIDs)), FactOrders[review_score])

GMV Previous Month = CALCULATE([Total GMV], DATEADD(DimDate[date], -1, MONTH))

GMV MoM Growth = DIVIDE([Total GMV] - [GMV Previous Month], [GMV Previous Month])

Category GMV Contribution =
DIVIDE([Total GMV], CALCULATE([Total GMV], REMOVEFILTERS(DimProduct[category])))

Cancellation Rate All Orders =
DIVIDE(CALCULATE(COUNTROWS(FactOrders), FactOrders[is_canceled] = TRUE()), COUNTROWS(FactOrders))
```

Repeat Customer Rate above counts multiple purchases **within the current date/category/seller selection**. On an unfiltered card it matches the Python full-window result. This differs from a permanent lifetime repeat-customer label. New/returning classification remains anchored to the customer's first eligible purchase in the full dataset. Explain both semantics in tooltips.

Cancellation is an order-level measure: disable product/seller interactions on that card, because orders without items cannot be allocated reliably. Do not use order payment totals as category revenue. For category GMV contribution, the denominator removes only category; other product attributes and non-product filters remain. MoM comparisons need complete comparable periods, not partial-month selections.

### Desktop validation checklist

Compare unfiltered GMV, orders, customers, AOV, repeat rate and late rate to `output/kpis.csv`; category GMV/order/late-rate to `categories.csv`; seller values to `sellers.csv`. Check a multi-item multi-payment order manually. Check an order in several categories appears once in each category but once in the total. Verify missing reviews do not count as good reviews. Verify date filters, category filters and seller filters independently before combining them.
