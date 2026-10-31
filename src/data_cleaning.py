"""Tahap preprocessing dataset Superstore (Kaggle: vivek468/superstore-dataset-final).

Jalankan dari root proyek:
    python -m src.data_cleaning
    python -m src.data_cleaning --raw "data/raw/Sample - Superstore.csv"
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_PATH = ROOT / "data" / "processed" / "cleaned_dataset.csv"
REPORT_PATH = ROOT / "data" / "processed" / "cleaning_report.json"

REQUIRED_COLUMNS = [
    "Order ID", "Order Date", "Ship Date", "Ship Mode", "Customer ID",
    "Customer Name", "Segment", "Country", "City", "State", "Postal Code",
    "Region", "Product ID", "Category", "Sub-Category", "Product Name",
    "Sales", "Quantity", "Discount", "Profit",
]
CRITICAL_COLUMNS = [
    "Order ID", "Order Date", "Ship Date", "Customer ID", "Segment", "Region",
    "State", "Category", "Sub-Category", "Sales", "Quantity", "Discount", "Profit",
]
DISCOUNT_BINS = [-0.001, 0.0, 0.10, 0.20, 0.30, 0.50, 1.0]
DISCOUNT_LABELS = ["0%", "1-10%", "11-20%", "21-30%", "31-50%", ">50%"]


def find_raw_file(path: str | Path | None = None) -> Path:
    """Cari file CSV mentah; jika path tidak diberikan, ambil CSV pertama di data/raw."""
    if path:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"File tidak ditemukan: {p}")
        return p
    candidates = sorted(RAW_DIR.glob("*.csv"))
    if not candidates:
        raise FileNotFoundError(
            f"Tidak ada file CSV di {RAW_DIR}. Unduh dataset dari Kaggle dan "
            "letakkan di folder data/raw/."
        )
    return candidates[0]


def read_csv_flexible(path: Path) -> pd.DataFrame:
    """Baca CSV dengan fallback encoding (file Superstore asli umumnya bukan UTF-8)."""
    last_error: Exception | None = None
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError as exc:
            last_error = exc
    raise ValueError(f"Gagal membaca {path}: {last_error}")


def _parse_dates(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series, format="%m/%d/%Y", errors="coerce")
    if parsed.isna().any():
        parsed = pd.to_datetime(series, format="mixed", errors="coerce")
    return parsed


def _iqr_flag(series: pd.Series) -> pd.Series:
    q1, q3 = series.quantile(0.25), series.quantile(0.75)
    iqr = q3 - q1
    return (series < q1 - 1.5 * iqr) | (series > q3 + 1.5 * iqr)


def clean(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Bersihkan data dan kembalikan (dataframe bersih, laporan proses)."""
    df = raw.copy()
    df.columns = [str(c).strip() for c in df.columns]

    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Kolom wajib tidak ditemukan: {missing_cols}")

    report: dict = {
        "rows_raw": int(len(df)),
        "cols_raw": int(df.shape[1]),
        "dtypes_raw": {c: str(t) for c, t in df.dtypes.items()},
        "missing_raw": {c: int(n) for c, n in df.isna().sum().items() if n > 0},
    }

    # 1. Rapikan teks (spasi berlebih dapat memecah satu kategori menjadi dua)
    for col in df.select_dtypes(include=["object", "string"]).columns:
        df[col] = df[col].astype("string").str.strip()

    # 2. Konversi tipe data
    df["Order Date"] = _parse_dates(df["Order Date"])
    df["Ship Date"] = _parse_dates(df["Ship Date"])
    for col in ["Sales", "Quantity", "Discount", "Profit"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    postal = pd.to_numeric(df["Postal Code"], errors="coerce").round().astype("Int64")
    df["Postal Code"] = postal.astype("string").str.zfill(5)  # kode pos AS 5 digit

    # 3. Duplikat (Row ID unik per baris, jadi diabaikan saat mendeteksi duplikat)
    subset = [c for c in df.columns if c != "Row ID"]
    report["duplicates_removed"] = int(df.duplicated(subset=subset).sum())
    df = df.drop_duplicates(subset=subset)

    # 4. Missing value pada kolom kritis: baris tidak bisa dianalisis tanpa nilai ini
    n_before = len(df)
    df = df.dropna(subset=CRITICAL_COLUMNS)
    report["rows_dropped_missing_critical"] = int(n_before - len(df))

    # 5. Inkonsistensi logis (secara bisnis tidak mungkin terjadi)
    invalid = (
        (df["Ship Date"] < df["Order Date"])
        | (df["Sales"] <= 0)
        | (df["Quantity"] <= 0)
        | (~df["Discount"].between(0, 1))
    )
    report["rows_dropped_invalid"] = int(invalid.sum())
    df = df.loc[~invalid].copy()

    # 6. Fitur turunan
    df["Order Year"] = df["Order Date"].dt.year
    df["Order Month"] = df["Order Date"].dt.month
    df["Order YearMonth"] = df["Order Date"].dt.to_period("M").dt.to_timestamp()
    df["Ship Days"] = (df["Ship Date"] - df["Order Date"]).dt.days
    df["Profit Margin (%)"] = df["Profit"] / df["Sales"] * 100
    df["Is Loss"] = df["Profit"] < 0
    df["Discount Band"] = pd.cut(
        df["Discount"], bins=DISCOUNT_BINS, labels=DISCOUNT_LABELS
    ).astype("string")

    # 7. Outlier: hanya DITANDAI (tidak dihapus). Transaksi besar atau rugi besar
    #    adalah data bisnis yang valid, bukan kesalahan input.
    df["Sales Outlier"] = _iqr_flag(df["Sales"])
    df["Profit Outlier"] = _iqr_flag(df["Profit"])
    report["outliers_flagged"] = {
        "Sales": int(df["Sales Outlier"].sum()),
        "Profit": int(df["Profit Outlier"].sum()),
    }

    df = df.sort_values("Order Date").reset_index(drop=True)
    report["rows_clean"] = int(len(df))
    report["cols_clean"] = int(df.shape[1])
    report["date_range"] = [
        df["Order Date"].min().strftime("%Y-%m-%d"),
        df["Order Date"].max().strftime("%Y-%m-%d"),
    ]
    report["categorical_unique"] = {
        c: int(df[c].nunique())
        for c in ["Ship Mode", "Segment", "Region", "State", "Category", "Sub-Category"]
    }
    return df, report


def run_cleaning(raw_path: str | Path | None = None) -> pd.DataFrame:
    """Pipeline lengkap: baca CSV mentah, bersihkan, simpan CSV + laporan JSON."""
    path = find_raw_file(raw_path)
    df, report = clean(read_csv_flexible(path))
    report["raw_file"] = path.name
    PROCESSED_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(PROCESSED_PATH, index=False)
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Preprocessing dataset Superstore")
    parser.add_argument("--raw", default=None, help="Path CSV mentah (opsional)")
    args = parser.parse_args()
    df = run_cleaning(args.raw)
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\nTersimpan: {PROCESSED_PATH} ({len(df):,} baris)")


if __name__ == "__main__":
    main()
