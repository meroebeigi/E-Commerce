-- SQLite 3.25+. One row per order; populations match Python.
WITH commercial AS (SELECT * FROM FactOrders WHERE commercial_eligible = 1),
customers AS (SELECT customer_unique_id, COUNT(*) n FROM commercial GROUP BY customer_unique_id)
SELECT SUM(merchandise_value) AS gmv, COUNT(*) AS orders,
       COUNT(DISTINCT customer_unique_id) AS customers,
       SUM(merchandise_value)/COUNT(*) AS aov,
       (SELECT AVG(CASE WHEN n>1 THEN 1.0 ELSE 0.0 END) FROM customers) AS repeat_customer_rate,
       (SELECT AVG(CAST(is_late AS REAL)) FROM FactOrders WHERE delivery_eligible=1) AS late_delivery_rate
FROM commercial;
