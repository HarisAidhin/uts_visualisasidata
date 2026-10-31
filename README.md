# Superstore Analytics Dashboard

Dashboard analitik interaktif (Streamlit + Plotly) untuk menganalisis penjualan, profitabilitas, dan dampak diskon pada dataset Superstore dari Kaggle.

# NAMA
Haris Aidhin Ramadhan

## 1. Project Overview
Aplikasi membaca data transaksi Superstore, membersihkannya lewat pipeline Pandas, lalu menyajikan KPI, 10 visualisasi, filter dinamis, data explorer, dan insight yang dihitung ulang mengikuti filter.

## 2. Background
Perusahaan ritel perlu tahu kategori, wilayah, dan segmen mana yang menghasilkan profit, serta apakah diskon besar berasosiasi dengan penurunan margin. Dashboard ini mengubah data transaksi mentah menjadi gambaran yang bisa dieksplorasi langsung.

## 3. Objectives
1. Membersihkan data transaksi agar konsisten dan siap analisis.
2. Mengidentifikasi tren, distribusi, korelasi, dan anomali.
3. Menyajikan hasilnya dalam dashboard interaktif.
4. Menghasilkan insight berbasis data aktual (tanpa klaim sebab-akibat).
5. Mempublikasikan kode di GitHub dan dashboard di Streamlit Community Cloud.

## 4. Dataset Source
- Kaggle: https://www.kaggle.com/datasets/vivek468/superstore-dataset-final
- Periksa lisensi pada halaman dataset sebelum meng-commit file mentah ke repositori publik. Jika lisensi tidak mengizinkan distribusi ulang, jangan commit `data/raw/` dan cukup beri instruksi unduh.

## 5. Data Description
Data transaksi tingkat baris pesanan: tanggal pesan/kirim, mode pengiriman, pelanggan dan segmen, lokasi (kota, negara bagian, wilayah), produk (kategori, sub-kategori), serta `Sales`, `Quantity`, `Discount`, `Profit`.
> Isi jumlah baris/kolom aktual dari `data/processed/cleaning_report.json` setelah menjalankan cleaning.

## 6. Data Cleaning Process (`src/data_cleaning.py`)
| Langkah | Alasan |
|---|---|
| Baca CSV dengan fallback encoding | File asli umumnya tidak UTF-8 |
| Trim spasi pada teks | Mencegah satu kategori terpecah dua |
| Konversi tanggal, numerik, kode pos 5 digit | Tipe data benar; kode pos tidak kehilangan nol di depan |
| Hapus duplikat (mengabaikan Row ID) | Baris identik menggandakan penjualan |
| Hapus baris kosong pada kolom kritis | Tidak dapat dianalisis |
| Hapus baris tidak logis (kirim sebelum pesan, Sales/Quantity ≤ 0, Discount di luar 0–1) | Mustahil secara bisnis |
| Outlier hanya **ditandai** (IQR), tidak dihapus | Transaksi besar/rugi besar adalah data bisnis valid |
| Fitur turunan: tahun, bulan, lama kirim, margin, penanda rugi, kelompok diskon | Mendukung analisis |

Hasil: `data/processed/cleaned_dataset.csv` dan `cleaning_report.json`.

## 7. Exploratory Data Analysis (`src/data_analysis.py`, `notebooks/`)
`python -m src.data_analysis` menghasilkan statistik deskriptif, skewness, korelasi, frekuensi kategori, KPI, dan insight otomatis ke `data/processed/eda_summary.txt`.

## 8. Dashboard Features
- 6 KPI card (penjualan, profit, nilai pesanan rata-rata, pelanggan, diskon rata-rata, pertumbuhan tahunan).
- Visualisasi: line, area, bar berkelompok, bar horizontal, histogram, scatter, bar berwarna, heatmap (2 jenis), donut, box plot.
- Filter: rentang tanggal, wilayah, kategori, segmen, rentang diskon; semuanya memengaruhi KPI, grafik, tabel, dan insight.
- Data Explorer: pencarian, sortir, jumlah record, unduh CSV hasil filter.
- Tab Insight dinamis.

## 9. Key Insights
> Isi 3–5 temuan **setelah** menjalankan analisis pada data asli (lihat tab Insight atau `eda_summary.txt`). Jangan menyalin angka sebelum dihitung.

## 10. Technology Stack
Python, Pandas, NumPy, Plotly, Streamlit, GitHub, Streamlit Community Cloud.

## 11. Installation Guide
```bash
git clone <URL-REPO-ANDA>
cd data-analytics-dashboard
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 12. Local Execution Guide
```bash
# 1. letakkan CSV Kaggle di data/raw/
python -m src.data_cleaning
python -m src.data_analysis
streamlit run app.py
```

## 13. Deployment (Streamlit Community Cloud)
1. Pastikan `data/processed/cleaned_dataset.csv` ikut di-commit.
2. Push repositori ke GitHub (publik).
3. Buka https://share.streamlit.io, login dengan GitHub, klik **Create app**.
4. Pilih repositori, branch `main`, file utama `app.py`, lalu **Deploy**.

## 14. Deployment URL
https://utsvisualisasidata-rybykfntujkapk7uy3nl5s.streamlit.app/

## 15. GitHub Repository URL
https://github.com/HarisAidhin/uts_visualisasidata/
