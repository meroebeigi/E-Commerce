WITH money AS (
 SELECT i.seller_id,SUM(i.price) gmv,COUNT(*) units,COUNT(DISTINCT i.order_id) orders
 FROM FactOrderItems i JOIN FactOrders o USING(order_id)
 WHERE o.commercial_eligible=1 GROUP BY i.seller_id
), pairs AS (
 SELECT DISTINCT i.seller_id,o.order_id,o.delivery_eligible,o.is_late
 FROM FactOrderItems i JOIN FactOrders o USING(order_id) WHERE o.commercial_eligible=1
), rates AS (
 SELECT seller_id,SUM(delivery_eligible) delivery_orders,
 AVG(CASE WHEN delivery_eligible=1 THEN CAST(is_late AS REAL) END) late_delivery_rate
 FROM pairs GROUP BY seller_id
)
SELECT m.*,r.delivery_orders,r.late_delivery_rate,
 CASE WHEN delivery_orders>=50 THEN 1 ELSE 0 END rate_sample_eligible,
 RANK() OVER (ORDER BY gmv DESC) commercial_rank,
 SUM(gmv) OVER (ORDER BY gmv DESC,m.seller_id ROWS UNBOUNDED PRECEDING)/SUM(gmv) OVER () cumulative_gmv_share
FROM money m JOIN rates r USING(seller_id) ORDER BY gmv DESC;
