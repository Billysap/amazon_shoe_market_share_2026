import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Amazon Shoes Market Explorer",
    page_icon="👟",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: #f4f4fb; }
[data-testid="stSidebar"] { background: #1e1b4b; }
[data-testid="stSidebar"] * { color: #e0e0f0 !important; }
[data-testid="stSidebar"] .stMultiSelect > div,
[data-testid="stSidebar"] .stSlider > div { color: #e0e0f0 !important; }
[data-testid="stSidebar"] hr { border-color: #3730a3; }

.hero {
    background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 50%, #db2777 100%);
    padding: 2rem 2.5rem;
    border-radius: 16px;
    color: white;
    margin-bottom: 1.5rem;
}
.hero h1 { margin: 0; font-size: 2rem; font-weight: 700; }
.hero p  { margin: 0.4rem 0 0; opacity: 0.88; font-size: 1rem; }

.kpi-card {
    background: white;
    border-radius: 12px;
    padding: 1.1rem 1.4rem;
    border-left: 5px solid;
    box-shadow: 0 2px 12px rgba(0,0,0,0.07);
    margin-bottom: 0.5rem;
}
.kpi-label { font-size: 0.78rem; color: #6b7280; font-weight: 600;
             text-transform: uppercase; letter-spacing: 0.05em; }
.kpi-value { font-size: 1.9rem; font-weight: 700; color: #1e1b4b; margin: 0.1rem 0 0; }
.kpi-delta { font-size: 0.78rem; color: #6b7280; margin-top: 0.1rem; }

.chart-card {
    background: white;
    border-radius: 12px;
    padding: 1rem 1.2rem 0.5rem;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
    margin-bottom: 1rem;
}
.chart-title {
    font-size: 0.95rem; font-weight: 600; color: #374151;
    margin-bottom: 0.6rem; padding-bottom: 0.4rem;
    border-bottom: 2px solid #f3f4f6;
}
.writeup-section { background: white; border-radius: 12px; padding: 1.5rem 2rem;
                   box-shadow: 0 2px 12px rgba(0,0,0,0.06); margin-top: 1rem; }
.writeup-section h3 { color: #4f46e5; margin-top: 1.2rem; }
.writeup-section h4 { color: #7c3aed; }
.ref-tag { background: #ede9fe; color: #5b21b6; padding: 2px 8px;
           border-radius: 4px; font-size: 0.82rem; margin-right: 4px; }
.est-badge { background: #fef3c7; color: #92400e; padding: 2px 8px;
             border-radius: 4px; font-size: 0.78rem; }
footer { visibility: hidden; }
#MainMenu { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Color constants ───────────────────────────────────────────────────────────
GENDER_COLORS  = {"Women": "#7c3aed", "Men": "#2563eb", "Unknown": "#9ca3af"}
BRAND_PALETTE  = px.colors.qualitative.Bold
SUBCAT_PALETTE = px.colors.qualitative.Vivid
KPI_BORDERS    = ["#4f46e5", "#0ea5e9", "#10b981", "#f59e0b"]

# ── Data loading & wrangling ──────────────────────────────────────────────────
@st.cache_data(show_spinner="Loading and processing data...")
def load_data(path: str) -> pd.DataFrame:
    if path.endswith(".xlsx") or path.endswith(".xls"):
        df = pd.read_excel(path, engine="openpyxl")
    else:
        try:
            df = pd.read_csv(path, low_memory=False)
        except Exception:
            df = pd.read_excel(path, engine="openpyxl")

    # ── Gender from title ────────────────────────────────────────────────────
    t = df["Title"].str.lower().fillna("")
    df["gender"] = "Unknown"
    df.loc[t.str.contains(r"women'?s|woman'?s|ladies|girl", regex=True), "gender"] = "Women"
    df.loc[t.str.contains(r"\bmen'?s\b|\bman'?s\b|boys", regex=True),  "gender"] = "Men"

    # ── Subcategory (last node of tree) ──────────────────────────────────────
    df["subcat"] = (
        df["Categories: Tree"].fillna("Shoes")
        .str.split("›").str[-1].str.strip()
    )

    # ── Price: buy box → new → list ──────────────────────────────────────────
    df["price"] = (
        df["Buy Box: Current"]
        .fillna(df["New: Current"])
        .fillna(df["List Price: Current"])
    )

    # ── Rating ────────────────────────────────────────────────────────────────
    df["rating"]       = pd.to_numeric(df["Reviews: Rating"], errors="coerce")
    df["review_count"] = pd.to_numeric(df["Reviews: Rating Count"], errors="coerce")

    # ── Sales rank ────────────────────────────────────────────────────────────
    df["rank"] = pd.to_numeric(df["Sales Rank: Current"], errors="coerce")

    # ── Power law calibration: log(sold) = log(a) + θ·log(rank) ─────────────
    cal = df[
        df["rank"].notna() & (df["rank"] > 0) &
        df["Monthly Sales Trends: Bought in past month"].notna() &
        (df["Monthly Sales Trends: Bought in past month"] > 0)
    ].copy()
    coef = np.polyfit(
        np.log(cal["rank"]),
        np.log(cal["Monthly Sales Trends: Bought in past month"]),
        1,
    )
    a_param, theta = float(np.exp(coef[1])), float(coef[0])

    df["est_monthly_sold"] = a_param * df["rank"] ** theta
    df["monthly_sold"] = df["Monthly Sales Trends: Bought in past month"].fillna(
        df["est_monthly_sold"]
    )
    df["is_estimated"] = df["Monthly Sales Trends: Bought in past month"].isna()

    # ── Market value ──────────────────────────────────────────────────────────
    df["market_value"] = df["price"] * df["monthly_sold"]

    # ── First image URL ───────────────────────────────────────────────────────
    df["image_url"] = df["Image"].fillna("").str.split(";").str[0]

    # ── Size as string for axis ───────────────────────────────────────────────
    df["size_str"] = df["Size"].apply(
        lambda x: str(int(x)) if pd.notna(x) and x == int(x) else str(x) if pd.notna(x) else "?"
    )

    # ── Store calibration params as attributes (not possible on df directly,
    #    so store in a metadata column placeholder) ───────────────────────────
    df.attrs["power_law_a"]     = round(a_param, 2)
    df.attrs["power_law_theta"] = round(theta, 4)
    df.attrs["cal_n"]           = len(cal)

    return df


DATA_PATH = "6600_amazon_soes.xlsx"
df_raw = load_data(DATA_PATH)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 👟 Shoes Explorer")
    st.markdown("---")

    brand_counts  = df_raw["Brand"].value_counts()
    top10_brands  = brand_counts.head(10).index.tolist()
    all_brands    = sorted(df_raw["Brand"].dropna().unique())
    sel_brands    = st.multiselect(
        "🏷️ Brand", all_brands, default=top10_brands[:8],
        help="Filter by brand. Default = top 8 by product count."
    )

    subcat_counts = df_raw["subcat"].value_counts()
    top6_subcats  = subcat_counts.head(6).index.tolist()
    all_subcats   = sorted(df_raw["subcat"].dropna().unique())
    sel_subcats   = st.multiselect(
        "👠 Subcategory", all_subcats, default=top6_subcats,
        help="Shoe type / subcategory."
    )

    all_sizes  = sorted(df_raw["Size"].dropna().unique())
    sel_sizes  = st.multiselect(
        "📏 Size (US)", all_sizes, default=all_sizes,
        help="Filter by US shoe size."
    )

    p_min = float(df_raw["price"].min(skipna=True) or 0)
    p_max = float(df_raw["price"].max(skipna=True) or 400)
    sel_price = st.slider(
        "💵 Price range ($)", p_min, p_max, (p_min, min(p_max, 200.0)), step=1.0
    )

    sel_rating = st.slider("⭐ Min rating", 1.0, 5.0, 3.5, step=0.5)

    top_n = st.slider("🏅 Top N products (bar chart)", 5, 20, 10, step=1)

    st.markdown("---")
    st.caption(
        f"📊 Dataset: {len(df_raw):,} products  \n"
        f"🔬 Power law: units ≈ {df_raw.attrs.get('power_law_a','?')} × rank^"
        f"({df_raw.attrs.get('power_law_theta','?')})  \n"
        f"📅 Keepa export · Amazon US · Apr 2026"
    )

# ── Apply filters ─────────────────────────────────────────────────────────────
df = df_raw.copy()
if sel_brands:
    df = df[df["Brand"].isin(sel_brands)]
if sel_subcats:
    df = df[df["subcat"].isin(sel_subcats)]
if sel_sizes:
    df = df[df["Size"].isin(sel_sizes)]
df = df[
    df["price"].between(sel_price[0], sel_price[1], inclusive="both") |
    df["price"].isna()
]
df = df[df["rating"].ge(sel_rating) | df["rating"].isna()]

# ── Hero header ───────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <h1>👟 Amazon Shoes Market Explorer</h1>
    <p>Explore market value, demand patterns, brand performance and size distribution
       across 10,000 Amazon shoe listings &mdash; powered by Keepa data &amp;
       power-law demand estimation (He &amp; Hollenbeck, 2020).</p>
</div>
""", unsafe_allow_html=True)

# ── KPI cards ─────────────────────────────────────────────────────────────────
total_mv  = df["market_value"].sum()
n_prod    = len(df)
avg_price = df["price"].mean()
avg_rat   = df["rating"].mean()
est_pct   = df["is_estimated"].mean() * 100

k1, k2, k3, k4 = st.columns(4)
kpi_data = [
    (k1, "💰 Est. Market Value",
     f"${total_mv/1e6:.1f}M",
     f"price × monthly sold · {100-est_pct:.0f}% observed",
     KPI_BORDERS[0]),
    (k2, "📦 Products Shown",
     f"{n_prod:,}",
     f"{n_prod/len(df_raw)*100:.0f}% of full dataset",
     KPI_BORDERS[1]),
    (k3, "💵 Avg Price",
     f"${avg_price:.2f}" if pd.notna(avg_price) else "—",
     f"range ${df['price'].min():.0f} – ${df['price'].max():.0f}",
     KPI_BORDERS[2]),
    (k4, "⭐ Avg Rating",
     f"{avg_rat:.2f}" if pd.notna(avg_rat) else "—",
     f"{df['review_count'].median():.0f} median reviews",
     KPI_BORDERS[3]),
]
for col, label, val, delta, color in kpi_data:
    with col:
        st.markdown(
            f'<div class="kpi-card" style="border-left-color:{color};">'
            f'<div class="kpi-label">{label}</div>'
            f'<div class="kpi-value">{val}</div>'
            f'<div class="kpi-delta">{delta}</div></div>',
            unsafe_allow_html=True,
        )

st.markdown("<br>", unsafe_allow_html=True)

# ── Row 1: Top N bar + Stacked size bar ───────────────────────────────────────
c1, c2 = st.columns([1.35, 0.65])

with c1:
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown(f'<div class="chart-title">🏆 Top {top_n} Products by Estimated Market Value</div>',
                unsafe_allow_html=True)

    top_df = (
        df[df["market_value"].notna()]
        .drop_duplicates("ASIN")
        .sort_values("market_value", ascending=False)
        .head(top_n)
    )
    top_df["short_title"] = top_df["Title"].str[:50] + "…"
    top_df = top_df.sort_values("market_value", ascending=True)

    fig1 = px.bar(
        top_df, x="market_value", y="short_title",
        color="Brand",
        orientation="h",
        text=top_df["market_value"].apply(lambda v: f"${v:,.0f}"),
        hover_data={
            "price":        ":.2f",
            "monthly_sold": ":.0f",
            "rating":       ":.1f",
            "subcat":       True,
        },
        color_discrete_sequence=BRAND_PALETTE,
        labels={"market_value": "Est. Market Value ($)", "short_title": ""},
    )
    fig1.update_traces(textposition="outside", textfont_size=10)
    fig1.update_layout(
        height=420, margin=dict(l=0, r=60, t=10, b=10),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor="#f3f4f6", title="Est. Market Value ($)"),
        yaxis=dict(tickfont=dict(size=11)),
        legend=dict(orientation="h", y=-0.18, title=""),
        showlegend=True,
    )
    st.plotly_chart(fig1, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with c2:
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown('<div class="chart-title">📊 Units Sold by Size &amp; Gender</div>',
                unsafe_allow_html=True)

    size_df = (
        df[df["Size"].notna() & df["gender"].isin(["Men", "Women"])]
        .groupby(["size_str", "gender"], sort=False)["monthly_sold"]
        .sum()
        .reset_index()
    )
    size_order = [
        s for s in ["7", "7.5", "8", "8.5", "9", "9.5", "10", "10.5", "11", "11.5", "12"]
        if s in size_df["size_str"].values
    ]

    fig2 = px.bar(
        size_df, x="size_str", y="monthly_sold", color="gender",
        barmode="stack",
        category_orders={"size_str": size_order},
        color_discrete_map=GENDER_COLORS,
        labels={"monthly_sold": "Est. Monthly Units", "size_str": "US Size", "gender": "Gender"},
    )
    fig2.update_layout(
        height=420, margin=dict(l=0, r=0, t=10, b=10),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(gridcolor="#f3f4f6"),
        legend=dict(orientation="h", y=-0.18, title=""),
    )
    st.plotly_chart(fig2, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ── Row 2: Bubble scatter + Price vs Rating ───────────────────────────────────
c3, c4 = st.columns(2)

with c3:
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown('<div class="chart-title">💹 Market Value: Price × Monthly Sold (bubble = rating)</div>',
                unsafe_allow_html=True)

    sc_df = (
        df[df["market_value"].notna() & df["price"].notna() & df["monthly_sold"].notna()]
        .drop_duplicates("ASIN")
    )
    sc_df = sc_df.sample(min(600, len(sc_df)), random_state=42)

    fig3 = px.scatter(
        sc_df, x="price", y="monthly_sold",
        color="Brand", size="rating",
        size_max=16,
        hover_name="Title",
        hover_data={
            "price":        ":.2f",
            "monthly_sold": ":.0f",
            "rating":       ":.1f",
            "subcat":       True,
            "is_estimated": True,
        },
        color_discrete_sequence=BRAND_PALETTE,
        labels={
            "price":        "Price ($)",
            "monthly_sold": "Est. Monthly Sold",
            "rating":       "Rating",
        },
        opacity=0.82,
    )
    fig3.update_layout(
        height=380, margin=dict(l=0, r=0, t=10, b=10),
        plot_bgcolor="#fafafa", paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor="#f0f0f0"),
        yaxis=dict(gridcolor="#f0f0f0"),
        legend=dict(orientation="h", y=-0.22, title=""),
    )
    st.plotly_chart(fig3, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with c4:
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown('<div class="chart-title">⭐ Price vs Rating by Subcategory</div>',
                unsafe_allow_html=True)

    pr_df = (
        df[df["price"].notna() & df["rating"].notna()]
        .drop_duplicates("ASIN")
    )
    pr_df = pr_df.sample(min(600, len(pr_df)), random_state=42)
    avg_r = pr_df["rating"].mean()

    fig4 = px.scatter(
        pr_df, x="price", y="rating",
        color="subcat",
        hover_name="Title",
        hover_data={"price": ":.2f", "rating": ":.1f", "Brand": True},
        color_discrete_sequence=SUBCAT_PALETTE,
        labels={"price": "Price ($)", "rating": "Rating ★", "subcat": "Subcategory"},
        opacity=0.75,
    )
    fig4.add_hline(
        y=avg_r, line_dash="dot", line_color="#6b7280",
        annotation_text=f" Avg {avg_r:.2f}★",
        annotation_font_size=11,
    )
    fig4.update_layout(
        height=380, margin=dict(l=0, r=0, t=10, b=10),
        plot_bgcolor="#fafafa", paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor="#f0f0f0"),
        yaxis=dict(gridcolor="#f0f0f0", range=[1, 5.3]),
        legend=dict(orientation="h", y=-0.22, title=""),
    )
    st.plotly_chart(fig4, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ── Row 3: Treemap + Brand bar ────────────────────────────────────────────────
c5, c6 = st.columns(2)

with c5:
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown('<div class="chart-title">🗺️ Market Share: Subcategory → Brand</div>',
                unsafe_allow_html=True)

    tree_df = (
        df[df["market_value"].notna()]
        .groupby(["subcat", "Brand"])["market_value"]
        .sum()
        .reset_index()
    )
    tree_df = tree_df[tree_df["market_value"] > 0]

    fig5 = px.treemap(
        tree_df, path=["subcat", "Brand"],
        values="market_value",
        color="market_value",
        color_continuous_scale="Purpor",
        labels={"market_value": "Market Value ($)"},
        hover_data={"market_value": ":,.0f"},
    )
    fig5.update_layout(
        height=380, margin=dict(l=0, r=0, t=10, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        coloraxis_colorbar=dict(title="Value ($)", tickformat="$,.0f"),
    )
    st.plotly_chart(fig5, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with c6:
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown('<div class="chart-title">📈 Brand Performance: Market Value &amp; Avg Rating</div>',
                unsafe_allow_html=True)

    brand_df = (
        df[df["market_value"].notna()]
        .groupby("Brand")
        .agg(
            total_mv  =("market_value", "sum"),
            n         =("ASIN",         "count"),
            avg_price =("price",        "mean"),
            avg_rating=("rating",       "mean"),
        )
        .reset_index()
        .sort_values("total_mv", ascending=False)
        .head(12)
    )

    fig6 = px.bar(
        brand_df, x="Brand", y="total_mv",
        color="avg_rating",
        color_continuous_scale="Plasma",
        text=brand_df["total_mv"].apply(lambda v: f"${v/1e3:.0f}k"),
        hover_data={
            "n":          True,
            "avg_price":  ":.2f",
            "avg_rating": ":.2f",
        },
        labels={
            "total_mv":   "Total Market Value ($)",
            "avg_rating": "Avg Rating",
            "n":          "# Products",
        },
    )
    fig6.update_traces(textposition="outside", textfont_size=9)
    fig6.update_layout(
        height=380, margin=dict(l=0, r=0, t=10, b=60),
        xaxis_tickangle=-30,
        plot_bgcolor="#fafafa", paper_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(gridcolor="#f0f0f0"),
        coloraxis_colorbar=dict(title="Avg ★"),
    )
    st.plotly_chart(fig6, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ── Row 4: Gender pie + Sales rank distribution ───────────────────────────────
c7, c8 = st.columns(2)

with c7:
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown('<div class="chart-title">👥 Market Value by Gender</div>',
                unsafe_allow_html=True)

    gender_df = (
        df[df["market_value"].notna()]
        .groupby("gender")["market_value"]
        .sum()
        .reset_index()
    )
    fig7 = px.pie(
        gender_df, names="gender", values="market_value",
        color="gender",
        color_discrete_map=GENDER_COLORS,
        hole=0.45,
        labels={"market_value": "Market Value ($)"},
    )
    fig7.update_traces(textposition="outside", textinfo="percent+label")
    fig7.update_layout(
        height=320, margin=dict(l=20, r=20, t=10, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=-0.05),
        showlegend=False,
    )
    st.plotly_chart(fig7, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with c8:
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown('<div class="chart-title">📉 Sales Rank Distribution by Subcategory</div>',
                unsafe_allow_html=True)

    rank_df = df[df["rank"].notna() & df["rank"] <= 100000].copy()
    top_subcats_rank = rank_df["subcat"].value_counts().head(5).index.tolist()
    rank_df = rank_df[rank_df["subcat"].isin(top_subcats_rank)]

    fig8 = px.box(
        rank_df, x="subcat", y="rank",
        color="subcat",
        color_discrete_sequence=SUBCAT_PALETTE,
        labels={"rank": "Sales Rank (lower = better)", "subcat": "Subcategory"},
        points=False,
        notched=True,
    )
    fig8.update_layout(
        height=320, margin=dict(l=0, r=0, t=10, b=60),
        xaxis_tickangle=-20,
        plot_bgcolor="#fafafa", paper_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(gridcolor="#f0f0f0"),
        showlegend=False,
    )
    st.plotly_chart(fig8, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ── Write-up / Footer ─────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
with st.expander("📋 Assignment Write-up — DS 4200 Interactive Visualization", expanded=False):
    st.markdown("""
<div class="writeup-section">

<h3>1. What question does this visualization answer?</h3>

<p><strong>Which Amazon shoe brands, subcategories, and sizes represent the most market
opportunity — and how does demand split between men and women?</strong></p>

<p>More specifically, this dashboard addresses three layered questions:</p>
<ul>
<li>Which brands and shoe types generate the highest estimated market value on Amazon
    (measured as price × estimated monthly units sold)?</li>
<li>Which sizes see the highest demand, and does that demand skew toward men or women?</li>
<li>Is there a relationship between price and customer rating — and does it vary by shoe type?</li>
</ul>

<p>These questions are directly relevant to anyone doing product sourcing, competitive
analysis, or market sizing in the Amazon footwear space.</p>

<hr>

<h3>2. Design rationale</h3>

<h4>Visual encodings</h4>

<p><strong>Horizontal bar chart (Top N sellers):</strong>
Horizontal orientation was chosen because product names are long strings that become
unreadable when rotated on a vertical axis. Color encodes brand, providing categorical
context at a glance. The Top N slider is the central dynamic query — inspired directly
by the HomeFinder dynamic query technique — letting the user compress or expand the
competition landscape without any page reload.</p>

<p><strong>Stacked bar (Units by size):</strong>
A stacked bar shows both total demand per size and the gender split simultaneously.
Grouped bars were considered and rejected because comparing total bar height across
sizes (the primary question) is harder with grouped bars. Women are shown in purple
on top of men in blue, following a consistent color scheme used throughout the dashboard.</p>

<p><strong>Bubble scatter (Market value):</strong>
The scatter plot maps price (x) against estimated monthly sold (y), which together
define market value. Bubble size encodes rating, adding a third dimension without
a separate chart. Color encodes brand. A sample of 600 points is drawn to avoid
overplotting while preserving the distribution shape.</p>

<p><strong>Treemap (Market share):</strong>
A treemap was chosen for the subcategory → brand breakdown because it conveys part-to-whole
relationships more intuitively than a nested bar chart. It answers "who owns what slice
of the market" at a single glance.</p>

<p><strong>Box plot (Sales rank distribution):</strong>
Notched box plots show the median, IQR, and outlier spread of sales ranks per subcategory.
This tells the user how concentrated vs. spread-out the competition is in each shoe type.</p>

<h4>Interaction techniques</h4>
<ul>
<li><strong>Multi-select dropdowns (Brand, Subcategory, Size):</strong> Dynamic query filtering
    cascades across all six charts simultaneously.</li>
<li><strong>Price + Rating sliders:</strong> Continuous range filters for two of the most
    important sourcing metrics.</li>
<li><strong>Top N slider:</strong> Controls ranking depth in the horizontal bar chart.</li>
<li><strong>Hover tooltips:</strong> All charts expose details-on-demand — product name, price,
    estimated monthly sold, rating, and source flag (observed vs. estimated).</li>
</ul>

<h4>Alternatives considered</h4>
<p>A time series chart of price history was considered but rejected because the Keepa
Product Finder export provides only snapshot data, not time series. A choropleth map
of sales by region was considered but Keepa does not provide geographic breakdowns at
the product level.</p>

<hr>

<h3>3. Demand estimation methodology</h3>

<p>Amazon's "Bought in past month" figure is available for only ~30% of products.
To fill the remaining 70%, this dashboard applies a
<span class="ref-tag">He & Hollenbeck (2020)</span> power-law model:</p>

<blockquote>
<strong>monthly_units ≈ a × rank<sup>θ</sup></strong>
</blockquote>

<p>Parameters a and θ are calibrated via log-log OLS regression on the
<strong>{cal_n} products</strong> that have both a sales rank and an observed
"Bought in past month" value, yielding:</p>

<blockquote>
monthly_units ≈ <strong>{a_param} × rank<sup>{theta}</sup></strong>
</blockquote>

<p>This follows the Pareto distribution approach originally established by
<span class="ref-tag">Chevalier & Goolsbee (2003)</span> for books and extended to
clothing and other categories by
<span class="ref-tag">Brynjolfsson et al. (2011)</span>.
Products using estimated rather than observed monthly sold are flagged with
<span class="est-badge">estimated</span> in hover tooltips.</p>

<hr>

<h3>4. Data sources &amp; references</h3>

<table style="width:100%;border-collapse:collapse;font-size:0.9rem;">
<tr style="background:#f5f3ff;">
  <th style="padding:8px;text-align:left;border-bottom:2px solid #ddd;">Source</th>
  <th style="padding:8px;text-align:left;border-bottom:2px solid #ddd;">Description</th>
</tr>
<tr><td style="padding:6px 8px;">Keepa Product Finder</td>
    <td style="padding:6px 8px;">Amazon US snapshot · Clothing, Shoes &amp; Jewelry · Apr 2026 · 10,000 ASINs</td></tr>
<tr style="background:#fafafa;"><td style="padding:6px 8px;">He &amp; Hollenbeck (2020)</td>
    <td style="padding:6px 8px;"><em>Sales and Rank on Amazon.com.</em> SSRN 3728281. Power-law rank-to-quantity method.</td></tr>
<tr><td style="padding:6px 8px;">Chevalier &amp; Goolsbee (2003)</td>
    <td style="padding:6px 8px;"><em>Measuring Prices Online.</em> Original BSR → quantity approach for books.</td></tr>
<tr style="background:#fafafa;"><td style="padding:6px 8px;">Brynjolfsson et al. (2011)</td>
    <td style="padding:6px 8px;">Power-law model extended to clothing &amp; other Amazon categories.</td></tr>
<tr><td style="padding:6px 8px;">Streamlit docs</td>
    <td style="padding:6px 8px;">App layout, caching, multiselect, slider components.</td></tr>
<tr style="background:#fafafa;"><td style="padding:6px 8px;">Plotly Express</td>
    <td style="padding:6px 8px;">All interactive charts — bar, scatter, treemap, box, pie.</td></tr>
</table>

<hr>

<h3>5. Development process</h3>

<table style="width:100%;border-collapse:collapse;font-size:0.9rem;">
<tr style="background:#f5f3ff;">
  <th style="padding:8px;">Phase</th>
  <th style="padding:8px;">Time</th>
  <th style="padding:8px;">Notes</th>
</tr>
<tr><td style="padding:6px 8px;">Dataset acquisition &amp; Keepa export</td>
    <td style="padding:6px 8px;">~1.5 hrs</td>
    <td style="padding:6px 8px;">Configuring product finder filter, exporting 10,000 rows</td></tr>
<tr style="background:#fafafa;"><td style="padding:6px 8px;">Exploratory analysis &amp; power law calibration</td>
    <td style="padding:6px 8px;">~2.5 hrs</td>
    <td style="padding:6px 8px;">Log-log OLS, validating against observed "Bought in past month"</td></tr>
<tr><td style="padding:6px 8px;">Streamlit UI + chart design</td>
    <td style="padding:6px 8px;">~4 hrs</td>
    <td style="padding:6px 8px;">6 chart types, sidebar filters, KPI cards, custom CSS</td></tr>
<tr style="background:#fafafa;"><td style="padding:6px 8px;">Write-up &amp; deployment</td>
    <td style="padding:6px 8px;">~1.5 hrs</td>
    <td style="padding:6px 8px;">Streamlit Cloud deployment, GitHub setup, requirements</td></tr>
</table>

<p><strong>What took the most time:</strong>
The power-law calibration required careful validation — the initial fit was driven by
outliers at very low sales ranks. Capping the calibration sample and checking residuals
took multiple iterations. Gender inference from product titles also required testing
regex patterns against edge cases like "mens" vs "men's" vs "men".</p>

</div>
""".format(
        cal_n   = df_raw.attrs.get("cal_n",     "~3,000"),
        a_param = df_raw.attrs.get("power_law_a",     "218"),
        theta   = df_raw.attrs.get("power_law_theta", "-0.114"),
    ), unsafe_allow_html=True)

# ── Sticky footer ─────────────────────────────────────────────────────────────
st.markdown("""
<br><hr>
<p style="text-align:center;color:#9ca3af;font-size:0.8rem;">
    👟 Amazon Shoes Market Explorer &nbsp;|&nbsp;
    DS 4200 Assignment 5 &nbsp;|&nbsp;
    Data: Keepa · Apr 2026 &nbsp;|&nbsp;
    Demand model: He &amp; Hollenbeck (2020)
</p>
""", unsafe_allow_html=True)
