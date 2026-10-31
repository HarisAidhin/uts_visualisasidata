"""Fungsi analisis: filter, KPI, agregasi, korelasi, insight dinamis, dan laporan EDA.

Laporan EDA dari terminal:
    python -m src.data_analysis
"""
from __future__ import annotations

import pandas as pd

from src.data_cleaning import PROCESSED_PATH, ROOT

NUMERIC_EDA_COLS = ["Sales", "Quantity", "Discount", "Profit", "Profit Margin (%)", "Ship Days"]
EDA_SUMMARY_PATH = ROOT / "data" / "processed" / "eda_summary.txt"


# ---------------------------------------------------------------- format angka
def fmt_money(value: float) -> str:
    sign = "-" if value < 0 else ""
    v = abs(value)
    if v >= 1_000_000:
        return f"{sign}${v / 1_000_000:,.2f}M"
    if v >= 1_000:
        return f"{sign}${v / 1_000:,.1f}K"
    return f"{sign}${v:,.0f}"


def fmt_pct(value: float, digits: int = 1) -> str:
    return f"{value:.{digits}f}%"


# --------------------------------------------------------------------- filter
def apply_filters(
    df: pd.DataFrame,
    start: pd.Timestamp | None = None,
    end: pd.Timestamp | None = None,
    regions: list[str] | None = None,
    categories: list[str] | None = None,
    segments: list[str] | None = None,
    discount_range: tuple[float, float] | None = None,
) -> pd.DataFrame:
    """Terapkan semua filter sidebar. Nilai None berarti filter tidak dipakai."""
    mask = pd.Series(True, index=df.index)
    if start is not None:
        mask &= df["Order Date"] >= pd.Timestamp(start)
    if end is not None:
        mask &= df["Order Date"] <= pd.Timestamp(end)
    if regions is not None:
        mask &= df["Region"].isin(regions)
    if categories is not None:
        mask &= df["Category"].isin(categories)
    if segments is not None:
        mask &= df["Segment"].isin(segments)
    if discount_range is not None:
        lo, hi = discount_range
        mask &= df["Discount"].between(lo, hi)
    return df.loc[mask]


# ------------------------------------------------------------------------ KPI
def yoy_growth(df: pd.DataFrame) -> tuple[float, int, int] | None:
    """Pertumbuhan penjualan tahun terakhir vs tahun sebelumnya pada data terfilter.

    Mengembalikan (persen, tahun_sebelumnya, tahun_terakhir) atau None bila
    data terfilter memuat kurang dari dua tahun kalender.
    """
    by_year = df.groupby("Order Year")["Sales"].sum().sort_index()
    if len(by_year) < 2 or by_year.iloc[-2] == 0:
        return None
    prev_year, last_year = int(by_year.index[-2]), int(by_year.index[-1])
    growth = (by_year.iloc[-1] / by_year.iloc[-2] - 1) * 100
    return float(growth), prev_year, last_year


def compute_kpis(df: pd.DataFrame) -> dict:
    """Hitung KPI utama dari data terfilter (semua nilai dihitung dinamis)."""
    if df.empty:
        return {}
    total_sales = float(df["Sales"].sum())
    total_profit = float(df["Profit"].sum())
    n_orders = int(df["Order ID"].nunique())
    return {
        "total_sales": total_sales,
        "total_profit": total_profit,
        "profit_margin": total_profit / total_sales * 100 if total_sales else 0.0,
        "n_orders": n_orders,
        "n_customers": int(df["Customer ID"].nunique()),
        "avg_order_value": total_sales / n_orders if n_orders else 0.0,
        "avg_discount": float(df["Discount"].mean() * 100),
        "loss_share": float(df["Is Loss"].mean() * 100),
        "yoy": yoy_growth(df),
    }


