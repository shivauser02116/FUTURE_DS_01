"""
scripts/03_check_app.py
=======================
Automated checks for the FUTURE_DS_01 Streamlit app and the underlying data.

Run from the repo root:
    python scripts/03_check_app.py

Requirements: streamlit >= 1.50 (for AppTest), pandas
"""

import sys
import traceback
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

# ── Paths ──────────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).parent.parent
APP_PATH  = REPO_ROOT / "app" / "streamlit_app.py"
CSV_PATH  = REPO_ROOT / "data" / "superstore_clean.csv"

# ── Tolerance for numeric checks (0.5 %) ──────────────────────────────────────
TOL = 0.005

# ── Result tracking ───────────────────────────────────────────────────────────
results: list[tuple[str, bool, str]] = []


def check(label: str, passed: bool, actual: str) -> None:
    """Record a PASS/FAIL result and print it immediately."""
    tag = "PASS" if passed else "FAIL"
    print(f"[{tag}] {label}: {actual}")
    results.append((label, passed, actual))


def within(actual: float, expected: float) -> bool:
    """True if actual is within TOL of expected (relative)."""
    if expected == 0:
        return abs(actual) < 1e-9
    return abs(actual - expected) / abs(expected) <= TOL


def parse_currency(s: str) -> float:
    """Parse '$2.30M' or '$286K' into a float."""
    s = s.replace("$", "").replace(",", "").replace("-", "").strip()
    if s.endswith("M"):
        return float(s[:-1]) * 1_000_000
    if s.endswith("K"):
        return float(s[:-1]) * 1_000
    return float(s) if s else 0.0


# ══════════════════════════════════════════════════════════════════════════════
# SECTION A — AppTest checks (Streamlit testing framework)
# ══════════════════════════════════════════════════════════════════════════════

print("\n=== SECTION A: AppTest (Streamlit app UI) ===\n")

# ── A1: Default run — no exceptions ───────────────────────────────────────────
# We need 'at' in scope for all subsequent checks; initialise outside try/except.
at = AppTest.from_file(str(APP_PATH), default_timeout=60)

try:
    at.run()
    no_exc = len(at.exception) == 0
    check("A1 No exceptions on default run", no_exc,
          "none" if no_exc else str(at.exception))
except Exception as e:
    check("A1 No exceptions on default run", False, f"ERROR: {e}")

# ── A2-A7: KPI metric cards ───────────────────────────────────────────────────
# Locate each metric by label; robust to DOM order changes.

def check_metric(test_id: str, label: str, expected_str: str) -> None:
    try:
        metrics_by_label = {m.label: m.value for m in at.metric}
        actual = metrics_by_label.get(label, "<not found>")
        check(test_id, actual == expected_str, repr(actual))
    except Exception as e:
        check(test_id, False, f"ERROR: {e}")

check_metric("A2 Total Sales",       "Total Sales",       "$2.30M")
check_metric("A3 Total Profit",      "Total Profit",      "$286K")
check_metric("A4 Profit Margin",     "Profit Margin",     "12.5%")
check_metric("A5 Orders",            "Orders",            "5,009")
check_metric("A6 Avg Order Value",   "Avg Order Value",   "$459")
check_metric("A7 Loss-making Lines", "Loss-making Lines", "18.7%")

# ── A8-A9: Overview headline ───────────────────────────────────────────────────
try:
    headline_text = ""
    for md in at.markdown:
        if "had the highest sales" in (md.value or ""):
            headline_text = md.value
            break
    check("A8 Headline contains '2017'",
          "2017"  in headline_text, repr(headline_text[:120]))
except Exception as e:
    check("A8 Headline contains '2017'", False, f"ERROR: {e}")
    headline_text = ""

try:
    check("A9 Headline contains '$733K'",
          "$733K" in headline_text, repr(headline_text[:120]))
except Exception as e:
    check("A9 Headline contains '$733K'", False, f"ERROR: {e}")

