#!/usr/bin/env python3
"""
Debug script to check face recognition data and process
"""
import pickle
import pandas as pd
from pathlib import Path

def debug_face_recognition():
    print("=== FACE RECOGNITION DEBUG ===\n")
    
    # 1. Check encoding.pkl
    encoding_file = Path("data/dummy-data/encoding.pkl")
    if encoding_file.exists():
        with open(encoding_file, "rb") as f:
            data = pickle.load(f)
        
        print("1. ENCODING.PKL DATA:")
        print(f"   Keys: {list(data.keys())}")
        print(f"   Employee IDs: {data.get('employee_ids', [])}")
        print(f"   Number of encodings: {len(data.get('encodings', []))}")
        print()
        
        # Check each encoding
        for i, emp_id in enumerate(data.get('employee_ids', [])):
            encoding = data['encodings'][i]
            print(f"   {emp_id}: encoding shape {encoding.shape if hasattr(encoding, 'shape') else 'unknown'}")
    else:
        print("❌ encoding.pkl not found!")
        return
    
    # 2. Check employee_details.csv
    csv_file = Path("data/dummy-data/employee_details.csv")
    if csv_file.exists():
        df = pd.read_csv(csv_file)
        print("\n2. EMPLOYEE_DETAILS.CSV:")
        print(f"   Total employees: {len(df)}")
        print("   Employee mapping:")
        for _, row in df.iterrows():
            print(f"   {row['EmployeeID']} -> {row['Name']} ({row['Email']})")
    else:
        print("❌ employee_details.csv not found!")
        return
    
    # 3. Check image files
    image_dir = Path("employee_image")
    if image_dir.exists():
        print(f"\n3. EMPLOYEE IMAGES:")
        image_files = list(image_dir.glob("*"))
        print(f"   Total images: {len(image_files)}")
        for img_file in sorted(image_files):
            size_kb = img_file.stat().st_size / 1024
            print(f"   {img_file.name}: {size_kb:.1f} KB")
    else:
        print("❌ employee_image directory not found!")
    
    # 4. Cross-check consistency
    print(f"\n4. CONSISTENCY CHECK:")
    encoding_ids = set(data.get('employee_ids', []))
    csv_ids = set(df['EmployeeID'].tolist())
    image_ids = set([f.stem for f in image_files if f.suffix.lower() in ['.jpg', '.png', '.jpeg']])
    
    print(f"   Encoding IDs: {sorted(encoding_ids)}")
    print(f"   CSV IDs: {sorted(csv_ids)}")
    print(f"   Image IDs: {sorted(image_ids)}")
    
    missing_in_csv = encoding_ids - csv_ids
    missing_in_encoding = csv_ids - encoding_ids
    missing_images = encoding_ids - image_ids
    
    if missing_in_csv:
        print(f"   ⚠️  IDs in encoding but not in CSV: {missing_in_csv}")
    if missing_in_encoding:
        print(f"   ⚠️  IDs in CSV but not in encoding: {missing_in_encoding}")
    if missing_images:
        print(f"   ⚠️  IDs in encoding but no image: {missing_images}")
    
    if not (missing_in_csv or missing_in_encoding or missing_images):
        print("   ✅ All data is consistent!")

if __name__ == "__main__":
    debug_face_recognition()
