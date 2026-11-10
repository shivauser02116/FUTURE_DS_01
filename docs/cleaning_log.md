# Data Cleaning Log - FUTURE_DS_01

- Loaded `Sample - Superstore.csv` with encoding `cp1252`: 9994 rows x 21 columns.
- Standardised column names to snake_case (e.g. `Order Date` -> `order_date`).
- Stripped leading/trailing whitespace from all text columns.
- Converted `order_date` to datetime (0 unparseable values remain).
- Converted `ship_date` to datetime (0 unparseable values remain).
- Converted `postal_code` to 5-character text to restore leading zeros.
- No missing values found.
- Removed 1 exact duplicate row(s) (ignoring `row_id`).
- Validation: ship before order = 0, discount outside 0-1 = 0, quantity <= 0 = 0, sales <= 0 = 0.
- Kept 1870 loss-making order lines (18.7% of all lines) - these are real losses, not errors, and are central to the analysis.
- 32 product_id value(s) map to more than one product_name - use `product_name` for product rankings.
- Added helper columns: `order_year`, `order_month`, `year_month`, `ship_days`, `profit_margin`.
- Saved cleaned data to `superstore_clean.csv`: 9993 rows x 26 columns.
