#!/usr/bin/env python3
"""
Test script untuk fitur deteksi bangunan
"""

import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import detect_building_types

def test_building_detection():
    """Test fungsi deteksi bangunan dengan berbagai skenario"""
    
    print("🧪 Testing Building Detection Feature")
    print("=" * 50)
    
    # Test case 1: Bangunan kosong
    print("\n1. Testing Bangunan Kosong:")
    text1 = """
    Rumah Kosong Jl. Merdeka
    Gedung Kosong Ruko
    Bangunan Tidak Terisi
    """
    result1 = detect_building_types(text1)
    print(f"   Input: {text1.strip()}")
    print(f"   Result: {result1}")
    print(f"   Expected: bangunan_kosong > 0")
    print(f"   Actual: {result1['bangunan_kosong']}")
    assert result1['bangunan_kosong'] > 0, "Should detect empty buildings"
    
    # Test case 2: Bangunan bukan tempat tinggal
    print("\n2. Testing Bangunan Bukan Tempat Tinggal:")
    text2 = """
    Masjid Al-Ikhlas
    SD Negeri 1
    Kantor Desa
    Gereja Katolik
    """
    result2 = detect_building_types(text2)
    print(f"   Input: {text2.strip()}")
    print(f"   Result: {result2}")
    print(f"   Expected: bangunan_bukan_tempat_tinggal > 0")
    print(f"   Actual: {result2['bangunan_bukan_tempat_tinggal']}")
    assert result2['bangunan_bukan_tempat_tinggal'] > 0, "Should detect non-residential buildings"
    
    # Test case 3: Bangunan usaha
    print("\n3. Testing Bangunan Usaha:")
    text3 = """
    Toko Sederhana
    Warung Makan Pak Haji
    Bank BCA
    SPBU Pertamina
    Salon Kecantikan
    """
    result3 = detect_building_types(text3)
    print(f"   Input: {text3.strip()}")
    print(f"   Result: {result3}")
    print(f"   Expected: bangunan_usaha > 0")
    print(f"   Actual: {result3['bangunan_usaha']}")
    assert result3['bangunan_usaha'] > 0, "Should detect business buildings"
    
    # Test case 4: Kos-kosan
    print("\n4. Testing Kos-kosan:")
    text4 = """
    Kost Putra Sejahtera
    Kost Campur
    Boarding House
    """
    result4 = detect_building_types(text4)
    print(f"   Input: {text4.strip()}")
    print(f"   Result: {result4}")
    print(f"   Expected: kos_kosan > 0")
    print(f"   Actual: {result4['kos_kosan']}")
    assert result4['kos_kosan'] > 0, "Should detect boarding houses"
    
    # Test case 5: Mixed buildings
    print("\n5. Testing Mixed Buildings:")
    text5 = """
    Rumah Kosong Jl. Merdeka
    Masjid Al-Ikhlas
    Toko Sederhana
    Kost Putra Sejahtera
    SD Negeri 1
    Bank BCA
    """
    result5 = detect_building_types(text5)
    print(f"   Input: {text5.strip()}")
    print(f"   Result: {result5}")
    print(f"   Expected: All building types > 0")
    print(f"   Actual: kosong={result5['bangunan_kosong']}, bukan_tinggal={result5['bangunan_bukan_tempat_tinggal']}, usaha={result5['bangunan_usaha']}, kos={result5['kos_kosan']}")
    assert result5['bangunan_kosong'] > 0, "Should detect empty buildings"
    assert result5['bangunan_bukan_tempat_tinggal'] > 0, "Should detect non-residential buildings"
    assert result5['bangunan_usaha'] > 0, "Should detect business buildings"
    assert result5['kos_kosan'] > 0, "Should detect boarding houses"
    
    # Test case 6: No buildings
    print("\n6. Testing No Buildings:")
    text6 = """
    Jalan Merdeka
    Lingkungan 1
    Koordinat: -8.123456, 115.123456
    """
    result6 = detect_building_types(text6)
    print(f"   Input: {text6.strip()}")
    print(f"   Result: {result6}")
    print(f"   Expected: All building types = 0")
    print(f"   Actual: kosong={result6['bangunan_kosong']}, bukan_tinggal={result6['bangunan_bukan_tempat_tinggal']}, usaha={result6['bangunan_usaha']}, kos={result6['kos_kosan']}")
    assert result6['bangunan_kosong'] == 0, "Should not detect empty buildings"
    assert result6['bangunan_bukan_tempat_tinggal'] == 0, "Should not detect non-residential buildings"
    assert result6['bangunan_usaha'] == 0, "Should not detect business buildings"
    assert result6['kos_kosan'] == 0, "Should not detect boarding houses"
    
    print("\n✅ All tests passed!")
    print("=" * 50)
    
    # Test details structure
    print("\n📋 Testing Details Structure:")
    for building_type, count in result5.items():
        if building_type != 'details':
            print(f"   {building_type}: {count}")
            if building_type in result5['details']:
                print(f"   Details: {result5['details'][building_type]}")
    
    print("\n🎉 Building detection feature is working correctly!")

if __name__ == "__main__":
    test_building_detection() 