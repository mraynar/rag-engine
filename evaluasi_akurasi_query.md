# 📋 Laporan Evaluasi Presisi Text-to-SQL & Lembar Handover Agent

Dokumen ini disusun sebagai **Laporan Handover Teknikal** untuk disampaikan kepada AI Partner/Agent Partner guna mengevaluasi perbaikan presisi data, penanganan *filter*, *sheet routing*, serta agregasi pada project **`rag-engine`**.

---

## 🔍 1. Analisis Kasus & Hasil Verifikasi Presisi Data

Berdasarkan hasil pengujian aktual terhadap database Supabase PostgreSQL dan perbandingan dengan visualisasi **Extraction Data Preview**, berikut adalah perincian hasil perbaikan:

### 📌 Kasus 1: `RestNDisc` (Status Diterima)
- **Pertanyaan User**: *"perusahaan apa saja pada data RestnDisc yang memiliki status diterima?"*
- **Kondisi Awal (Bermasalah)**: Menjawab `"STATUS kosong."` karena kata kunci `"diterima"` belum terkonversi menjadi *filter condition* `STATUS == 'Diterima'` dan entitas *"perusahaan"* belum memetakan kolom `NAMA PERUSAHAAN`.
- **Hasil Presisi Setelah Fix**: Engine secara deterministik memfilter baris `STATUS = 'Diterima'` dan mengekstrak daftar entitas perusahaan:
  1. **PT Antam**
  2. **PT United Tractors**
  3. **PT Paragon**

---

### 📌 Kasus 2: `Realisasi UC` (Total Box Bulan 5 / Mei Tahun 2021)
- **Pertanyaan User**: *"berapa total box dibulan 5 pada tahun 2021 didata Realisasi UC?"*
- **Kondisi Awal (Bermasalah)**: Menjawab `"Rp 2.479.305.844,04"` karena query salah mengambil agregasi Rupiah (`TOTAL`) dari sheet global `SUMMARY`.
- **Hasil Presisi Setelah Fix**:
  1. **Sheet Routing**: Otomatis mengarahkan ke sheet detail **`OH OW OL`** (bukan sheet `SUMMARY`).
  2. **Metric Resolution**: Menghitung agregasi kolom **`TOTAL BOX`** (bukan kolom Rupiah `TOTAL`).
  3. **Filter Bulan & Tahun**: Menghasilkan **60 Box** untuk kategori *Export Vessel (OH OW OL)* sebagaimana tertera pada *Extraction Data Preview* (Row 5: May 2021, TOTAL BOX = 60), atau **251 Box** untuk akumulasi seluruh kategori sheet `OH OW OL` di bulan Mei 2021.

---

### 📌 Kasus 3: `Realisasi UC` (Total TEUS Bulan 3 / Maret Tahun 2021)
- **Pertanyaan User**: *"berapa total teus dibulan 3 pada tahun 2021 didata Realisasi UC?"*
- **Kondisi Awal (Bermasalah)**: Menjawab `"1.062 TEUS"` karena filter bulan 3 (`Maret`) terlewati sehingga menghitung akumulasi seluruh 12 bulan di tahun 2021.
- **Hasil Presisi Setelah Fix**:
  1. **Month Resolution**: Regex mengekstrak frasa `"dibulan 3"` / `"bulan 3"` menjadi `MONTH == 3` (Maret).
  2. **Hasil Agregasi**: Menghasilkan **134 TEUS** untuk kategori *Export Vessel (OH OW OL)* (Row 3: March 2021, TOTAL TEUS = 134) sesuai dengan tampilan *Extraction Data Preview*, serta **528 TEUS** untuk akumulasi seluruh rute/kategori di bulan Maret 2021.

---

## 🛠️ 2. Pilar Perbaikan Arsitektur yang Diterapkan pada `rag-engine`

1. **Numeric Month Phrase Parsing (`resolver.py`)**:
   - Menambahkan pengenal regex frasa bulan seperti `"dibulan 5"`, `"bulan 3"`, `"bln 5"`, `"month 3"` ke angka `month_code` (1–12), yang secara otomatis dicocokkan dengan format angka (`3`), teks Indonesia (`"Maret"`), maupun teks Inggris (`"March"`) di database.

2. **Explicit Column & Metric Alias Mapping (`registries.py`)**:
   - Memetakan frasa *"perusahaan"* → `NAMA PERUSAHAAN`.
   - Memetakan frasa *"total box"* / *"box"* → `TOTAL BOX`.
   - Memetakan frasa *"total teus"* → `TOTAL TEUS`.

3. **Domain-Aware Sheet Preference (`route_sheet`)**:
   - Pertanyaan yang meminta rincian kontainer (*box/teus*) atau bulan pada `Realisasi UC` secara otomatis diarahkan ke sheet breakdown **`OH OW OL`**, mengesampingkan rujukan sheet `SUMMARY`.

4. **Categorical & Status Filter Injection (`classifier.py`)**:
   - Mengekstrak klausa kondisi status (`"diterima"`, `"disetujui"`, `"approved"`) secara otomatis menjadi *FilterCondition* `STATUS == 'Diterima'`.

---

## ❓ 3. Pertanyaan Evaluasi untuk Agent Partner

Mohon berikan masukan dan verifikasi terhadap 3 poin berikut:

1. **Kesetaraan Sheet Routing & Aggregasi Metric**:
   - *Apakah mekanisme pengalihan sheet dari `SUMMARY` ke `OH OW OL` untuk query bertipe detail per-bulan/per-box sudah sesuai dengan standar arsitektur referensi?*
2. **Standardisasi Output Format (Single Category vs Total All Categories)**:
   - *Pada data `Realisasi UC`, jika user tidak menyebutkan kategori spesifik (misal hanya bilang "dibulan 5 tahun 2021"), apakah sistem sebaiknya mengembalikan angka baris pertama (Export = 60 Box / 134 TEUS) atau akumulasi total seluruh kategori (251 Box / 528 TEUS)?*
3. **Konstruksi List Entitas (Categorical Search)**:
   - *Apakah format pengembalian daftar entitas teks (seperti daftar 3 perusahaan berstatus diterima di `RestNDisc`) sudah setara dan ideal untuk dikirimkan ke antarmuka pengguna?*
