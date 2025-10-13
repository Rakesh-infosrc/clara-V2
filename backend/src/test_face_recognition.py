#!/usr/bin/env python3
"""
Test script to debug face recognition issues
"""
import pickle
import pandas as pd
from pathlib import Path

# Load encoding data
try:
    with open("../data/dummy-data/encoding.pkl", "rb") as f:
        encoding_data = pickle.load(f)
    
    print("=== FACE RECOGNITION DEBUG ===")
    print(f"✅ Encoding file loaded successfully")
    print(f"📊 Number of encoded faces: {len(encoding_data['encodings'])}")
    print(f"👥 Employee IDs in encodings: {encoding_data['employee_ids']}")
    
except Exception as e:
    print(f"❌ Error loading encodings: {e}")
    exit(1)

# Check employee CSV
try:
    employee_df = pd.read_csv("../data/dummy-data/employee_details.csv")
    print(f"\n📋 Employee CSV loaded successfully")
    print(f"👥 Employee IDs in CSV: {list(employee_df['EmployeeID'])}")
    print(f"📝 Employee Names: {list(employee_df['Name'])}")
    
    # Check for mismatches
    csv_ids = set(employee_df['EmployeeID'])
    encoding_ids = set(encoding_data['employee_ids'])
    
    missing_in_csv = encoding_ids - csv_ids
    missing_in_encodings = csv_ids - encoding_ids
    
    if missing_in_csv:
        print(f"⚠️  Employee IDs in encodings but NOT in CSV: {missing_in_csv}")
    if missing_in_encodings:
        print(f"⚠️  Employee IDs in CSV but NOT in encodings: {missing_in_encodings}")
    
    if not missing_in_csv and not missing_in_encodings:
        print(f"✅ All employee IDs match between encodings and CSV")
        
except Exception as e:
    print(f"❌ Error loading employee CSV: {e}")

# Check employee images
try:
    image_dir = Path("../employee_image")
    if image_dir.exists():
        image_files = list(image_dir.glob("*.jpg")) + list(image_dir.glob("*.png"))
        print(f"\n📸 Found {len(image_files)} employee images:")
        for img in image_files:
            print(f"   - {img.name}")
    else:
        print(f"❌ Employee image directory not found: {image_dir}")
except Exception as e:
    print(f"❌ Error checking images: {e}")

print(f"\n=== RECOMMENDATIONS ===")
print(f"1. Ensure employee images are named with correct IDs (E001.jpg, E002.jpg, etc.)")
print(f"2. Run 'python encode_faces.py' after adding/updating images")
print(f"3. Check face recognition tolerance in tools/face_recognition.py")
print(f"4. Test with good lighting and clear face visibility")
