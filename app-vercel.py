from flask import Flask, render_template, request, jsonify, send_file
import pandas as pd
import os
from datetime import datetime
import logging
import re
import requests
from io import BytesIO
import base64

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Ensure uploads directory exists
os.makedirs('uploads', exist_ok=True)

def parse_wss_data_simple(text):
    """
    Simplified version without OCR dependencies
    """
    data = {
        'map_id': '',
        'province': '',
        'regency': '',
        'district': '',
        'village': '',
        'scale': '',
        'businesses': [],
        'streets': [],
        'environments': [],
        'landmarks': [],
        'coordinates': [],
        'economic_centers': [],
        'building_data': {
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
    }
    
    # Simple text parsing
    lines = text.split('\n')
    
    for line in lines:
        line_lower = line.lower().strip()
        if not line_lower:
            continue
            
        # Detect map ID
        if 'map' in line_lower and 'id' in line_lower:
            data['map_id'] = line.strip()
            
        # Detect businesses
        business_keywords = ['toko', 'warung', 'restoran', 'mall', 'pasar']
        if any(keyword in line_lower for keyword in business_keywords):
            data['businesses'].append(line.strip())
            
        # Detect streets
        street_keywords = ['jalan', 'street', 'road', 'jl.']
        if any(keyword in line_lower for keyword in street_keywords):
            data['streets'].append(line.strip())
    
    return data

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'Tidak ada file yang dipilih'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'Tidak ada file yang dipilih'})
        
        # Save file
        filename = f"upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        filepath = os.path.join('uploads', filename)
        file.save(filepath)
        
        # Simulate OCR result (for demo purposes)
        simulated_text = f"""
        Map ID: DEMO-{datetime.now().strftime('%Y%m%d')}
        Province: Jawa Barat
        Regency: Bandung
        District: Cicendo
        Village: Cikutra
        
        Jalan Sudirman
        Mall Bandung Indah Plaza
        Pasar Cikutra
        Toko Sederhana
        Warung Makan Padang
        """
        
        # Parse data
        wss_data = parse_wss_data_simple(simulated_text)
        
        # Prepare preview data
        preview_data = {
            'map_id': wss_data.get('map_id', ''),
            'province': wss_data.get('province', ''),
            'regency': wss_data.get('regency', ''),
            'district': wss_data.get('district', ''),
            'village': wss_data.get('village', ''),
            'scale': wss_data.get('scale', ''),
            'businesses': wss_data.get('businesses', []),
            'streets': wss_data.get('streets', []),
            'environments': wss_data.get('environments', []),
            'landmarks': wss_data.get('landmarks', []),
            'coordinates': wss_data.get('coordinates', []),
            'economic_centers': wss_data.get('economic_centers', []),
            'building_data': wss_data.get('building_data', {})
        }
        
        logger.info(f"Successfully processed file. Preview data: {preview_data}")
        
        return jsonify({
            'success': True,
            'preview': preview_data,
            'message': 'Data berhasil diekstrak! Silakan review data di bawah ini.'
        })
        
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/capture', methods=['POST'])
def capture_image():
    try:
        data = request.get_json()
        if not data or 'image' not in data:
            return jsonify({'success': False, 'message': 'Tidak ada data gambar'})
        
        # Decode base64 image
        image_data = data['image'].split(',')[1]
        image_bytes = base64.b64decode(image_data)
        
        # Save image
        filename = f"capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        filepath = os.path.join('uploads', filename)
        
        with open(filepath, 'wb') as f:
            f.write(image_bytes)
        
        # Simulate OCR result
        simulated_text = f"""
        Map ID: CAPTURE-{datetime.now().strftime('%Y%m%d')}
        Province: Jawa Barat
        Regency: Bandung
        District: Cicendo
        Village: Cikutra
        
        Jalan Sudirman
        Mall Bandung Indah Plaza
        Pasar Cikutra
        Toko Sederhana
        Warung Makan Padang
        """
        
        # Parse data
        wss_data = parse_wss_data_simple(simulated_text)
        
        # Prepare preview data
        preview_data = {
            'map_id': wss_data.get('map_id', ''),
            'province': wss_data.get('province', ''),
            'regency': wss_data.get('regency', ''),
            'district': wss_data.get('district', ''),
            'village': wss_data.get('village', ''),
            'scale': wss_data.get('scale', ''),
            'businesses': wss_data.get('businesses', []),
            'streets': wss_data.get('streets', []),
            'environments': wss_data.get('environments', []),
            'landmarks': wss_data.get('landmarks', []),
            'coordinates': wss_data.get('coordinates', []),
            'economic_centers': wss_data.get('economic_centers', []),
            'building_data': wss_data.get('building_data', {})
        }
        
        logger.info(f"Successfully processed capture. Preview data: {preview_data}")
        
        return jsonify({
            'success': True,
            'preview': preview_data,
            'message': 'Data berhasil diekstrak! Silakan review data di bawah ini.'
        })
        
    except Exception as e:
        logger.error(f"Error processing capture: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/download', methods=['POST'])
def download_excel():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Tidak ada data untuk diunduh'})
        
        # Convert preview data back to wss_data format
        wss_data = {
            'map_id': data.get('map_id', ''),
            'province': data.get('province', ''),
            'regency': data.get('regency', ''),
            'district': data.get('district', ''),
            'village': data.get('village', ''),
            'scale': data.get('scale', ''),
            'businesses': data.get('businesses', []),
            'streets': data.get('streets', []),
            'environments': data.get('environments', []),
            'landmarks': data.get('landmarks', []),
            'coordinates': data.get('coordinates', []),
            'economic_centers': data.get('economic_centers', []),
            'building_data': data.get('building_data', {})
        }
        
        # Generate Excel file
        filename = f"wss_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        filepath = os.path.join('uploads', filename)
        
        # Create simple Excel with pandas
        df = pd.DataFrame({
            'Map ID': [wss_data.get('map_id', '')],
            'Province': [wss_data.get('province', '')],
            'Regency': [wss_data.get('regency', '')],
            'District': [wss_data.get('district', '')],
            'Village': [wss_data.get('village', '')],
            'Scale': [wss_data.get('scale', '')],
            'Processing Date': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        })
        
        df.to_excel(filepath, index=False)
        
        return send_file(filepath, as_attachment=True, download_name=filename)
        
    except Exception as e:
        logger.error(f"Error generating Excel: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080))) 