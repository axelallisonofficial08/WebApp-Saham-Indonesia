# Pasar Hari Ini

Web app Python sederhana untuk melihat ringkasan IHSG dan saham pilihan BEI.
Antarmuka berbahasa Indonesia, dengan pencarian, filter top naik/turun/volume, dan grafik intraday.

## Menjalankan

```powershell
py app.py
```

Buka <http://127.0.0.1:5000> di browser. Server mengambil data chart dari Yahoo Finance
dan menyimpannya dalam cache selama 60 detik. Klik kode saham untuk melihat grafik intraday,
candle 5 menit, dan volume dalam lot (1 lot = 100 saham). Feed Yahoo saat ini tidak menyediakan
orderbook atau trade tape per transaksi; tab terkait menjelaskan data yang dibutuhkan.
Koneksi internet diperlukan untuk kutipan pasar. Jika data tidak tersedia, dashboard menampilkan
angka contoh yang ditandai jelas.

Data pasar Yahoo Finance dapat terlambat dan ketersediaannya bergantung pada sumbernya;
aplikasi ini bukan layanan transaksi maupun rekomendasi investasi.
