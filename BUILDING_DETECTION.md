# Deteksi Bangunan - Fitur Baru

## Overview
Sistem WSS Map Data Extractor sekarang dilengkapi dengan fitur deteksi bangunan yang dapat mengidentifikasi dan menghitung berbagai jenis bangunan dari gambar peta yang diupload.

## Jenis Bangunan yang Dideteksi

### 1. 🏚️ Bangunan Kosong
- **Deskripsi**: Bangunan yang tidak terisi atau belum dihuni
- **Keywords**: kosong, empty, vacant, tidak terisi, belum dihuni, bangunan kosong, rumah kosong, gedung kosong, ruko kosong, tidak ada penghuni, belum ada penghuni, masih kosong
- **Contoh**: "Rumah Kosong", "Gedung Kosong", "Ruko Tidak Terisi"

### 2. 🏛️ Bangunan Bukan Tempat Tinggal
- **Deskripsi**: Fasilitas umum seperti masjid, sekolah, kantor, dll
- **Keywords**: masjid, musholla, surau, gereja, kapel, pura, vihara, klenteng, kantor, office, gedung perkantoran, balai desa, kantor desa, sekolah, sd, smp, sma, universitas, kampus, madrasah, rumah sakit, klinik, puskesmas, apotek, rumah ibadah, tempat ibadah, worship, temple, church, mosque
- **Contoh**: "Masjid Al-Ikhlas", "SD Negeri 1", "Kantor Desa"

### 3. 🏪 Bangunan Usaha
- **Deskripsi**: Bangunan yang digunakan untuk kegiatan komersial
- **Keywords**: toko, warung, restoran, rumah makan, cafe, kafe, bank, atm, spbu, gas station, salon, spa, hotel, penginapan, guesthouse, resort, inn, bengkel, workshop, garasi, showroom, dealer, apotek, pharmacy, klinik, dental, gigi, supermarket, minimarket, market, mall, plaza, pasar, traditional market, pasar tradisional
- **Contoh**: "Toko Sederhana", "Warung Makan", "Bank BCA"

### 4. 🏠 Kos-kosan
- **Deskripsi**: Tempat tinggal sewa/kontrakan
- **Keywords**: kos, kost, kostan, kos-kosan, kost-kostan, boarding house, kontrakan, sewa kamar, kamar sewa, rumah kos, gedung kos, asrama, dormitory, kamar kost, kost putra, kost putri, kost campur
- **Contoh**: "Kos Putra", "Kost Campur", "Boarding House"

## Implementasi Teknis

### Fungsi Deteksi
```python
def detect_building_types(text):
    """
    Detect different types of buildings from OCR text
    Returns: dict with counts of different building types
    """
```

### Struktur Data Output
```python
building_data = {
    'bangunan_kosong': 0,
    'bangunan_bukan_tempat_tinggal': 0,
    'bangunan_usaha': 0,
    'kos_kosan': 0,
    'details': {
        'bangunan_kosong': [],
        'bangunan_bukan_tempat_tinggal': [],
        'bangunan_usaha': [],
        'kos_kosan': []
    }
}
```

## Integrasi dengan Sistem

### 1. Parsing Data
- Fungsi `parse_wss_data()` dan `parse_wss_data_improved()` sekarang memanggil `detect_building_types()`
- Data bangunan disimpan dalam field `building_data`

### 2. Frontend Display
- Data bangunan ditampilkan dalam section "🏗️ DATA BANGUNAN YANG DITEMUKAN"
- Setiap jenis bangunan ditampilkan dengan jumlah dan detail
- Styling menggunakan CSS class `.building-count`

### 3. Excel Export
- Sheet baru "Data Bangunan" ditambahkan ke file Excel
- Kolom: Tipe Bangunan, Nama Bangunan, Jumlah, Kategori, Catatan
- Informasi total bangunan ditambahkan ke sheet "Informasi Peta"

## Contoh Output

### Frontend Display
```
🏗️ DATA BANGUNAN YANG DITEMUKAN

🏚️ Bangunan Kosong (2)
Detail Bangunan Kosong:
• Rumah Kosong Jl. Merdeka
• Gedung Kosong Ruko

🏛️ Bangunan Bukan Tempat Tinggal (3)
Detail Bangunan (Masjid, Sekolah, dll):
• Masjid Al-Ikhlas
• SD Negeri 1
• Kantor Desa

🏪 Bangunan Usaha (5)
Detail Bangunan Usaha:
• Toko Sederhana
• Warung Makan Pak Haji
• Bank BCA
• SPBU Pertamina
• Salon Kecantikan

🏠 Kos-kosan (1)
Detail Kos-kosan:
• Kost Putra Sejahtera
```

### Excel Sheet "Data Bangunan"
| Tipe Bangunan | Nama Bangunan | Jumlah | Kategori | Catatan |
|---------------|---------------|--------|----------|---------|
| Bangunan Kosong | Rumah Kosong Jl. Merdeka | 1 | Tidak Terisi | Bangunan yang tidak terisi atau belum dihuni |
| Bangunan Bukan Tempat Tinggal | Masjid Al-Ikhlas | 1 | Fasilitas Umum | Masjid, sekolah, kantor, dll |
| Bangunan Usaha | Toko Sederhana | 1 | Komersial | Toko, warung, restoran, dll |
| Kos-kosan | Kost Putra Sejahtera | 1 | Tempat Tinggal | Tempat tinggal sewa/kontrakan |

## Keunggulan Fitur

1. **Akurasi Tinggi**: Menggunakan keyword yang spesifik untuk setiap jenis bangunan
2. **Kategorisasi Otomatis**: Sistem otomatis mengkategorikan bangunan berdasarkan keyword
3. **Detail Lengkap**: Menyimpan nama bangunan dan jumlah untuk setiap kategori
4. **Integrasi Seamless**: Terintegrasi dengan sistem existing tanpa mengganggu fitur lain
5. **Export Excel**: Data bangunan otomatis masuk ke file Excel yang dihasilkan

## Penggunaan

1. Upload gambar peta seperti biasa
2. Sistem akan otomatis mendeteksi bangunan-bangunan dalam gambar
3. Hasil deteksi akan ditampilkan di section "Data Bangunan"
4. Data bangunan akan masuk ke file Excel saat download

## Catatan Teknis

- Deteksi berdasarkan keyword matching pada text hasil OCR
- Case-insensitive matching untuk akurasi yang lebih baik
- Filter teks pendek untuk mengurangi noise
- Logging detail untuk debugging
- Error handling untuk data yang tidak valid 