# ------------------------------------------------------------------- agregasi
def summarize_by(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """Ringkasan penjualan, profit, margin, dan jumlah pesanan per kategori kolom."""
    g = df.groupby(col, observed=True).agg(
        Sales=("Sales", "sum"),
        Profit=("Profit", "sum"),
        Orders=("Order ID", "nunique"),
        Lines=("Order ID", "size"),
        Loss_Lines=("Is Loss", "sum"),
    )
    g["Margin (%)"] = g["Profit"] / g["Sales"] * 100
    g["Loss Share (%)"] = g["Loss_Lines"] / g["Lines"] * 100
    return g.drop(columns="Loss_Lines").reset_index()


def correlation_matrix(df: pd.DataFrame) -> pd.DataFrame:
    return df[NUMERIC_EDA_COLS].corr(numeric_only=True)


# -------------------------------------------------------------------- insight
def generate_insights(df: pd.DataFrame) -> list[dict]:
    """Insight berbasis data terfilter. Bahasa dijaga asosiatif, bukan kausal."""
    if df.empty:
        return []
    out: list[dict] = []
    total_sales = df["Sales"].sum()

    # 1. Kategori
    cat = summarize_by(df, "Category").sort_values("Sales", ascending=False)
    top = cat.iloc[0]
    text = (
        f"Kategori {top['Category']} menyumbang {fmt_money(top['Sales'])} "
        f"({top['Sales'] / total_sales * 100:.1f}% penjualan) dengan margin {fmt_pct(top['Margin (%)'])}."
    )
    if len(cat) > 1:
        low = cat.sort_values("Margin (%)").iloc[0]
        text += f" Margin terendah ada pada {low['Category']} ({fmt_pct(low['Margin (%)'])})."
    out.append({"title": "Kontribusi dan margin per kategori", "text": text})

    # 2. Sub-kategori
    sub = summarize_by(df, "Sub-Category")
    best = sub.sort_values("Profit", ascending=False).iloc[0]
    losers = sub[sub["Profit"] < 0].sort_values("Profit")
    text = f"Sub-kategori paling menguntungkan: {best['Sub-Category']} ({fmt_money(best['Profit'])})."
    if len(losers):
        names = ", ".join(losers["Sub-Category"].head(3))
        text += (
            f" {len(losers)} sub-kategori mencatat profit negatif, terbesar: {names} "
            f"(total {fmt_money(losers['Profit'].sum())})."
        )
    else:
        text += " Tidak ada sub-kategori dengan profit negatif pada filter ini."
    out.append({"title": "Sub-kategori terbaik dan yang merugi", "text": text})

    # 3. Diskon (asosiasi, bukan sebab-akibat)
    hi, lo = df[df["Discount"] > 0.20], df[df["Discount"] <= 0.20]
    if len(hi) and len(lo):
        out.append({
            "title": "Diskon tinggi dan profitabilitas",
            "text": (
                f"Baris transaksi dengan diskon >20% ({len(hi):,} baris) memiliki margin agregat "
                f"{fmt_pct(hi['Profit'].sum() / hi['Sales'].sum() * 100)} dan {fmt_pct(hi['Is Loss'].mean() * 100)} "
                f"di antaranya merugi, dibanding margin {fmt_pct(lo['Profit'].sum() / lo['Sales'].sum() * 100)} "
                f"dan {fmt_pct(lo['Is Loss'].mean() * 100)} merugi pada diskon <=20%. "
                "Ini asosiasi pada data; faktor lain (jenis produk, wilayah) tidak dikendalikan."
            ),
        })

    # 4. Wilayah
    reg = summarize_by(df, "Region")
    if len(reg) > 1:
        top_s = reg.sort_values("Sales", ascending=False).iloc[0]
        top_m = reg.sort_values("Margin (%)", ascending=False).iloc[0]
        low_m = reg.sort_values("Margin (%)").iloc[0]
        out.append({
            "title": "Perbedaan kinerja antarwilayah",
            "text": (
                f"Penjualan terbesar dari wilayah {top_s['Region']} ({fmt_money(top_s['Sales'])}). "
                f"Margin tertinggi di {top_m['Region']} ({fmt_pct(top_m['Margin (%)'])}) dan "
                f"terendah di {low_m['Region']} ({fmt_pct(low_m['Margin (%)'])})."
            ),
        })

    # 5. Musiman (hanya jika data mencakup >= 12 bulan)
    if df["Order YearMonth"].nunique() >= 12:
        by_month = df.groupby("Order Month")["Sales"].sum()
        m = int(by_month.idxmax())
        names = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
        out.append({
            "title": "Pola musiman",
            "text": (
                f"Bulan {names[m - 1]} memiliki akumulasi penjualan tertinggi "
                f"({fmt_money(by_month.max())}, {by_month.max() / total_sales * 100:.1f}% dari total pada filter ini)."
            ),
        })

    # 6. Segmen
    seg = summarize_by(df, "Segment").sort_values("Sales", ascending=False)
    if len(seg) > 1:
        s = seg.iloc[0]
        out.append({
            "title": "Komposisi segmen pelanggan",
            "text": (
                f"Segmen {s['Segment']} mendominasi dengan {s['Sales'] / total_sales * 100:.1f}% penjualan "
                f"dan margin {fmt_pct(s['Margin (%)'])}."
            ),
        })
    return out


# ------------------------------------------------------------- laporan EDA CLI
def build_eda_report(df: pd.DataFrame) -> str:
    kpi = compute_kpis(df)
    lines = [
        "=== EDA DATASET SUPERSTORE (setelah cleaning) ===",
        f"Baris x kolom : {df.shape[0]:,} x {df.shape[1]}",
        f"Rentang tanggal: {df['Order Date'].min():%Y-%m-%d} s/d {df['Order Date'].max():%Y-%m-%d}",
        "",
        "--- Statistik deskriptif (numerik) ---",
        df[NUMERIC_EDA_COLS].describe().round(2).to_string(),
        "",
        "--- Skewness (kemiringan distribusi) ---",
        df[NUMERIC_EDA_COLS].skew().round(2).to_string(),
        "",
        "--- Korelasi Pearson ---",
        correlation_matrix(df).round(2).to_string(),
        "",
    ]
    for col in ["Category", "Segment", "Region", "Ship Mode", "Discount Band"]:
        lines += [f"--- Frekuensi {col} ---", df[col].value_counts().to_string(), ""]
    lines += [
        "--- KPI keseluruhan ---",
        f"Total penjualan: {fmt_money(kpi['total_sales'])} | Total profit: {fmt_money(kpi['total_profit'])} "
        f"| Margin: {fmt_pct(kpi['profit_margin'])}",
        "",
        "--- Insight otomatis ---",
    ]
    lines += [f"* {i['title']}: {i['text']}" for i in generate_insights(df)]
    return "\n".join(lines)


def main() -> None:
    if not PROCESSED_PATH.exists():
        raise SystemExit("Jalankan dulu: python -m src.data_cleaning")
    df = pd.read_csv(
        PROCESSED_PATH, dtype={"Postal Code": "string"},
        parse_dates=["Order Date", "Ship Date", "Order YearMonth"],
    )
    report = build_eda_report(df)
    EDA_SUMMARY_PATH.write_text(report, encoding="utf-8")
    print(report)
    print(f"\nTersimpan: {EDA_SUMMARY_PATH}")


if __name__ == "__main__":
    main()
