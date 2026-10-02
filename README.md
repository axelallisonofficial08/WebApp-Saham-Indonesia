# WebApp Saham Indonesia — Pasar Hari Ini

Aplikasi web Python sederhana untuk memantau ringkasan IHSG dan saham pilihan Bursa Efek Indonesia. Data harga diambil dari Yahoo Finance.

Antarmuka berbahasa Indonesia menyediakan pencarian saham, filter saham top naik/turun/volume, grafik intraday, candle 5 menit, dan volume dalam lot (1 lot = 100 saham). Klik kode saham untuk melihat rincian.

Menu **Dompet demo** menyediakan modal awal Rp 100 juta untuk simulasi beli/jual beberapa saham. Posisi, saldo, dan riwayat transaksi disimpan lokal dalam `portfolio_demo.sqlite3`; transaksi memakai kutipan harga nyata terakhir yang diterima aplikasi. Jika harga pasar tidak tersedia, transaksi dinonaktifkan.

## Menjalankan

```powershell
py app.py
```

Buka <http://127.0.0.1:5000> di browser. Server menyimpan data dalam cache selama 60 detik. Koneksi internet diperlukan untuk mengambil kutipan pasar. Jika penyedia harga tidak dapat diakses, harga dan grafik ditampilkan sebagai tidak tersedia; aplikasi tidak mengganti kutipan dengan angka contoh dan transaksi demo dinonaktifkan sampai harga nyata tersedia.

Yahoo Finance tidak menyediakan orderbook atau trade tape per transaksi; tab terkait menjelaskan data yang dibutuhkan untuk fitur tersebut. Data pasar dapat terlambat dan ketersediaannya bergantung pada sumbernya. Aplikasi ini bukan layanan transaksi maupun rekomendasi investasi.
