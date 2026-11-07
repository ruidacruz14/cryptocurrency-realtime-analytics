# Cryptocurrency Real-Time Analytics (Simple Version)

Versi sederhana tanpa Kafka, Spark, Docker, atau PostgreSQL.

## Teknologi
- Python 3.11
- Streamlit dashboard
- Binance public API
- Pandas + Plotly
- SQLite (database lokal)

## Menjalankan di Windows PowerShell

1. Ekstrak ZIP ini ke folder, misalnya `C:\crypto_realtime_simple`.
2. Buka PowerShell di folder tersebut.
3. Install library:

```powershell
python -m pip install -r requirements.txt
```

4. Jalankan dashboard:

```powershell
python -m streamlit run app.py
```

5. Browser akan membuka dashboard. Jika tidak, buka alamat lokal yang ditampilkan di terminal, biasanya `http://localhost:8501`.

## Cara kerja
- Aplikasi mengambil ringkasan pasar BTC, ETH, BNB, dan SOL dari Binance.
- Dashboard meminta pembaruan setiap 5 detik.
- Setiap pengambilan data disimpan ke file SQLite `crypto_data.db`.
- Grafik harga dibentuk dari data yang sudah tersimpan.
- Riwayat dapat diunduh sebagai CSV.

## Catatan
- Perlu koneksi internet untuk mengakses Binance API.
- Jangan menutup terminal saat dashboard sedang digunakan.
- SQLite menyimpan data di folder yang sama dengan `app.py`.
- Ini adalah simulasi arsitektur streaming sederhana, bukan sistem big-data terdistribusi.
