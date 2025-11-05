#!/usr/bin/env python3

import os
import sys
sys.path.append('backend/src')

from tools.employee_repository import get_employee_by_id
from tools.config import EMPLOYEE_TABLE_NAME, EMPLOYEE_ID_INDEX, EMPLOYEE_PRIMARY_KEY

def test_employee_lookup():
    print(f"Testing DynamoDB employee lookup...")
    print(f"Table: {EMPLOYEE_TABLE_NAME}")
    print(f"Index: {EMPLOYEE_ID_INDEX}")
    print(f"Primary Key: {EMPLOYEE_PRIMARY_KEY}")
    print(f"AWS Region: {os.getenv('AWS_REGION', 'NOT SET')}")
    print()
    
    # Test employee ID 1307 (from face recognition result)
    employee_id = "1307"
    print(f"Looking up employee ID: {employee_id}")
    
    try:
        result = get_employee_by_id(employee_id)
        if result:
            print(f"✅ Found employee: {result}")
            print(f"Name: {result.get('name', 'NOT SET')}")
            print(f"Employee ID: {result.get('employee_id', 'NOT SET')}")
        else:
            print(f"❌ No employee found for ID: {employee_id}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_employee_lookup()
