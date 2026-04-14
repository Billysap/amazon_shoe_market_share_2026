# Amazon Shoes Market Explorer

An interactive market intelligence dashboard for the Amazon US footwear category.
Built to support data-driven decisions in product sourcing, competitive analysis,
and demand forecasting across the shoes vertical.

---

## Background

The footwear category on Amazon is one of the most competitive segments in
e-commerce. Thousands of new listings enter the market every month, and making
informed decisions about which brands to track, which sizes to stock, and which
subcategories hold the most untapped value requires more than browsing bestseller
lists.

This dashboard was built to turn raw Amazon product data into a clear, actionable
view of where demand is concentrated, how brands are positioned relative to each
other, and what the market looks like by size and gender — without needing to
write SQL or dig through spreadsheets.

The underlying dataset covers 10,000 shoe listings across the Clothing, Shoes &
Jewelry root category on Amazon US, extracted via Keepa's Product Finder.

---

## What this dashboard does

**Answers one central question:** Which shoe brands drive the most market value
on Amazon — and who buys which size?

**Four interactive charts:**

- **Top brands by units sold** — ranked bar chart, high to low
- **Top brands by market value** — ranked bar chart, high to low
- **Size distribution** — stacked bar by size and gender (men vs women)
- **Price vs demand scatter** — bubble chart where size = rating, color = brand

**Brushing:** clicking any brand in either bar chart highlights that brand in the
scatter plot and dims all others. This links the ranking view to the positioning
view in one click.

**Sidebar filters** — brand, subcategory, shoe size, price range, and minimum
rating — cascade across all four charts simultaneously.

---

## Demand estimation

Amazon does not publish unit sales. Monthly units are estimated two ways:

1. For the ~30% of products where Amazon displays "Bought in past month" — that
   observed figure is used directly.

2. For the remaining ~70% — a power-law model is fit on the observed data
   following He & Hollenbeck (2020):

   ```
   estimated_monthly_units = 218 × sales_rank ^ (−0.114)
   ```

   Spearman correlation between rank and observed monthly sold: r = −0.14,
   p < 0.001. Estimated values are flagged in hover tooltips.

Market value = price × estimated monthly units.

---

## Data source

- **Provider:** Keepa Product Finder (keepa.com)
- **Marketplace:** Amazon US
- **Category:** Clothing, Shoes & Jewelry — Shoes
- **Export date:** April 2026
- **Product count:** 10,000 ASINs
- **Rank filter:** Sales rank 1–5,000 (top sellers only)
- **Sizes:** US 7 through 12 including half sizes

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
3. Click **New app** → select your repo → set main file to `app.py`
4. Click **Deploy**

---

## Repository structure

```
├── app.py                   # Streamlit application
├── 6600_amazon_soes.xlsx    # Source dataset (Keepa export)
├── requirements.txt         # Python dependencies
└── README.md
```

---

## References

- He, S. & Hollenbeck, B. (2020). *Sales and Rank on Amazon.com.* SSRN 3728281.
