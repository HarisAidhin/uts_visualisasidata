"""Dashboard analitik interaktif Superstore (Streamlit).

Jalankan:  streamlit run app.py
"""
from __future__ import annotations

import json
import math

import pandas as pd
import streamlit as st

from src import data_analysis as da
from src import visualization as viz
from src.data_cleaning import PROCESSED_PATH, REPORT_PATH, run_cleaning

KAGGLE_URL = "https://www.kaggle.com/datasets/vivek468/superstore-dataset-final"
REQUIRED_PROCESSED = {
    "Order Date", "Order ID", "Customer ID", "Region", "Category", "Segment", "State",
    "Sub-Category", "Sales", "Profit", "Quantity", "Discount", "Discount Band",
    "Order Year", "Order Month", "Order YearMonth", "Is Loss", "Profit Margin (%)", "Ship Days",
}

st.set_page_config(page_title="Superstore Analytics Dashboard", page_icon="📊", layout="wide")

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1280px; }
footer { visibility: hidden; }
.hero h1 { font-size: 1.9rem; font-weight: 700; margin: 0; color: #1B2430; }
.hero p { color: #5B6678; margin: .25rem 0 1rem; font-size: .95rem; }
.kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 14px; margin: 4px 0 20px; }
.kpi-card { background: #fff; border: 1px solid #E5E9F0; border-radius: 14px; padding: 16px 18px;
            box-shadow: 0 1px 2px rgba(16,24,40,.04); }
.kpi-label { font-size: .75rem; text-transform: uppercase; letter-spacing: .04em; color: #5B6678; font-weight: 600; }
.kpi-value { font-size: 1.65rem; font-weight: 700; color: #1F4E79; margin: 4px 0 2px; }
.kpi-hint { font-size: .78rem; color: #6B7686; }
.kpi-up { color: #2A9D8F; font-weight: 600; } .kpi-down { color: #E76F51; font-weight: 600; }
.insight { background: #fff; border: 1px solid #E5E9F0; border-left: 4px solid #2A9D8F; border-radius: 10px;
           padding: 14px 18px; margin-bottom: 12px; }
.insight h4 { margin: 0 0 4px; font-size: 1rem; color: #1F4E79; }
.insight p { margin: 0; color: #2B3545; font-size: .93rem; line-height: 1.5; }
@media (max-width: 640px) { .hero h1 { font-size: 1.4rem; } .kpi-value { font-size: 1.3rem; } }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


@st.cache_data(show_spinner="Memuat data...")
def load_data() -> pd.DataFrame:
    """Baca dataset bersih; jalankan cleaning otomatis bila CSV bersih belum ada."""
    if not PROCESSED_PATH.exists():
        run_cleaning()
    return pd.read_csv(
        PROCESSED_PATH,
        dtype={"Postal Code": "string"},
        parse_dates=["Order Date", "Ship Date", "Order YearMonth"],
    )


def kpi_card(label: str, value: str, hint: str, hint_class: str = "") -> str:
    return (
        f'<div class="kpi-card"><div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div><div class="kpi-hint {hint_class}">{hint}</div></div>'
    )


def render_kpis(kpi: dict) -> None:
    yoy = kpi["yoy"]
    if yoy:
        growth, prev_y, last_y = yoy
        yoy_value = f"{growth:+.1f}%"
        yoy_hint = f"Penjualan {last_y} vs {prev_y}"
        yoy_cls = "kpi-up" if growth >= 0 else "kpi-down"
    else:
        yoy_value, yoy_hint, yoy_cls = "n/a", "Perlu data minimal 2 tahun", ""
    cards = [
        kpi_card("Total Penjualan", da.fmt_money(kpi["total_sales"]), f"{kpi['n_orders']:,} pesanan unik"),
        kpi_card("Total Profit", da.fmt_money(kpi["total_profit"]), f"Margin {da.fmt_pct(kpi['profit_margin'])} dari penjualan"),
        kpi_card("Rata-rata Nilai Pesanan", da.fmt_money(kpi["avg_order_value"]), "Penjualan ÷ jumlah pesanan"),
        kpi_card("Pelanggan Aktif", f"{kpi['n_customers']:,}", "Pelanggan unik pada filter"),
        kpi_card("Rata-rata Diskon", da.fmt_pct(kpi["avg_discount"]), f"{da.fmt_pct(kpi['loss_share'])} baris transaksi merugi"),
        kpi_card("Pertumbuhan Tahunan", yoy_value, yoy_hint, yoy_cls),
    ]
    st.markdown(f'<div class="kpi-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def sidebar_filters(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.header("Filter data")
    dmin, dmax = df["Order Date"].min().date(), df["Order Date"].max().date()
    picked = st.sidebar.date_input("Rentang tanggal pesanan", (dmin, dmax), min_value=dmin, max_value=dmax)
    if isinstance(picked, (tuple, list)) and len(picked) == 2:
        start, end = picked
    else:  # pengguna baru memilih satu tanggal
        start, end = dmin, dmax
        st.sidebar.caption("Pilih tanggal akhir untuk menerapkan rentang.")

    regions = st.sidebar.multiselect("Wilayah", sorted(df["Region"].unique()), default=sorted(df["Region"].unique()))
    cats = st.sidebar.multiselect("Kategori", sorted(df["Category"].unique()), default=sorted(df["Category"].unique()))
    segs = st.sidebar.multiselect("Segmen", sorted(df["Segment"].unique()), default=sorted(df["Segment"].unique()))
    max_disc = int(math.ceil(df["Discount"].max() * 100))
    disc = st.sidebar.slider("Diskon (%)", 0, max_disc, (0, max_disc))
    st.sidebar.caption("Seluruh KPI, grafik, tabel, dan insight mengikuti filter ini.")

    return da.apply_filters(
        df, pd.Timestamp(start), pd.Timestamp(end) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1),
        regions, cats, segs, (disc[0] / 100 - 1e-9, disc[1] / 100 + 1e-9),
    )


def render_explorer(fdf: pd.DataFrame) -> None:
    query = st.text_input("Cari (nama pelanggan, produk, atau kota)", placeholder="mis. Chair, Smith, Seattle")
    view = fdf
    if query:
        q = query.strip()
        hit = (
            fdf["Customer Name"].str.contains(q, case=False, na=False, regex=False)
            | fdf["Product Name"].str.contains(q, case=False, na=False, regex=False)
            | fdf["City"].str.contains(q, case=False, na=False, regex=False)
        )
        view = fdf[hit]
    st.caption(f"Menampilkan **{len(view):,}** dari {len(fdf):,} baris terfilter. Klik judul kolom untuk mengurutkan.")
    st.dataframe(
        view.head(1000), width="stretch", hide_index=True,
        column_config={
            "Order Date": st.column_config.DateColumn("Order Date", format="YYYY-MM-DD"),
            "Ship Date": st.column_config.DateColumn("Ship Date", format="YYYY-MM-DD"),
            "Order YearMonth": None,
        },
    )
    if len(view) > 1000:
        st.caption("Pratinjau dibatasi 1.000 baris; file unduhan memuat seluruh hasil.")
    st.download_button("Unduh data terfilter (CSV)", view.to_csv(index=False).encode("utf-8"),
                       "superstore_filtered.csv", "text/csv")
    if REPORT_PATH.exists():
        with st.expander("Ringkasan proses pembersihan data"):
            rep = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Baris mentah", f"{rep['rows_raw']:,}")
            c2.metric("Baris bersih", f"{rep['rows_clean']:,}")
            c3.metric("Duplikat dibuang", rep["duplicates_removed"])
            c4.metric("Baris tidak valid dibuang", rep["rows_dropped_invalid"] + rep["rows_dropped_missing_critical"])
            st.caption(
                f"Outlier ditandai (tidak dihapus): Sales {rep['outliers_flagged']['Sales']:,}, "
                f"Profit {rep['outliers_flagged']['Profit']:,}. Rentang tanggal: {rep['date_range'][0]} s/d {rep['date_range'][1]}."
            )


def main() -> None:
    try:
        df = load_data()
    except FileNotFoundError as exc:
        st.error(str(exc))
        st.info(f"Unduh dataset dari {KAGGLE_URL}, letakkan CSV di `data/raw/`, lalu jalankan "
                "`python -m src.data_cleaning` atau muat ulang halaman.")
        st.stop()
    missing = REQUIRED_PROCESSED - set(df.columns)
    if missing:
        st.error(f"Kolom pada dataset bersih tidak lengkap: {sorted(missing)}. Jalankan ulang `python -m src.data_cleaning`.")
        st.stop()

    st.markdown(
        '<div class="hero"><h1>Superstore Analytics Dashboard</h1>'
        f'<p>Analisis penjualan, profitabilitas, dan dampak diskon. Sumber: <a href="{KAGGLE_URL}" target="_blank">Kaggle – Superstore Dataset</a></p></div>',
        unsafe_allow_html=True,
    )
    fdf = sidebar_filters(df)
    if fdf.empty:
        st.warning("Tidak ada data yang cocok dengan filter. Longgarkan filter di sidebar.")
        st.stop()

    render_kpis(da.compute_kpis(fdf))
    t_over, t_prod, t_geo, t_disc, t_data, t_ins = st.tabs(
        ["Ringkasan", "Produk", "Wilayah & Pelanggan", "Diskon & Profitabilitas", "Data Explorer", "Insight"]
    )
    with t_over:
        st.plotly_chart(viz.fig_monthly_trend(fdf), width="stretch")
        c1, c2 = st.columns(2)
        c1.plotly_chart(viz.fig_area_by_category(fdf), width="stretch")
        c2.plotly_chart(viz.fig_category_bar(fdf), width="stretch")
    with t_prod:
        st.plotly_chart(viz.fig_subcategory_profit(fdf), width="stretch")
        c1, c2 = st.columns(2)
        c1.plotly_chart(viz.fig_margin_hist(fdf), width="stretch")
        c2.plotly_chart(viz.fig_sales_profit_scatter(fdf), width="stretch")
    with t_geo:
        c1, c2 = st.columns(2)
        c1.plotly_chart(viz.fig_top_states(fdf), width="stretch")
        c2.plotly_chart(viz.fig_region_category_heatmap(fdf), width="stretch")
        st.plotly_chart(viz.fig_segment_donut(fdf), width="stretch")
    with t_disc:
        c1, c2 = st.columns(2)
        c1.plotly_chart(viz.fig_discount_box(fdf), width="stretch")
        c2.plotly_chart(viz.fig_correlation_heatmap(fdf), width="stretch")
        st.markdown("**Ringkasan per kelompok diskon**")
        band = da.summarize_by(fdf, "Discount Band").round(1)
        order = {b: i for i, b in enumerate(viz.BAND_ORDER)}
        band = band.sort_values("Discount Band", key=lambda s: s.map(order))
        st.dataframe(band, width="stretch", hide_index=True)
    with t_data:
        render_explorer(fdf)
    with t_ins:
        st.caption("Insight dihitung ulang dari data terfilter. Temuan bersifat asosiatif, bukan bukti sebab-akibat.")
        for item in da.generate_insights(fdf):
            st.markdown(f'<div class="insight"><h4>{item["title"]}</h4><p>{item["text"]}</p></div>',
                        unsafe_allow_html=True)


main()
