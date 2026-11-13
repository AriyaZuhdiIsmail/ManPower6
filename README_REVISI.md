# Monitoring SDM — integrasi SOTK Master terbaru

## Isi paket

- `index.html`, `app.js`, `features.js`, `styles.css`: aplikasi Monitoring SDM.
- `data.js`: preload SOTK yang dibangun dari master terbaru.
- `source_data/SOTK_MASTER_FINAL.xlsx`: sumber SOTK aktif yang dipakai untuk build.
- `source_data/REFERENSI_FORMASI_CABANG.xlsx`: pembanding formasi cabang (400 outlet).
- `tools/build_data.py`: build preload sekaligus validasi struktur dan referensi formasi.
- `lib/position-type-summary.js`: helper pengelompokan Position Type yang dapat diuji terpisah.
- `tools/test_position_type_summary.js`: pengujian helper Position Type.
- `QA_REPORT_SOTK_MONITORING_SDM.md`: ringkasan perubahan dan pengujian.

## Menjalankan website

Jalankan dari folder proyek menggunakan server lokal, misalnya:

```cmd
python -m http.server 8000
```

Buka `http://localhost:8000` pada browser. Jangan membuka halaman melalui preview file yang memblokir pembacaan aset lokal atau worker.

## Membuat ulang `data.js` setelah SOTK berubah

1. Simpan workbook terbaru sebagai `source_data/SOTK_MASTER_FINAL.xlsx`.
2. Perbarui `source_data/REFERENSI_FORMASI_CABANG.xlsx` bila file referensi resmi terbaru tersedia.
3. Dari folder utama proyek, jalankan:

```cmd
python tools\build_data.py source_data\SOTK_MASTER_FINAL.xlsx data.js source_data\REFERENSI_FORMASI_CABANG.xlsx
```

Script memvalidasi delapan sheet, kolom wajib, kunci formasi, unit master, kelas cabang, kelas UPC/UPS, serta relasi cabang induk. Bila referensi diberikan, script juga membandingkan kebutuhan formasi per outlet dan jabatan. Build dihentikan bila validasi gagal.

`data.js` dibentuk dari workbook yang diberikan; workbook sumber tidak ditimpa. Jangan mengedit `data.js` secara manual.

## Perubahan utama versi ini

### SOTK dan klasifikasi outlet

- Preload dibangun ulang dari `SOTK_MASTER_FINAL.xlsx`.
- `KELAS CABANG` A/B tetap berlaku untuk seluruh jenis outlet.
- `KELAS UPC/UPS` U1–U4 dibaca dari `UNIT_MASTER_CABANG` sebagai sumber utama.
- Filter `Kelas UPC/UPS` tersedia pada seluruh panel level Cabang/Outlet yang memiliki filter outlet. Memilih U1–U4 otomatis membatasi jenis outlet ke UPC/UPS; pilihan ini tidak menggantikan filter Kelas Cabang A/B.
- Kelas UPC/UPS juga ditampilkan pada SOTK Explorer, Snapshot Outlet, dan detail outlet terpilih.
- Upload SOTK melalui Data & Set Up memeriksa seluruh delapan sheet serta konsistensi kode outlet, kelas, dan relasi induk sebelum master diterapkan.


### Filter UPC/UPS dan cache navigasi

- Seluruh halaman yang memakai panel filter level Cabang/Outlet menyediakan dropdown `Kelas UPC/UPS` (U1–U4), termasuk Ringkasan SDM, Monitoring Karyawan, Monitoring Struktur Jabatan, Monitoring Non-Definitif, Gap Formasi, Proyeksi Pensiun, SOTK Explorer, Snapshot Outlet, Vacancy Priority, Grade Mismatch, dan Definitive Placement.
- Memilih U1–U4 otomatis menyaring jenis outlet menjadi `UPC/UPS`. Mengubah jenis outlet ke CP/CPS, BRI Unit, atau co-location menghapus filter kelas UPC/UPS agar tidak menghasilkan kombinasi filter yang membingungkan.
- Penyaringan kelas diterapkan sebelum opsi lokasi bertingkat dibentuk. Karena itu, setelah U1/U2/U3/U4 dipilih, daftar Outlet yang dapat dipilih dan hasil tabel ikut terbatas pada kelas tersebut, bukan hanya hasil akhir tabel.
- Saat kelas diubah, pilihan Outlet lama yang tidak termasuk kelas terpilih otomatis dibersihkan agar tidak membuat hasil tampak kosong akibat pilihan outlet yang bertentangan.
- Navigasi halaman menggunakan cache DOM dalam memori browser. Filter, isi pencarian, hasil tabel, pagination, detail Snapshot Outlet yang sedang terbuka, posisi scroll, dan chart disimpan ketika berpindah halaman. Kembali ke halaman tersebut akan memulihkan tampilan tanpa membangun ulang panel dari awal.
- Cache dibatasi untuk 16 halaman dan mencakup semua tab aplikasi saat ini. Cache dibersihkan saat data karyawan diterapkan, SOTK Master diperbarui, mode pembacaan global berubah, atau pengguna logout. Hal ini mencegah data lama tampil setelah sumber data berubah.
- Cache berlaku selama sesi halaman/browser berjalan; refresh browser atau membuka ulang aplikasi memulai sesi baru.

