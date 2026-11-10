"""
FUTURE_DS_01 - Step 1: Data cleaning for the Superstore Sales dataset.

Usage:
    1. Download the dataset from Kaggle (vivek468/superstore-dataset-final).
    2. Put the CSV next to this script (default name: Sample - Superstore.csv).
    3. Run:  python 01_clean_superstore.py
       (or paste the code into a Jupyter notebook, cell by cell)

Outputs:
    superstore_clean.csv   -> load this into Power BI
    cleaning_log.md        -> paste/commit into your GitHub repo
"""

import pandas as pd

RAW_FILE = "Sample - Superstore.csv"
CLEAN_FILE = "superstore_clean.csv"
LOG_FILE = "cleaning_log.md"

log = []  # every cleaning decision is recorded here


def note(msg):
    print(msg)
    log.append(f"- {msg}")


# ---------------------------------------------------------------- 1. LOAD
# This file is usually not UTF-8, so try common encodings.
for enc in ("utf-8", "cp1252", "latin-1"):
    try:
        df = pd.read_csv(RAW_FILE, encoding=enc)
        note(f"Loaded `{RAW_FILE}` with encoding `{enc}`: {df.shape[0]} rows x {df.shape[1]} columns.")
        break
    except UnicodeDecodeError:
        continue
else:
    raise SystemExit("Could not read the file with any common encoding.")

# ---------------------------------------------------------------- 2. INSPECT
print("\n--- dtypes ---")
print(df.dtypes)
print("\n--- null counts ---")
print(df.isna().sum())

# ---------------------------------------------------------------- 3. COLUMN NAMES
df.columns = (
    df.columns.str.strip().str.lower().str.replace(r"[^a-z0-9]+", "_", regex=True).str.strip("_")
)
note("Standardised column names to snake_case (e.g. `Order Date` -> `order_date`).")

# ---------------------------------------------------------------- 4. TEXT TIDY
text_cols = df.select_dtypes(include=["object", "string"]).columns
df[text_cols] = df[text_cols].apply(lambda s: s.str.strip())
note("Stripped leading/trailing whitespace from all text columns.")

# ---------------------------------------------------------------- 5. DATES
for col in ("order_date", "ship_date"):
    parsed = pd.to_datetime(df[col], format="%m/%d/%Y", errors="coerce")
    failed = parsed.isna().sum()
    if failed:  # fall back to flexible parsing for any odd rows
        parsed = parsed.fillna(pd.to_datetime(df[col], errors="coerce"))
    df[col] = parsed
    note(f"Converted `{col}` to datetime ({parsed.isna().sum()} unparseable values remain).")

# ---------------------------------------------------------------- 6. POSTAL CODE
# Postal codes are identifiers, not numbers. Reading them as ints drops leading zeros
# (e.g. 01234 -> 1234), so store as 5-character text.
if "postal_code" in df.columns:
    df["postal_code"] = (
        df["postal_code"].astype("string").str.replace(r"\.0$", "", regex=True).str.zfill(5)
    )
    note("Converted `postal_code` to 5-character text to restore leading zeros.")

# ---------------------------------------------------------------- 7. NULLS
nulls = df.isna().sum()
nulls = nulls[nulls > 0]
if nulls.empty:
    note("No missing values found.")
else:
    note(f"Missing values found: {nulls.to_dict()} - review these manually before dropping.")

# ---------------------------------------------------------------- 8. DUPLICATES
# row_id is unique per row, so ignore it when looking for repeated records.
check_cols = [c for c in df.columns if c != "row_id"]
dupes = df.duplicated(subset=check_cols).sum()
if dupes:
    df = df.drop_duplicates(subset=check_cols).reset_index(drop=True)
note(f"Removed {dupes} exact duplicate row(s) (ignoring `row_id`).")

# ---------------------------------------------------------------- 9. VALIDATION
bad_ship = (df["ship_date"] < df["order_date"]).sum()
bad_disc = (~df["discount"].between(0, 1)).sum()
bad_qty = (df["quantity"] <= 0).sum()
bad_sales = (df["sales"] <= 0).sum()
note(
    f"Validation: ship before order = {bad_ship}, discount outside 0-1 = {bad_disc}, "
    f"quantity <= 0 = {bad_qty}, sales <= 0 = {bad_sales}."
)

neg_profit = (df["profit"] < 0).sum()
note(
    f"Kept {neg_profit} loss-making order lines ({neg_profit / len(df):.1%} of all lines) - "
    "these are real losses, not errors, and are central to the analysis."
)

# Product IDs that map to more than one product name can distort product-level analysis.
multi = df.groupby("product_id")["product_name"].nunique()
multi = (multi > 1).sum()
note(
    f"{multi} product_id value(s) map to more than one product_name - "
    "use `product_name` for product rankings."
)

# ---------------------------------------------------------------- 10. NEW COLUMNS
df["order_year"] = df["order_date"].dt.year
df["order_month"] = df["order_date"].dt.month
df["year_month"] = df["order_date"].dt.to_period("M").astype(str)
df["ship_days"] = (df["ship_date"] - df["order_date"]).dt.days
df["profit_margin"] = (df["profit"] / df["sales"]).round(4)
note("Added helper columns: `order_year`, `order_month`, `year_month`, `ship_days`, `profit_margin`.")

# ---------------------------------------------------------------- 11. SAVE
df.to_csv(CLEAN_FILE, index=False)
note(f"Saved cleaned data to `{CLEAN_FILE}`: {df.shape[0]} rows x {df.shape[1]} columns.")

with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write("# Data Cleaning Log - FUTURE_DS_01\n\n" + "\n".join(log) + "\n")

print("\nDone. Quick summary of the cleaned data:")
print(df[["sales", "quantity", "discount", "profit"]].describe().round(2))
print(f"\nDate range: {df['order_date'].min().date()} to {df['order_date'].max().date()}")
