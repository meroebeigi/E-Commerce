# Review of the starting notebook

Source: `meroebeigi/E-Commerce`, commit `41710981b96a59a5399d88c62339ede3c8207e46`, `Ecommence.ipynb`.

| Original behavior | Consequence | Rebuilt behavior |
|---|---|---|
| Orders → items → payments joined directly | Multiple item and payment rows expand each other; payment/category totals inflate | Aggregate items and payments separately to orders; use item prices for category GMV; quantify defect in `output/original_join_impact.csv` |
| Payment value described as actual revenue | Payment includes freight and is not platform accounting revenue | Separate GMV, freight and payment values with a reconciliation |
| No documented order-status population | Unresolved/canceled orders can mix with delivered commerce | Explicit commercial, delivery, review and all-order populations |
| Growth interpreted as marketing working | No channel or experiment evidence supports attribution | Accounting growth bridge and association-only interpretation |
| Non-repeat purchase described as weak retention | Unequal observation windows and marketplace behavior matter | Monthly cohorts and a matured 90-day second-purchase denominator |
| Pareto principle asserted without reporting a threshold | Assumes an 80/20 result | Calculate customer/category/seller share required for 50% and 80% GMV |
| Absolute local Windows paths | Not portable | Project-relative raw input folder and documented setup |
| No key/foreign-key validation or reconciliations | Join failures can pass silently | Assertions, explicit merge validation, unmatched coverage and SQL reconciliation |

Preserved analytical intent: monthly commercial trends, category contribution, unique-customer repeat behavior, cumulative contribution and business recommendations. Rewrote calculations and conclusions wherever the original approach was unsupported. The source notebook is retained under `docs/` for provenance, not presented as validated analysis.

No confidential industry-project files were required or incorporated. The public project uses the general volume-versus-rate analytical principle from the supplied brief only.