# ── A10-A11: Remove 2017, re-run ───────────────────────────────────────────────
# Capture Total Sales before the filter change.
try:
    metrics_before   = {m.label: m.value for m in at.metric}
    sales_before_str = metrics_before.get("Total Sales", "$0")
    sales_before     = parse_currency(sales_before_str)
except Exception as e:
    sales_before = None
    print(f"[WARN] Could not read sales_before: {e}")

try:
    # Find the Year multiselect by iterating the ElementList (not by label= kwarg)
    year_widget = next(w for w in at.multiselect if w.label == "Year")
    year_widget.set_value([2014, 2015, 2016])   # int values, exclude 2017
    at.run()
    no_exc_2 = len(at.exception) == 0
    check("A10 No exceptions after removing 2017", no_exc_2,
          "none" if no_exc_2 else str(at.exception))
except Exception as e:
    check("A10 No exceptions after removing 2017", False, f"ERROR: {e}")

try:
    metrics_after   = {m.label: m.value for m in at.metric}
    sales_after_str = metrics_after.get("Total Sales", "$0")
    sales_after     = parse_currency(sales_after_str)
    if sales_before is not None:
        check("A11 Total Sales lower without 2017",
              sales_after < sales_before,
              f"{sales_after_str} vs before {sales_before_str}")
    else:
        check("A11 Total Sales lower without 2017", False,
              "sales_before was not captured")
except Exception as e:
    check("A11 Total Sales lower without 2017", False, f"ERROR: {e}")

# ── A12-A14: Tab 4 (Summary & Recommendations) checks ──────────────────────────
try:
    has_rec_tab = any("Summary & Recommendations" in t.label for t in at.tabs)
    check("A12 Tab labelled 'Summary & Recommendations'",
          has_rec_tab, "found" if has_rec_tab else "not found")
except Exception as e:
    check("A12 Tab labelled 'Summary & Recommendations'", False, f"ERROR: {e}")

try:
    rec_tab = next(t for t in at.tabs if "Summary & Recommendations" in t.label)
    tab_text = " ".join(m.value for m in rec_tab.markdown)
    has_texas = "Texas" in tab_text
    has_135 = "$135" in tab_text
    check("A13 Tab text contains 'Texas' and discount loss starting with '$135'",
          has_texas and has_135,
          f"Texas={'found' if has_texas else 'missing'}, $135={'found' if has_135 else 'missing'}")
except Exception as e:
    check("A13 Tab text contains 'Texas' and discount loss starting with '$135'", False, f"ERROR: {e}")

try:
    at_default = AppTest.from_file(str(APP_PATH), default_timeout=60)
    at_default.run()
    no_exc_default = len(at_default.exception) == 0
    check("A14 No exceptions on default run after change",
          no_exc_default, "none" if no_exc_default else str(at_default.exception))