### Monitoring Struktur Jabatan — distribusi Position Type

- Kolom `rata rata grade` diganti dengan kolom dinamis untuk seluruh nilai Position Type current.
- Kategori standar ditata di awal: Definitif, Penugasan, dan Masa Evaluasi. Kategori lain muncul otomatis sesuai data; nilai kosong/tidak diketahui ditampilkan sebagai `Tidak Terklasifikasi`.
- Pengelompokan menggunakan JOB CODE current dan nama jabatan current. Pada level Cabang, label jabatan current mengikuti resolver Position Name yang sudah tersedia.
- NIK dihitung satu kali pada cakupan tabel yang sedang difilter.
- Kategori Position Type disusun dari seluruh data aktif sehingga kategori tetap tersedia sebagai kolom meskipun nilainya nol pada filter tertentu.
- Ringkasan ini tidak dibatasi mode global Definitif Saja / Semua Karyawan.

### Aturan bisnis yang dipertahankan

- Keluarga jabatan current ditentukan oleh `JOB CODE` current, bukan `JOB CODE DEF`.
- Position Name current digunakan untuk mengonfirmasi tingkatan jabatan; AO ber-grade tinggi tidak otomatis dianggap Senior Account Officer.
- Gap Formasi dan proses aktual/mode global tetap menggunakan logika yang sudah ada pada aplikasi. Secara default mode pembacaan adalah Definitif Saja; mode Semua Karyawan tetap merupakan pilihan global yang terpisah.
- Vacancy Priority tetap menggunakan posisi current sesuai resolver yang sudah ada.
- Kartu/ringkasan Job Grade pada fitur lain tidak dihapus. Yang diganti hanya kolom rata-rata grade di Monitoring Struktur Jabatan.
- Tampilan utama, navigasi, warna, sidebar, dan layout lama dipertahankan. Penambahan UI dibatasi pada filter kelas UPC/UPS dan kolom distribusi Position Type.

## Pengujian otomatis

Jalankan pengujian filter kelas UPC/UPS dan agregasi Position Type:

```cmd
node tools\test_upc_ups_filter_cascade.js
node tools\test_position_type_summary.js
```

Build SOTK sekaligus validasi terhadap referensi:

```cmd
python tools\build_data.py source_data\SOTK_MASTER_FINAL.xlsx data.js source_data\REFERENSI_FORMASI_CABANG.xlsx
```


## Normalisasi Penaksir UPC/UPS ke formasi Penaksir

Pada data karyawan, jabatan current `PPC / Penaksir UPC` di outlet UPC/UPS dipetakan ke keluarga formasi SOTK `PSR / Penaksir`.

Aturan ini dibuat eksplisit dalam `lib/sotk-job-aliases.js` dan hanya aktif jika seluruh kondisi terpenuhi: level Cabang, jenis outlet kanonis dari Unit Master adalah UPC/UPS, JOB CODE current adalah PPC, JOB NAME adalah Penaksir UPC, dan POSITION NAME dimulai dengan Penaksir UPC atau Penaksir UPS.

Data sumber tidak diubah. `JOB CODE`, `JOB NAME`, `JOB CODE DEF`, dan seluruh nama posisi asli tetap disimpan. Nilai `sotkJobCode` dan `sotkJobName` hanya digunakan untuk pencocokan formasi, klasifikasi jabatan current, dan agregasi analisis.

Aturan Position Grade legacy `Penaksir UPC/S` di master digunakan untuk mengenali kedua nama Position Name (UPC dan UPS). Gap Formasi tetap hanya menghitung Position Type Definitif; Penugasan/Masa Evaluasi tetap dikecualikan dari aktual definitif sesuai aturan yang telah berlaku.

Uji otomatis alias dapat dijalankan dari folder `Power`:

```cmd
node tools/test_penaksir_upc_mapping.js
```
