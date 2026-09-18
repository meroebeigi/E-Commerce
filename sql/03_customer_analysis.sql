WITH customer AS (
 SELECT customer_unique_id, COUNT(*) orders, SUM(merchandise_value) gmv,
 MIN(order_purchase_timestamp) first_purchase,
 SUM(CASE WHEN is_returning=1 THEN merchandise_value ELSE 0 END) returning_order_gmv
 FROM FactOrders WHERE commercial_eligible=1 GROUP BY customer_unique_id
)
SELECT *, RANK() OVER (ORDER BY gmv DESC) value_rank,
 SUM(gmv) OVER (ORDER BY gmv DESC, customer_unique_id ROWS UNBOUNDED PRECEDING)/SUM(gmv) OVER () cumulative_gmv_share
FROM customer ORDER BY gmv DESC, customer_unique_id;
