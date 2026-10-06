# WebApp Saham Indonesia — Pasar Hari Ini

Aplikasi web Python sederhana untuk memantau ringkasan IHSG dan saham pilihan Bursa Efek Indonesia. Data harga diambil dari Yahoo Finance.

Antarmuka berbahasa Indonesia menyediakan pencarian saham, filter saham top naik/turun/volume, grafik intraday, candle 5 menit, dan volume dalam lot (1 lot = 100 saham). Klik kode saham untuk melihat rincian.

Menu **Dompet demo** menyediakan modal awal Rp 100 juta untuk simulasi beli/jual beberapa saham. Posisi, saldo, dan riwayat transaksi disimpan lokal dalam `portfolio_demo.sqlite3`; transaksi memakai kutipan harga nyata terakhir yang diterima aplikasi. Form beli bisa menghitung lot maksimal berdasarkan saldo tunai, dan tombol jual semua melikuidasi seluruh posisi secara atomik. Jika kutipan pasar tidak tersedia untuk semua posisi, jual semua dibatalkan.

## Menjalankan

```powershell
py app.py
```

Buka <http://127.0.0.1:5000> di komputer. Server mendengarkan di semua antarmuka jaringan; untuk membatasi akses smartphone ke subnet lokal, jalankan aturan firewall berikut sekali di PowerShell **Run as administrator** (sesuaikan `-Profile` dengan profil Wi-Fi Windows):

```powershell
New-NetFirewallRule -DisplayName "Pasar Hari Ini LAN port 5000" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 5000 -RemoteAddress LocalSubnet -Profile Public
```

Lalu buka `http://ALAMAT-IP-KOMPUTER:5000` di smartphone yang terhubung ke Wi-Fi yang sama (alamat komputer dapat dilihat dengan `ipconfig`). Jangan meneruskan port ini dari router ke internet publik. Server menyimpan data dalam cache selama 60 detik. Koneksi internet diperlukan untuk mengambil kutipan pasar. Jika penyedia harga tidak dapat diakses, harga dan grafik ditampilkan sebagai tidak tersedia; aplikasi tidak mengganti kutipan dengan angka contoh dan transaksi demo dinonaktifkan sampai harga nyata tersedia.

Yahoo Finance tidak menyediakan orderbook atau trade tape per transaksi; tab terkait menjelaskan data yang dibutuhkan untuk fitur tersebut. Data pasar dapat terlambat dan ketersediaannya bergantung pada sumbernya. Aplikasi ini bukan layanan transaksi maupun rekomendasi investasi.

## GitHub Pages

GitHub Pages menerbitkan situs statis; ia tidak menjalankan server Python. Workflow `.github/workflows/deploy-pages.yml` membangun halaman statis dari UI yang sama dan memperbarui snapshot pasar dengan GitHub Actions. Dompet Pages disimpan di `localStorage` browser, sehingga dompet di ponsel dan komputer terpisah dan tidak memakai database dompet server lokal.

Di repo GitHub, buka **Settings → Pages** lalu pilih **GitHub Actions** pada bagian **Build and deployment → Source**. Setelah perubahan pada branch `main` di-push, workflow akan membangun dan menerbitkan situs di <https://axelallisonofficial08.github.io/WebApp-Saham-Indonesia/>.

Actions mengambil data Yahoo Finance tiap 5 menit pada hari kerja selama jam bursa Indonesia, lalu mengambil snapshot penutupan pada 16.10 WIB. Actions tidak mendukung jadwal per detik atau per menit; jadwal minimalnya 5 menit dan dapat terlambat karena antrean GitHub. Harga Yahoo Finance sendiri tertunda sekitar 10 menit. Jika feed gagal atau tidak berubah setelah bursa tutup, situs mempertahankan kutipan valid terakhir, bukan menggantinya dengan nol. Snapshot terakhir disimpan pada branch `market-data` yang hanya menyimpan satu revisi terbaru.
