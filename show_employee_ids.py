import pickle
import sys

try:
    with open('encoding.pkl', 'rb') as f:
        data = pickle.load(f)
    
    print("Employee IDs in pickle file:")
    employee_ids = data.get('employee_ids', [])
    for i, emp_id in enumerate(employee_ids):
        print(f"{i+1}. {emp_id}")
    
    print(f"\nTotal: {len(employee_ids)} employees registered")
    
except Exception as e:
    print(f"Error: {e}")
