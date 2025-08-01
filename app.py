import os
import numpy as np
import easyocr
import pandas as pd
from flask import Flask, render_template, request, send_file, jsonify
from werkzeug.utils import secure_filename
from PIL import Image
import io
import re
from datetime import datetime
import logging
import requests
import time
import base64

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}

# Initialize EasyOCR reader
reader = None

def get_reader():
    global reader
    if reader is None:
        # Use both Indonesian and English for better accuracy
        reader = easyocr.Reader(['id', 'en'], gpu=False, model_storage_directory='./models')
    return reader

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def preprocess_image(image):
    """Preprocess image for better OCR accuracy using PIL"""
    # Convert to grayscale
    gray = image.convert('L')
    
    # Resize image to make it larger for better OCR
    width, height = gray.size
    resized = gray.resize((width*2, height*2), Image.Resampling.LANCZOS)
    
    return resized

def validate_map_data(wss_data):
    """
    Validate that the extracted map data contains required fields
    Returns: (is_valid, missing_fields, message)
    """
    required_fields = ['map_id', 'province', 'regency', 'district', 'village']
    missing_fields = []
    
    for field in required_fields:
        value = wss_data.get(field, '').strip()
        if not value or value == 'Tidak ditemukan':
            missing_fields.append(field)
    
    if missing_fields:
        return False, missing_fields, f"Data map tidak lengkap. Field yang tidak ditemukan: {', '.join(missing_fields)}"
    
    # Additional validation for map_id format (should be 16 digits)
    map_id = wss_data.get('map_id', '')
    if not re.match(r'^\d{16}$', map_id):
        return False, ['map_id'], f"Map ID tidak valid. Format harus 16 digit angka. Ditemukan: {map_id}"
    
    return True, [], "Data map valid dan lengkap"

