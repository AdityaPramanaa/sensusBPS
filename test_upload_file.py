import requests
import os

def test_upload():
    """Test the upload endpoint with a real image file"""
    
    # Check if test image exists
    test_image_path = "uploads/5171030005000103_WS.jpg"
    
    if not os.path.exists(test_image_path):
        print(f"❌ Test image not found: {test_image_path}")
        return
    
    try:
        # Prepare the file upload
        with open(test_image_path, 'rb') as f:
            files = {'file': (os.path.basename(test_image_path), f, 'image/jpeg')}
            
            # Test upload endpoint
            response = requests.post(
                'http://127.0.0.1:5000/upload',
                files=files
            )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Upload successful!")
            print(f"Response: {data}")
        else:
            print(f"❌ Upload failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_upload() 