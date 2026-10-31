"""Fungsi pembuat grafik Plotly. Semua fungsi menerima DataFrame terfilter dan mengembalikan Figure."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.data_analysis import correlation_matrix, summarize_by

NAVY, TEAL, CORAL, GOLD, GREY = "#1F4E79", "#2A9D8F", "#E76F51", "#E9C46A", "#8A94A6"
CATEGORY_COLORS = {"Furniture": NAVY, "Office Supplies": TEAL, "Technology": CORAL}
SEGMENT_COLORS = [NAVY, TEAL, GOLD]
DIVERGING = [[0.0, CORAL], [0.5, "#F7F7F7"], [1.0, TEAL]]
BAND_ORDER = ["0%", "1-10%", "11-20%", "21-30%", "31-50%", ">50%"]


def _style(fig: go.Figure, title: str, height: int = 380) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, x=0.01, font=dict(size=16, color="#1B2430")),
        template="plotly_white",
        height=height,
        margin=dict(l=10, r=10, t=56, b=10),
        font=dict(family="Inter, Segoe UI, sans-serif", size=12, color="#1B2430"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title_text=""),
        hoverlabel=dict(bgcolor="white", font_size=12),
    )
    return fig


def fig_monthly_trend(df: pd.DataFrame) -> go.Figure:
    m = df.groupby("Order YearMonth").agg(Sales=("Sales", "sum"), Profit=("Profit", "sum")).reset_index()
    long = m.melt("Order YearMonth", var_name="Metrik", value_name="USD")
    fig = px.line(
        long, x="Order YearMonth", y="USD", color="Metrik",
        color_discrete_map={"Sales": NAVY, "Profit": TEAL}, markers=True,
    )
    fig.update_traces(hovertemplate="%{x|%b %Y}<br>%{y:$,.0f}<extra>%{fullData.name}</extra>")
    fig.update_xaxes(title="Bulan pesanan")
    fig.update_yaxes(title="USD", tickprefix="$", tickformat=",.0f")
    return _style(fig, "Tren penjualan dan profit bulanan")


def fig_area_by_category(df: pd.DataFrame) -> go.Figure:
    m = df.groupby(["Order YearMonth", "Category"])["Sales"].sum().reset_index()
    fig = px.area(m, x="Order YearMonth", y="Sales", color="Category", color_discrete_map=CATEGORY_COLORS)
    fig.update_traces(hovertemplate="%{x|%b %Y}<br>%{y:$,.0f}<extra>%{fullData.name}</extra>")
    fig.update_xaxes(title="Bulan pesanan")
    fig.update_yaxes(title="Penjualan (USD, ditumpuk)", tickprefix="$", tickformat=",.0f")
    return _style(fig, "Komposisi penjualan bulanan per kategori")


def fig_category_bar(df: pd.DataFrame) -> go.Figure:
    c = summarize_by(df, "Category").melt(
        id_vars="Category", value_vars=["Sales", "Profit"], var_name="Metrik", value_name="USD"
    )
    fig = px.bar(c, x="Category", y="USD", color="Metrik", barmode="group",
                 color_discrete_map={"Sales": NAVY, "Profit": TEAL})
    fig.update_traces(hovertemplate="%{x}<br>%{y:$,.0f}<extra>%{fullData.name}</extra>")
    fig.update_xaxes(title="Kategori")
    fig.update_yaxes(title="USD", tickprefix="$", tickformat=",.0f")
    return _style(fig, "Penjualan vs profit per kategori")


def fig_subcategory_profit(df: pd.DataFrame) -> go.Figure:
    s = summarize_by(df, "Sub-Category").sort_values("Profit")
    s["Arah"] = np.where(s["Profit"] >= 0, "Profit", "Rugi")
    fig = px.bar(
        s, x="Profit", y="Sub-Category", orientation="h", color="Arah",
        color_discrete_map={"Profit": TEAL, "Rugi": CORAL},
        custom_data=["Sales", "Margin (%)"],
    )
    fig.update_traces(hovertemplate=(
        "%{y}<br>Profit: %{x:$,.0f}<br>Penjualan: %{customdata[0]:$,.0f}"
        "<br>Margin: %{customdata[1]:.1f}%<extra></extra>"))
    fig.update_xaxes(title="Total profit (USD)", tickprefix="$", tickformat=",.0f")
    fig.update_yaxes(title="")
    return _style(fig, "Profit per sub-kategori", height=max(380, 26 * len(s) + 120))


def fig_margin_hist(df: pd.DataFrame, limit: float = 100.0) -> go.Figure:
    m = df["Profit Margin (%)"]
    shown = m[m.between(-limit, limit)]
    pct_shown = len(shown) / len(m) * 100 if len(m) else 0
    fig = px.histogram(shown, x="Profit Margin (%)", nbins=40, color_discrete_sequence=[NAVY])
    fig.update_traces(hovertemplate="Margin %{x}%<br>%{y} baris<extra></extra>")
    fig.add_vline(x=0, line_dash="dash", line_color=CORAL)
    fig.update_xaxes(title="Margin profit per baris transaksi (%)")
    fig.update_yaxes(title="Jumlah baris transaksi")
    return _style(fig, f"Distribusi margin profit (menampilkan {pct_shown:.1f}% data, rentang ±{limit:.0f}%)")


def fig_sales_profit_scatter(df: pd.DataFrame) -> go.Figure:
    fig = px.scatter(
        df, x="Sales", y="Profit", color="Category", color_discrete_map=CATEGORY_COLORS,
        opacity=0.55, hover_data={"Sub-Category": True, "Discount": ":.0%", "Sales": ":$,.0f", "Profit": ":$,.0f"},
    )
    fig.add_hline(y=0, line_dash="dash", line_color=GREY)
    fig.update_xaxes(title="Penjualan per baris (USD)", tickprefix="$")
    fig.update_yaxes(title="Profit per baris (USD)", tickprefix="$")
    return _style(fig, "Hubungan penjualan dan profit per baris transaksi")


def fig_top_states(df: pd.DataFrame, n: int = 10) -> go.Figure:
    s = summarize_by(df, "State").nlargest(n, "Sales").sort_values("Sales")
    fig = px.bar(s, x="Sales", y="State", orientation="h", color="Profit",
                 color_continuous_scale=DIVERGING, color_continuous_midpoint=0,
                 custom_data=["Profit", "Margin (%)"])
    fig.update_traces(hovertemplate=(
        "%{y}<br>Penjualan: %{x:$,.0f}<br>Profit: %{customdata[0]:$,.0f}"
        "<br>Margin: %{customdata[1]:.1f}%<extra></extra>"))
    fig.update_xaxes(title="Penjualan (USD)", tickprefix="$", tickformat=",.0f")
    fig.update_yaxes(title="")
    fig.update_coloraxes(colorbar_title="Profit")
    return _style(fig, f"{min(n, len(s))} negara bagian dengan penjualan tertinggi (warna = profit)", height=420)


def fig_region_category_heatmap(df: pd.DataFrame) -> go.Figure:
    p = df.groupby(["Region", "Category"]).agg(S=("Sales", "sum"), P=("Profit", "sum")).reset_index()
    p["Margin"] = p["P"] / p["S"] * 100
    pivot = p.pivot(index="Region", columns="Category", values="Margin")
    fig = px.imshow(pivot, text_auto=".1f", aspect="auto", color_continuous_scale=DIVERGING,
                    color_continuous_midpoint=0, labels=dict(color="Margin (%)"))
    fig.update_xaxes(title="Kategori")
    fig.update_yaxes(title="Wilayah")
    return _style(fig, "Margin profit (%) per wilayah dan kategori", height=420)


def fig_segment_donut(df: pd.DataFrame) -> go.Figure:
    s = summarize_by(df, "Segment")
    fig = go.Figure(go.Pie(
        labels=s["Segment"], values=s["Sales"], hole=0.55, marker=dict(colors=SEGMENT_COLORS),
        hovertemplate="%{label}<br>%{value:$,.0f} (%{percent})<extra></extra>", sort=False,
    ))
    return _style(fig, "Proporsi penjualan per segmen pelanggan", height=420)


def fig_discount_box(df: pd.DataFrame) -> go.Figure:
    present = [b for b in BAND_ORDER if b in set(df["Discount Band"].dropna())]
    fig = px.box(df, x="Discount Band", y="Profit Margin (%)", category_orders={"Discount Band": present},
                 color_discrete_sequence=[NAVY], points="outliers")
    fig.add_hline(y=0, line_dash="dash", line_color=CORAL)
    fig.update_xaxes(title="Kelompok diskon")
    fig.update_yaxes(title="Margin profit (%)")
    return _style(fig, "Sebaran margin profit menurut kelompok diskon")


def fig_correlation_heatmap(df: pd.DataFrame) -> go.Figure:
    corr = correlation_matrix(df)
    fig = px.imshow(corr, text_auto=".2f", zmin=-1, zmax=1, aspect="auto",
                    color_continuous_scale=DIVERGING, labels=dict(color="r"))
    return _style(fig, "Korelasi Pearson antarvariabel numerik", height=420)