except Exception as e:
    check("A14 No exceptions on default run after change", False, f"ERROR: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION B — Pandas data-fact checks (direct CSV, no app)
# Always runs, even if Section A raised errors.
# ══════════════════════════════════════════════════════════════════════════════

print("\n=== SECTION B: Pandas data-fact checks ===\n")


def disc_band(d: float) -> str:
    if d == 0:      return "0%"
    if d <= 0.20:   return "1-20%"
    if d <= 0.50:   return "21-50%"
    return "51-80%"


# Load CSV once; if this fails all B-checks will FAIL individually via try/except.
try:
    df = pd.read_csv(CSV_PATH, dtype={"postal_code": str},
                     parse_dates=["order_date", "ship_date"])
    df["disc_band"] = df["discount"].apply(disc_band)
    _df_ok = True
except Exception as e:
    _df_ok = False
    print(f"[ERROR] Could not load CSV: {e}")
    df = None

# ── B1-B4: Sales by year ───────────────────────────────────────────────────────
YEAR_EXPECTED = {2014: 484_000, 2015: 471_000, 2016: 609_000, 2017: 733_000}
for year, exp in YEAR_EXPECTED.items():
    try:
        yr   = df.groupby("order_year")["sales"].sum()
        act  = yr.get(year, 0)
        check(f"B{year-2013} Sales {year}",
              within(act, exp), f"${act/1e3:.0f}K (expected ~${exp/1e3:.0f}K)")
    except Exception as e:
        check(f"B{year-2013} Sales {year}", False, f"ERROR: {e}")

# ── B5-B8: Profit by discount band ────────────────────────────────────────────
BAND_ORDER    = ["0%", "1-20%", "21-50%", "51-80%"]
BAND_EXPECTED = [321_000, 100_800, -58_800, -76_600]
for i, (band, exp) in enumerate(zip(BAND_ORDER, BAND_EXPECTED)):
    try:
        band_profit = df.groupby("disc_band")["profit"].sum()
        act = band_profit.get(band, 0)
        check(f"B{i+5} Profit band '{band}'",
              within(act, exp), f"${act/1e3:+.1f}K (expected ${exp/1e3:+.1f}K)")
    except Exception as e:
        check(f"B{i+5} Profit band '{band}'", False, f"ERROR: {e}")

# ── B9-B12: Worst states ──────────────────────────────────────────────────────
STATE_EXPECTED = {
    "Texas":        -25_700,
    "Ohio":         -17_000,
    "Pennsylvania": -15_600,
    "Illinois":     -12_600,
}
for i, (state, exp) in enumerate(STATE_EXPECTED.items()):
    try:
        state_profit = df.groupby("state")["profit"].sum()
        act = state_profit.get(state, 0)
        check(f"B{i+9} State '{state}'",
              within(act, exp), f"${act/1e3:.1f}K (expected ${exp/1e3:.1f}K)")
    except Exception as e:
        check(f"B{i+9} State '{state}'", False, f"ERROR: {e}")

# ── B13-B14: Region margins ────────────────────────────────────────────────────
for b_id, (region, exp_pct) in zip([13, 14], [("Central", 7.9), ("West", 14.9)]):
    try:
        reg = df.groupby("region").agg(sales=("sales","sum"), profit=("profit","sum"))
        reg["margin"] = reg["profit"] / reg["sales"] * 100
        act = reg.loc[region, "margin"] if region in reg.index else float("nan")
        check(f"B{b_id} Region '{region}' margin",
              within(act, exp_pct), f"{act:.1f}% (expected {exp_pct}%)")
    except Exception as e:
        check(f"B{b_id} Region '{region}' margin", False, f"ERROR: {e}")

# ── B15-B16: Furniture = 32% of sales, 6% of profit ──────────────────────────
# Compare rounded whole percentages as instructed.
try:
    cat = df.groupby("category").agg(sales=("sales","sum"), profit=("profit","sum"))
    furn_sales_share  = cat.loc["Furniture","sales"]  / cat["sales"].sum()  * 100
    check("B15 Furniture 32% of sales",
          round(furn_sales_share) == 32,
          f"{furn_sales_share:.1f}% rounds to {round(furn_sales_share)} (expected 32)")
except Exception as e:
    check("B15 Furniture 32% of sales", False, f"ERROR: {e}")

try:
    cat = df.groupby("category").agg(sales=("sales","sum"), profit=("profit","sum"))
    furn_profit_share = cat.loc["Furniture","profit"] / cat["profit"].sum() * 100
    check("B16 Furniture 6% of profit",
          round(furn_profit_share) == 6,
          f"{furn_profit_share:.1f}% rounds to {round(furn_profit_share)} (expected 6)")
except Exception as e:
    check("B16 Furniture 6% of profit", False, f"ERROR: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════════════════════

print("\n=== SUMMARY ===\n")
passed = sum(1 for _, ok, _ in results if ok)
failed = sum(1 for _, ok, _ in results if not ok)
total  = len(results)

for label, ok, actual in results:
    tag = "PASS" if ok else "FAIL"
    print(f"  [{tag}] {label}")

print(f"\n{passed}/{total} checks passed", end="")
if failed:
    print(f", {failed} FAILED ← fix required")
    sys.exit(1)
else:
    print(" — all good ✓")
    sys.exit(0)
