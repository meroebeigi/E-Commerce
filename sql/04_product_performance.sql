-- Item GMV is additive; distinct order counts across categories are not additive.
WITH money AS (
 SELECT p.category, SUM(i.price) gmv, COUNT(*) units, COUNT(DISTINCT i.order_id) orders,
 COUNT(DISTINCT o.customer_unique_id) customers
 FROM FactOrderItems i JOIN FactOrders o USING(order_id) JOIN DimProduct p USING(product_id)
 WHERE o.commercial_eligible=1 GROUP BY p.category
), pairs AS (
 SELECT DISTINCT p.category,o.order_id,o.is_late,o.delivery_eligible,o.review_score,o.review_eligible
 FROM FactOrderItems i JOIN FactOrders o USING(order_id) JOIN DimProduct p USING(product_id)
 WHERE o.commercial_eligible=1
), experience AS (
 SELECT category, AVG(CASE WHEN delivery_eligible=1 THEN CAST(is_late AS REAL) END) late_delivery_rate,
 AVG(CASE WHEN review_eligible=1 THEN review_score END) average_review_score
 FROM pairs GROUP BY category
)
SELECT m.*, gmv/orders aov, gmv/SUM(gmv) OVER () gmv_share,e.late_delivery_rate,e.average_review_score
FROM money m JOIN experience e USING(category) ORDER BY gmv DESC;
