#!/usr/bin/env python3
"""
Test script untuk menguji fungsi estimasi KK yang telah diperbaiki
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import (
    detect_residential_area, 
    estimate_kk_count_improved, 
    estimate_btt_count_improved,
    estimate_bku_count_improved,
    estimate_business_count_improved,
    search_business_info
)

def test_residential_detection():
    """Test deteksi area permukiman"""
    print("=== TEST DETEKSI AREA PERMUKIMAN ===")
    
    test_cases = [
        ("LINGKUNGAN PERUMAHAN GRIYA", "high_density_residential"),
        ("LINGKUNGAN VILLA SANUR", "low_density_residential"),
        ("LINGKUNGAN KAMPUNG BARU", "standard_residential"),
        ("MALL BALI COLLECTION", "commercial"),
        ("KAWASAN INDUSTRI DENPASAR", "industrial"),
        ("LINGKUNGAN DAUH PURI", "standard_residential"),
        ("JALAN GATOT SUBROTO", "standard_residential"),
        ("PASAR KUMBASARI", "commercial"),
        ("HOTEL GRAND BALI BEACH", "commercial"),
        ("KANTOR WALIKOTA DENPASAR", "commercial")
    ]
    
    for name, expected_type in test_cases:
        area_type, estimated_kk = detect_residential_area(name)
        print(f"Area: {name}")
        print(f"  Detected Type: {area_type}")
        print(f"  Expected Type: {expected_type}")
        print(f"  Estimated KK: {estimated_kk}")
        print(f"  Status: {'✅' if area_type == expected_type else '❌'}")
        print()

def test_kk_estimation():
    """Test estimasi KK berdasarkan tipe area"""
    print("=== TEST ESTIMASI KK ===")
    
    test_cases = [
        ("LINGKUNGAN PERUMAHAN GRIYA", 150),
        ("LINGKUNGAN VILLA SANUR", 50),
        ("LINGKUNGAN KAMPUNG BARU", 100),
        ("MALL BALI COLLECTION", 20),
        ("KAWASAN INDUSTRI DENPASAR", 100),
        ("LINGKUNGAN DAUH PURI", 80),
        ("JALAN GATOT SUBROTO", 50),
        ("PASAR KUMBASARI", 20),
        ("HOTEL GRAND BALI BEACH", 50),
        ("KANTOR WALIKOTA DENPASAR", 30)
    ]
    
    for name, expected_kk in test_cases:
        estimated_kk = estimate_kk_count_improved(name)
        print(f"Area: {name}")
        print(f"  Estimated KK: {estimated_kk}")
        print(f"  Expected KK: {expected_kk}")
        print(f"  Status: {'✅' if estimated_kk == expected_kk else '❌'}")
        print()

def test_business_info_search():
    """Test pencarian informasi bisnis dari maps"""
    print("=== TEST PENCARIAN INFO BISNIS ===")
    
    test_businesses = [
        "SiCepat Ekspres Denpasar Timurl",
        "Mall Bali Collection",
        "Pasar Kumbasari",
        "Hotel Grand Bali Beach",
        "Bank BCA Denpasar"
    ]
    
    for business_name in test_businesses:
        print(f"Searching for: {business_name}")
        business_info = search_business_info(business_name, "Denpasar")
        
        if business_info:
            print(f"  ✅ Found business info:")
            print(f"    Address: {business_info.get('address', 'N/A')}")
            print(f"    Coordinates: {business_info.get('coordinates', 'N/A')}")
            print(f"    Phone: {business_info.get('phone', 'N/A')}")
            print(f"    Hours: {business_info.get('operational_hours', 'N/A')}")
            print(f"    Type: {business_info.get('business_type', 'N/A')}")
        else:
            print(f"  ❌ No business info found")
        print()

def test_complete_estimation():
    """Test estimasi lengkap untuk segmen"""
    print("=== TEST ESTIMASI LENGKAP SEGMEN ===")
    
    test_areas = [
        ("LINGKUNGAN PERUMAHAN GRIYA", "high_density_residential"),
        ("LINGKUNGAN VILLA SANUR", "low_density_residential"),
        ("LINGKUNGAN KAMPUNG BARU", "standard_residential"),
        ("MALL BALI COLLECTION", "commercial"),
        ("KAWASAN INDUSTRI DENPASAR", "industrial")
    ]
    
    for area_name, expected_type in test_areas:
        print(f"Area: {area_name}")
        
        # Detect area type
        area_type, kk_count = detect_residential_area(area_name)
        print(f"  Detected Type: {area_type}")
        print(f"  KK Count: {kk_count}")
        
        # Estimate other counts
        btt_count = estimate_btt_count_improved(area_name, kk_count)
        bku_count = estimate_bku_count_improved(area_name, kk_count)
        business_count = estimate_business_count_improved(area_name)
        
        print(f"  BTT Count: {btt_count}")
        print(f"  BKU Count: {bku_count}")
        print(f"  Business Count: {business_count}")
        
        # Calculate totals
        btt_kosong = max(0, kk_count - btt_count)
        bbtt_non_usaha = max(0, int(kk_count * 0.05))
        total_muatan = max(kk_count, btt_count) + btt_kosong + bbtt_non_usaha + business_count
        
        print(f"  BTT Kosong: {btt_kosong}")
        print(f"  BBTT Non Usaha: {bbtt_non_usaha}")
        print(f"  Total Muatan: {total_muatan}")
        print(f"  Status: {'✅' if area_type == expected_type else '❌'}")
        print()

if __name__ == "__main__":
    print("🧪 TESTING IMPROVED ESTIMATION FUNCTIONS")
    print("=" * 50)
    
    try:
        test_residential_detection()
        test_kk_estimation()
        test_business_info_search()
        test_complete_estimation()
        
        print("✅ All tests completed!")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc() 