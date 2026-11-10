"""
FUTURE_DS_01 - Step 2: Build the 3-page sales performance dashboard.

Run from anywhere:   python scripts/02_build_dashboard.py
Input : data/superstore_clean.csv   (created by scripts/01_clean_superstore.py)
Output: dashboard/FUTURE_DS_01_dashboard.pdf  and  images/page_1..3 PNGs
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages

BASE = Path(__file__).resolve().parent.parent
df = pd.read_csv(BASE / "data" / "superstore_clean.csv", dtype={"postal_code": str},
                 parse_dates=["order_date", "ship_date"])

NAVY, TEAL, RED, GREY, AMBER, LIGHT = "#1F3A5F", "#2A9D8F", "#D1495B", "#8D99AE", "#EDAE49", "#F2F5FA"
CAT_COL = {"Furniture": AMBER, "Office Supplies": TEAL, "Technology": NAVY}
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.titleweight": "bold", "axes.titlesize": 10.5, "axes.titlelocation": "left"})


def money(x, d=0):
    s = "-" if x < 0 else ""
    x = abs(x)
    return f"{s}${x/1e6:,.2f}M" if x >= 1e6 else f"{s}${x/1e3:,.{d}f}K"


def short(s, n=30):
    return s if len(s) <= n else s[: n - 1] + "…"


def sign_colors(vals):
    return [RED if v < 0 else TEAL for v in vals]


def k_axis(axis):
    axis.set_major_formatter(lambda v, _: f"-${abs(v)/1e3:.0f}K" if v < 0 else f"${v/1e3:.0f}K")


# ------------------------------------------------------------ KPIs & aggregates
S, P = df.sales.sum(), df.profit.sum()
orders = df.order_id.nunique()
kpis = [("Total Sales", money(S)), ("Total Profit", money(P)), ("Profit Margin", f"{P/S:.1%}"),
        ("Orders", f"{orders:,}"), ("Avg Order Value", f"${S/orders:,.0f}"),
        ("Loss-making Lines", f"{(df.profit < 0).mean():.1%}")]

yr = df.groupby("order_year").agg(sales=("sales", "sum"), profit=("profit", "sum"))
yr["margin"] = yr.profit / yr.sales
yr["growth"] = yr.sales.pct_change()
mon = df.groupby("year_month").agg(sales=("sales", "sum"), profit=("profit", "sum"))
mon.index = pd.to_datetime(mon.index)
season = df.pivot_table(index="order_month", columns="order_year", values="sales", aggfunc="sum")
msh = df.groupby("order_month").sales.sum() / S
peak3 = msh[[9, 11, 12]].sum()

sub = df.groupby("sub_category").profit.sum().sort_values()
cat = df.groupby("category").agg(sales=("sales", "sum"), profit=("profit", "sum"))
cat["s_share"], cat["p_share"] = cat.sales / S, cat.profit / P
prod = df.groupby("product_name").agg(sales=("sales", "sum"), profit=("profit", "sum"),
                                      category=("category", "first"))
bot_prod = prod.profit.sort_values().head(10)

bands = pd.cut(df.discount, [-0.01, 0, 0.2, 0.5, 0.81], labels=["0%", "1-20%", "21-50%", "51-80%"])
bd = df.groupby(bands, observed=True).agg(sales=("sales", "sum"), profit=("profit", "sum"))
bd["margin"] = bd.profit / bd.sales
over20 = df[df.discount > 0.2]

st = df.groupby("state").agg(sales=("sales", "sum"), profit=("profit", "sum"), disc=("discount", "mean"))
st["margin"] = st.profit / st.sales
bot_st = st.profit.sort_values().head(10)
bad4 = ["Texas", "Ohio", "Pennsylvania", "Illinois"]
reg = df.groupby("region").agg(sales=("sales", "sum"), profit=("profit", "sum"))
reg["margin"] = reg.profit / reg.sales
fur = cat.loc["Furniture"]
tables = df[df.sub_category == "Tables"].profit.sum()


# ------------------------------------------------------------ page helpers
def blank(ax, color=None):
    if color:
        ax.set_facecolor(color)
    ax.set_xticks([])
    ax.set_yticks([])
    for s_ in ax.spines.values():
        s_.set_visible(False)


def new_page(title, subtitle):
    fig = plt.figure(figsize=(16, 9), facecolor="white")
    h = fig.add_axes([0, 0.9, 1, 0.1])
    blank(h, NAVY)
    h.text(0.03, 0.62, title, color="white", fontsize=19, fontweight="bold", va="center", transform=h.transAxes)
    h.text(0.03, 0.2, subtitle, color="#C9D6EA", fontsize=10.5, va="center", transform=h.transAxes)
    fig.text(0.03, 0.012, "Source: Sample Superstore dataset (Kaggle), orders Jan 2014 - Dec 2017  |  "
             "FUTURE_DS_01  |  Tools: Python (pandas, matplotlib)", fontsize=7.5, color=GREY)
    return fig


def note_box(fig, rect, heading, lines):
    ax = fig.add_axes(rect)
    blank(ax, LIGHT)
    ax.text(0.04, 0.92, heading, fontsize=11, fontweight="bold", color=NAVY, va="top", transform=ax.transAxes)
    y = 0.78
    for ln in lines:
        ax.text(0.04, y, "•  " + ln, fontsize=9.3, color="#222", va="top", transform=ax.transAxes)
        y -= 0.19


# ------------------------------------------------------------ PAGE 1 - overview
f1 = new_page("Sales Performance Overview",
              f"Sales grew strongly in 2016-17, but profit grew more slowly - margin slipped from "
              f"{yr.margin[2016]:.1%} to {yr.margin[2017]:.1%} in 2017")
for i, (lab, val) in enumerate(kpis):
    a = f1.add_axes([0.03 + i * 0.1625, 0.765, 0.15, 0.105])
    blank(a, LIGHT)
    a.text(0.5, 0.64, val, ha="center", va="center", fontsize=19, fontweight="bold",
           color=RED if "Loss" in lab else NAVY, transform=a.transAxes)
    a.text(0.5, 0.22, lab, ha="center", va="center", fontsize=9.5, color=GREY, transform=a.transAxes)

a = f1.add_axes([0.05, 0.40, 0.30, 0.31])
x = np.arange(len(yr))
w = 0.38
a.bar(x - w / 2, yr.sales, w, color=NAVY, label="Sales")
a.bar(x + w / 2, yr.profit, w, color=TEAL, label="Profit")
for i, (sv, pv, g) in enumerate(zip(yr.sales, yr.profit, yr.growth)):
    a.text(i - w / 2, sv, money(sv), ha="center", va="bottom", fontsize=7.5)
    a.text(i + w / 2, pv, money(pv), ha="center", va="bottom", fontsize=7.5)
    if not np.isnan(g):
        a.text(i, -yr.sales.max() * 0.13, f"{g:+.1%} YoY", ha="center", fontsize=8, color=TEAL if g > 0 else RED)
a.set_xticks(x)
a.set_xticklabels(yr.index)
a.set_yticks([])
a.spines["left"].set_visible(False)
a.set_ylim(-yr.sales.max() * 0.18, yr.sales.max() * 1.15)
a.set_title("Sales & profit by year")
a.legend(frameon=False, loc="upper left", fontsize=8)

a = f1.add_axes([0.42, 0.40, 0.53, 0.31])
a.plot(mon.index, mon.sales, color=NAVY, lw=1.8, label="Sales")
a.plot(mon.index, mon.profit, color=TEAL, lw=1.8, label="Profit")
a.fill_between(mon.index, 0, mon.profit, where=mon.profit < 0, color=RED, alpha=0.4)
a.set_title("Monthly sales and profit")
k_axis(a.yaxis)
a.legend(frameon=False, fontsize=8)
a.grid(axis="y", alpha=0.25)

a = f1.add_axes([0.05, 0.07, 0.40, 0.25])
mnames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
for y, col in zip(season.columns, [GREY, AMBER, TEAL, NAVY]):
    a.plot(range(12), season[y], marker="o", ms=3, lw=1.6, color=col, label=str(y))
a.set_xticks(range(12))
a.set_xticklabels(mnames)
k_axis(a.yaxis)
a.set_title("Seasonality: sales by month")
a.legend(frameon=False, ncol=4, fontsize=8)
a.grid(axis="y", alpha=0.25)

note_box(f1, [0.52, 0.07, 0.43, 0.25], "What this means", [
    f"Sales reached {money(yr.sales[2017])} in 2017 ({yr.growth[2017]:+.1%}), after {yr.growth[2016]:+.1%} in 2016.",
    f"Profit grew slower than sales in 2017, so margin fell to {yr.margin[2017]:.1%}.",
    f"Sep, Nov and Dec generate {peak3:.0%} of annual sales; Jan-Feb are the weakest months.",
    "Action: plan stock and promotions around Sep-Dec, and protect margin as volume grows.",
])

# ------------------------------------------------------------ PAGE 2 - products
f2 = new_page("Products & Categories",
              f"Furniture is {fur.s_share:.0%} of sales but only {fur.p_share:.0%} of profit; "
              f"Tables alone lose {money(-tables, 1)}")
a = f2.add_axes([0.10, 0.50, 0.37, 0.34])
a.barh(sub.index, sub.values, color=sign_colors(sub.values))
for i, v in enumerate(sub.values):
    a.text(v + (600 if v >= 0 else -600), i, money(v, 1), va="center", ha="left" if v >= 0 else "right", fontsize=7.5)
a.axvline(0, color="#333", lw=0.8)
a.set_title("Profit by sub-category")
k_axis(a.xaxis)
a.set_xlim(sub.min() * 1.7, sub.max() * 1.2)

a = f2.add_axes([0.56, 0.50, 0.40, 0.34])
x = np.arange(len(cat))
w = 0.38
a.bar(x - w / 2, cat.s_share, w, color=GREY, label="Share of sales")
a.bar(x + w / 2, cat.p_share, w, color=TEAL, label="Share of profit")
for i, (s_, p_) in enumerate(zip(cat.s_share, cat.p_share)):
    a.text(i - w / 2, s_, f"{s_:.0%}", ha="center", va="bottom")
    a.text(i + w / 2, p_, f"{p_:.0%}", ha="center", va="bottom")
a.set_xticks(x)
a.set_xticklabels(cat.index)
a.set_yticks([])
a.spines["left"].set_visible(False)
a.set_title("Share of sales vs share of profit, by category")
a.legend(frameon=False, fontsize=8)

a = f2.add_axes([0.06, 0.07, 0.38, 0.34])
for c, col in CAT_COL.items():
    d_ = prod[prod.category == c]
    a.scatter(d_.sales, d_.profit, s=11, alpha=0.55, color=col, label=c)
a.axhline(0, color="#333", lw=0.8)
lab = list(prod.sales.nlargest(3).index) + list(prod.profit.nsmallest(3).index)
for p_ in dict.fromkeys(lab):
    a.annotate(short(p_, 24), (prod.sales[p_], prod.profit[p_]), fontsize=7, xytext=(4, 4), textcoords="offset points")
a.set_title("Every product: sales vs profit")
a.legend(frameon=False, fontsize=8)
k_axis(a.xaxis)
k_axis(a.yaxis)

a = f2.add_axes([0.73, 0.07, 0.23, 0.34])
bp = bot_prod.sort_values(ascending=False)
a.barh([short(n, 32) for n in bp.index], bp.values, color=RED)
for i, v in enumerate(bp.values):
    a.text(v - 150, i, money(v, 1), va="center", ha="right", fontsize=7)
a.tick_params(axis="y", labelsize=7)
a.set_title("10 least profitable products")
a.set_xlim(bp.min() * 1.3, 0)
k_axis(a.xaxis)

# ------------------------------------------------------------ PAGE 3 - regions & discounts
f3 = new_page("Regions & Discounts",
              f"Discounts above 20% lose {money(-over20.profit.sum())} in total - "
              f"and the four worst states discount the most")
a = f3.add_axes([0.06, 0.50, 0.38, 0.34])
a.bar(bd.index.astype(str), bd.profit, color=sign_colors(bd.profit.values))
for i, (pv, mv) in enumerate(zip(bd.profit, bd.margin)):
    a.text(i, pv + (6000 if pv >= 0 else -6000), f"{money(pv, 1)}\n({mv:.0%} margin)", ha="center",
           va="bottom" if pv >= 0 else "top", fontsize=8)
a.axhline(0, color="#333", lw=0.8)
a.set_yticks([])
a.spines["left"].set_visible(False)
a.set_ylim(bd.profit.min() * 2.3, bd.profit.max() * 1.25)
a.set_xlabel("Discount band")
a.set_title("Profit by discount band")

a = f3.add_axes([0.56, 0.50, 0.40, 0.34])
a.scatter(st.disc * 100, st.margin * 100, s=st.sales / 1500, color=GREY, alpha=0.6)
a.scatter(st.loc[bad4].disc * 100, st.loc[bad4].margin * 100, s=st.loc[bad4].sales / 1500, color=RED, alpha=0.85)
m, b = np.polyfit(st.disc * 100, st.margin * 100, 1)
xs = np.array([0, st.disc.max() * 100])
a.plot(xs, m * xs + b, color=NAVY, lw=1.2, ls="--")
offsets = {"Texas": (-12, -16), "Illinois": (-6, -14), "Pennsylvania": (5, 5), "Ohio": (5, -11)}
for s_ in bad4 + ["California", "New York", "Michigan"]:
    a.annotate(s_, (st.disc[s_] * 100, st.margin[s_] * 100), fontsize=7.5,
               xytext=offsets.get(s_, (5, 4)), textcoords="offset points")
r = np.corrcoef(st.disc, st.margin)[0, 1]
a.axhline(0, color="#333", lw=0.6)
a.set_xlabel("Average discount (%)")
a.set_ylabel("Profit margin (%)")
a.set_title(f"States: higher discounts, lower margin (r = {r:.2f})")

a = f3.add_axes([0.12, 0.07, 0.32, 0.34])
bs = bot_st.sort_values(ascending=False)
a.barh(bs.index, bs.values, color=RED)
for i, v in enumerate(bs.values):
    a.text(v - 200, i, money(v, 1), va="center", ha="right", fontsize=7.5)
a.set_xlim(bs.min() * 1.3, 0)
a.set_title("10 states with the largest losses")
k_axis(a.xaxis)

a = f3.add_axes([0.60, 0.07, 0.36, 0.34])
rg = reg.sort_values("margin", ascending=False)
a.bar(rg.index, rg.margin * 100, color=NAVY)
for i, (mv, pv) in enumerate(zip(rg.margin, rg.profit)):
    a.text(i, mv * 100 + 0.3, f"{mv:.1%}\n({money(pv)})", ha="center", va="bottom", fontsize=8)
a.axhline(P / S * 100, color=AMBER, ls="--", lw=1.2)
a.text(3.45, P / S * 100 + 0.3, "company avg", color=AMBER, ha="right", fontsize=8)
a.set_yticks([])
a.spines["left"].set_visible(False)
a.set_ylim(0, rg.margin.max() * 100 * 1.35)
a.set_title("Profit margin by region (profit in brackets)")

# ------------------------------------------------------------ SAVE
(BASE / "images").mkdir(exist_ok=True)
(BASE / "dashboard").mkdir(exist_ok=True)
names = ["overview", "products", "regions_discounts"]
with PdfPages(BASE / "dashboard" / "FUTURE_DS_01_dashboard.pdf") as pdf:
    for i, f in enumerate([f1, f2, f3], 1):
        f.savefig(BASE / "images" / f"page_{i}_{names[i - 1]}.png", dpi=130)
        pdf.savefig(f)

print("Dashboard saved.")
print(f"Sales {S:,.0f} | Profit {P:,.0f} | Margin {P/S:.2%} | Orders {orders} | AOV {S/orders:,.2f} | "
      f"Loss lines {(df.profit < 0).mean():.2%}")
print(yr.round(3))
print(f"Peak Sep+Nov+Dec share {peak3:.1%} | over-20% discount loss {over20.profit.sum():,.0f}")
print(f"bad4 loss {st.loc[bad4].profit.sum():,.0f} | corr {r:.2f} | tables {tables:,.0f} | "
      f"furniture {fur.s_share:.1%}/{fur.p_share:.1%} | Central margin {reg.margin['Central']:.1%} West {reg.margin['West']:.1%}")
