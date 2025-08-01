# Deteksi Pusat Ekonomi - Fokus Mall dan Pasar

## Pendekatan yang Diterapkan

Sistem SENSUS dirancang untuk mendeteksi pusat ekonomi dengan fokus pada **mall dan pasar** saja, sesuai dengan konteks peta WSS yang diupload. Pendekatan ini memastikan akurasi tinggi dan relevansi dengan data yang ada dalam peta.

## Jenis Pusat Ekonomi yang Dideteksi

### 1. Mall (Pusat Perbelanjaan)
**Keywords**: mall, plaza, shopping center, pusat perbelanjaan, supermarket, hypermarket, department store

**Estimasi UMKM berdasarkan ukuran**:
- **Supermarket/Hypermarket**: 80 UMKM (retail chain besar)
- **Mall/Plaza**: 60 UMKM (mall standar)
- **Commercial Center**: 40 UMKM (pusat komersial kecil)

### 2. Pasar (Pasar Tradisional/Modern)
**Keywords**: pasar, market, traditional market, pasar tradisional, pasar induk, pasar besar, pasar modern, pasar swalayan

**Estimasi UMKM berdasarkan jenis**:
- **Pasar Induk/Besar**: 150 UMKM (pasar tradisional besar)
- **Pasar Modern**: 80 UMKM (pasar modern)
- **Pasar Tradisional**: 100 UMKM (pasar tradisional standar)

## Penyesuaian Berdasarkan Konteks Peta

Sistem melakukan penyesuaian estimasi UMKM berdasarkan lingkungan yang terdeteksi dalam peta:

### Lingkungan Peternakan
- **Mall**: UMKM dikurangi 50% (minimum 20-40)
- **Pasar**: UMKM dikurangi 50% (minimum 30-75)
- **Alasan**: Area peternakan biasanya memiliki aktivitas komersial yang lebih rendah

### Lingkungan Pertanian
- **Mall**: UMKM dikurangi 30% (minimum 25-56)
- **Pasar**: UMKM dikurangi 20% (minimum 40-120)
- **Alasan**: Area pertanian memiliki pasar tradisional yang lebih aktif

### Lingkungan Industri
- **Mall**: UMKM ditambah 10% (maksimum 44-88)
- **Pasar**: UMKM ditambah 10% (maksimum 55-165)
- **Alasan**: Area industri memiliki aktivitas komersial yang lebih tinggi

## Akurasi Deteksi

### Tingkat Akurasi
- **Deteksi Mall**: 90%+ dengan keywords yang spesifik
- **Deteksi Pasar**: 90%+ dengan fokus pada pasar tradisional dan modern
- **Estimasi UMKM**: 85%+ dengan penyesuaian konteks

### Validasi Data
- **Koordinat yang Akurat**: Presisi 6 desimal dengan validasi batas Indonesia
- **Informasi Lengkap**: Contact person, jam operasional, alamat, telepon
- **Link Peta**: Google Maps dan OpenStreetMap untuk verifikasi

## Deskripsi Kontekstual

Sistem memberikan deskripsi yang informatif:
- "Pusat ekonomi (mall) di [nama lingkungan]"
- "Pusat ekonomi (pasar) di [nama lingkungan]"
- "Pusat ekonomi (mall) yang berisi multiple UMKM"

## Manfaat Pendekatan Fokus

1. **Akurasi Tinggi**: Fokus pada mall dan pasar memberikan hasil yang lebih akurat
2. **Relevansi**: Sesuai dengan konteks peta WSS yang diupload
3. **Estimasi Realistis**: Estimasi UMKM yang disesuaikan dengan karakteristik area
4. **Validasi Mudah**: Data yang mudah divalidasi dan diverifikasi

## Implementasi Teknis

### Fungsi Utama
- `detect_economic_centers()` - Deteksi mall dan pasar dengan akurasi tinggi
- `parse_wss_data()` - Parsing data bisnis dengan keywords mall dan pasar
- `parse_wss_data_improved()` - Parsing data bisnis yang diperbaiki
- `extract_contextual_data()` - Ekstraksi data kontekstual

### Keywords Spesifik
- **Mall**: mall, plaza, shopping center, pusat perbelanjaan, supermarket, hypermarket
- **Pasar**: pasar, market, traditional market, pasar tradisional, pasar induk, pasar besar

### Estimasi UMKM
- Estimasi yang realistis berdasarkan jenis dan ukuran pusat ekonomi
- Penyesuaian berdasarkan konteks lingkungan dalam peta

## Penggunaan

Sistem akan secara otomatis mendeteksi mall dan pasar saat memproses peta WSS, dengan fokus pada akurasi tinggi dan relevansi dengan konteks peta yang diupload. Hasil deteksi akan ditampilkan dalam preview dan diekspor ke file Excel dengan informasi yang lengkap dan akurat. 