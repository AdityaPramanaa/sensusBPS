#!/usr/bin/env python3
"""
Test script untuk memverifikasi fungsi dominant load descriptions
"""

def determine_dominant_load(name):
    """Determine dominant load type based on name"""
    name_lower = name.lower()
    
    # Check for industrial areas first (more specific)
    if any(word in name_lower for word in ['kawasan industri', 'industrial zone', 'industri', 'factory', 'pabrik']):
        return 9  # Kawasan industri
    
    # Check for office areas
    elif any(word in name_lower for word in ['kantor', 'office', 'perkantoran']):
        return 12  # Perkantoran
    
    # Check for shopping/commercial areas
    elif any(word in name_lower for word in ['mall', 'pasar', 'toko', 'shop', 'market', 'plaza', 'center']):
        return 8  # Pusat perbelanjaan
    
    # Check for hotel/tourism areas
    elif any(word in name_lower for word in ['hotel', 'resort', 'wisata', 'tourism']):
        return 10  # Hotel/tempat rekreasi
    
    # Check for transportation areas
    elif any(word in name_lower for word in ['bandara', 'terminal', 'stasiun', 'pelabuhan', 'airport']):
        return 13  # Pelabuhan/Bandara/Terminal
    
    # Check for educational areas
    elif any(word in name_lower for word in ['sekolah', 'universitas', 'kampus', 'pendidikan', 'education']):
        return 11  # Kawasan Pendidikan
    
    # Check for agricultural areas
    elif any(word in name_lower for word in ['pertanian', 'sawah', 'ladang', 'kebun', 'agriculture']):
        return 14  # Kawasan Pertanian
    
    # Check for livestock areas
    elif any(word in name_lower for word in ['peternakan', 'ternak', 'livestock']):
        return 15  # Kawasan Peternakan
    
    # Check for fishery areas
    elif any(word in name_lower for word in ['perikanan', 'tambak', 'fishery']):
        return 16  # Kawasan Perikanan
    
    # Check for mining areas
    elif any(word in name_lower for word in ['pertambangan', 'tambang', 'mining']):
        return 17  # Kawasan Pertambangan
    
    # Check for forestry areas
    elif any(word in name_lower for word in ['kehutanan', 'hutan', 'forestry']):
        return 18  # Kawasan Kehutanan
    
    # Check for tourism areas
    elif any(word in name_lower for word in ['pariwisata', 'wisata', 'tourism']):
        return 19  # Kawasan Pariwisata
    
    else:
        return 1  # Permukiman Biasa (default)

def get_dominant_load_description(load_code):
    """Convert dominant load code to descriptive text"""
    load_descriptions = {
        1: "Permukiman Biasa",
        2: "Permukiman Padat",
        3: "Permukiman Kumuh",
        4: "Permukiman Elite",
        5: "Permukiman Transmigrasi",
        6: "Permukiman Pesisir",
        7: "Permukiman Pegunungan",
        8: "Pusat Perbelanjaan",
        9: "Kawasan Industri",
        10: "Hotel/Tempat Rekreasi",
        11: "Kawasan Pendidikan",
        12: "Perkantoran",
        13: "Pelabuhan/Bandara/Terminal",
        14: "Kawasan Pertanian",
        15: "Kawasan Peternakan",
        16: "Kawasan Perikanan",
        17: "Kawasan Pertambangan",
        18: "Kawasan Kehutanan",
        19: "Kawasan Pariwisata",
        20: "Kawasan Khusus Lainnya"
    }
    return load_descriptions.get(load_code, f"Kode {load_code} (Tidak Diketahui)")

def test_dominant_load_descriptions():
    """Test fungsi dominant load descriptions"""
    print("🧪 TESTING DOMINANT LOAD DESCRIPTIONS")
    print("=" * 50)
    
    # Test cases
    test_cases = [
        "LINGKUNGAN KAMPUNG BARU",
        "MALL BALI COLLECTION",
        "KAWASAN INDUSTRI DENPASAR",
        "HOTEL GRAND BALI BEACH",
        "KANTOR WALIKOTA DENPASAR",
        "BANDARA NGURAH RAI",
        "PASAR TRADISIONAL",
        "KAMPUNG PERUMAHAN",
        "KANTOR BUPATI",
        "TERMINAL BUS",
        "STASIUN KERETA",
        "PELABUHAN BENOA"
    ]
    
    print("Test Cases:")
    print("-" * 30)
    
    for test_name in test_cases:
        load_code = determine_dominant_load(test_name)
        description = get_dominant_load_description(load_code)
        
        print(f"📍 {test_name}")
        print(f"   Kode: {load_code}")
        print(f"   Deskripsi: {description}")
        print()
    
    # Test semua kode yang mungkin
    print("Test Semua Kode Muatan Dominan:")
    print("-" * 40)
    
    for code in range(1, 21):
        description = get_dominant_load_description(code)
        print(f"Kode {code:2d}: {description}")
    
    # Test kode yang tidak valid
    print("\nTest Kode Tidak Valid:")
    print("-" * 25)
    
    invalid_codes = [0, 21, 99, 100]
    for code in invalid_codes:
        description = get_dominant_load_description(code)
        print(f"Kode {code}: {description}")

if __name__ == "__main__":
    test_dominant_load_descriptions() 