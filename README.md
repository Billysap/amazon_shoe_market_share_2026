# Amazon Shoes Market Explorer

An interactive market intelligence dashboard for the Amazon US footwear category,
built to support data-driven sourcing, competitive analysis, and demand forecasting
decisions across the shoes vertical.

---

## Background

The footwear category on Amazon is one of the most competitive and data-rich segments
in e-commerce. With thousands of new listings entering the market every month, making
informed decisions about which brands to track, which sizes to stock, and which
subcategories hold the most untapped value requires more than browsing bestseller lists.

This dashboard was built out of a practical need: to turn raw Amazon product data into
a clear, actionable view of where demand is concentrated, how brands are positioned
relative to each other, and what the market looks like by size and gender. The goal
is to give anyone working on footwear strategy — whether in sourcing, category
management, or competitive intelligence — a single place to explore the market without
needing to write SQL or dig through spreadsheets.

The underlying dataset covers 10,000 shoe listings across the Clothing, Shoes & Jewelry
root category on Amazon US, extracted via Keepa's Product Finder. It includes current
pricing, sales rank, customer ratings, review counts, and Amazon's "Bought in past month"
signal where available.

---

## Why this dashboard exists

Amazon publishes sales rank publicly, but it does not publish unit sales. This creates
a visibility problem: you can see that a product is popular, but you cannot easily
quantify how popular, or compare demand across brands and subcategories at scale.

This tool addresses that gap in three ways:

**1. Demand estimation from sales rank.**
For the roughly 70% of products where Amazon does not display a "Bought in past month"
figure, monthly unit sales are estimated using a power-law regression model calibrated
on the 3,027 products in this dataset that do have observed sales data. The approach
follows the methodology established by He & Hollenbeck (2020) in *Sales and Rank on
Amazon.com*, which showed that the rank-to-quantity relationship follows a Pareto
distribution. Estimated values are flagged clearly throughout the dashboard.

**2. Market value estimation.**
By combining estimated monthly units with current price, the dashboard computes an
estimated monthly market value (in USD) for each product and rolls it up to brand,
subcategory, and size level. This gives a demand-weighted view of the market rather
than a simple product count.

**3. Interactive exploration.**
All charts respond to the sidebar filters in real time. You can slice by brand,
subcategory, size, price range, and minimum rating — and all six charts update
simultaneously, making it fast to answer questions like "which Nike subcategories
are winning in size 9 women's shoes under $80?"

---

## What you can do with this dashboard

- **Identify high-value subcategories** — the treemap shows where market value is
  concentrated across shoe types and brands at a glance.
- **Spot size demand gaps** — the stacked bar chart breaks down estimated monthly
  units by size and gender, highlighting where supply may not match demand.
- **Compare brand positioning** — the bubble scatter and brand performance bar show
  how brands are positioned on price, demand, and customer rating simultaneously.
- **Find underpriced quality** — the price vs. rating scatter reveals subcategories
  where high-rated products are available at lower price points.
- **Track sales rank competitiveness** — the box plot shows how spread out the sales
  ranks are within each subcategory, signaling how competitive each segment is.

---

## Data source

- **Provider:** Keepa Product Finder (keepa.com)
- **Marketplace:** Amazon US
- **Category:** Clothing, Shoes & Jewelry — Shoes
- **Export date:** April 2026
- **Product count:** 10,000 ASINs
- **Rank filter applied:** Sales rank 1–5,000 (top sellers only)
- **Sizes included:** US 7 through 12 (including half sizes)

---

## Methodology note

Monthly unit estimates use a log-log OLS regression fit on 3,027 products with
observed "Bought in past month" data:

```
estimated_monthly_units = 218.0 × sales_rank ^ (−0.114)
```

The Spearman correlation between sales rank and observed monthly sold is r = −0.14
(p < 0.001), which is statistically significant but practically weak. This is expected
given two structural constraints in the data: the rank range is narrow (101–4,846,
all top sellers), and Amazon rounds "Bought in past month" to the nearest 50 units.
Estimated values should be treated as directional proxies, not precise forecasts.

---

## How to run

### Local

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO
pip install -r requirements.txt
streamlit run app.py
```

### Streamlit Cloud

1. Push all files to a public GitHub repository
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click **New app** → select your repository → set main file to `app.py`
4. Click **Deploy**

---

## Repository structure

```
├── app.py                  # Main Streamlit application
├── 6600_amazon_soes.xlsx   # Source dataset (Keepa export)
├── requirements.txt        # Python dependencies
└── README.md               # This file
```

---

## References

- He, S. & Hollenbeck, B. (2020). *Sales and Rank on Amazon.com.* SSRN 3728281.
- Chevalier, J. & Goolsbee, A. (2003). *Measuring Prices and Price Competition Online.*
  NBER Working Paper.
- Brynjolfsson, E. et al. (2011). *Goodbye Pareto Principle, Hello Long Tail.*
  Management Science.
