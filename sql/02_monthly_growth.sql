WITH monthly AS (
 SELECT purchase_month, SUM(merchandise_value) gmv, COUNT(*) orders,
 COUNT(DISTINCT customer_unique_id) customers, SUM(merchandise_value)/COUNT(*) aov
 FROM FactOrders WHERE commercial_eligible=1 GROUP BY purchase_month
), lagged AS (
 SELECT *, LAG(gmv) OVER (ORDER BY purchase_month) prior_gmv,
 AVG(gmv) OVER (ORDER BY purchase_month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) trailing_3_active_month_gmv
 FROM monthly
)
SELECT *, gmv/NULLIF(prior_gmv,0)-1 AS gmv_mom FROM lagged ORDER BY purchase_month;
