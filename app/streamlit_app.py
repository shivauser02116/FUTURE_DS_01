"""
FUTURE_DS_01 — Superstore Sales Analytics  (Interactive Streamlit App)
Mirrors the 3-page static dashboard with live sidebar filters.

Run:  streamlit run app/streamlit_app.py
"""

from pathlib import Path
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ── Colour constants ───────────────────────────────────────────────────────────
NAVY  = "#1B3A6B"
TEAL  = "#2AA198"
RED   = "#D94F3D"
GREEN = "#2CA02C"

REGION_PALETTE = {
    "Central": "#F4A261",
    "East":    "#2AA198",
    "South":   "#E9C46A",
    "West":    "#1B3A6B",
}

# ── Helpers ────────────────────────────────────────────────────────────────────

def fmt_currency(value: float) -> str:
    """Format a dollar value compactly: $2.30M or $286K or $1.23K."""
    abs_v = abs(value)
    sign  = "-" if value < 0 else ""
    if abs_v >= 1_000_000:
        return f"{sign}${abs_v/1_000_000:.2f}M"
    if abs_v >= 1_000:
        return f"{sign}${abs_v/1_000:.0f}K"
    return f"{sign}${abs_v:.0f}"


def fmt_pct(value: float) -> str:
    """Format as percentage with one decimal place."""
    return f"{value:.1f}%"


def disc_band(d: float) -> str:
    """Map a discount fraction to its named band."""
    if d == 0:
        return "0%"
    if d <= 0.20:
        return "1-20%"
    if d <= 0.50:
        return "21-50%"
    return "51-80%"


# ── Data loading ───────────────────────────────────────────────────────────────

@st.cache_data
def load_data() -> pd.DataFrame:
    """Load cleaned Superstore CSV; path is relative to this file."""
    csv_path = Path(__file__).parent.parent / "data" / "superstore_clean.csv"
    df = pd.read_csv(
        csv_path,
        dtype={"postal_code": str},
        parse_dates=["order_date", "ship_date"],
    )
    # Ensure helper columns exist (they were added during cleaning)
    if "order_year" not in df.columns:
        df["order_year"] = df["order_date"].dt.year
    if "order_month" not in df.columns:
        df["order_month"] = df["order_date"].dt.month
    # Discount bands
    df["disc_band"] = df["discount"].apply(disc_band)
    return df


# ── Page config ────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Superstore Analytics",
    page_icon="📊",
    layout="wide",
)

# ── Load data ──────────────────────────────────────────────────────────────────

df_all = load_data()

# ── Sidebar filters ────────────────────────────────────────────────────────────

st.sidebar.title("🔍 Filters")

all_years      = sorted(df_all["order_year"].unique().tolist())
all_regions    = sorted(df_all["region"].unique().tolist())
all_categories = sorted(df_all["category"].unique().tolist())

sel_years = st.sidebar.multiselect(
    "Year", all_years, default=all_years
)
sel_regions = st.sidebar.multiselect(
    "Region", all_regions, default=all_regions
)
sel_cats = st.sidebar.multiselect(
    "Category", all_categories, default=all_categories
)

# Apply filters
mask = (
    df_all["order_year"].isin(sel_years) &
    df_all["region"].isin(sel_regions) &
    df_all["category"].isin(sel_cats)
)
df = df_all[mask].copy()

if df.empty:
    st.warning("No data matches the current filters. Please broaden your selection.")
    st.stop()

# ── Tabs ───────────────────────────────────────────────────────────────────────

