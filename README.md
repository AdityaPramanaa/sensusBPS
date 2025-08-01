# WSS Map Data Extractor

Aplikasi web untuk mengekstrak data dari peta WSS (Wajib Serah Simpan) menggunakan OCR canggih dan pencarian maps otomatis.

## 🚀 Fitur Utama

### 📸 Foto Langsung dengan Validasi
- **Ambil foto langsung** dari map menggunakan kamera
- **Validasi otomatis** data map sesuai kriteria:
  - Map ID: 5171030005000103
  - Provinsi: BALI
  - Kabupaten: DENPASAR
  - Kecamatan: DENPASAR BARAT
  - Desa: DAUH PURI
- **Feedback real-time** jika data tidak sesuai kriteria
- **Auto-capture** setelah 2 detik preview kamera

### 🔍 Pencarian Maps Otomatis
- **OpenStreetMap integration** untuk mencari informasi bisnis
- **Data otomatis terisi**:
  - Contact Person
  - Jam Operasional
  - Koordinat
  - Alamat
  - Telepon
  - Email
- **Fallback manual** jika data tidak ditemukan di maps

### 📊 Preview Data Sebelum Download
- **Review data** yang berhasil diekstrak
- **Validasi visual** field yang sudah terisi otomatis
- **Statistik lengkap** bisnis, jalan, lingkungan, dll.

### 📋 Generate Excel Template
- **Format BLOK III** sesuai standar
- **Segmen otomatis** berdasarkan lingkungan/jalan
- **Sheet Detail Bisnis** dengan informasi lengkap
- **Koordinat dan landmark** dalam sheet terpisah

## 🛠️ Teknologi

- **Backend**: Flask (Python)
- **OCR**: EasyOCR (Free & Accurate)
- **Maps API**: OpenStreetMap Nominatim (Free)
- **Excel**: Openpyxl
- **Frontend**: HTML5, CSS3, JavaScript
- **Camera**: WebRTC getUserMedia API

## 📦 Instalasi

1. **Clone repository**
```bash
git clone <repository-url>
cd SENSUS
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Run aplikasi**
```bash
python app.py
```

4. **Buka browser**
```
http://localhost:5000
```

## 🎯 Cara Penggunaan

### Metode 1: Upload File
1. Klik area upload atau drag & drop file gambar
2. Pilih file WSS map (PNG, JPG, JPEG, GIF, BMP, TIFF)
3. Klik "Proses & Preview Data"
4. Review data yang diekstrak
5. Klik "Download Excel"

### Metode 2: Foto Langsung
1. Klik tombol "📷 Ambil Foto"
2. Izinkan akses kamera
3. Arahkan kamera ke map WSS
4. Foto akan diambil otomatis setelah 2 detik
5. Sistem akan memvalidasi data map
6. Jika valid, review dan download Excel
7. Jika tidak valid, lihat feedback error

## 🔍 Validasi Data Map

Aplikasi akan memvalidasi bahwa foto map mengandung data berikut:
- **Map ID**: 5171030005000103
- **Provinsi**: BALI
- **Kabupaten**: DENPASAR
- **Kecamatan**: DENPASAR BARAT
- **Desa**: DAUH PURI

Jika data tidak sesuai, aplikasi akan menampilkan:
- Data yang berhasil diekstrak
- Field yang salah/tidak sesuai
- Solusi untuk memperbaiki

## 📊 Output Excel

File Excel yang dihasilkan berisi:

### Sheet BLOK III
- Segmen otomatis berdasarkan lingkungan/jalan
- Estimasi beban dominan
- Estimasi jumlah KK, BTT, BKU
- Field kosong untuk input manual

### Sheet Detail Bisnis
- Nama dan tipe bisnis
- Contact Person (dari maps)
- Jam Operasional (dari maps)
- Koordinat (dari maps)
- Alamat (dari maps)
- Telepon (dari maps)
- Email (dari maps)

### Sheet Lainnya
- Header Info (statistik lengkap)
- Legend (keterangan)
- Extracted Data (data mentah)
- Coordinates (jika ada)

## 🎯 Tips untuk Hasil Terbaik

### Untuk Upload File:
- Gunakan gambar dengan resolusi tinggi (minimal 300 DPI)
- Pastikan teks dalam gambar jelas dan tidak blur
- Hindari gambar yang terlalu gelap atau terang
- Format PNG atau JPG memberikan hasil terbaik

### Untuk Foto Langsung:
- Pastikan map dalam kondisi pencahayaan yang baik
- Hindari bayangan atau refleksi pada map
- Pastikan seluruh area map terlihat jelas
- Tunggu 2 detik setelah preview kamera muncul

## 🔧 Troubleshooting

### Error "Tidak dapat mengakses kamera"
- Pastikan browser mendukung WebRTC
- Berikan izin akses kamera
- Gunakan HTTPS untuk production

### Error "Data map tidak sesuai"
- Pastikan foto map yang benar
- Periksa kriteria validasi
- Coba foto ulang dengan sudut yang berbeda

### Error "Tidak ada teks yang dapat diekstrak"
- Pastikan gambar jelas dan tidak blur
- Coba dengan resolusi yang lebih tinggi
- Pastikan teks dalam gambar terbaca

## 📝 Changelog

### v2.0.0
- ✅ Fitur foto langsung dengan validasi
- ✅ Integrasi OpenStreetMap untuk data bisnis
- ✅ Preview data dengan indikator field terisi
- ✅ Validasi otomatis data map
- ✅ Feedback error yang detail

### v1.0.0
- ✅ OCR dengan EasyOCR
- ✅ Upload file gambar
- ✅ Generate Excel template
- ✅ Preview data sebelum download

## 🤝 Kontribusi

Silakan buat issue atau pull request untuk kontribusi.

## 📄 Lisensi

MIT License 