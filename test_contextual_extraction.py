#!/usr/bin/env python3
"""
Test script for contextual data extraction functionality
"""

import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import extract_contextual_data

def test_contextual_extraction():
    """Test the contextual data extraction function"""
    
    print("🧪 Testing Contextual Data Extraction")
    print("=" * 50)
    
    # Test cases with different environments
    test_cases = [
        {
            "name": "Perkambingan Environment",
            "text": """
            Map ID: 5171030005000103
            Provinsi: BALI
            Kabupaten: DENPASAR
            Kecamatan: DENPASAR BARAT
            Desa: DAUH PURI
            Skala: 1:353
            
            LINGKUNGAN PERKAMBINGAN
            Peternakan Kambing Sari
            Kandang Kambing Utama
            Jl. Peternakan No. 1
            Masjid Al-Ikhlas
            Taman Peternakan
            Koordinat: -8.6500, 115.2167
            """,
            "expected_environment": "perkambingan"
        },
        {
            "name": "Perumahan Environment",
            "text": """
            Map ID: 5171030005000103
            Provinsi: BALI
            Kabupaten: DENPASAR
            Kecamatan: DENPASAR BARAT
            Desa: DAUH PURI
            Skala: 1:353
            
            PERUMAHAN GRIYA ASRI
            Rumah Tinggal
            Jl. Perumahan No. 5
            Taman Perumahan
            Masjid Perumahan
            Koordinat: -8.6500, 115.2167
            """,
            "expected_environment": "perumahan"
        },
        {
            "name": "Komersial Environment",
            "text": """
            Map ID: 5171030005000103
            Provinsi: BALI
            Kabupaten: DENPASAR
            Kecamatan: DENPASAR BARAT
            Desa: DAUH PURI
            Skala: 1:353
            
            KAWASAN KOMERSIAL
            Mall Denpasar
            Hotel Bali
            Restaurant Sari
            Bank BCA
            Toko Elektronik
            Jl. Komersial No. 10
            Koordinat: -8.6500, 115.2167
            """,
            "expected_environment": "komersial"
        },
        {
            "name": "Industri Environment",
            "text": """
            Map ID: 5171030005000103
            Provinsi: BALI
            Kabupaten: DENPASAR
            Kecamatan: DENPASAR BARAT
            Desa: DAUH PURI
            Skala: 1:353
            
            KAWASAN INDUSTRI
            Pabrik Tekstil
            Factory Garment
            Industrial Zone
            Jl. Industri No. 15
            Koordinat: -8.6500, 115.2167
            """,
            "expected_environment": "industri"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 Test Case {i}: {test_case['name']}")
        print("-" * 40)
        
        try:
            # Extract contextual data
            result = extract_contextual_data(test_case['text'])
            
            # Check if result is a dictionary
            if isinstance(result, dict):
                # Display results
                print(f"✅ Target Environment: {result.get('target_environment', 'N/A')}")
                print(f"✅ Area Type: {result.get('area_type', 'N/A')}")
                print(f"✅ Estimated KK: {result.get('estimated_kk', 'N/A')}")
                print(f"✅ Dominant Load: {result.get('dominant_load', 'N/A')}")
                print(f"✅ Total Businesses: {result.get('total_businesses', 'N/A')}")
                print(f"✅ Total Streets: {result.get('total_streets', 'N/A')}")
                print(f"✅ Total Landmarks: {result.get('total_landmarks', 'N/A')}")
                print(f"✅ Total Coordinates: {len(result.get('coordinates', []))}")
                
                # Check if environment detection is correct
                if result.get('target_environment') == test_case['expected_environment']:
                    print(f"✅ Environment detection: CORRECT")
                else:
                    print(f"❌ Environment detection: EXPECTED {test_case['expected_environment']}, GOT {result.get('target_environment')}")
                
                # Show businesses found
                businesses = result.get('businesses', [])
                if businesses:
                    print(f"🏢 Businesses found: {', '.join(businesses)}")
                
                # Show streets found
                streets = result.get('streets', [])
                if streets:
                    print(f"🛣️ Streets found: {', '.join(streets)}")
                
                # Show landmarks found
                landmarks = result.get('landmarks', [])
                if landmarks:
                    print(f"🗺️ Landmarks found: {', '.join(landmarks)}")
            else:
                print(f"❌ ERROR: Expected dictionary, got {type(result)}")
                print(f"❌ Result content: {result}")
                
        except Exception as e:
            print(f"❌ Error in test case {i}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 50)
    print("🎯 Contextual Extraction Test Complete!")
    print("=" * 50)

if __name__ == "__main__":
    test_contextual_extraction() 