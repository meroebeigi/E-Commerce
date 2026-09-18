-- Recursion creates true zero cells. Latest eligible month is treated as incomplete.
WITH RECURSIVE ages(age) AS (
 SELECT 0 UNION ALL SELECT age+1 FROM ages WHERE age<120
), c AS (SELECT * FROM FactOrders WHERE commercial_eligible=1),
sizes AS (SELECT cohort_month,COUNT(DISTINCT customer_unique_id) cohort_size FROM c GROUP BY cohort_month),
activity AS (
 SELECT cohort_month,
 (CAST(substr(purchase_month,1,4) AS INT)-CAST(substr(cohort_month,1,4) AS INT))*12
 +CAST(substr(purchase_month,6,2) AS INT)-CAST(substr(cohort_month,6,2) AS INT) age,
 COUNT(DISTINCT customer_unique_id) active_customers
 FROM c GROUP BY cohort_month,age
), grid AS (
 SELECT s.*,a.age,date(s.cohort_month||'-01','+'||a.age||' months') period
 FROM sizes s CROSS JOIN ages a
 WHERE date(s.cohort_month||'-01','+'||a.age||' months')<=date((SELECT MAX(purchase_month) FROM c)||'-01')
)
SELECT g.cohort_month,g.age age_month,g.cohort_size,
 CASE WHEN g.period<date((SELECT MAX(purchase_month) FROM c)||'-01') THEN COALESCE(a.active_customers,0) END active_customers,
 CASE WHEN g.period<date((SELECT MAX(purchase_month) FROM c)||'-01') THEN 1.0*COALESCE(a.active_customers,0)/g.cohort_size END retention_rate
FROM grid g LEFT JOIN activity a ON g.cohort_month=a.cohort_month AND g.age=a.age
ORDER BY g.cohort_month,g.age;