def search_business_info(business_name, location="Indonesia"):
    """
    Search business information from OpenStreetMap Nominatim API with improved accuracy
    Returns: dict with business details
    """
    try:
        # Clean business name for search
        clean_name = re.sub(r'[^\w\s]', '', business_name).strip()
        if len(clean_name) < 3:
            return {}
        
        # Search query with more specific location
        search_query = f"{clean_name}, {location}"
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': search_query,
            'format': 'json',
            'limit': 3,  # Get more results for better accuracy
            'addressdetails': 1,
            'extratags': 1
        }
        headers = {
            'User-Agent': 'WSS-Map-Extractor/1.0'
        }
        
        logger.info(f"Searching for business: {search_query}")
        response = requests.get(url, params=params, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            if data:
                # Try to find the best match
                best_result = None
                for result in data:
                    # Check if the result is actually a business/POI
                    if result.get('type') in ['node', 'way']:
                        best_result = result
                        break
                
                if not best_result:
                    best_result = data[0]  # Use first result if no specific business found
                
                address = best_result.get('display_name', '')
                
                # Extract detailed information
                address_details = best_result.get('address', {})
                extratags = best_result.get('extratags', {})
                
                # Get phone number from various sources
                phone = ''
                if 'phone' in address_details:
                    phone = address_details['phone']
                elif 'contact:phone' in extratags:
                    phone = extratags['contact:phone']
                
                # Get website from various sources
                website = ''
                if 'website' in address_details:
                    website = address_details['website']
                elif 'contact:website' in extratags:
                    website = extratags['contact:website']
                
                # Get opening hours from various sources
                opening_hours = ''
                if 'opening_hours' in address_details:
                    opening_hours = address_details['opening_hours']
                elif 'opening_hours' in extratags:
                    opening_hours = extratags['opening_hours']
                else:
                    # Try to find hours in display_name
                    hours_match = re.search(r'(\d{1,2}:\d{2}\s*[-–]\s*\d{1,2}:\d{2})', address)
                    if hours_match:
                        opening_hours = hours_match.group(1)
                
                # Determine business type from OSM tags
                business_type = 'general'
                if extratags.get('shop'):
                    business_type = extratags['shop']
                elif extratags.get('amenity'):
                    business_type = extratags['amenity']
                elif extratags.get('tourism'):
                    business_type = extratags['tourism']
                
                # Set default operational hours based on business type
                if not opening_hours:
                    if business_type in ['restaurant', 'cafe', 'fast_food']:
                        opening_hours = '08:00-22:00'
                    elif business_type in ['bank', 'atm']:
                        opening_hours = '08:00-16:00'
                    elif business_type in ['shop', 'supermarket', 'mall']:
                        opening_hours = '09:00-21:00'
                    elif business_type in ['hotel', 'guest_house']:
                        opening_hours = '24 Jam'
                    else:
                        opening_hours = '08:00-17:00'
                
                return {
                    'address': address,
                    'coordinates': f"{best_result.get('lat', '')}, {best_result.get('lon', '')}",
                    'phone': phone,
                    'website': website,
                    'operational_hours': opening_hours,
                    'contact_person': 'Hubungi langsung',  # Default since OSM doesn't provide contact person
                    'email': '',  # OSM doesn't provide email
                    'business_type': business_type
                }
        
        return {}
        
    except Exception as e:
        logger.error(f"Error searching business info: {e}")
        return {}

def estimate_kk_count_improved(name, business_details=None):
    """
    Improved KK count estimation based on environment type and business details
    """
    name_lower = name.lower()
    
    # Check if it's a residential area
    if any(word in name_lower for word in ['perumahan', 'kompleks', 'villa', 'rumah', 'permukiman', 'kampung', 'desa', 'kelurahan', 'lingkungan']):
        # Estimate based on typical residential density
        if 'perumahan' in name_lower or 'kompleks' in name_lower:
            return 150  # High density residential
        elif 'villa' in name_lower:
            return 50   # Low density residential
        elif 'lingkungan' in name_lower:
            # For lingkungan, estimate based on typical neighborhood size
            return 80   # Standard neighborhood
        else:
            return 100  # Standard residential
    
    # Check if it's commercial area
    elif any(word in name_lower for word in ['mall', 'pasar', 'toko', 'shop', 'market', 'plaza', 'center']):
        return 20  # Commercial areas have fewer KK
    
    # Check if it's industrial area
    elif any(word in name_lower for word in ['industri', 'factory', 'pabrik', 'kawasan']):
        return 100  # Industrial areas may have worker housing
    
    # Check if it's hotel/resort area
    elif any(word in name_lower for word in ['hotel', 'resort', 'wisata', 'tourism']):
        return 50  # Tourism areas
    
    # Check if it's office area
    elif any(word in name_lower for word in ['kantor', 'office', 'perkantoran', 'gedung']):
        return 30  # Office areas
    
    # If business details are available, use them for better estimation
    if business_details:
        business_count = len(business_details)
        if business_count > 20:
            return 80  # High business density
        elif business_count > 10:
            return 60  # Medium business density
        elif business_count > 5:
            return 40  # Low business density
        else:
            return 30  # Very low business density
    
    # Default estimation for unknown areas
    return 50

def estimate_btt_count_improved(name, kk_count):
    """
    Improved BTT count estimation based on KK count
    """
    # BTT is typically 90% of KK count
    return int(kk_count * 0.9)

def estimate_bku_count_improved(name, kk_count):
    """
    Improved BKU count estimation based on KK count
    """
    # BKU is typically 20% of KK count
    return int(kk_count * 0.2)

def estimate_business_count_improved(name, business_details=None):
    """
    Improved business count estimation
    """
    if business_details:
        return len(business_details)
    
    name_lower = name.lower()
    
    if any(word in name_lower for word in ['mall', 'pasar', 'toko']):
        return 20
    elif any(word in name_lower for word in ['industri', 'factory']):
        return 100
    elif any(word in name_lower for word in ['hotel', 'resort']):
        return 50
    else:
        return 10

def detect_residential_area(name, business_details=None):
    """
    Detect residential area type and estimate KK count based on area name and business details
    Returns: dict with area_type and estimated_kk
    """
    name_lower = name.lower()
    
    # High density residential indicators
    high_density_keywords = ['padat', 'kumuh', 'kampung', 'slum', 'dense', 'crowded', 'perumahan', 'komplek']
    if any(keyword in name_lower for keyword in high_density_keywords):
        return {
            'area_type': 'high_density_residential',
            'estimated_kk': 150  # High density areas have more KK
        }
    
    # Commercial area indicators
    commercial_keywords = ['pasar', 'mall', 'plaza', 'commercial', 'bisnis', 'usaha', 'toko', 'warung']
    if any(keyword in name_lower for keyword in commercial_keywords):
        return {
            'area_type': 'commercial',
            'estimated_kk': 80   # Commercial areas have fewer residential KK
        }
    
    # Industrial area indicators
    industrial_keywords = ['industri', 'pabrik', 'factory', 'industrial', 'kawasan industri']
    if any(keyword in name_lower for keyword in industrial_keywords):
        return {
            'area_type': 'industrial',
            'estimated_kk': 60   # Industrial areas have even fewer residential KK
        }
    
    # Low density residential indicators
    low_density_keywords = ['elite', 'mewah', 'luxury', 'villa', 'perumahan mewah', 'komplek mewah']
    if any(keyword in name_lower for keyword in low_density_keywords):
        return {
            'area_type': 'low_density_residential',
            'estimated_kk': 40   # Low density areas have fewer KK
        }
    
    # Default to standard residential
    return {
        'area_type': 'standard_residential',
        'estimated_kk': 100  # Standard residential area
    }

def detect_building_types(text):
    """
    Detect different types of buildings from OCR text
    Returns: dict with counts of different building types
    """
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
    
    lines = text.split('\n')
    
    # Keywords for different building types
    kosong_keywords = [
        'kosong', 'empty', 'vacant', 'tidak terisi', 'belum dihuni',
        'bangunan kosong', 'rumah kosong', 'gedung kosong', 'ruko kosong',
        'tidak ada penghuni', 'belum ada penghuni', 'masih kosong'
    ]
    
    bukan_tempat_tinggal_keywords = [
        'masjid', 'musholla', 'surau', 'gereja', 'kapel', 'pura', 'vihara', 'klenteng',
        'kantor', 'office', 'gedung perkantoran', 'balai desa', 'kantor desa',
        'sekolah', 'sd', 'smp', 'sma', 'universitas', 'kampus', 'madrasah',
        'rumah sakit', 'klinik', 'puskesmas', 'apotek', 'rumah ibadah',
        'tempat ibadah', 'worship', 'temple', 'church', 'mosque'
    ]
    
    bangunan_usaha_keywords = [
        'toko', 'warung', 'restoran', 'rumah makan', 'cafe', 'kafe',
        'bank', 'atm', 'spbu', 'gas station', 'salon', 'spa',
        'hotel', 'penginapan', 'guesthouse', 'resort', 'inn',
        'bengkel', 'workshop', 'garasi', 'showroom', 'dealer',
        'apotek', 'pharmacy', 'klinik', 'dental', 'gigi',
        'supermarket', 'minimarket', 'market', 'mall', 'plaza',
        'pasar', 'traditional market', 'pasar tradisional'
    ]
    
    kos_kosan_keywords = [
        'kos', 'kost', 'kostan', 'kos-kosan', 'kost-kostan',
        'boarding house', 'kontrakan', 'sewa kamar', 'kamar sewa',
        'rumah kos', 'gedung kos', 'asrama', 'dormitory',
        'kamar kost', 'kost putra', 'kost putri', 'kost campur'
    ]
    
    for line in lines:
        line_lower = line.lower().strip()
        if not line_lower:
            continue
            
        # Detect bangunan kosong
        if any(keyword in line_lower for keyword in kosong_keywords):
            building_name = re.sub(r'[^\w\s\-\.]', '', line).strip()
            if len(building_name) > 2:
                building_data['bangunan_kosong'] += 1
                building_data['details']['bangunan_kosong'].append(building_name)
        
        # Detect bangunan bukan tempat tinggal
        if any(keyword in line_lower for keyword in bukan_tempat_tinggal_keywords):
            building_name = re.sub(r'[^\w\s\-\.]', '', line).strip()
            if len(building_name) > 2:
                building_data['bangunan_bukan_tempat_tinggal'] += 1
                building_data['details']['bangunan_bukan_tempat_tinggal'].append(building_name)
        
        # Detect bangunan usaha
        if any(keyword in line_lower for keyword in bangunan_usaha_keywords):
            building_name = re.sub(r'[^\w\s\-\.]', '', line).strip()
            if len(building_name) > 2:
                building_data['bangunan_usaha'] += 1
                building_data['details']['bangunan_usaha'].append(building_name)
        
        # Detect kos-kosan
        if any(keyword in line_lower for keyword in kos_kosan_keywords):
            building_name = re.sub(r'[^\w\s\-\.]', '', line).strip()
            if len(building_name) > 2:
                building_data['kos_kosan'] += 1
                building_data['details']['kos_kosan'].append(building_name)
    
    return building_data

def extract_text_from_image(image_path):
    """Extract text from image using EasyOCR with improved preprocessing and error handling"""
    try:
        logger.info(f"Starting OCR for image: {image_path}")
        
        # Get OCR reader
        ocr_reader = get_reader()
        
        # Read image using PIL
        pil_image = Image.open(image_path)
        logger.info(f"Image size: {pil_image.size}")
        
        # Enhanced preprocessing for better OCR accuracy
        # Convert to grayscale
        gray_image = pil_image.convert('L')
        
        # Resize if image is too small (minimum 300px width)
        width, height = gray_image.size
        if width < 300:
            scale_factor = 300 / width
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            gray_image = gray_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            logger.info(f"Resized image to {new_width}x{new_height}")
        
        processed_array = np.array(gray_image)
        
        # Perform OCR with multiple attempts and different parameters
        logger.info("Performing OCR...")
        
        # First attempt: with paragraph=True
        results = ocr_reader.readtext(processed_array, paragraph=True)
        logger.info(f"First OCR attempt found {len(results)} text blocks")
        
        # If no results, try without paragraph
        if not results:
            logger.info("No results with paragraph=True, trying without...")
            results = ocr_reader.readtext(processed_array, paragraph=False)
            logger.info(f"Second OCR attempt found {len(results)} text blocks")
        
        # If still no results, try with different preprocessing
        if not results:
            logger.info("No results with grayscale, trying with original image...")
            original_array = np.array(pil_image)
            results = ocr_reader.readtext(original_array, paragraph=False)
            logger.info(f"Third OCR attempt found {len(results)} text blocks")
        
        # Extract text from results with very low confidence threshold
        text_lines = []
        for i, result in enumerate(results):
            logger.info(f"Processing result {i+1}: {result}")
            if isinstance(result, (tuple, list)) and len(result) >= 2:
                bbox, text = result[:2]
                confidence = result[2] if len(result) > 2 else 1.0
                logger.info(f"Text block {i+1}: '{text}' (confidence: {confidence:.2f})")
                # Lower confidence threshold to 0.01 (1%)
                if confidence > 0.01:
                    cleaned_text = text.strip()
                    if len(cleaned_text) > 0:  # Accept even single characters
                        text_lines.append(cleaned_text)
            else:
                logger.warning(f"Skipping result {i+1} with unexpected format: {result}")
        
        final_text = '\n'.join(text_lines)
        logger.info(f"Final extracted text ({len(text_lines)} lines):\n{final_text}")
        
        if not final_text.strip():
            logger.warning("No text extracted from image")
            return "Tidak ada teks yang dapat diekstrak dari gambar. Pastikan gambar jelas dan mengandung teks."
        
        return final_text
    except Exception as e:
        logger.error(f"Error in OCR: {e}")
        import traceback
        traceback.print_exc()
        return f"Error dalam proses OCR: {str(e)}"

def parse_wss_data(text):
    """Parse WSS map data from OCR text with improved accuracy"""
    logger.info(f"Parsing WSS data from text:\n{text}")
    data = {
        'map_id': '', 'province': '', 'regency': '', 'district': '', 'village': '', 'scale': '',
        'businesses': [], 'business_details': {}, # Added business_details
        'streets': [], 'environments': [], 'coordinates': [], 'landmarks': [],
        'business_types': {}, 'total_businesses': 0, 'total_streets': 0,
        'total_environments': 0, 'total_landmarks': 0,
        'building_data': {}  # Added building data
    }
    lines = text.split('\n')
    logger.info(f"Processing {len(lines)} lines of text")
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line: continue
        logger.info(f"Processing line {i+1}: '{line}'")
        
        # Extract Map ID (16 digit number) - improved regex for SLS format
        map_id_match = re.search(r'(\d{16})', line)
        if map_id_match:
            data['map_id'] = map_id_match.group(1)
            logger.info(f"Found Map ID: {data['map_id']}")
        
        # Extract administrative data with improved matching for format like "Provinsi : [51] BALI"
        if 'PROVINSI' in line.upper() or 'PROVINCE' in line.upper():
            # Try to extract province name after colon or bracket
            province_match = re.search(r'PROVINSI\s*:\s*\[?\d+\]?\s*([A-Z\s]+)', line, re.IGNORECASE)
            if province_match:
                data['province'] = province_match.group(1).strip()
                logger.info(f"Found Province: {data['province']}")
            else:
                # Try simpler pattern
                if 'BALI' in line.upper(): data['province'] = 'BALI'
                elif 'JAWA' in line.upper():
                    if 'TIMUR' in line.upper(): data['province'] = 'JAWA TIMUR'
                    elif 'TENGAH' in line.upper(): data['province'] = 'JAWA TENGAH'
                    elif 'BARAT' in line.upper(): data['province'] = 'JAWA BARAT'
                    else: data['province'] = 'JAWA'
                elif 'SUMATERA' in line.upper() or 'SUMATRA' in line.upper(): data['province'] = 'SUMATERA'
                elif 'KALIMANTAN' in line.upper(): data['province'] = 'KALIMANTAN'
                elif 'SULAWESI' in line.upper(): data['province'] = 'SULAWESI'
                elif 'PAPUA' in line.upper(): data['province'] = 'PAPUA'
                elif 'MALUKU' in line.upper(): data['province'] = 'MALUKU'
                elif 'NUSA TENGGARA' in line.upper(): data['province'] = 'NUSA TENGGARA'
        
        if 'KABUPATEN' in line.upper() or 'KOTA' in line.upper() or 'REGENCY' in line.upper():
            # Try to extract regency name after colon or bracket
            regency_match = re.search(r'(?:KABUPATEN|KOTA)\s*:\s*\[?\d+\]?\s*([A-Z\s]+)', line, re.IGNORECASE)
            if regency_match:
                data['regency'] = regency_match.group(1).strip()
                logger.info(f"Found Regency: {data['regency']}")
            else:
                # Try simpler pattern
                if 'DENPASAR' in line.upper(): data['regency'] = 'DENPASAR'
                elif 'BADUNG' in line.upper(): data['regency'] = 'BADUNG'
                elif 'GIANYAR' in line.upper(): data['regency'] = 'GIANYAR'
                elif 'KLUNGKUNG' in line.upper(): data['regency'] = 'KLUNGKUNG'
                elif 'BANGLI' in line.upper(): data['regency'] = 'BANGLI'
                elif 'KARANGASEM' in line.upper(): data['regency'] = 'KARANGASEM'
                elif 'BULELENG' in line.upper(): data['regency'] = 'BULELENG'
                elif 'JEMBRANA' in line.upper(): data['regency'] = 'JEMBRANA'
                elif 'TABANAN' in line.upper(): data['regency'] = 'TABANAN'
        
        if 'KECAMATAN' in line.upper() or 'DISTRICT' in line.upper():
            # Try to extract district name after colon or bracket
            district_match = re.search(r'KECAMATAN\s*:\s*\[?\d+\]?\s*([A-Z\s]+)', line, re.IGNORECASE)
            if district_match:
                data['district'] = district_match.group(1).strip()
                logger.info(f"Found District: {data['district']}")
            else:
                # Try simpler pattern
                if 'DENPASAR BARAT' in line.upper(): data['district'] = 'DENPASAR BARAT'
                elif 'DENPASAR TIMUR' in line.upper(): data['district'] = 'DENPASAR TIMUR'
                elif 'DENPASAR SELATAN' in line.upper(): data['district'] = 'DENPASAR SELATAN'
                elif 'DENPASAR UTARA' in line.upper(): data['district'] = 'DENPASAR UTARA'
        
        if 'DESA' in line.upper() or 'KELURAHAN' in line.upper() or 'VILLAGE' in line.upper():
            # Try to extract village name after colon or bracket
            village_match = re.search(r'(?:DESA|KELURAHAN)\s*:\s*\[?\d+\]?\s*([A-Z\s]+)', line, re.IGNORECASE)
            if village_match:
                data['village'] = village_match.group(1).strip()
                logger.info(f"Found Village: {data['village']}")
            else:
                # Try simpler pattern
                if 'DAUH PURI' in line.upper(): data['village'] = 'DAUH PURI'
                elif 'KELURAHAN' in line.upper():
                    kel_match = re.search(r'KELURAHAN\s+([A-Z\s]+)', line, re.IGNORECASE)
                    if kel_match: data['village'] = kel_match.group(1).strip()
                elif 'DESA' in line.upper():
                    desa_match = re.search(r'DESA\s+([A-Z\s]+)', line, re.IGNORECASE)
                    if desa_match: data['village'] = desa_match.group(1).strip()
        
        # Extract scale with improved pattern
        if 'SKALA' in line.upper():
            scale_match = re.search(r'SKALA\s*(\d+:\d+)', line, re.IGNORECASE)
            if scale_match:
                data['scale'] = scale_match.group(1)
                logger.info(f"Found Scale: {data['scale']}")
            else:
                # Try to find scale in format like "1:353"
                scale_simple = re.search(r'(\d+:\d+)', line)
                if scale_simple:
                    data['scale'] = scale_simple.group(1)
                    logger.info(f"Found Scale: {data['scale']}")
                
        # Extract business names with expanded keywords and categorize them
        business_keywords = {
            'mall': ['mall', 'plaza', 'center', 'pasar', 'supermarket', 'hypermarket'],
            'pasar': ['pasar', 'market', 'traditional market', 'pasar tradisional', 'pasar induk', 'pasar besar'],
            'hotel': ['hotel', 'resort', 'inn', 'guesthouse', 'penginapan'],
            'restaurant': ['restaurant', 'cafe', 'warung', 'rumah makan', 'restoran'],
            'bank': ['bank', 'atm', 'bca', 'mandiri', 'bni', 'bri'],
            'hospital': ['hospital', 'rumah sakit', 'klinik', 'apotek', 'puskesmas'],
            'school': ['school', 'sekolah', 'universitas', 'kampus', 'sd', 'smp', 'sma'],
            'office': ['office', 'kantor', 'perkantoran', 'gedung'],
            'gas_station': ['gas', 'spbu', 'pertamina', 'shell', 'bp'],
            'car_wash': ['car wash', 'cuci mobil', 'cuci motor'],
            'salon': ['salon', 'spa', 'beauty', 'kecantikan'],
            'store': ['toko', 'store', 'shop', 'market', 'warung'],
            'motorcycle': ['motor', 'honda', 'yamaha', 'suzuki', 'kawasaki'],
            'dental': ['dental', 'gigi', 'drg', 'dokter gigi'],
            'music': ['music', 'gitar', 'piano', 'alat musik'],
            'battery': ['battery', 'aki', 'accu', 'baterai'],
            'pharmacy': ['pharmacy', 'apotek', 'kimia farma', 'century'],
            'mosque': ['mosque', 'masjid', 'musholla', 'surau'],
            'church': ['church', 'gereja', 'kapel'],
            'temple': ['temple', 'pura', 'vihara', 'klenteng'],
            'park': ['park', 'taman', 'alun-alun', 'lapangan']
        }
        
        business_found = False
        for business_type, keywords in business_keywords.items():
            if any(keyword.lower() in line.lower() for keyword in keywords):
                business_name = re.sub(r'[^\w\s\-\.]', '', line).strip()
                if len(business_name) > 2 and business_name not in data['businesses']:
                    data['businesses'].append(business_name)
                    data['business_types'][business_name] = business_type
                    
                    # Search for business information from maps
                    logger.info(f"Searching for business info: {business_name}")
                    business_info = search_business_info(business_name, data.get('regency', 'Indonesia'))
                    
                    # Add detailed business information
                    data['business_details'][business_name] = {
                        'type': business_type,
                        'contact_person': business_info.get('contact_person', 'Hubungi langsung'),
                        'operational_hours': business_info.get('operational_hours', '08:00-17:00'),
                        'coordinates': business_info.get('coordinates', ''),
                        'address': business_info.get('address', ''),
                        'phone': business_info.get('phone', ''),
                        'email': business_info.get('email', ''),
                        'business_type_osm': business_info.get('business_type', 'general')
                    }
                    
                    business_found = True
                    logger.info(f"Found Business: {business_name} (Type: {business_type})")
                    break
        
        # If no specific type found, categorize as general business
        if not business_found and any(keyword.lower() in line.lower() for keyword in ['warung', 'toko', 'restaurant', 'store', 'shop', 'gallery', 'motor', 'dental', 'battery', 'music', 'hotel', 'mall', 'market', 'cafe', 'bank', 'pharmacy', 'hospital', 'school', 'university', 'office', 'factory', 'warehouse', 'gas station', 'car wash', 'salon', 'spa']):
            business_name = re.sub(r'[^\w\s\-\.]', '', line).strip()
            if len(business_name) > 2 and business_name not in data['businesses']:
                data['businesses'].append(business_name)
                data['business_types'][business_name] = 'general'
                
                # Search for business information from maps
                logger.info(f"Searching for business info: {business_name}")
                business_info = search_business_info(business_name, data.get('regency', 'Indonesia'))
                
                # Add detailed business information
                data['business_details'][business_name] = {
                    'type': 'general',
                    'contact_person': business_info.get('contact_person', 'Hubungi langsung'),
                    'operational_hours': business_info.get('operational_hours', '08:00-17:00'),
                    'coordinates': business_info.get('coordinates', ''),
                    'address': business_info.get('address', ''),
                    'phone': business_info.get('phone', ''),
                    'email': business_info.get('email', '')
                }
                
                logger.info(f"Found General Business: {business_name}")
                
        # Extract street names with improved regex
        if 'Jl.' in line or 'Jalan' in line or 'Jl ' in line:
            street_match = re.search(r'(Jl\.?\s*[A-Za-z\s]+)', line)
            if street_match:
                street_name = street_match.group(1).strip()
                if street_name not in data['streets']:
                    data['streets'].append(street_name)
                    logger.info(f"Found Street: {street_name}")
            else:
                # Try to extract street name after "Jalan"
                jalan_match = re.search(r'Jalan\s+([A-Za-z\s]+)', line)
                if jalan_match:
                    street_name = f"Jl. {jalan_match.group(1).strip()}"
                    if street_name not in data['streets']:
                        data['streets'].append(street_name)
                        logger.info(f"Found Street: {street_name}")
                
        # Extract environment names with improved regex
        if 'LINGKUNGAN' in line.upper():
            env_match = re.search(r'LINGKUNGAN\s+([A-Z\s]+)\s*\[(\d+)\]', line, re.IGNORECASE)
            if env_match:
                env_name = env_match.group(1).strip()
                env_code = env_match.group(2)
                # Check if environment already exists
                if not any(env['name'] == env_name and env['code'] == env_code for env in data['environments']):
                    data['environments'].append({
                        'name': env_name,
                        'code': env_code
                    })
                    logger.info(f"Found Environment: {env_name} [{env_code}]")
            else:
                # Try simpler pattern
                env_simple_match = re.search(r'LINGKUNGAN\s+([A-Z\s]+)', line, re.IGNORECASE)
                if env_simple_match:
                    env_name = env_simple_match.group(1).strip()
                    # Generate a simple code
                    env_code = str(len(data['environments']) + 1).zfill(2)
                    if not any(env['name'] == env_name for env in data['environments']):
                        data['environments'].append({
                            'name': env_name,
                            'code': env_code
                        })
                        logger.info(f"Found Environment: {env_name} [{env_code}]")
                
        # Extract coordinates if present
        coord_match = re.search(r'(-?\d+\.\d+),\s*(-?\d+\.\d+)', line)
        if coord_match:
            lat = float(coord_match.group(1))
            lon = float(coord_match.group(2))
            coord_data = {'latitude': lat, 'longitude': lon}
            if coord_data not in data['coordinates']:
                data['coordinates'].append(coord_data)
                logger.info(f"Found Coordinates: {lat}, {lon}")
                
        # Extract landmarks
        landmark_keywords = ['Monument', 'Park', 'Square', 'Temple', 'Church', 'Mosque', 'Museum', 'Tugu', 'Patung', 'Alun-alun']
        if any(keyword.lower() in line.lower() for keyword in landmark_keywords):
            landmark_name = re.sub(r'[^\w\s\-\.]', '', line).strip()
            if len(landmark_name) > 2 and landmark_name not in data['landmarks']:
                data['landmarks'].append(landmark_name)
                logger.info(f"Found Landmark: {landmark_name}")
    
    data['total_businesses'] = len(data['businesses'])
    data['total_streets'] = len(data['streets'])
    data['total_environments'] = len(data['environments'])
    data['total_landmarks'] = len(data['landmarks'])
    
    # Detect building types
    building_data = detect_building_types(text)
    data['building_data'] = building_data
    logger.info(f"Building data detected: {building_data}")
    
    logger.info(f"Final parsed data: {data}")
    return data

def generate_segments_from_data(wss_data):
    """Generate segments automatically based on extracted data with improved residential detection"""
    segments = []
    
    # Generate segments based on environments
    for i, env in enumerate(wss_data.get('environments', []), 1):
        # Detect area type and estimate KK count
        area_info = detect_residential_area(env['name'], wss_data.get('business_details', {}))
        area_type = area_info['area_type']
        estimated_kk = area_info['estimated_kk']
        
        # Adjust estimates based on area type
        if area_type == 'high_density_residential':
            kk_count = estimated_kk
            btt_count = int(kk_count * 0.95)  # High density has more BTT
            bku_count = int(kk_count * 0.25)  # More businesses in high density
        elif area_type == 'low_density_residential':
            kk_count = estimated_kk
            btt_count = int(kk_count * 0.85)  # Lower BTT ratio
            bku_count = int(kk_count * 0.15)  # Fewer businesses
        elif area_type == 'commercial':
            kk_count = estimated_kk
            btt_count = int(kk_count * 0.3)   # Few residential buildings
            bku_count = int(kk_count * 0.8)   # Many businesses
        elif area_type == 'industrial':
            kk_count = estimated_kk
            btt_count = int(kk_count * 0.7)   # Worker housing
            bku_count = int(kk_count * 0.4)   # Industrial businesses
        else:  # standard_residential
            kk_count = estimated_kk
            btt_count = int(kk_count * 0.9)   # Standard ratio
            bku_count = int(kk_count * 0.2)   # Standard ratio
        
        load_code = determine_dominant_load(env['name'])
        segments.append({
            'no': i,
            'no_segmen': f"SEG{i:02d}",
            'muatan_dominan': get_dominant_load_description(load_code),
            'nama_wilayah': env['name'],
            'jumlah_shift': '',  # Let user fill
            'jam_operasional': '',  # Let user fill
            'contact_person': '',  # Let user fill
            'muatan_kk': kk_count,
            'btt': btt_count,
            'btt_kosong': max(0, kk_count - btt_count),  # Empty BTT
            'bku': bku_count,
            'bbtt_non_usaha': max(0, int(kk_count * 0.05)),  # Non-business buildings
            'muatan_usaha': estimate_business_count_improved(env['name'], wss_data.get('business_details', {})),
            'total_muatan': 0,  # Will be calculated
            'kode_sub_sls': f"{int(env['code']):02d}",
            'area_type': area_type  # Add area type for reference
        })
    
    # Generate segments based on streets if no environments found
    if not segments and wss_data.get('streets'):
        for i, street in enumerate(wss_data['streets'], 1):
            # Detect area type and estimate KK count
            area_info = detect_residential_area(street, wss_data.get('business_details', {}))
            area_type = area_info['area_type']
            estimated_kk = area_info['estimated_kk']
            
            # Adjust estimates based on area type
            if area_type == 'high_density_residential':
                kk_count = estimated_kk
                btt_count = int(kk_count * 0.95)
                bku_count = int(kk_count * 0.25)
            elif area_type == 'low_density_residential':
                kk_count = estimated_kk
                btt_count = int(kk_count * 0.85)
                bku_count = int(kk_count * 0.15)
            elif area_type == 'commercial':
                kk_count = estimated_kk
                btt_count = int(kk_count * 0.3)
                bku_count = int(kk_count * 0.8)
            elif area_type == 'industrial':
                kk_count = estimated_kk
                btt_count = int(kk_count * 0.7)
                bku_count = int(kk_count * 0.4)
            else:  # standard_residential
                kk_count = estimated_kk
                btt_count = int(kk_count * 0.9)
                bku_count = int(kk_count * 0.2)
            
            load_code = determine_dominant_load(street)
            segments.append({
                'no': i,
                'no_segmen': f"SEG{i:02d}",
                'muatan_dominan': get_dominant_load_description(load_code),
                'nama_wilayah': street,
                'jumlah_shift': '',  # Let user fill
                'jam_operasional': '',  # Let user fill
                'contact_person': '',  # Let user fill
                'muatan_kk': kk_count,
                'btt': btt_count,
                'btt_kosong': max(0, kk_count - btt_count),
                'bku': bku_count,
                'bbtt_non_usaha': max(0, int(kk_count * 0.05)),
                'muatan_usaha': estimate_business_count_improved(street, wss_data.get('business_details', {})),
                'total_muatan': 0,  # Will be calculated
                'kode_sub_sls': f"{i:02d}",
                'area_type': area_type
            })
    
    # If still no segments, create a default one
    if not segments:
        area_info = detect_residential_area(wss_data.get('village', 'Wilayah Tidak Diketahui'), wss_data.get('business_details', {}))
        area_type = area_info['area_type']
        estimated_kk = area_info['estimated_kk']
        kk_count = estimated_kk
        btt_count = int(kk_count * 0.9)
        bku_count = int(kk_count * 0.2)
        
        load_code = determine_dominant_load(wss_data.get('village', 'Wilayah Tidak Diketahui'))
        segments.append({
            'no': 1,
            'no_segmen': 'SEG01',
            'muatan_dominan': get_dominant_load_description(load_code),
            'nama_wilayah': wss_data.get('village', 'Wilayah Tidak Diketahui'),
            'jumlah_shift': '',  # Let user fill
            'jam_operasional': '',  # Let user fill
            'contact_person': '',  # Let user fill
            'muatan_kk': kk_count,
            'btt': btt_count,
            'btt_kosong': max(0, kk_count - btt_count),
            'bku': bku_count,
            'bbtt_non_usaha': max(0, int(kk_count * 0.05)),
            'muatan_usaha': estimate_business_count_improved(wss_data.get('village', 'Wilayah Tidak Diketahui'), wss_data.get('business_details', {})),
            'total_muatan': 0,  # Will be calculated
            'kode_sub_sls': '01',
            'area_type': area_type
        })
    
    # Calculate total muatan for each segment
    for segment in segments:
        segment['total_muatan'] = max(segment['muatan_kk'], segment['btt']) + segment['btt_kosong'] + segment['bbtt_non_usaha'] + segment['muatan_usaha']
    
    return segments

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

def generate_excel_template(wss_data):
    """Generate Excel template based on WSS data with proper BLOK III format matching the image"""
    
    # Generate segments automatically
    segments = generate_segments_from_data(wss_data)
    
    # Create a new Excel workbook
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Create BLOK III worksheet with proper format matching the image
        blok3_data = []
        
        # Add header row with proper column names matching the image
        header_row = {
            'No (1)': 'No (1)',
            'No Segmen (2)': 'No Segmen (2)',
            'Muatan Dominan Segmen *) (3)': 'Muatan Dominan Segmen *) (3)',
            'Nama Wilayah Konsentrasi Ekonomi (4a)': 'Nama Wilayah Konsentrasi Ekonomi (4a)',
            'Jumlah Shift Pada Wilayah Konsentrasi Ekonomi (4b)': 'Jumlah Shift Pada Wilayah Konsentrasi Ekonomi (4b)',
            'Jam Operasional (4c)': 'Jam Operasional (4c)',
            'Contact Person Telepon/ Email (4d)': 'Contact Person Telepon/ Email (4d)',
            'Perkiraan Jumlah Muatan KK (Keluarga) (5)': 'Perkiraan Jumlah Muatan KK (Keluarga) (5)',
            'Bangunan Tempat Tinggal (BTT) (6)': 'Bangunan Tempat Tinggal (BTT) (6)',
            'Bangunan Tempat Tinggal Kosong (BTT Kosong) (7)': 'Bangunan Tempat Tinggal Kosong (BTT Kosong) (7)',
            'Bangunan Khusus Usaha (BKU) (8)': 'Bangunan Khusus Usaha (BKU) (8)',
            'Bangunan Bukan Tempat Tinggal (BBTT non Usaha) (9)': 'Bangunan Bukan Tempat Tinggal (BBTT non Usaha) (9)',
            'Perkiraan Jumlah Muatan Usaha (10)': 'Perkiraan Jumlah Muatan Usaha (10)',
            'Total Muatan (11)': 'Total Muatan (11)',
            'Kode Sub-SLS (Baru) (12)': 'Kode Sub-SLS (Baru) (12)'
        }
        blok3_data.append(header_row)
        
        # Add segments data
        for segment in segments:
            # Calculate total muatan using the formula from the image
            # Formula: (Maks(Kol 5, Kol 6) + Kol 7 + Kol 9 + Kol 10)
            kol5 = segment['muatan_kk']  # KK count
            kol6 = segment['btt']        # BTT count
            kol7 = segment['btt_kosong'] # BTT Kosong count
            kol9 = segment['bbtt_non_usaha']  # BBTT non Usaha count
            kol10 = segment['muatan_usaha']   # Usaha count
            
            # Calculate max of Kol 5 and Kol 6
            max_kol5_kol6 = max(kol5, kol6)
            total_muatan = max_kol5_kol6 + kol7 + kol9 + kol10
            
            blok3_data.append({
                'No (1)': segment['no'],
                'No Segmen (2)': segment['no_segmen'],
                'Muatan Dominan Segmen *) (3)': segment['muatan_dominan'],
                'Nama Wilayah Konsentrasi Ekonomi (4a)': segment['nama_wilayah'],
                'Jumlah Shift Pada Wilayah Konsentrasi Ekonomi (4b)': segment['jumlah_shift'],
                'Jam Operasional (4c)': segment['jam_operasional'],
                'Contact Person Telepon/ Email (4d)': segment['contact_person'],
                'Perkiraan Jumlah Muatan KK (Keluarga) (5)': segment['muatan_kk'],
                'Bangunan Tempat Tinggal (BTT) (6)': segment['btt'],
                'Bangunan Tempat Tinggal Kosong (BTT Kosong) (7)': segment['btt_kosong'],
                'Bangunan Khusus Usaha (BKU) (8)': segment['bku'],
                'Bangunan Bukan Tempat Tinggal (BBTT non Usaha) (9)': segment['bbtt_non_usaha'],
                'Perkiraan Jumlah Muatan Usaha (10)': segment['muatan_usaha'],
                'Total Muatan (11)': total_muatan,
                'Kode Sub-SLS (Baru) (12)': segment['kode_sub_sls']
            })
        
        # Add empty rows for manual entry (matching the image format)
        for i in range(10):  # Add more empty rows for manual entry
            blok3_data.append({
                'No (1)': '',
                'No Segmen (2)': '',
                'Muatan Dominan Segmen *) (3)': '',
                'Nama Wilayah Konsentrasi Ekonomi (4a)': '',
                'Jumlah Shift Pada Wilayah Konsentrasi Ekonomi (4b)': '',
                'Jam Operasional (4c)': '',
                'Contact Person Telepon/ Email (4d)': '',
                'Perkiraan Jumlah Muatan KK (Keluarga) (5)': '',
                'Bangunan Tempat Tinggal (BTT) (6)': '',
                'Bangunan Tempat Tinggal Kosong (BTT Kosong) (7)': '',
                'Bangunan Khusus Usaha (BKU) (8)': '',
                'Bangunan Bukan Tempat Tinggal (BBTT non Usaha) (9)': '',
                'Perkiraan Jumlah Muatan Usaha (10)': '',
                'Total Muatan (11)': '',
                'Kode Sub-SLS (Baru) (12)': ''
            })
        
        df_blok3 = pd.DataFrame(blok3_data)
        df_blok3.to_excel(writer, sheet_name='BLOK III - LEMBAR KERJA PENGHITUNGAN MUATAN', index=False)
        
        # Create detailed business information sheet
        business_details = []
        for business_name in wss_data.get('businesses', []):
            business_detail = wss_data.get('business_details', {}).get(business_name, {})
            business_details.append({
                'Nama Bisnis': business_name,
                'Tipe Bisnis': business_detail.get('type', 'general'),
                'Contact Person': business_detail.get('contact_person', ''),
                'Jam Operasional': business_detail.get('operational_hours', ''),
                'Koordinat (Decimal)': business_detail.get('coordinates_decimal', business_detail.get('coordinates', '')),
                'Koordinat (DMS)': business_detail.get('coordinates_dms', ''),
                'Latitude': business_detail.get('latitude', ''),
                'Longitude': business_detail.get('longitude', ''),
                'Link Google Maps': business_detail.get('google_maps_link', ''),
                'Link OpenStreetMap': business_detail.get('osm_link', ''),
                'Tipe Lokasi': business_detail.get('location_type', ''),
                'Provinsi': business_detail.get('province', ''),
                'Kabupaten': business_detail.get('regency', ''),
                'Kecamatan': business_detail.get('district', ''),
                'Desa': business_detail.get('village', ''),
                'Akurasi': business_detail.get('accuracy', 'low'),
                'Tervalidasi': business_detail.get('validated', False),
                'Alamat': business_detail.get('address', ''),
                'Telepon': business_detail.get('phone', ''),
                'Email': business_detail.get('email', ''),
                'Catatan': 'Koordinat yang pasti dengan validasi dan presisi tinggi'
            })
        
        # Create economic centers information sheet
        economic_centers_details = []
        for center in wss_data.get('economic_centers', []):
            economic_centers_details.append({
                'Nama Pusat Ekonomi': center.get('name', ''),
                'Tipe Pusat': center.get('type', ''),
                'Perkiraan UMKM': center.get('estimated_umkm', 0),
                'Lingkungan': center.get('environment', ''),
                'Tipe Area': center.get('area_type', ''),
                'Konteks': center.get('context', 'Pusat ekonomi yang berisi multiple UMKM'),
                'Contact Person': center.get('contact_person', ''),
                'Jam Operasional': center.get('operational_hours', ''),
                'Koordinat (Decimal)': center.get('coordinates_decimal', center.get('coordinates', '')),
                'Koordinat (DMS)': center.get('coordinates_dms', ''),
                'Latitude': center.get('latitude', ''),
                'Longitude': center.get('longitude', ''),
                'Link Google Maps': center.get('google_maps_link', ''),
                'Link OpenStreetMap': center.get('osm_link', ''),
                'Tipe Lokasi': center.get('location_type', ''),
                'Provinsi': center.get('province', ''),
                'Kabupaten': center.get('regency', ''),
                'Kecamatan': center.get('district', ''),
                'Desa': center.get('village', ''),
                'Akurasi': center.get('accuracy', 'low'),
                'Tervalidasi': center.get('validated', False),
                'Alamat': center.get('address', ''),
                'Telepon': center.get('phone', ''),
                'Email': center.get('email', ''),
                'Catatan': 'Pusat ekonomi dengan koordinat yang pasti sesuai konteks lingkungan'
            })
        
        # Add empty rows for additional businesses
        for i in range(10):
            business_details.append({
                'Nama Bisnis': '',
                'Tipe Bisnis': '',
                'Contact Person': '',
                'Jam Operasional': '',
                'Koordinat': '',
                'Alamat': '',
                'Telepon': '',
                'Email': '',
                'Catatan': ''
            })
        
        df_business = pd.DataFrame(business_details)
        df_business.to_excel(writer, sheet_name='Detail Bisnis', index=False)
        
        # Add economic centers sheet if there are any
        if economic_centers_details:
            df_economic_centers = pd.DataFrame(economic_centers_details)
            df_economic_centers.to_excel(writer, sheet_name='Pusat Ekonomi', index=False)
        
        # Add building data sheet if there are any buildings detected
        building_data = wss_data.get('building_data', {})
        if building_data and (building_data.get('bangunan_kosong', 0) > 0 or 
                            building_data.get('bangunan_bukan_tempat_tinggal', 0) > 0 or
                            building_data.get('bangunan_usaha', 0) > 0 or
                            building_data.get('kos_kosan', 0) > 0):
            
            building_details = []
            
            # Add bangunan kosong
            for building in building_data.get('details', {}).get('bangunan_kosong', []):
                building_details.append({
                    'Tipe Bangunan': 'Bangunan Kosong',
                    'Nama Bangunan': building,
                    'Jumlah': 1,
                    'Kategori': 'Tidak Terisi',
                    'Catatan': 'Bangunan yang tidak terisi atau belum dihuni'
                })
            
            # Add bangunan bukan tempat tinggal
            for building in building_data.get('details', {}).get('bangunan_bukan_tempat_tinggal', []):
                building_details.append({
                    'Tipe Bangunan': 'Bangunan Bukan Tempat Tinggal',
                    'Nama Bangunan': building,
                    'Jumlah': 1,
                    'Kategori': 'Fasilitas Umum',
                    'Catatan': 'Masjid, sekolah, kantor, dll'
                })
            
            # Add bangunan usaha
            for building in building_data.get('details', {}).get('bangunan_usaha', []):
                building_details.append({
                    'Tipe Bangunan': 'Bangunan Usaha',
                    'Nama Bangunan': building,
                    'Jumlah': 1,
                    'Kategori': 'Komersial',
                    'Catatan': 'Toko, warung, restoran, dll'
                })
            
            # Add kos-kosan
            for building in building_data.get('details', {}).get('kos_kosan', []):
                building_details.append({
                    'Tipe Bangunan': 'Kos-kosan',
                    'Nama Bangunan': building,
                    'Jumlah': 1,
                    'Kategori': 'Tempat Tinggal',
                    'Catatan': 'Tempat tinggal sewa/kontrakan'
                })
            
            # Add empty rows for manual entry
            for i in range(5):
                building_details.append({
                    'Tipe Bangunan': '',
                    'Nama Bangunan': '',
                    'Jumlah': '',
                    'Kategori': '',
                    'Catatan': ''
                })
            
            df_building = pd.DataFrame(building_details)
            df_building.to_excel(writer, sheet_name='Data Bangunan', index=False)
        
        # Create header information sheet
        header_data = {
            'Map ID': wss_data.get('map_id', ''),
            'Province': wss_data.get('province', ''),
            'Regency': wss_data.get('regency', ''),
            'District': wss_data.get('district', ''),
            'Village': wss_data.get('village', ''),
            'Scale': wss_data.get('scale', ''),
            'Processing Date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'OCR Engine': 'EasyOCR (Free & Accurate)',
            'Total Businesses Found': len(wss_data.get('businesses', [])),
            'Total Streets Found': len(wss_data.get('streets', [])),
            'Total Environments': len(wss_data.get('environments', [])),
            'Total Segments Generated': len(segments),
            'Total Bangunan Kosong': building_data.get('bangunan_kosong', 0),
            'Total Bangunan Bukan Tempat Tinggal': building_data.get('bangunan_bukan_tempat_tinggal', 0),
            'Total Bangunan Usaha': building_data.get('bangunan_usaha', 0),
            'Total Kos-kosan': building_data.get('kos_kosan', 0),
            'Formula Total Muatan': '(Maks(Kol 5, Kol 6) + Kol 7 + Kol 9 + Kol 10)',
            'Note': 'Diisi jika kolom (3) = 8-13 dan selain 11'
        }
        
        df_header = pd.DataFrame([header_data])
        df_header.to_excel(writer, sheet_name='Informasi Peta', index=False)
        
        # Get the workbook to apply formatting
        workbook = writer.book
        
        # Apply formatting to BLOK III sheet
        worksheet = writer.sheets['BLOK III - LEMBAR KERJA PENGHITUNGAN MUATAN']
        
        # Auto-adjust column widths
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
        
        # Add note about conditional filling
        worksheet['A' + str(len(blok3_data) + 3)] = 'Note: Diisi jika kolom (3) = 8-13 dan selain 11'
        worksheet['A' + str(len(blok3_data) + 4)] = 'Formula Total Muatan: (Maks(Kol 5, Kol 6) + Kol 7 + Kol 9 + Kol 10)'
        
    output.seek(0)
    return output

def extract_contextual_data(text, target_environment=None):
    """
    Extract data contextually based on specific areas/environments within the map
    Args:
        text: OCR extracted text
        target_environment: Specific environment to focus on (e.g., 'perkambingan', 'perumahan', 'komersial')
    Returns:
        dict: Contextual data for the specified environment
    """
    logger.info(f"Extracting contextual data for environment: {target_environment}")
    
    contextual_data = {
        'target_environment': target_environment,
        'businesses': [],
        'business_details': {},
        'streets': [],
        'landmarks': [],
        'coordinates': [],
        'area_type': '',
        'estimated_kk': 0,
        'dominant_load': '',
        'total_businesses': 0,
        'total_streets': 0,
        'total_landmarks': 0
    }
    
    lines = text.split('\n')
    in_target_area = False
    area_context = []
    
    # Define environment keywords for contextual extraction
    environment_keywords = {
        'perkambingan': ['perkambingan', 'kambing', 'ternak', 'peternakan', 'farm'],
        'perumahan': ['perumahan', 'rumah', 'housing', 'residential', 'permukiman'],
        'komersial': ['komersial', 'commercial', 'bisnis', 'business', 'toko', 'mall'],
        'industri': ['industri', 'industrial', 'pabrik', 'factory', 'kawasan industri'],
        'pendidikan': ['pendidikan', 'education', 'sekolah', 'school', 'universitas'],
        'kesehatan': ['kesehatan', 'health', 'rumah sakit', 'hospital', 'klinik'],
        'pariwisata': ['pariwisata', 'tourism', 'hotel', 'resort', 'wisata'],
        'pertanian': ['pertanian', 'agriculture', 'sawah', 'ladang', 'kebun'],
        'perikanan': ['perikanan', 'fishery', 'tambak', 'kolam', 'ikan'],
        'kehutanan': ['kehutanan', 'forestry', 'hutan', 'forest', 'kayu']
    }
    
    # If no specific target, try to detect the main environment type
    if not target_environment:
        for env_type, keywords in environment_keywords.items():
            for keyword in keywords:
                if keyword.lower() in text.lower():
                    target_environment = env_type
                    logger.info(f"Detected target environment: {target_environment}")
                    break
            if target_environment:
                break
    
    # If still no target, default to residential
    if not target_environment:
        target_environment = 'perumahan'
        logger.info(f"Defaulting to environment: {target_environment}")
    
    contextual_data['target_environment'] = target_environment
    
    # Extract data only from the target environment area
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
            
        # Check if we're entering the target environment area
        target_keywords = environment_keywords.get(target_environment, [])
        if any(keyword.lower() in line.lower() for keyword in target_keywords):
            in_target_area = True
            area_context.append(line)
            logger.info(f"Entering target area: {line}")
            continue
        
        # If we're in the target area, extract relevant data
        if in_target_area:
            area_context.append(line)
            
            # Extract business names within the target area
            business_keywords = {
                'mall': ['mall', 'plaza', 'center', 'pasar', 'supermarket', 'hypermarket'],
                'pasar': ['pasar', 'market', 'traditional market', 'pasar tradisional', 'pasar induk', 'pasar besar'],
                'hotel': ['hotel', 'resort', 'inn', 'guesthouse', 'penginapan'],
                'restaurant': ['restaurant', 'cafe', 'warung', 'rumah makan', 'restoran'],
                'bank': ['bank', 'atm', 'bca', 'mandiri', 'bni', 'bri'],
                'hospital': ['hospital', 'rumah sakit', 'klinik', 'apotek', 'puskesmas'],
                'school': ['school', 'sekolah', 'universitas', 'kampus', 'sd', 'smp', 'sma'],
                'office': ['office', 'kantor', 'perkantoran', 'gedung'],
                'gas_station': ['gas', 'spbu', 'pertamina', 'shell', 'bp'],
                'car_wash': ['car wash', 'cuci mobil', 'cuci motor'],
                'salon': ['salon', 'spa', 'beauty', 'kecantikan'],
                'store': ['toko', 'store', 'shop', 'market', 'warung'],
                'motorcycle': ['motor', 'honda', 'yamaha', 'suzuki', 'kawasaki'],
                'dental': ['dental', 'gigi', 'drg', 'dokter gigi'],
                'music': ['music', 'gitar', 'piano', 'alat musik'],
                'battery': ['battery', 'aki', 'accu', 'baterai'],
                'pharmacy': ['pharmacy', 'apotek', 'kimia farma', 'century'],
                'mosque': ['mosque', 'masjid', 'musholla', 'surau'],
                'church': ['church', 'gereja', 'kapel'],
                'temple': ['temple', 'pura', 'vihara', 'klenteng'],
                'park': ['park', 'taman', 'alun-alun', 'lapangan']
            }
            
            business_found = False
            for business_type, keywords in business_keywords.items():
                if any(keyword.lower() in line.lower() for keyword in keywords):
                    business_name = re.sub(r'[^\w\s\-\.]', '', line).strip()
                    if len(business_name) > 2 and business_name not in contextual_data['businesses']:
                        contextual_data['businesses'].append(business_name)
                        
                        # Search for business information from maps
                        logger.info(f"Searching for business info in {target_environment}: {business_name}")
                        business_info = search_business_info(business_name, "Indonesia")
                        
                        # Add detailed business information
                        contextual_data['business_details'][business_name] = {
                            'type': business_type,
                            'environment': target_environment,
                            'contact_person': business_info.get('contact_person', 'Hubungi langsung'),
                            'operational_hours': business_info.get('operational_hours', '08:00-17:00'),
                            'coordinates': business_info.get('coordinates', ''),
                            'address': business_info.get('address', ''),
                            'phone': business_info.get('phone', ''),
                            'email': business_info.get('email', ''),
                            'business_type_osm': business_info.get('business_type', 'general')
                        }
                        
                        business_found = True
                        logger.info(f"Found Business in {target_environment}: {business_name} (Type: {business_type})")
                        break
            
            # Extract street names within the target area
            if 'Jl.' in line or 'Jalan' in line or 'Jl ' in line:
                street_match = re.search(r'(Jl\.?\s*[A-Za-z\s]+|Jalan\s+[A-Za-z\s]+)', line)
                if street_match:
                    street_name = street_match.group(1).strip()
                    if street_name not in contextual_data['streets']:
                        contextual_data['streets'].append(street_name)
                        logger.info(f"Found Street in {target_environment}: {street_name}")
            
            # Extract landmarks within the target area
            landmark_keywords = ['masjid', 'gereja', 'pura', 'taman', 'lapangan', 'alun-alun', 'monumen', 'museum', 'stasiun', 'terminal', 'bandara', 'pelabuhan']
            if any(keyword.lower() in line.lower() for keyword in landmark_keywords):
                landmark_name = re.sub(r'[^\w\s\-\.]', '', line).strip()
                if len(landmark_name) > 2 and landmark_name not in contextual_data['landmarks']:
                    contextual_data['landmarks'].append(landmark_name)
                    logger.info(f"Found Landmark in {target_environment}: {landmark_name}")
            
            # Extract coordinates within the target area
            coord_match = re.search(r'(\d+\.\d+,\s*\d+\.\d+)', line)
            if coord_match:
                coordinates = coord_match.group(1)
                if coordinates not in contextual_data['coordinates']:
                    contextual_data['coordinates'].append(coordinates)
                    logger.info(f"Found Coordinates in {target_environment}: {coordinates}")
    
    # Calculate totals
    contextual_data['total_businesses'] = len(contextual_data['businesses'])
    contextual_data['total_streets'] = len(contextual_data['streets'])
    contextual_data['total_landmarks'] = len(contextual_data['landmarks'])
    
    # Determine area type and estimate KK for the target environment
    area_info = detect_residential_area(target_environment, contextual_data['business_details'])
    contextual_data['area_type'] = area_info['area_type']
    contextual_data['estimated_kk'] = area_info['estimated_kk']
    
    # Determine dominant load for the target environment
    dominant_load_code = determine_dominant_load(target_environment)
    contextual_data['dominant_load'] = get_dominant_load_description(dominant_load_code)
    
    logger.info(f"Contextual extraction complete for {target_environment}: {contextual_data['total_businesses']} businesses, {contextual_data['total_streets']} streets, {contextual_data['total_landmarks']} landmarks")
    
    return contextual_data

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed. Please upload PNG, JPG, JPEG, GIF, BMP, or TIFF files.'}), 400
        
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Ensure upload directory exists
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        file.save(filepath)
        logger.info(f"File uploaded: {filename}")
        
        # Extract text from image
        extracted_text = extract_text_from_image(filepath)
        
        if not extracted_text or extracted_text.strip() == "":
            logger.warning("No text extracted from image")
            return jsonify({'error': 'Tidak ada teks yang dapat diekstrak dari gambar. Pastikan gambar jelas dan mengandung teks.'}), 400
        
        # Check if extracted text contains error message
        if "Error dalam proses OCR" in extracted_text or "Tidak ada teks yang dapat diekstrak" in extracted_text:
            return jsonify({'error': extracted_text}), 400
        
        # Parse WSS data for basic map information
        wss_data = parse_wss_data_improved(extracted_text)
        
        # Validate map data
        is_valid, missing_fields, message = validate_map_data(wss_data)
        if not is_valid:
            return jsonify({'error': message, 'missing_fields': missing_fields}), 400
        
        # Extract contextual data based on detected environment
        contextual_data = extract_contextual_data(extracted_text)
        
        # Generate segments for preview using contextual data
        segments = generate_segments_from_data(wss_data)
        
        # Calculate total estimated KK and dominant loads
        total_estimated_kk = contextual_data.get('estimated_kk', 0)
        dominant_loads = [contextual_data.get('dominant_load', 'Tidak Diketahui')]
        
        # Return preview data with contextual information
        preview_data = {
            'map_id': wss_data.get('map_id', 'Tidak ditemukan'),
            'province': wss_data.get('province', 'Tidak ditemukan'),
            'regency': wss_data.get('regency', 'Tidak ditemukan'),
            'district': wss_data.get('district', 'Tidak ditemukan'),
            'village': wss_data.get('village', 'Tidak ditemukan'),
            'scale': wss_data.get('scale', 'Tidak ditemukan'),
            'target_environment': contextual_data.get('target_environment', 'Tidak terdeteksi'),
            'area_type': contextual_data.get('area_type', 'Tidak terdeteksi'),
            'businesses': contextual_data.get('businesses', []),
            'business_types': wss_data.get('business_types', {}),
            'business_details': contextual_data.get('business_details', {}),
            'streets': contextual_data.get('streets', []),
            'environments': wss_data.get('environments', []),
            'landmarks': contextual_data.get('landmarks', []),
            'coordinates': contextual_data.get('coordinates', []),
            'total_businesses': contextual_data.get('total_businesses', 0),
            'total_streets': contextual_data.get('total_streets', 0),
            'total_environments': wss_data.get('total_environments', 0),
            'total_landmarks': contextual_data.get('total_landmarks', 0),
            'total_coordinates': len(contextual_data.get('coordinates', [])),
            'total_estimated_kk': total_estimated_kk,
            'dominant_loads': dominant_loads,
            'segments': segments,
            'economic_centers': wss_data.get('economic_centers', [])
        }
        
        # Don't delete the file to avoid permission errors
        # os.remove(filepath)
        
        # Add building data to preview
        preview_data['building_data'] = wss_data.get('building_data', {})
        
        logger.info(f"Successfully processed file. Preview data: {preview_data}")
        
        return jsonify({
            'success': True,
            'preview': preview_data,
            'message': 'Data berhasil diekstrak! Silakan review data di bawah ini.'
        })
        
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        # Don't delete file in case of error either
        # if os.path.exists(filepath):
        #     os.remove(filepath)
        return jsonify({'error': f'Processing error: {str(e)}'}), 500

@app.route('/capture', methods=['POST'])
def capture_map():
    """Capture map data directly from camera/photo with validation"""
    try:
        data = request.get_json()
        if not data or 'image' not in data:
            return jsonify({'error': 'No image data received'}), 400
        
        # Decode base64 image
        try:
            image_data = base64.b64decode(data['image'].split(',')[1])
            image = Image.open(io.BytesIO(image_data))
            
            # Save temporary file
            temp_filename = f"capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            temp_path = os.path.join('uploads', temp_filename)
            image.save(temp_path)
            
            logger.info(f"Captured image saved to: {temp_path}")
            
        except Exception as e:
            logger.error(f"Error processing captured image: {e}")
            return jsonify({'error': 'Invalid image data format'}), 400
        
        # Extract text from captured image
        extracted_text = extract_text_from_image(temp_path)
        if not extracted_text.strip():
            logger.warning("No text extracted from captured image")
            return jsonify({'error': 'Tidak ada teks yang dapat diekstrak dari gambar. Pastikan gambar jelas dan mengandung teks.'}), 400
        
        # Parse WSS data for basic map information
        wss_data = parse_wss_data_improved(extracted_text)
        
        # Validate map data
        is_valid, missing_fields, message = validate_map_data(wss_data)
        if not is_valid:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return jsonify({
                'error': message, 
                'missing_fields': missing_fields,
                'extracted_data': {
                    'map_id': wss_data.get('map_id', ''),
                    'province': wss_data.get('province', ''),
                    'regency': wss_data.get('regency', ''),
                    'district': wss_data.get('district', ''),
                    'village': wss_data.get('village', ''),
                    'scale': wss_data.get('scale', '')
                }
            }), 400
        
        # Extract contextual data based on detected environment
        contextual_data = extract_contextual_data(extracted_text)
        
        # Generate segments for preview using contextual data
        segments = generate_segments_from_data(wss_data)
        
        # Calculate total estimated KK and dominant loads
        total_estimated_kk = contextual_data.get('estimated_kk', 0)
        dominant_loads = [contextual_data.get('dominant_load', 'Tidak Diketahui')]
        
        # Create preview data with contextual information
        preview_data = {
            'map_id': wss_data.get('map_id', 'Tidak ditemukan'),
            'province': wss_data.get('province', 'Tidak ditemukan'),
            'regency': wss_data.get('regency', 'Tidak ditemukan'),
            'district': wss_data.get('district', 'Tidak ditemukan'),
            'village': wss_data.get('village', 'Tidak ditemukan'),
            'scale': wss_data.get('scale', 'Tidak ditemukan'),
            'target_environment': contextual_data.get('target_environment', 'Tidak terdeteksi'),
            'area_type': contextual_data.get('area_type', 'Tidak terdeteksi'),
            'businesses': contextual_data.get('businesses', []),
            'business_types': wss_data.get('business_types', {}),
            'business_details': contextual_data.get('business_details', {}),
            'streets': contextual_data.get('streets', []),
            'environments': wss_data.get('environments', []),
            'landmarks': contextual_data.get('landmarks', []),
            'coordinates': contextual_data.get('coordinates', []),
            'total_businesses': contextual_data.get('total_businesses', 0),
            'total_streets': contextual_data.get('total_streets', 0),
            'total_environments': wss_data.get('total_environments', 0),
            'total_landmarks': contextual_data.get('total_landmarks', 0),
            'total_coordinates': len(contextual_data.get('coordinates', [])),
            'total_estimated_kk': total_estimated_kk,
            'dominant_loads': dominant_loads,
            'segments': segments,
            'economic_centers': wss_data.get('economic_centers', [])
        }
        
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        # Add building data to preview
        preview_data['building_data'] = wss_data.get('building_data', {})
        
        logger.info(f"Successfully processed captured image. Preview data: {preview_data}")
        return jsonify({
            'success': True, 
            'preview': preview_data, 
            'message': 'Foto map berhasil diproses! Data valid dan sesuai kriteria.'
        })
        
    except Exception as e:
        logger.error(f"Error processing captured image: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Processing error: {str(e)}'}), 500

@app.route('/download', methods=['POST'])
def download_excel():
    """Download Excel file after preview"""
    try:
        # Get data from request
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data received'}), 400
        
        # Convert preview data back to WSS data format
        wss_data = {
            'map_id': data.get('map_id', ''),
            'province': data.get('province', ''),
            'regency': data.get('regency', ''),
            'district': data.get('district', ''),
            'village': data.get('village', ''),
            'scale': data.get('scale', ''),
            'businesses': data.get('businesses', []),
            'business_types': data.get('business_types', {}),
            'business_details': data.get('business_details', {}),
            'streets': data.get('streets', []),
            'environments': data.get('environments', []),
            'landmarks': data.get('landmarks', []),
            'coordinates': data.get('coordinates', []),
            'total_businesses': data.get('total_businesses', 0),
            'total_streets': data.get('total_streets', 0),
            'total_environments': data.get('total_environments', 0),
            'total_landmarks': data.get('total_landmarks', 0),
            'building_data': data.get('building_data', {})
        }
        
        # Generate Excel template
        excel_output = generate_excel_template(wss_data)
        
        # Return Excel file
        return send_file(
            excel_output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'WSS_Data_Extraction_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        )
        
    except Exception as e:
        logger.error(f"Download error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Download error: {str(e)}'}), 500

def detect_economic_centers(businesses, business_details, environments=None, dominant_load=None):
    """
    Detect economic centers (mall, pasar) that contain multiple UMKM
    Focused on high accuracy detection of malls and traditional markets
    Returns: dict with economic center information
    """
    economic_centers = []
    
    # Get environment context
    environment_context = ""
    if environments:
        env_names = [env.get('name', '').lower() for env in environments]
        environment_context = ' '.join(env_names)
    
    # Determine area type based on dominant load
    area_type = ""
    if dominant_load:
        area_type = get_dominant_load_description(dominant_load).lower()
    
    # High-accuracy keywords for mall and pasar detection
    mall_keywords = [
        'mall', 'plaza', 'shopping center', 'pusat perbelanjaan', 
        'supermarket', 'hypermarket', 'department store', 'mal',
        'shopping mall', 'retail center', 'commercial center'
    ]
    
    pasar_keywords = [
        'pasar', 'market', 'traditional market', 'pasar tradisional',
        'pasar induk', 'pasar besar', 'pasar utama', 'pasar raya', 
        'pasar modern', 'pasar swalayan'
    ]
    
    for business_name, details in business_details.items():
        business_name_lower = business_name.lower()
        
        # Check if this business is an economic center (mall or pasar only)
        center_type = None
        estimated_umkm = 0
        
        # High-accuracy detection for mall
        if any(keyword in business_name_lower for keyword in mall_keywords):
            center_type = 'mall'
            # Estimate UMKM based on mall size indicators
            if any(word in business_name_lower for word in ['supermarket', 'hypermarket', 'department store']):
                estimated_umkm = 80  # Large retail chains
            elif any(word in business_name_lower for word in ['mall', 'plaza', 'shopping center']):
                estimated_umkm = 60  # Standard mall
            else:
                estimated_umkm = 40  # Smaller commercial center
        
        # High-accuracy detection for pasar
        elif any(keyword in business_name_lower for keyword in pasar_keywords):
            center_type = 'pasar'
            # Estimate UMKM based on pasar type
            if any(word in business_name_lower for word in ['pasar induk', 'pasar besar', 'pasar utama']):
                estimated_umkm = 150  # Large traditional market
            elif any(word in business_name_lower for word in ['pasar modern', 'pasar swalayan']):
                estimated_umkm = 80  # Modern market
            else:
                estimated_umkm = 100  # Standard traditional market
        
        # Adjust UMKM count based on map context and environment
        if center_type:
            # Context-based adjustments for higher accuracy
            if 'perkambingan' in environment_context or 'ternak' in area_type:
                # Livestock area - reduce estimates for non-agricultural centers
                if center_type == 'mall':
                    estimated_umkm = max(20, estimated_umkm // 2)
                elif center_type == 'pasar':
                    estimated_umkm = max(30, estimated_umkm // 2)
            elif 'pertanian' in area_type or 'sawah' in environment_context:
                # Agricultural area - moderate adjustment
                if center_type == 'mall':
                    estimated_umkm = max(25, estimated_umkm // 1.3)
                elif center_type == 'pasar':
                    estimated_umkm = max(50, estimated_umkm // 1.2)
            elif 'industri' in area_type or 'pabrik' in environment_context:
                # Industrial area - may have larger commercial centers
                if center_type == 'mall':
                    estimated_umkm = min(80, estimated_umkm * 1.1)
                elif center_type == 'pasar':
                    estimated_umkm = min(120, estimated_umkm * 1.1)
            
            # Create context-aware description with high accuracy focus
            context_description = ""
            if environment_context:
                context_description = f"Pusat ekonomi ({center_type}) di {environment_context}"
            elif area_type:
                context_description = f"Pusat ekonomi ({center_type}) di {area_type}"
            else:
                context_description = f"Pusat ekonomi ({center_type}) yang berisi multiple UMKM"
            
            # Get precise coordinates for economic center
            precise_coords = get_precise_coordinates(business_name, "Indonesia")
            
            economic_centers.append({
                'name': business_name,
                'type': center_type,
                'estimated_umkm': estimated_umkm,
                'contact_person': details.get('contact_person', 'Hubungi langsung'),
                'operational_hours': details.get('operational_hours', '08:00-22:00'),
                'coordinates': precise_coords.get('coordinates', details.get('coordinates', '')),
                'coordinates_decimal': precise_coords.get('coordinates_decimal', ''),
                'coordinates_dms': precise_coords.get('coordinates_dms', ''),
                'latitude': precise_coords.get('latitude', ''),
                'longitude': precise_coords.get('longitude', ''),
                'google_maps_link': precise_coords.get('google_maps_link', ''),
                'osm_link': precise_coords.get('osm_link', ''),
                'location_type': precise_coords.get('location_type', ''),
                'province': precise_coords.get('province', ''),
                'regency': precise_coords.get('regency', ''),
                'district': precise_coords.get('district', ''),
                'village': precise_coords.get('village', ''),
                'accuracy': precise_coords.get('accuracy', 'low'),
                'validated': precise_coords.get('validated', False),
                'address': details.get('address', ''),
                'phone': details.get('phone', ''),
                'email': details.get('email', ''),
                'business_type_osm': details.get('business_type_osm', 'general'),
                'context': context_description,
                'environment': environment_context,
                'area_type': area_type
            })
    
    return economic_centers

def search_business_info_improved(business_name, location="Indonesia"):
    """
    Improved business information search with better accuracy
    Returns: dict with business details
    """
    try:
        # Clean business name for search
        clean_name = re.sub(r'[^\w\s]', '', business_name).strip()
        if len(clean_name) < 3:
            return {}
        
        # Enhanced search query with location context
        search_query = f"{clean_name}, {location}"
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': search_query,
            'format': 'json',
            'limit': 5,  # Get more results for better accuracy
            'addressdetails': 1,
            'extratags': 1
        }
        headers = {
            'User-Agent': 'WSS-Map-Extractor/1.0'
        }
        
        logger.info(f"Searching for business: {search_query}")
        response = requests.get(url, params=params, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            if data:
                # Find the best match based on business type
                best_result = None
                business_type = 'general'
                
                # Determine business type from name
                name_lower = business_name.lower()
                if any(word in name_lower for word in ['mall', 'plaza', 'center']):
                    business_type = 'mall'
                elif any(word in name_lower for word in ['pasar', 'market']):
                    business_type = 'pasar'
                elif any(word in name_lower for word in ['hotel', 'resort']):
                    business_type = 'hotel'
                elif any(word in name_lower for word in ['restaurant', 'cafe', 'warung']):
                    business_type = 'restaurant'
                elif any(word in name_lower for word in ['bank', 'atm']):
                    business_type = 'bank'
                elif any(word in name_lower for word in ['hospital', 'klinik']):
                    business_type = 'hospital'
                elif any(word in name_lower for word in ['school', 'sekolah']):
                    business_type = 'school'
                elif any(word in name_lower for word in ['office', 'kantor']):
                    business_type = 'office'
                elif any(word in name_lower for word in ['gas', 'spbu']):
                    business_type = 'gas_station'
                elif any(word in name_lower for word in ['car wash', 'cuci']):
                    business_type = 'car_wash'
                elif any(word in name_lower for word in ['salon', 'spa']):
                    business_type = 'salon'
                elif any(word in name_lower for word in ['motor', 'honda', 'yamaha']):
                    business_type = 'motorcycle'
                elif any(word in name_lower for word in ['dental', 'gigi']):
                    business_type = 'dental'
                elif any(word in name_lower for word in ['music', 'gitar']):
                    business_type = 'music'
                elif any(word in name_lower for word in ['battery', 'aki']):
                    business_type = 'battery'
                elif any(word in name_lower for word in ['pharmacy', 'apotek']):
                    business_type = 'pharmacy'
                elif any(word in name_lower for word in ['mosque', 'masjid']):
                    business_type = 'mosque'
                elif any(word in name_lower for word in ['church', 'gereja']):
                    business_type = 'church'
                elif any(word in name_lower for word in ['temple', 'pura']):
                    business_type = 'temple'
                elif any(word in name_lower for word in ['park', 'taman']):
                    business_type = 'park'
                
                # Try to find matching business type in results
                for result in data:
                    if result.get('type') in ['node', 'way']:
                        extratags = result.get('extratags', {})
                        if business_type == 'mall' and extratags.get('shop') in ['mall', 'supermarket']:
                            best_result = result
                            break
                        elif business_type == 'pasar' and extratags.get('amenity') == 'marketplace':
                            best_result = result
                            break
                        elif business_type == 'hotel' and extratags.get('tourism') == 'hotel':
                            best_result = result
                            break
                        elif business_type == 'restaurant' and extratags.get('amenity') == 'restaurant':
                            best_result = result
                            break
                        elif business_type == 'bank' and extratags.get('amenity') == 'bank':
                            best_result = result
                            break
                        elif business_type == 'hospital' and extratags.get('amenity') == 'hospital':
                            best_result = result
                            break
                        elif business_type == 'school' and extratags.get('amenity') == 'school':
                            best_result = result
                            break
                        elif business_type == 'office' and extratags.get('office'):
                            best_result = result
                            break
                        elif business_type == 'gas_station' and extratags.get('amenity') == 'fuel':
                            best_result = result
                            break
                        elif business_type == 'car_wash' and extratags.get('shop') == 'car_repair':
                            best_result = result
                            break
                        elif business_type == 'salon' and extratags.get('shop') == 'hairdresser':
                            best_result = result
                            break
                        elif business_type == 'motorcycle' and extratags.get('shop') == 'motorcycle':
                            best_result = result
                            break
                        elif business_type == 'dental' and extratags.get('amenity') == 'dentist':
                            best_result = result
                            break
                        elif business_type == 'music' and extratags.get('shop') == 'music':
                            best_result = result
                            break
                        elif business_type == 'battery' and extratags.get('shop') == 'car_parts':
                            best_result = result
                            break
                        elif business_type == 'pharmacy' and extratags.get('amenity') == 'pharmacy':
                            best_result = result
                            break
                        elif business_type == 'mosque' and extratags.get('amenity') == 'place_of_worship':
                            best_result = result
                            break
                        elif business_type == 'church' and extratags.get('amenity') == 'place_of_worship':
                            best_result = result
                            break
                        elif business_type == 'temple' and extratags.get('amenity') == 'place_of_worship':
                            best_result = result
                            break
                        elif business_type == 'park' and extratags.get('leisure') == 'park':
                            best_result = result
                            break
                
                # If no specific match found, use first result
                if not best_result:
                    best_result = data[0]
                
                address = best_result.get('display_name', '')
                address_details = best_result.get('address', {})
                extratags = best_result.get('extratags', {})
                
                # Get phone number from various sources
                phone = ''
                if 'phone' in address_details:
                    phone = address_details['phone']
                elif 'contact:phone' in extratags:
                    phone = extratags['contact:phone']
                
                # Get website from various sources
                website = ''
                if 'website' in address_details:
                    website = address_details['website']
                elif 'contact:website' in extratags:
                    website = extratags['contact:website']
                
                # Get opening hours from various sources
                opening_hours = ''
                if 'opening_hours' in address_details:
                    opening_hours = address_details['opening_hours']
                elif 'opening_hours' in extratags:
                    opening_hours = extratags['opening_hours']
                else:
                    # Try to find hours in display_name
                    hours_match = re.search(r'(\d{1,2}:\d{2}\s*[-–]\s*\d{1,2}:\d{2})', address)
                    if hours_match:
                        opening_hours = hours_match.group(1)
                
                # Set default operational hours based on business type
                if not opening_hours:
                    if business_type in ['restaurant', 'cafe', 'fast_food']:
                        opening_hours = '08:00-22:00'
                    elif business_type in ['bank', 'atm']:
                        opening_hours = '08:00-16:00'
                    elif business_type in ['shop', 'supermarket', 'mall']:
                        opening_hours = '09:00-21:00'
                    elif business_type in ['hotel', 'guest_house']:
                        opening_hours = '24 Jam'
                    elif business_type in ['hospital', 'klinik']:
                        opening_hours = '24 Jam'
                    elif business_type in ['school', 'sekolah']:
                        opening_hours = '07:00-15:00'
                    elif business_type in ['office', 'kantor']:
                        opening_hours = '08:00-17:00'
                    elif business_type in ['gas_station', 'spbu']:
                        opening_hours = '06:00-22:00'
                    elif business_type in ['car_wash', 'cuci']:
                        opening_hours = '08:00-18:00'
                    elif business_type in ['salon', 'spa']:
                        opening_hours = '09:00-20:00'
                    elif business_type in ['motorcycle', 'motor']:
                        opening_hours = '08:00-17:00'
                    elif business_type in ['dental', 'gigi']:
                        opening_hours = '09:00-17:00'
                    elif business_type in ['music', 'gitar']:
                        opening_hours = '09:00-18:00'
                    elif business_type in ['battery', 'aki']:
                        opening_hours = '08:00-17:00'
                    elif business_type in ['pharmacy', 'apotek']:
                        opening_hours = '08:00-21:00'
                    elif business_type in ['mosque', 'masjid']:
                        opening_hours = '24 Jam'
                    elif business_type in ['church', 'gereja']:
                        opening_hours = '24 Jam'
                    elif business_type in ['temple', 'pura']:
                        opening_hours = '24 Jam'
                    elif business_type in ['park', 'taman']:
                        opening_hours = '06:00-22:00'
                    else:
                        opening_hours = '08:00-17:00'
                
                # Get precise coordinates
                precise_coords = get_precise_coordinates(business_name, location)
                
                return {
                    'address': address,
                    'coordinates': precise_coords.get('coordinates', f"{best_result.get('lat', '')}, {best_result.get('lon', '')}"),
                    'coordinates_decimal': precise_coords.get('coordinates_decimal', ''),
                    'coordinates_dms': precise_coords.get('coordinates_dms', ''),
                    'latitude': precise_coords.get('latitude', ''),
                    'longitude': precise_coords.get('longitude', ''),
                    'google_maps_link': precise_coords.get('google_maps_link', ''),
                    'osm_link': precise_coords.get('osm_link', ''),
                    'location_type': precise_coords.get('location_type', ''),
                    'province': precise_coords.get('province', ''),
                    'regency': precise_coords.get('regency', ''),
                    'district': precise_coords.get('district', ''),
                    'village': precise_coords.get('village', ''),
                    'accuracy': precise_coords.get('accuracy', 'low'),
                    'validated': precise_coords.get('validated', False),
                    'phone': phone,
                    'website': website,
                    'operational_hours': opening_hours,
                    'contact_person': 'Hubungi langsung',
                    'email': '',
                    'business_type': business_type
                }
        
        return {}
        
    except Exception as e:
        logger.error(f"Error searching business info: {e}")
        return {}

def parse_wss_data_improved(text):
    """Improved WSS map data parsing with better accuracy"""
    logger.info(f"Parsing WSS data from text:\n{text}")
    data = {
        'map_id': '', 'province': '', 'regency': '', 'district': '', 'village': '', 'scale': '',
        'businesses': [], 'business_details': {},
        'streets': [], 'environments': [], 'coordinates': [], 'landmarks': [],
        'business_types': {}, 'total_businesses': 0, 'total_streets': 0,
        'total_environments': 0, 'total_landmarks': 0,
        'economic_centers': []  # New field for economic centers
    }
    lines = text.split('\n')
    logger.info(f"Processing {len(lines)} lines of text")
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line: continue
        logger.info(f"Processing line {i+1}: '{line}'")
        
        # Extract Map ID (16 digit number) - improved regex
        map_id_match = re.search(r'(\d{16})', line)
        if map_id_match:
            data['map_id'] = map_id_match.group(1)
            logger.info(f"Found Map ID: {data['map_id']}")
        
        # Extract administrative data with improved matching
        if 'PROVINSI' in line.upper() or 'PROVINCE' in line.upper():
            province_match = re.search(r'PROVINSI\s*:\s*\[?\d+\]?\s*([A-Z\s]+)', line, re.IGNORECASE)
            if province_match:
                data['province'] = province_match.group(1).strip()
                logger.info(f"Found Province: {data['province']}")
            else:
                # Enhanced province detection
                if 'BALI' in line.upper(): data['province'] = 'BALI'
                elif 'JAWA' in line.upper():
                    if 'TIMUR' in line.upper(): data['province'] = 'JAWA TIMUR'
                    elif 'TENGAH' in line.upper(): data['province'] = 'JAWA TENGAH'
                    elif 'BARAT' in line.upper(): data['province'] = 'JAWA BARAT'
                    else: data['province'] = 'JAWA'
                elif 'SUMATERA' in line.upper() or 'SUMATRA' in line.upper(): data['province'] = 'SUMATERA'
                elif 'KALIMANTAN' in line.upper(): data['province'] = 'KALIMANTAN'
                elif 'SULAWESI' in line.upper(): data['province'] = 'SULAWESI'
                elif 'PAPUA' in line.upper(): data['province'] = 'PAPUA'
                elif 'MALUKU' in line.upper(): data['province'] = 'MALUKU'
                elif 'NUSA TENGGARA' in line.upper(): data['province'] = 'NUSA TENGGARA'
        
        if 'KABUPATEN' in line.upper() or 'KOTA' in line.upper() or 'REGENCY' in line.upper():
            regency_match = re.search(r'(?:KABUPATEN|KOTA)\s*:\s*\[?\d+\]?\s*([A-Z\s]+)', line, re.IGNORECASE)
            if regency_match:
                data['regency'] = regency_match.group(1).strip()
                logger.info(f"Found Regency: {data['regency']}")
            else:
                # Enhanced regency detection for Bali
                if 'DENPASAR' in line.upper(): data['regency'] = 'DENPASAR'
                elif 'BADUNG' in line.upper(): data['regency'] = 'BADUNG'
                elif 'GIANYAR' in line.upper(): data['regency'] = 'GIANYAR'
                elif 'KLUNGKUNG' in line.upper(): data['regency'] = 'KLUNGKUNG'
                elif 'BANGLI' in line.upper(): data['regency'] = 'BANGLI'
                elif 'KARANGASEM' in line.upper(): data['regency'] = 'KARANGASEM'
                elif 'BULELENG' in line.upper(): data['regency'] = 'BULELENG'
                elif 'JEMBRANA' in line.upper(): data['regency'] = 'JEMBRANA'
                elif 'TABANAN' in line.upper(): data['regency'] = 'TABANAN'
        
        if 'KECAMATAN' in line.upper() or 'DISTRICT' in line.upper():
            district_match = re.search(r'KECAMATAN\s*:\s*\[?\d+\]?\s*([A-Z\s]+)', line, re.IGNORECASE)
            if district_match:
                data['district'] = district_match.group(1).strip()
                logger.info(f"Found District: {data['district']}")
            else:
                # Enhanced district detection for Denpasar
                if 'DENPASAR BARAT' in line.upper(): data['district'] = 'DENPASAR BARAT'
                elif 'DENPASAR TIMUR' in line.upper(): data['district'] = 'DENPASAR TIMUR'
                elif 'DENPASAR SELATAN' in line.upper(): data['district'] = 'DENPASAR SELATAN'
                elif 'DENPASAR UTARA' in line.upper(): data['district'] = 'DENPASAR UTARA'
        
        if 'DESA' in line.upper() or 'KELURAHAN' in line.upper() or 'VILLAGE' in line.upper():
            village_match = re.search(r'(?:DESA|KELURAHAN)\s*:\s*\[?\d+\]?\s*([A-Z\s]+)', line, re.IGNORECASE)
            if village_match:
                data['village'] = village_match.group(1).strip()
                logger.info(f"Found Village: {data['village']}")
            else:
                # Enhanced village detection
                if 'DAUH PURI' in line.upper(): data['village'] = 'DAUH PURI'
                elif 'KELURAHAN' in line.upper():
                    kel_match = re.search(r'KELURAHAN\s+([A-Z\s]+)', line, re.IGNORECASE)
                    if kel_match: data['village'] = kel_match.group(1).strip()
                elif 'DESA' in line.upper():
                    desa_match = re.search(r'DESA\s+([A-Z\s]+)', line, re.IGNORECASE)
                    if desa_match: data['village'] = desa_match.group(1).strip()
        
        # Extract scale with improved pattern
        if 'SKALA' in line.upper():
            scale_match = re.search(r'SKALA\s*(\d+:\d+)', line, re.IGNORECASE)
            if scale_match:
                data['scale'] = scale_match.group(1)
                logger.info(f"Found Scale: {data['scale']}")
            else:
                scale_simple = re.search(r'(\d+:\d+)', line)
                if scale_simple:
                    data['scale'] = scale_simple.group(1)
                    logger.info(f"Found Scale: {data['scale']}")
                
        # Extract business names with enhanced accuracy for mall and pasar detection
        business_keywords = {
            'mall': ['mall', 'plaza', 'center', 'supermarket', 'hypermarket', 'department store', 'pusat perbelanjaan'],
            'pasar': ['pasar', 'market', 'traditional market', 'pasar tradisional', 'pasar induk', 'pasar besar'],
            'hotel': ['hotel', 'resort', 'inn', 'guesthouse', 'penginapan'],
            'restaurant': ['restaurant', 'cafe', 'warung', 'rumah makan', 'restoran'],
            'bank': ['bank', 'atm', 'bca', 'mandiri', 'bni', 'bri'],
            'hospital': ['hospital', 'rumah sakit', 'klinik', 'apotek', 'puskesmas'],
            'school': ['school', 'sekolah', 'universitas', 'kampus', 'sd', 'smp', 'sma'],
            'office': ['office', 'kantor', 'perkantoran', 'gedung'],
            'gas_station': ['gas', 'spbu', 'pertamina', 'shell', 'bp'],
            'car_wash': ['car wash', 'cuci mobil', 'cuci motor'],
            'salon': ['salon', 'spa', 'beauty', 'kecantikan'],
            'store': ['toko', 'store', 'shop', 'market', 'warung'],
            'motorcycle': ['motor', 'honda', 'yamaha', 'suzuki', 'kawasaki'],
            'dental': ['dental', 'gigi', 'drg', 'dokter gigi'],
            'music': ['music', 'gitar', 'piano', 'alat musik'],
            'battery': ['battery', 'aki', 'accu', 'baterai'],
            'pharmacy': ['pharmacy', 'apotek', 'kimia farma', 'century'],
            'mosque': ['mosque', 'masjid', 'musholla', 'surau'],
            'church': ['church', 'gereja', 'kapel'],
            'temple': ['temple', 'pura', 'vihara', 'klenteng'],
            'park': ['park', 'taman', 'alun-alun', 'lapangan']
        }
        
        business_found = False
        for business_type, keywords in business_keywords.items():
            if any(keyword.lower() in line.lower() for keyword in keywords):
                business_name = re.sub(r'[^\w\s\-\.]', '', line).strip()
                if len(business_name) > 2 and business_name not in data['businesses']:
                    data['businesses'].append(business_name)
                    data['business_types'][business_name] = business_type
                    
                    # Search for business information with improved accuracy
                    logger.info(f"Searching for business info: {business_name}")
                    business_info = search_business_info_improved(business_name, data.get('regency', 'Indonesia'))
                    
                    # Add detailed business information
                    data['business_details'][business_name] = {
                        'type': business_type,
                        'contact_person': business_info.get('contact_person', 'Hubungi langsung'),
                        'operational_hours': business_info.get('operational_hours', '08:00-17:00'),
                        'coordinates': business_info.get('coordinates', ''),
                        'address': business_info.get('address', ''),
                        'phone': business_info.get('phone', ''),
                        'email': business_info.get('email', ''),
                        'business_type_osm': business_info.get('business_type', 'general')
                    }
                    
                    business_found = True
                    logger.info(f"Found Business: {business_name} (Type: {business_type})")
                    break
        
        # If no specific type found, categorize as general business
        if not business_found and any(keyword.lower() in line.lower() for keyword in ['warung', 'toko', 'restaurant', 'store', 'shop', 'gallery', 'motor', 'dental', 'battery', 'music', 'hotel', 'mall', 'market', 'cafe', 'bank', 'pharmacy', 'hospital', 'school', 'university', 'office', 'factory', 'warehouse', 'gas station', 'car wash', 'salon', 'spa']):
            business_name = re.sub(r'[^\w\s\-\.]', '', line).strip()
            if len(business_name) > 2 and business_name not in data['businesses']:
                data['businesses'].append(business_name)
                data['business_types'][business_name] = 'general'
                
                # Search for business information with improved accuracy
                logger.info(f"Searching for business info: {business_name}")
                business_info = search_business_info_improved(business_name, data.get('regency', 'Indonesia'))
                
                # Add detailed business information
                data['business_details'][business_name] = {
                    'type': 'general',
                    'contact_person': business_info.get('contact_person', 'Hubungi langsung'),
                    'operational_hours': business_info.get('operational_hours', '08:00-17:00'),
                    'coordinates': business_info.get('coordinates', ''),
                    'address': business_info.get('address', ''),
                    'phone': business_info.get('phone', ''),
                    'email': business_info.get('email', '')
                }
                
                logger.info(f"Found General Business: {business_name}")
                
        # Extract street names with improved regex
        if 'Jl.' in line or 'Jalan' in line or 'Jl ' in line:
            street_match = re.search(r'(Jl\.?\s*[A-Za-z\s]+)', line)
            if street_match:
                street_name = street_match.group(1).strip()
                if street_name not in data['streets']:
                    data['streets'].append(street_name)
                    logger.info(f"Found Street: {street_name}")
            else:
                jalan_match = re.search(r'Jalan\s+([A-Za-z\s]+)', line)
                if jalan_match:
                    street_name = f"Jl. {jalan_match.group(1).strip()}"
                    if street_name not in data['streets']:
                        data['streets'].append(street_name)
                        logger.info(f"Found Street: {street_name}")
                
        # Extract environment names with improved regex
        if 'LINGKUNGAN' in line.upper():
            env_match = re.search(r'LINGKUNGAN\s+([A-Z\s]+)\s*\[(\d+)\]', line, re.IGNORECASE)
            if env_match:
                env_name = env_match.group(1).strip()
                env_code = env_match.group(2)
                if not any(env['name'] == env_name and env['code'] == env_code for env in data['environments']):
                    data['environments'].append({
                        'name': env_name,
                        'code': env_code
                    })
                    logger.info(f"Found Environment: {env_name} [{env_code}]")
            else:
                env_simple_match = re.search(r'LINGKUNGAN\s+([A-Z\s]+)', line, re.IGNORECASE)
                if env_simple_match:
                    env_name = env_simple_match.group(1).strip()
                    env_code = str(len(data['environments']) + 1).zfill(2)
                    if not any(env['name'] == env_name for env in data['environments']):
                        data['environments'].append({
                            'name': env_name,
                            'code': env_code
                        })
                        logger.info(f"Found Environment: {env_name} [{env_code}]")
                
        # Extract coordinates if present
        coord_match = re.search(r'(-?\d+\.\d+),\s*(-?\d+\.\d+)', line)
        if coord_match:
            lat = float(coord_match.group(1))
            lon = float(coord_match.group(2))
            coord_data = {'latitude': lat, 'longitude': lon}
            if coord_data not in data['coordinates']:
                data['coordinates'].append(coord_data)
                logger.info(f"Found Coordinates: {lat}, {lon}")
                
        # Extract landmarks
        landmark_keywords = ['Monument', 'Park', 'Square', 'Temple', 'Church', 'Mosque', 'Museum', 'Tugu', 'Patung', 'Alun-alun']
        if any(keyword.lower() in line.lower() for keyword in landmark_keywords):
            landmark_name = re.sub(r'[^\w\s\-\.]', '', line).strip()
            if len(landmark_name) > 2 and landmark_name not in data['landmarks']:
                data['landmarks'].append(landmark_name)
                logger.info(f"Found Landmark: {landmark_name}")
    
    # Detect economic centers with environmental context
    # Determine dominant load based on environments and business types
    dominant_load = None
    if data['environments']:
        # Use the first environment to determine dominant load
        first_env = data['environments'][0]['name']
        dominant_load = determine_dominant_load(first_env)
    
    data['economic_centers'] = detect_economic_centers(
        data['businesses'], 
        data['business_details'],
        environments=data['environments'],
        dominant_load=dominant_load
    )
    
    data['total_businesses'] = len(data['businesses'])
    data['total_streets'] = len(data['streets'])
    data['total_environments'] = len(data['environments'])
    data['total_landmarks'] = len(data['landmarks'])
    
    # Detect building types
    building_data = detect_building_types(text)
    data['building_data'] = building_data
    logger.info(f"Building data detected: {building_data}")
    
    logger.info(f"Final parsed data: {data}")
    return data

def get_precise_coordinates(business_name, location="Indonesia"):
    """
    Get precise coordinates with validation and higher accuracy
    Returns: dict with validated coordinates and additional location data
    """
    try:
        # Clean business name for search
        clean_name = re.sub(r'[^\w\s]', '', business_name).strip()
        if len(clean_name) < 3:
            return {}
        
        # Enhanced search query with location context
        search_query = f"{clean_name}, {location}"
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': search_query,
            'format': 'json',
            'limit': 10,  # Get more results for better accuracy
            'addressdetails': 1,
            'extratags': 1,
            'polygon': 1,  # Get polygon data for better accuracy
            'viewbox': None  # Will be set based on location
        }
        headers = {
            'User-Agent': 'WSS-Map-Extractor/1.0'
        }
        
        logger.info(f"Getting precise coordinates for: {search_query}")
        response = requests.get(url, params=params, headers=headers, timeout=20)
        
        if response.status_code == 200:
            data = response.json()
            if data:
                # Find the best match with highest accuracy
                best_result = None
                highest_importance = 0
                
                for result in data:
                    importance = result.get('importance', 0)
                    if importance > highest_importance:
                        highest_importance = importance
                        best_result = result
                
                if best_result:
                    lat = best_result.get('lat', '')
                    lon = best_result.get('lon', '')
                    
                    # Validate coordinates
                    try:
                        lat_float = float(lat)
                        lon_float = float(lon)
                        
                        # Check if coordinates are within reasonable bounds for Indonesia
                        if -11.0 <= lat_float <= 6.0 and 95.0 <= lon_float <= 141.0:
                            # Format coordinates with higher precision
                            lat_formatted = f"{lat_float:.6f}"
                            lon_formatted = f"{lon_float:.6f}"
                            
                            # Get additional location data
                            address_details = best_result.get('address', {})
                            extratags = best_result.get('extratags', {})
                            
                            # Determine location type and accuracy
                            location_type = 'business'
                            if extratags.get('amenity'):
                                location_type = extratags.get('amenity')
                            elif extratags.get('shop'):
                                location_type = extratags.get('shop')
                            elif extratags.get('tourism'):
                                location_type = extratags.get('tourism')
                            
                            # Get administrative boundaries for context
                            province = address_details.get('state', '')
                            regency = address_details.get('county', '')
                            district = address_details.get('city_district', '')
                            village = address_details.get('suburb', '')
                            
                            # Create Google Maps link
                            google_maps_link = f"https://www.google.com/maps?q={lat_float},{lon_float}"
                            
                            # Create OpenStreetMap link
                            osm_link = f"https://www.openstreetmap.org/?mlat={lat_float}&mlon={lon_float}&zoom=18"
                            
                            return {
                                'latitude': lat_formatted,
                                'longitude': lon_formatted,
                                'coordinates': f"{lat_formatted}, {lon_formatted}",
                                'coordinates_decimal': f"{lat_float:.6f}, {lon_float:.6f}",
                                'coordinates_dms': f"{int(lat_float)}°{int((lat_float % 1) * 60)}'{((lat_float % 1) * 60 % 1) * 60:.2f}\"S, {int(lon_float)}°{int((lon_float % 1) * 60)}'{((lon_float % 1) * 60 % 1) * 60:.2f}\"E",
                                'location_type': location_type,
                                'province': province,
                                'regency': regency,
                                'district': district,
                                'village': village,
                                'google_maps_link': google_maps_link,
                                'osm_link': osm_link,
                                'accuracy': 'high',
                                'validated': True
                            }
                        else:
                            logger.warning(f"Coordinates outside Indonesia bounds: {lat}, {lon}")
                            return {
                                'coordinates': f"{lat}, {lon}",
                                'accuracy': 'low',
                                'validated': False,
                                'error': 'Koordinat di luar batas Indonesia'
                            }
                    
                    except (ValueError, TypeError) as e:
                        logger.error(f"Invalid coordinate format: {e}")
                        return {
                            'coordinates': f"{lat}, {lon}",
                            'accuracy': 'low',
                            'validated': False,
                            'error': 'Format koordinat tidak valid'
                        }
        
        return {
            'coordinates': '',
            'accuracy': 'none',
            'validated': False,
            'error': 'Tidak dapat menemukan koordinat'
        }
        
    except Exception as e:
        logger.error(f"Error getting precise coordinates: {e}")
        return {
            'coordinates': '',
            'accuracy': 'none',
            'validated': False,
            'error': f'Error: {str(e)}'
        }

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 