tab1, tab2, tab3, tab4 = st.tabs([
    "📈 Overview",
    "📦 Products & Categories",
    "🗺️ Regions & Discounts",
    "📋 Summary & Recommendations",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════

with tab1:

    # ── KPIs ──────────────────────────────────────────────────────────────────
    total_sales   = df["sales"].sum()
    total_profit  = df["profit"].sum()
    margin        = total_profit / total_sales * 100 if total_sales else 0
    n_orders      = df["order_id"].nunique()
    avg_ov        = total_sales / n_orders if n_orders else 0
    loss_pct      = (df["profit"] < 0).mean() * 100

    # Insight: each number is explicitly scoped to avoid ambiguity
    yr_sales     = df.groupby("order_year")["sales"].sum()
    best_yr      = yr_sales.idxmax()           # year with highest sales
    best_yr_sales = yr_sales[best_yr]          # that year's sales value
    headline1 = (
        f"**{best_yr}** had the highest sales ({fmt_currency(best_yr_sales)}); "
        f"overall margin in this view is **{fmt_pct(margin)}**."
    )
    st.markdown(f"### 💡 {headline1}")

    # KPI row
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Total Sales",         fmt_currency(total_sales))
    k2.metric("Total Profit",        fmt_currency(total_profit))
    k3.metric("Profit Margin",       fmt_pct(margin))
    k4.metric("Orders",              f"{n_orders:,}")
    k5.metric("Avg Order Value",     fmt_currency(avg_ov))
    k6.metric("Loss-making Lines",   fmt_pct(loss_pct))

    st.divider()

    # ── Sales & Profit by Year ─────────────────────────────────────────────────
    by_year = (
        df.groupby("order_year")
          .agg(sales=("sales", "sum"), profit=("profit", "sum"))
          .reset_index()
    )
    by_year["margin_pct"] = by_year["profit"] / by_year["sales"] * 100

    col_a, col_b = st.columns(2)

    with col_a:
        fig_yr = go.Figure()
        fig_yr.add_bar(
            x=by_year["order_year"].astype(str),
            y=by_year["sales"],
            name="Sales",
            marker_color=NAVY,
        )
        fig_yr.add_bar(
            x=by_year["order_year"].astype(str),
            y=by_year["profit"],
            name="Profit",
            marker_color=TEAL,
        )
        fig_yr.update_layout(
            title="Sales & Profit by Year",
            barmode="group",
            xaxis_title="Year",
            yaxis_title="Amount ($)",
            legend=dict(orientation="h", y=1.1),
        )
        st.plotly_chart(fig_yr, width="stretch")

    with col_b:
        # Monthly sales & profit (all years aggregated)
        by_month = (
            df.groupby("order_month")
              .agg(sales=("sales", "sum"), profit=("profit", "sum"))
              .reset_index()
        )
        MONTH_LABELS = {
            1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
            7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"
        }
        by_month["month_name"] = by_month["order_month"].map(MONTH_LABELS)

        fig_mo = go.Figure()
        fig_mo.add_scatter(
            x=by_month["month_name"], y=by_month["sales"],
            mode="lines+markers", name="Sales", line=dict(color=NAVY),
        )
        fig_mo.add_scatter(
            x=by_month["month_name"], y=by_month["profit"],
            mode="lines+markers", name="Profit", line=dict(color=TEAL),
        )
        fig_mo.update_layout(
            title="Monthly Sales & Profit (All Selected Years)",
            xaxis_title="Month", yaxis_title="Amount ($)",
            legend=dict(orientation="h", y=1.1),
        )
        st.plotly_chart(fig_mo, width="stretch")

    # ── Seasonality: Sales by Month, one line per Year ─────────────────────────
    by_yr_mo = (
        df.groupby(["order_year", "order_month"])["sales"]
          .sum()
          .reset_index()
    )
    by_yr_mo["month_name"] = by_yr_mo["order_month"].map(MONTH_LABELS)

    fig_seas = px.line(
        by_yr_mo,
        x="month_name", y="sales",
        color="order_year",
        color_discrete_sequence=px.colors.qualitative.Set1,
        markers=True,
        title="Seasonality — Sales by Month per Year",
        labels={"order_year": "Year", "sales": "Sales ($)", "month_name": "Month"},
    )
    fig_seas.update_layout(legend_title="Year")
    # Sort x-axis by calendar month order
    fig_seas.update_xaxes(
        categoryorder="array",
        categoryarray=[MONTH_LABELS[m] for m in range(1, 13)],
    )
    st.plotly_chart(fig_seas, width="stretch")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — PRODUCTS & CATEGORIES
# ══════════════════════════════════════════════════════════════════════════════

with tab2:

    # ── Insight headline ───────────────────────────────────────────────────────
    # Category with best and worst profit
    cat_profit = df.groupby("category")["profit"].sum()
    best_cat   = cat_profit.idxmax()
    worst_cat  = cat_profit.idxmin()

    headline2 = (
        f"**{best_cat}** is the most profitable category "
        f"({fmt_currency(cat_profit[best_cat])}); "
        f"**{worst_cat}** is the weakest "
        f"({fmt_currency(cat_profit[worst_cat])})."
    )
    st.markdown(f"### 💡 {headline2}")

    col_c, col_d = st.columns(2)

    # ── Profit by Sub-category ─────────────────────────────────────────────────
    with col_c:
        subcat = (
            df.groupby("sub_category")["profit"]
              .sum()
              .sort_values()
              .reset_index()
        )
        subcat["colour"] = subcat["profit"].apply(
            lambda p: RED if p < 0 else GREEN
        )

        fig_sub = px.bar(
            subcat,
            x="profit", y="sub_category",
            orientation="h",
            color="colour",
            color_discrete_map={RED: RED, GREEN: GREEN},
            title="Profit by Sub-category",
            labels={"profit": "Profit ($)", "sub_category": "Sub-category"},
        )
        fig_sub.update_layout(showlegend=False)
        fig_sub.add_vline(x=0, line_dash="dash", line_color="gray")
        st.plotly_chart(fig_sub, width="stretch")

    # ── Sales share vs Profit share by Category ────────────────────────────────
    with col_d:
        cat_agg = (
            df.groupby("category")
              .agg(sales=("sales","sum"), profit=("profit","sum"))
        )
        cat_agg["sales_share"]  = cat_agg["sales"]  / cat_agg["sales"].sum()  * 100
        cat_agg["profit_share"] = cat_agg["profit"] / cat_agg["profit"].sum() * 100
        cat_agg = cat_agg.reset_index()

        fig_share = go.Figure()
        fig_share.add_bar(
            name="Sales share %",
            x=cat_agg["category"],
            y=cat_agg["sales_share"],
            marker_color=NAVY,
        )
        fig_share.add_bar(
            name="Profit share %",
            x=cat_agg["category"],
            y=cat_agg["profit_share"],
            marker_color=TEAL,
        )
        fig_share.update_layout(
            title="Sales vs Profit Share by Category",
            barmode="group",
            yaxis_title="Share (%)",
            legend=dict(orientation="h", y=1.1),
        )
        st.plotly_chart(fig_share, width="stretch")

    # ── Product scatter: Sales vs Profit ───────────────────────────────────────
    prod = (
        df.groupby(["product_name", "category"])
          .agg(sales=("sales","sum"), profit=("profit","sum"))
          .reset_index()
    )

    fig_scat = px.scatter(
        prod,
        x="sales", y="profit",
        color="category",
        hover_name="product_name",
        title="Product Sales vs Profit (coloured by Category)",
        labels={"sales": "Sales ($)", "profit": "Profit ($)"},
        opacity=0.65,
        color_discrete_sequence=[NAVY, TEAL, "#F4A261"],
    )
    fig_scat.add_hline(y=0, line_dash="dash", line_color="gray")
    st.plotly_chart(fig_scat, width="stretch")

    # ── 10 Least Profitable Products ──────────────────────────────────────────
    # Group by product_name (not product_id) per requirement
    worst_prod = (
        df.groupby("product_name")["profit"]
          .sum()
          .nsmallest(10)
          .reset_index()
          .sort_values("profit")
    )

    fig_wp = px.bar(
        worst_prod,
        x="profit", y="product_name",
        orientation="h",
        title="10 Least Profitable Products",
        labels={"profit": "Profit ($)", "product_name": "Product"},
        color_discrete_sequence=[RED],
    )
    fig_wp.update_layout(yaxis=dict(autorange="reversed"))
    fig_wp.add_vline(x=0, line_dash="dash", line_color="gray")
    st.plotly_chart(fig_wp, width="stretch")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — REGIONS & DISCOUNTS
# ══════════════════════════════════════════════════════════════════════════════

with tab3:

    # ── Insight headline ───────────────────────────────────────────────────────
    reg_agg = (
        df.groupby("region")
          .agg(sales=("sales","sum"), profit=("profit","sum"))
    )
    reg_agg["margin"] = reg_agg["profit"] / reg_agg["sales"] * 100
    best_reg  = reg_agg["margin"].idxmax()
    worst_reg = reg_agg["margin"].idxmin()

    headline3 = (
        f"**{best_reg}** leads with a {fmt_pct(reg_agg.loc[best_reg,'margin'])} margin; "
        f"**{worst_reg}** lags at {fmt_pct(reg_agg.loc[worst_reg,'margin'])}."
    )
    st.markdown(f"### 💡 {headline3}")

    col_e, col_f = st.columns(2)

    # ── Profit by Discount Band ────────────────────────────────────────────────
    with col_e:
        BAND_ORDER = ["0%", "1-20%", "21-50%", "51-80%"]

        band_agg = (
            df.groupby("disc_band")
              .agg(
                  profit=("profit", "sum"),
                  sales=("sales",  "sum"),
              )
              .reindex(BAND_ORDER)  # enforce display order
              .reset_index()
        )
        band_agg["margin_pct"] = (
            band_agg["profit"] / band_agg["sales"] * 100
        ).round(1)
        band_agg["colour"] = band_agg["profit"].apply(
            lambda p: RED if p < 0 else GREEN
        )
        band_agg["label"] = band_agg.apply(
            lambda r: f"{fmt_currency(r['profit'])}<br>margin {r['margin_pct']:.1f}%",
            axis=1,
        )

        fig_band = px.bar(
            band_agg,
            x="disc_band", y="profit",
            color="colour",
            color_discrete_map={RED: RED, GREEN: GREEN},
            text="label",
            title="Profit by Discount Band",
            labels={"disc_band": "Discount Band", "profit": "Profit ($)"},
            category_orders={"disc_band": BAND_ORDER},
        )
        fig_band.update_traces(textposition="outside")
        fig_band.update_layout(showlegend=False)
        fig_band.add_hline(y=0, line_dash="dash", line_color="gray")
        st.plotly_chart(fig_band, width="stretch")

    # ── State scatter: Avg Discount vs Profit Margin ──────────────────────────
    with col_f:
        state_agg = (
            df.groupby("state")
              .agg(
                  avg_disc=("discount", "mean"),
                  sales=("sales", "sum"),
                  profit=("profit", "sum"),
              )
              .reset_index()
        )
        state_agg["margin_pct"] = state_agg["profit"] / state_agg["sales"] * 100

        fig_st = px.scatter(
            state_agg,
            x="avg_disc", y="margin_pct",
            hover_name="state",
            title="State: Avg Discount vs Profit Margin",
            labels={
                "avg_disc":   "Avg Discount (fraction)",
                "margin_pct": "Profit Margin (%)",
            },
            color_discrete_sequence=[NAVY],
        )
        # Add numpy-computed trend line (no statsmodels needed)
        if len(state_agg) >= 2:
            x_vals = state_agg["avg_disc"].values
            y_vals = state_agg["margin_pct"].values
            slope, intercept = np.polyfit(x_vals, y_vals, 1)
            x_line = np.array([x_vals.min(), x_vals.max()])
            y_line = slope * x_line + intercept
            fig_st.add_trace(go.Scatter(
                x=x_line, y=y_line,
                mode="lines",
                line=dict(color=RED, dash="dash"),
                name="Trend",
                showlegend=False,
            ))
        fig_st.update_layout(showlegend=False)
        st.plotly_chart(fig_st, width="stretch")

    # ── 10 States with Largest Losses ─────────────────────────────────────────
    state_loss = (
        df.groupby("state")["profit"]
          .sum()
          .nsmallest(10)
          .reset_index()
          .sort_values("profit")
    )

    fig_sl = px.bar(
        state_loss,
        x="profit", y="state",
        orientation="h",
        title="10 States with Largest Losses",
        labels={"profit": "Profit ($)", "state": "State"},
        color_discrete_sequence=[RED],
    )
    fig_sl.update_layout(yaxis=dict(autorange="reversed"))
    fig_sl.add_vline(x=0, line_dash="dash", line_color="gray")
    st.plotly_chart(fig_sl, width="stretch")

    # ── Profit Margin by Region ────────────────────────────────────────────────
    reg_plot = reg_agg.reset_index()
    reg_plot["colour"] = reg_plot["region"].map(REGION_PALETTE)
    reg_plot["label"]  = reg_plot["margin"].apply(fmt_pct)

    fig_reg = px.bar(
        reg_plot.sort_values("margin"),
        x="margin", y="region",
        orientation="h",
        color="region",
        color_discrete_map=REGION_PALETTE,
        text="label",
        title="Profit Margin by Region",
        labels={"margin": "Profit Margin (%)", "region": "Region"},
    )
    fig_reg.update_traces(textposition="outside")
    fig_reg.update_layout(showlegend=False)
    fig_reg.add_vline(x=0, line_dash="dash", line_color="gray")
    st.plotly_chart(fig_reg, width="stretch")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — SUMMARY & RECOMMENDATIONS
# ══════════════════════════════════════════════════════════════════════════════

with tab4:
    st.caption("Based on all data, 2014-2017, regardless of the filters.")

    # ── Calculations on full dataset (df_all) ───────────────────────────────────
    # a. Discounts above 20%: profit lost and share of order lines
    d_over20 = df_all[df_all["discount"] > 0.20]
    loss_over20 = d_over20["profit"].sum()
    share_over20 = len(d_over20) / len(df_all) * 100

    # b. Profit margin: no discount vs 51-80% discount
    d_zero = df_all[df_all["discount"] == 0]
    margin_zero = d_zero["profit"].sum() / d_zero["sales"].sum() * 100
    d_deep = df_all[df_all["discount"] > 0.50]
    margin_deep = d_deep["profit"].sum() / d_deep["sales"].sum() * 100

    # c. Four worst states by profit and discount comparison
    worst_4_series = df_all.groupby("state")["profit"].sum().nsmallest(4)
    worst_4_states = list(worst_4_series.index)
    worst_4_loss = worst_4_series.sum()
    worst_4_disc = df_all[df_all["state"].isin(worst_4_states)]["discount"].mean() * 100
    overall_disc = df_all["discount"].mean() * 100

    # d. Furniture share of sales vs profit and Tables total profit
    cat_all = df_all.groupby("category").agg(sales=("sales", "sum"), profit=("profit", "sum"))
    furn_name = "Furniture"
    furn_sales_pct = cat_all.loc[furn_name, "sales"] / cat_all["sales"].sum() * 100
    furn_profit_pct = cat_all.loc[furn_name, "profit"] / cat_all["profit"].sum() * 100
    tables_name = "Tables"
    tables_loss = df_all[df_all["sub_category"] == tables_name]["profit"].sum()

    # e. Sales growth in 2017 and margin 2016 vs 2017
    yr_all = df_all.groupby("order_year").agg(sales=("sales", "sum"), profit=("profit", "sum"))
    yr_all["margin"] = yr_all["profit"] / yr_all["sales"] * 100
    latest_yr = yr_all.index.max()
    prev_yr = latest_yr - 1
    sales_growth = (yr_all.loc[latest_yr, "sales"] - yr_all.loc[prev_yr, "sales"]) / yr_all.loc[prev_yr, "sales"] * 100
    margin_prev = yr_all.loc[prev_yr, "margin"]
    margin_curr = yr_all.loc[latest_yr, "margin"]

    # f. Combined share of annual sales from top 3 seasonal months (Sep, Nov, Dec)
    MONTH_MAP = {
        1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
        7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"
    }
    mo_sales = df_all.groupby("order_month")["sales"].sum()
    top_3_mo_nums = sorted(mo_sales.nlargest(3).index.tolist())
    top_3_mo_names = ", ".join(MONTH_MAP[m] for m in top_3_mo_nums)
    top_3_mo_sales = df_all[df_all["order_month"].isin(top_3_mo_nums)]["sales"].sum()
    top_3_share = top_3_mo_sales / df_all["sales"].sum() * 100

    # ── 1. Key Findings ────────────────────────────────────────────────────────
    st.subheader("Key Findings")
    st.markdown(
        f"1. **Discounts above 20% are the biggest profit leak:** Order lines discounted >20% account for "
        f"**{share_over20:.1f}%** of all lines but lose **${abs(loss_over20)/1000:.0f}K** in total ({fmt_currency(loss_over20)}).\n"
        f"2. **Margin collapse under deep discounts:** Transactions with no discount earn a **{fmt_pct(margin_zero)}** "
        f"margin, whereas 51–80% discounts drop to **{fmt_pct(margin_deep)}**.\n"
        f"3. **Concentrated state losses:** The four worst states ({', '.join(worst_4_states)}) "
        f"lost a combined **${abs(worst_4_loss)/1000:.0f}K** ({fmt_currency(worst_4_loss)}), with an average discount of "
        f"**{worst_4_disc:.1f}%** vs. the national average of **{overall_disc:.1f}%**.\n"
        f"4. **Furniture volume without return:** {furn_name} drives **{furn_sales_pct:.0f}%** of sales but only "
        f"**{furn_profit_pct:.0f}%** of profit, led by losses in {tables_name} ({fmt_currency(tables_loss)}).\n"
        f"5. **Growth vs. margin tradeoff:** {latest_yr} sales grew by **+{sales_growth:.1f}%**, but profit margin "
        f"fell from **{fmt_pct(margin_prev)}** ({prev_yr}) to **{fmt_pct(margin_curr)}** ({latest_yr}).\n"
        f"6. **Seasonal revenue concentration:** The top three months ({top_3_mo_names}) generate "
        f"**{top_3_share:.0f}%** of annual sales."
    )

    st.divider()

    # ── 2. Recommendations ─────────────────────────────────────────────────────
    st.subheader("Recommendations")
    st.markdown(
        "1. **Cap discounts near 20%** with mandatory manager approval required above that threshold.\n"
        "2. **Review discount rules in the four loss-making states first** (Texas, Ohio, Pennsylvania, Illinois).\n"
        "3. **Reprice Tables and Bookcases or cut their discounts** before expanding catalog volume.\n"
        "4. **Promote high-margin lines** (Copiers, Phones, Accessories, Paper) to protect margin mix.\n"
        "5. **Plan stock and campaigns around Sep–Dec** and track profit margins monthly."
    )

    st.divider()

    # ── 3. About this analysis ─────────────────────────────────────────────────
    st.subheader("About this analysis")
    st.markdown(
        "- **Dataset:** Sample Superstore (Kaggle), 9,994 order lines, 2014–2017, United States.\n"
        "- **Data Cleaning:** 1 duplicate removed, 0 missing values, verified postal codes and dates.\n"
        "- **Tools:** Python, pandas, Plotly, Streamlit.\n"
        "- **Limitations:** Observational data; discounts and losses are strongly linked but this does not prove cause; no cost data.\n"
        "- **Project:** Future Interns - Data Science & Analytics, Task 1."
    )

