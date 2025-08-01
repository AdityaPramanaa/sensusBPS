# SENSUS - Sistem Ekstraksi Data Peta WSS

Sistem otomatis untuk mengekstrak dan menganalisis data dari peta WSS (Water Supply System) menggunakan OCR dan AI.

## Fitur Utama

### 🔍 **Deteksi Pusat Ekonomi - Fokus Mall dan Pasar**
Sistem dirancang untuk mendeteksi pusat ekonomi dengan fokus pada mall dan pasar sesuai konteks peta WSS:

- **Mall**: Pusat perbelanjaan modern (40-80 UMKM)
- **Pasar**: Pasar tradisional dan modern (80-150 UMKM)

### 📊 **Estimasi UMKM yang Akurat**
Estimasi UMKM disesuaikan dengan jenis dan ukuran pusat ekonomi:
- **Mall**: 40-80 UMKM (tergantung ukuran)
- **Pasar Induk**: 150 UMKM (pasar tradisional besar)
- **Pasar Modern**: 80 UMKM (pasar modern)
- **Pasar Tradisional**: 100 UMKM (pasar standar)

### 🎯 **Penyesuaian Berdasarkan Konteks**
Sistem melakukan penyesuaian estimasi berdasarkan lingkungan dalam peta:
- **Lingkungan Peternakan**: UMKM dikurangi 50% (aktivitas komersial rendah)
- **Lingkungan Pertanian**: UMKM dikurangi 20-30% (pasar tradisional lebih aktif)
- **Lingkungan Industri**: UMKM ditambah 10% (aktivitas komersial tinggi)

### 📱 **Upload & Capture**
- Upload file gambar peta WSS
- Capture langsung menggunakan kamera
- Mendukung format: PNG, JPG, JPEG, GIF, BMP, TIFF

### 🔍 **OCR Canggih**
- Menggunakan EasyOCR dengan akurasi tinggi
- Mendukung bahasa Indonesia dan Inggris
- Preprocessing gambar untuk hasil optimal

### 📋 **Ekstraksi Data Lengkap**
- Map ID, Provinsi, Kabupaten, Kecamatan, Desa
- Skala peta
- Daftar bisnis dan detailnya
- Nama jalan dan lingkungan
- Landmark dan koordinat
- Pusat ekonomi dengan estimasi UMKM

### 📊 **Template Excel Otomatis**
- Format BLOK III sesuai standar
- Sheet detail bisnis
- Sheet pusat ekonomi
- Sheet data bangunan
- Informasi koordinat dan kontak

### 🏗️ **Deteksi Bangunan**
Sistem dapat mendeteksi dan menghitung berbagai jenis bangunan:
- **🏚️ Bangunan Kosong**: Rumah/gedung yang tidak terisi
- **🏛️ Bangunan Bukan Tempat Tinggal**: Masjid, sekolah, kantor, dll
- **🏪 Bangunan Usaha**: Toko, warung, restoran, dll
- **🏠 Kos-kosan**: Tempat tinggal sewa/kontrakan

## Instalasi

```bash
# Clone repository
git clone [repository-url]
cd SENSUS

# Install dependencies
pip install -r requirements.txt

# Jalankan aplikasi
python app.py
```

## Penggunaan

1. **Upload File**: Pilih file gambar peta WSS
2. **Capture**: Ambil foto peta langsung dari kamera
3. **Preview**: Review data yang diekstrak
4. **Download**: Unduh file Excel dengan data lengkap

## Struktur Data

### Pusat Ekonomi yang Dideteksi
```json
{
  "name": "Nama Pusat Ekonomi",
  "type": "jenis_pusat_ekonomi",
  "type_description": "Deskripsi Jenis",
  "estimated_umkm": 100,
  "contact_person": "Kontak",
  "operational_hours": "Jam Operasional",
  "coordinates": "Koordinat",
  "address": "Alamat",
  "context": "Deskripsi Kontekstual"
}
```

### Jenis Pusat Ekonomi
- `mall` - Pusat Perbelanjaan (Mall, Plaza, Supermarket)
- `pasar` - Pasar Tradisional/Modern (Pasar Induk, Pasar Modern, Pasar Tradisional)

### Data Bangunan
```json
{
  "bangunan_kosong": 2,
  "bangunan_bukan_tempat_tinggal": 3,
  "bangunan_usaha": 5,
  "kos_kosan": 1,
  "details": {
    "bangunan_kosong": ["Rumah Kosong Jl. Merdeka", "Gedung Kosong Ruko"],
    "bangunan_bukan_tempat_tinggal": ["Masjid Al-Ikhlas", "SD Negeri 1", "Kantor Desa"],
    "bangunan_usaha": ["Toko Sederhana", "Warung Makan", "Bank BCA"],
    "kos_kosan": ["Kost Putra Sejahtera"]
  }
}
```

## API Endpoints

- `GET /` - Halaman utama
- `POST /upload` - Upload file gambar
- `POST /capture` - Capture gambar dari kamera
- `POST /download` - Download file Excel

## Teknologi

- **Backend**: Flask (Python)
- **OCR**: EasyOCR
- **Image Processing**: PIL/Pillow
- **Data Processing**: Pandas, NumPy
- **Maps API**: OpenStreetMap Nominatim
- **Frontend**: HTML, CSS, JavaScript

## Dokumentasi

- [ECONOMIC_CENTERS_EXPANSION.md](ECONOMIC_CENTERS_EXPANSION.md) - Detail perluasan deteksi pusat ekonomi
- [COORDINATES_ACCURACY.md](COORDINATES_ACCURACY.md) - Akurasi koordinat
- [IMPROVEMENTS.md](IMPROVEMENTS.md) - Peningkatan sistem

## Kontribusi

Silakan berkontribusi dengan:
1. Fork repository
2. Buat branch fitur baru
3. Commit perubahan
4. Push ke branch
5. Buat Pull Request

## Lisensi

[MIT License](LICENSE)

## Support

Untuk pertanyaan atau dukungan, silakan buat issue di repository ini. 