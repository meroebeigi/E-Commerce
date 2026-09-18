# Public Olist input data

Original source: [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce).
This build retrieved the user's public mirror at [meroebeigi/E-Commerce](https://github.com/meroebeigi/E-Commerce/tree/41710981b96a59a5399d88c62339ede3c8207e46/archive).
`source_manifest.json` records the exact URLs, byte sizes and SHA-256 hashes. `output/source_checksums.csv` rechecks actual inputs each run.

Download the public dataset, extract it, and put these eight files in `data/raw/`:

```
olist_orders_dataset.csv
olist_customers_dataset.csv
olist_order_items_dataset.csv
olist_order_payments_dataset.csv
olist_order_reviews_dataset.csv
olist_products_dataset.csv
olist_sellers_dataset.csv
product_category_name_translation.csv
```

The optional large geolocation file is not needed: this version uses state-level geography and makes no precise distance claims. Files are ignored by Git; do not commit raw archives or row-level exports by default. Follow the original dataset's license and attribution requirements for any redistribution. Whiteaway data, charts, records and recommendations are not used.
