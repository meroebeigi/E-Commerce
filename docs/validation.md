# Validation record

Validated source commit: `41710981b96a59a5399d88c62339ede3c8207e46`.

| Check | Result |
|---|---|
| Public source files | Eight SHA-256 hashes verified against download manifest |
| Raw/model financial and status totals | Seven checks passed |
| SQL/Python metrics | Eighteen checks passed |
| Targeted regression tests | Six passed under the recorded analysis runtime |
| Notebook execution | Four notebooks, 30 code cells, no error outputs |
| Figures | Nine analytical charts and four dashboard previews visually reviewed |
| Native Power BI / DAX | Not executed; build instructions and design artifacts supplied |

Tests cover item/payment multiplication, same-day promise handling, latest review selection, invalid chronology, duplicate keys, orphan references and unobserved cohort periods. Test fixtures are synthetic and used only for regression checks; no synthetic result enters the public-data analysis.

A final packaging check validates notebook structure/execution counts, parses Python sources, verifies original data hashes and reconciles the confusion-matrix counts. Package versions are in `requirements-validated.txt`.

The final visual review removed tiny cohorts from plotted rates (minimum 50), while retaining all cohorts in the exported tables. The model remains exploratory because precision and intervention evidence are insufficient for deployment.
