# WebApp Saham Indonesia — Pasar Hari Ini

Aplikasi web Python sederhana untuk memantau ringkasan IHSG dan saham pilihan Bursa Efek Indonesia. Data harga diambil dari Yahoo Finance.

Antarmuka berbahasa Indonesia menyediakan pencarian saham, filter saham top naik/turun/volume, grafik intraday, candle 5 menit, dan volume dalam lot (1 lot = 100 saham). Klik kode saham untuk melihat rincian.

## Menjalankan

```powershell
py app.py
```

Buka <http://127.0.0.1:5000> di browser. Server menyimpan data dalam cache selama 60 detik. Koneksi internet diperlukan untuk mengambil kutipan pasar. Jika data tidak tersedia, dashboard menampilkan angka contoh yang ditandai jelas.

Yahoo Finance tidak menyediakan orderbook atau trade tape per transaksi; tab terkait menjelaskan data yang dibutuhkan untuk fitur tersebut. Data pasar dapat terlambat dan ketersediaannya bergantung pada sumbernya. Aplikasi ini bukan layanan transaksi maupun rekomendasi investasi.
