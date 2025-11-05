import pickle
import sys

try:
    with open('encoding.pkl', 'rb') as f:
        data = pickle.load(f)
    
    print("Pickle file loaded successfully!")
    print(f"Type: {type(data)}")
    print(f"Keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
    
    if isinstance(data, dict):
        for key, value in data.items():
            print(f"{key}: {type(value)} - {len(value) if hasattr(value, '__len__') else 'No length'}")
            if hasattr(value, '__len__') and len(value) > 0:
                print(f"  First item type: {type(value[0]) if len(value) > 0 else 'Empty'}")
    
except Exception as e:
    print(f"Error loading pickle file: {e}")
