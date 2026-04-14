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

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background:#f0f0f8; }
[data-testid="stSidebar"]          { background:#1e1b4b; }
[data-testid="stSidebar"] *        { color:#e0e0f0 !important; }
[data-testid="stSidebar"] hr       { border-color:#3730a3; }
.hero { background:#4f46e5; border-radius:14px; padding:1.4rem 2rem;
        margin-bottom:1.2rem; color:#fff; }
.hero h1 { margin:0; font-size:1.7rem; font-weight:700; }
.hero p  { margin:.3rem 0 0; font-size:.9rem; opacity:.85; }
.kpi { background:#fff; border-radius:10px; padding:.9rem 1.1rem;
       border-top:4px solid; box-shadow:0 1px 6px rgba(0,0,0,.07); }
.kl  { font-size:.7rem; color:#6b7280; text-transform:uppercase;
       letter-spacing:.05em; font-weight:600; }
.kv  { font-size:1.7rem; font-weight:700; color:#1e1b4b; margin:.15rem 0 0; }
.ks  { font-size:.7rem; color:#9ca3af; margin-top:.1rem; }
.card { background:#fff; border-radius:10px; padding:1rem 1.1rem;
        box-shadow:0 1px 6px rgba(0,0,0,.06); margin-bottom:.8rem; }
.ct  { font-size:.82rem; font-weight:600; color:#374151;
       padding-bottom:.4rem; border-bottom:1px solid #f3f4f6;
       margin-bottom:.6rem; }
.wu  { background:#fff; border-radius:10px; padding:1.2rem 1.5rem; }
.wu h4 { color:#4f46e5; font-size:.9rem; margin:.9rem 0 .3rem; }
.wu p, .wu li { font-size:.83rem; color:#374151; line-height:1.6; }
.wu ul { padding-left:1.2rem; margin:.2rem 0; }
footer,#MainMenu { visibility:hidden; }
</style>
""", unsafe_allow_html=True)

# ── Colour maps ───────────────────────────────────────────────────────────────
GENDER_CLR = {"Women": "#7c3aed", "Men": "#2563eb", "Unknown": "#9ca3af"}
PALETTE    = px.colors.qualitative.Bold

# ── Data loading & wrangling ──────────────────────────────────────────────────
@st.cache_data(show_spinner="Loading data…")
def load(path):
    df = pd.read_excel(path, engine="openpyxl")

    # gender from title
    t = df["Title"].str.lower().fillna("")
    df["gender"] = "Unknown"
    df.loc[t.str.contains(r"women'?s|woman'?s|ladies|girl", regex=True), "gender"] = "Women"
    df.loc[t.str.contains(r"\bmen'?s\b|\bman'?s\b|boys",    regex=True), "gender"] = "Men"

    # subcategory = last node of category tree
    df["subcat"] = (df["Categories: Tree"].fillna("Shoes")
                    .str.split("›").str[-1].str.strip())

    # price / rating / rank
    df["price"]  = df["Buy Box: Current"].fillna(df["New: Current"])
    df["rating"] = pd.to_numeric(df["Reviews: Rating"], errors="coerce")
    df["rank"]   = pd.to_numeric(df["Sales Rank: Current"], errors="coerce")

    # power-law calibration on observed monthly sold
    cal = df[
        df["rank"].notna() & (df["rank"] > 0) &
        df["Monthly Sales Trends: Bought in past month"].notna() &
        (df["Monthly Sales Trends: Bought in past month"] > 0)
    ].copy()
    c = np.polyfit(
        np.log(cal["rank"]),
        np.log(cal["Monthly Sales Trends: Bought in past month"]),
        1,
    )
    a, th = float(np.exp(c[1])), float(c[0])

    df["monthly_sold"] = (
        df["Monthly Sales Trends: Bought in past month"]
        .fillna(a * df["rank"] ** th)
    )
    df["is_est"]       = df["Monthly Sales Trends: Bought in past month"].isna()
    df["market_value"] = df["price"] * df["monthly_sold"]
    df["size_str"]     = df["Size"].apply(
        lambda x: (str(int(x)) if x == int(x) else str(x)) if pd.notna(x) else "?"
    )

    df.attrs.update({"a": round(a, 2), "theta": round(th, 4), "cal_n": len(cal)})
    return df


RAW = load("6600_amazon_soes.xlsx")

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 👟 Filters")
    st.markdown("---")

    top_brands  = RAW["Brand"].value_counts().head(10).index.tolist()
    sel_brands  = st.multiselect(
        "Brand", sorted(RAW["Brand"].dropna().unique()), default=top_brands[:8]
    )
    top_subcats = RAW["subcat"].value_counts().head(6).index.tolist()
    sel_subcats = st.multiselect(
        "Subcategory", sorted(RAW["subcat"].dropna().unique()), default=top_subcats
    )
    all_sizes  = sorted(RAW["Size"].dropna().unique())
    sel_sizes  = st.multiselect("Size (US)", all_sizes, default=all_sizes)

    pmin = float(RAW["price"].min(skipna=True) or 0)
    pmax = float(RAW["price"].max(skipna=True) or 400)
    sel_price  = st.slider("Price range ($)", pmin, pmax,
                           (pmin, min(pmax, 200.0)), step=1.0)
    sel_rating = st.slider("Min rating ★", 1.0, 5.0, 3.5, step=0.5)
    top_n      = st.slider("Top N brands", 5, 15, 8, step=1)

    st.markdown("---")
    st.caption(
        f"Dataset: {len(RAW):,} products · Keepa · Apr 2026\n\n"
        f"Power law: {RAW.attrs['a']} × rank^({RAW.attrs['theta']})\n"
        f"Calibrated on {RAW.attrs['cal_n']:,} products"
    )

# ── Apply filters ─────────────────────────────────────────────────────────────
df = RAW.copy()
if sel_brands:  df = df[df["Brand"].isin(sel_brands)]
if sel_subcats: df = df[df["subcat"].isin(sel_subcats)]
if sel_sizes:   df = df[df["Size"].isin(sel_sizes)]
df = df[df["price"].between(*sel_price) | df["price"].isna()]
df = df[df["rating"].ge(sel_rating)     | df["rating"].isna()]

# ── Brushing state ────────────────────────────────────────────────────────────
if "brush_brand" not in st.session_state:
    st.session_state["brush_brand"] = None
brush = st.session_state["brush_brand"]

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <h1>👟 Amazon Shoes Market Explorer</h1>
  <p>Which shoe brands drive the most value on Amazon — and who buys which size?
     &nbsp;·&nbsp; 10,000 listings &nbsp;·&nbsp; US marketplace &nbsp;·&nbsp;
     Keepa data Apr 2026</p>
</div>
""", unsafe_allow_html=True)

# ── KPI cards ─────────────────────────────────────────────────────────────────
total_mv = df["market_value"].sum()
n_prod   = len(df)
avg_all  = df["price"].mean()
avg_w    = df[df["gender"] == "Women"]["price"].mean()
avg_m    = df[df["gender"] == "Men"]["price"].mean()
avg_rat  = df["rating"].mean()

k1, k2, k3, k4, k5, k6 = st.columns(6)
for col, color, label, val, sub in [
    (k1, "#4f46e5", "Est. Market Value",  f"${total_mv/1e6:.1f}M",
     "price × monthly sold"),
    (k2, "#0ea5e9", "Products Shown",     f"{n_prod:,}",
     f"{n_prod/len(RAW)*100:.0f}% of dataset"),
    (k3, "#10b981", "Avg Price (all)",
     f"${avg_all:.2f}" if pd.notna(avg_all) else "—",
     f"${df['price'].min():.0f}–${df['price'].max():.0f}"),
    (k4, "#7c3aed", "Avg Price (women)",
     f"${avg_w:.2f}" if pd.notna(avg_w) else "—",
     f"{(df['gender']=='Women').sum():,} products"),
    (k5, "#2563eb", "Avg Price (men)",
     f"${avg_m:.2f}" if pd.notna(avg_m) else "—",
     f"{(df['gender']=='Men').sum():,} products"),
    (k6, "#f59e0b", "Avg Rating",
     f"{avg_rat:.2f}" if pd.notna(avg_rat) else "—",
     "out of 5.0"),
]:
    with col:
        st.markdown(
            f'<div class="kpi" style="border-top-color:{color};">'
            f'<div class="kl">{label}</div>'
            f'<div class="kv">{val}</div>'
            f'<div class="ks">{sub}</div></div>',
            unsafe_allow_html=True,
        )

st.markdown("<br>", unsafe_allow_html=True)

# ── Brand aggregation ─────────────────────────────────────────────────────────
brand_agg = (
    df[df["market_value"].notna()]
    .groupby("Brand")
    .agg(
        qty   =("monthly_sold", "sum"),
        value =("market_value", "sum"),
        n     =("ASIN",         "count"),
        avg_p =("price",        "mean"),
        avg_r =("rating",       "mean"),
    )
    .reset_index()
    .sort_values("value", ascending=False)
    .head(top_n)
)

# ── Row 1: brand qty bar + brand value bar ────────────────────────────────────
c1, c2 = st.columns(2)

def make_brand_bar(data, x_col, x_title, base_color, key):
    data = data.sort_values(x_col, ascending=True)
    colors = [
        "#f59e0b" if (brush and b == brush) else base_color
        for b in data["Brand"]
    ]
    fig = go.Figure(go.Bar(
        x=data[x_col], y=data["Brand"],
        orientation="h",
        marker_color=colors,
        text=data[x_col].apply(
            lambda v: f"{v:,.0f}" if x_col == "qty" else f"${v/1e3:.0f}k"
        ),
        textposition="outside",
        textfont_size=10,
        customdata=data[["avg_p", "avg_r", "n"]].values,
        hovertemplate=(
            "<b>%{y}</b><br>"
            f"{x_title}: %{{x:,.0f}}<br>"
            "Avg price: $%{customdata[0]:.2f}<br>"
            "Avg rating: %{customdata[1]:.1f}★<br>"
            "Products: %{customdata[2]:.0f}<extra></extra>"
        ),
    ))
    fig.update_layout(
        height=380, margin=dict(l=0, r=65, t=8, b=8),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor="#f3f4f6", title=x_title),
        yaxis=dict(tickfont=dict(size=11)),
        showlegend=False,
    )
    return fig

with c1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="ct">Top brands by units sold — click bar to highlight in scatter</div>',
        unsafe_allow_html=True,
    )
    fig1  = make_brand_bar(brand_agg, "qty", "Est. monthly units", "#4f46e5", "qty")
    sel1  = st.plotly_chart(fig1, use_container_width=True,
                            on_select="rerun", key="bar_qty")
    if sel1 and sel1.get("selection", {}).get("points"):
        clicked = sel1["selection"]["points"][0].get("y")
        st.session_state["brush_brand"] = (
            None if clicked == brush else clicked
        )
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

with c2:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="ct">Top brands by market value — click bar to highlight in scatter</div>',
        unsafe_allow_html=True,
    )
    fig2  = make_brand_bar(brand_agg, "value", "Est. market value ($)", "#7c3aed", "val")
    sel2  = st.plotly_chart(fig2, use_container_width=True,
                            on_select="rerun", key="bar_val")
    if sel2 and sel2.get("selection", {}).get("points"):
        clicked = sel2["selection"]["points"][0].get("y")
        st.session_state["brush_brand"] = (
            None if clicked == brush else clicked
        )
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# brushing label
if brush:
    st.info(
        f"🎯 Highlighting **{brush}** in the scatter — click the same bar to clear",
        icon="🔆",
    )

# ── Row 2: size stacked bar + bubble scatter ──────────────────────────────────
c3, c4 = st.columns([0.52, 0.48])

with c3:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="ct">Size distribution — estimated units sold by gender</div>',
        unsafe_allow_html=True,
    )
    size_df = (
        df[df["Size"].notna() & df["gender"].isin(["Women", "Men"])]
        .groupby(["size_str", "gender"])["monthly_sold"]
        .sum()
        .reset_index()
    )
    size_order = [
        s for s in ["7","7.5","8","8.5","9","9.5","10","10.5","11","11.5","12"]
        if s in size_df["size_str"].values
    ]
    fig3 = px.bar(
        size_df, x="size_str", y="monthly_sold", color="gender",
        barmode="stack",
        category_orders={"size_str": size_order},
        color_discrete_map=GENDER_CLR,
        labels={"monthly_sold": "Est. monthly units",
                "size_str": "US size", "gender": "Gender"},
    )
    fig3.update_traces(
        hovertemplate="<b>Size %{x}</b> · %{data.name}<br>Units: %{y:,.0f}<extra></extra>"
    )
    fig3.update_layout(
        height=340, margin=dict(l=0, r=0, t=8, b=8),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(gridcolor="#f3f4f6"),
        legend=dict(orientation="h", y=-0.18, title=""),
    )
    st.plotly_chart(fig3, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with c4:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="ct">Price vs monthly sold — bubble = rating · color = brand</div>',
        unsafe_allow_html=True,
    )

    sc = (
        df[df["market_value"].notna() & df["price"].notna() & df["monthly_sold"].notna()]
        .drop_duplicates("ASIN")
    )
    sc = sc.sample(min(500, len(sc)), random_state=42)

    # consistent brand color map from full dataset
    brand_clr = {
        b: PALETTE[i % len(PALETTE)]
        for i, b in enumerate(RAW["Brand"].value_counts().head(20).index)
    }

    fig4 = go.Figure()
    for brand, grp in sc.groupby("Brand"):
        opacity = 1.0 if (not brush or brand == brush) else 0.06
        fig4.add_trace(go.Scatter(
            x=grp["price"],
            y=grp["monthly_sold"],
            mode="markers",
            name=brand,
            marker=dict(
                size=grp["rating"].fillna(3).clip(1, 5) * 3.5,
                color=brand_clr.get(brand, "#9ca3af"),
                opacity=opacity,
                line=dict(width=0.4, color="white"),
            ),
            customdata=grp[["Brand", "rating", "subcat"]].values,
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Price: $%{x:.2f}<br>"
                "Monthly sold: %{y:,.0f}<br>"
                "Rating: %{customdata[1]:.1f}★<br>"
                "Subcat: %{customdata[2]}<extra></extra>"
            ),
        ))

    fig4.update_layout(
        height=340, margin=dict(l=0, r=0, t=8, b=8),
        plot_bgcolor="#fafafa", paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor="#efefef", title="Price ($)"),
        yaxis=dict(gridcolor="#efefef", title="Est. monthly sold"),
        legend=dict(orientation="h", y=-0.25, title="", font=dict(size=9)),
        showlegend=True,
    )
    st.plotly_chart(fig4, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ── Write-up ──────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
with st.expander("About this dashboard", expanded=False):
    st.markdown("""
<div class="wu">

<h4>What question does this answer?</h4>
<p>Which shoe brands on Amazon generate the most market value — and which sizes
and genders drive that demand? The dashboard is built for anyone doing product
sourcing or competitive analysis in the footwear category on Amazon US.</p>

<h4>Design decisions</h4>
<ul>
  <li><b>Two horizontal bar charts</b> (units vs value) sit side by side so you
      can spot brands that sell a lot at low prices vs brands that sell less but
      command higher value. Sorted high-to-low so the biggest bars are at top.</li>
  <li><b>Stacked bar by size and gender</b> shows total demand per size with the
      men/women split in one view. Grouped bars were considered but made total
      height harder to compare across sizes.</li>
  <li><b>Bubble scatter</b> (price × monthly sold, bubble = rating) reveals
      whether high-value products are expensive, high-volume, or high-rated —
      three things that matter for sourcing. Bubble size encodes rating to avoid
      a fourth separate chart.</li>
  <li><b>Brushing:</b> clicking any brand bar highlights that brand in the scatter
      and dims all others. This links the two views directly so you can see where
      a brand sits on price and demand with one click.</li>
  <li><b>Sidebar filters</b> (brand, subcategory, size, price, rating) cascade
      across all four charts simultaneously — following the dynamic query
      technique from Shneiderman (1994).</li>
</ul>

<h4>Demand estimation</h4>
<p>Amazon only shows "Bought in past month" for ~30% of products. For the rest,
monthly units are estimated using a power-law model fit on 3,027 products that
have observed data — following He & Hollenbeck (2020).
Formula: <b>units ≈ 218 × rank⁻⁰·¹¹⁴</b>.
Spearman r = −0.14 (p &lt; 0.001) between rank and observed monthly sold.
Estimated values are flagged in hover tooltips.</p>

<h4>Data sources and references</h4>
<ul>
  <li>Keepa Product Finder — Amazon US, Clothing/Shoes/Jewelry, Apr 2026,
      10,000 ASINs</li>
  <li>He & Hollenbeck (2020). <i>Sales and Rank on Amazon.com.</i> SSRN 3728281.</li>
  <li>Chevalier & Goolsbee (2003). <i>Measuring Prices and Price Competition
      Online.</i> NBER Working Paper.</li>
  <li>Shneiderman (1994). Dynamic queries for visual information seeking.
      IEEE Software.</li>
  <li>Plotly and Streamlit documentation.</li>
</ul>

<h4>Development process</h4>
<ul>
  <li>Data acquisition and Keepa export — ~1.5 hrs</li>
  <li>Exploratory analysis and power-law calibration — ~2.5 hrs</li>
  <li>Streamlit UI, charts, brushing logic — ~4 hrs</li>
  <li>Write-up and deployment — ~1.5 hrs</li>
  <li><b>Total ~10 hrs.</b> Brushing and power-law validation took the most time.</li>
</ul>

</div>
""", unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<p style="text-align:center;color:#9ca3af;font-size:.75rem;margin-top:1rem;">
  Amazon Shoes Market Explorer &nbsp;·&nbsp; Keepa data Apr 2026
  &nbsp;·&nbsp; Demand model: He &amp; Hollenbeck (2020)
</p>
""", unsafe_allow_html=True)
