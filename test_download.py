import requests
import json

def test_download():
    """Test the download endpoint with proper data structure"""
    
    # Sample data that matches the expected structure
    test_data = {
        'map_id': '5171030005000103',
        'province': 'BALI',
        'regency': 'DENPASAR',
        'district': 'DENPASAR BARAT',
        'village': 'DAUH PURI',
        'scale': '1:5000',
        'businesses': ['Mall Bali', 'Hotel Grand Bali', 'Restaurant Bali'],
        'business_types': {
            'Mall Bali': 'mall',
            'Hotel Grand Bali': 'hotel',
            'Restaurant Bali': 'restaurant'
        },
        'business_details': {
            'Mall Bali': {
                'type': 'mall',
                'contact_person': 'John Doe',
                'operational_hours': '09:00-22:00',
                'coordinates': '-8.6500,115.2167',
                'address': 'Jl. Raya Kuta No. 123',
                'phone': '+62-361-123456',
                'email': 'info@mallbali.com'
            },
            'Hotel Grand Bali': {
                'type': 'hotel',
                'contact_person': 'Jane Smith',
                'operational_hours': '24 Jam',
                'coordinates': '-8.6501,115.2168',
                'address': 'Jl. Sunset Road No. 456',
                'phone': '+62-361-654321',
                'email': 'reservation@grandbali.com'
            },
            'Restaurant Bali': {
                'type': 'restaurant',
                'contact_person': 'Budi Santoso',
                'operational_hours': '08:00-23:00',
                'coordinates': '-8.6502,115.2169',
                'address': 'Jl. Legian No. 789',
                'phone': '+62-361-789012',
                'email': 'info@restaurantbali.com'
            }
        },
        'streets': ['Jl. Raya Kuta', 'Jl. Sunset Road', 'Jl. Legian'],
        'environments': [
            {'name': 'LINGKUNGAN KUTA', 'code': '01'},
            {'name': 'LINGKUNGAN LEGIAN', 'code': '02'}
        ],
        'landmarks': ['Monument Bali', 'Taman Sari'],
        'coordinates': [
            {'latitude': -8.6500, 'longitude': 115.2167},
            {'latitude': -8.6501, 'longitude': 115.2168}
        ],
        'total_businesses': 3,
        'total_streets': 3,
        'total_environments': 2,
        'total_landmarks': 2,
        'total_coordinates': 2
    }
    
    try:
        # Test download endpoint
        response = requests.post(
            'http://127.0.0.1:5000/download',
            json=test_data,
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            # Save the Excel file
            with open('test_output.xlsx', 'wb') as f:
                f.write(response.content)
            print("✅ Download successful! File saved as 'test_output.xlsx'")
        else:
            print(f"❌ Download failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_download() 