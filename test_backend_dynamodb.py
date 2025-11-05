#!/usr/bin/env python3
"""
Test DynamoDB connection from backend
"""
import boto3
import os

def test_dynamodb_connection():
    print("Testing DynamoDB connection...")
    print(f"AWS Region: {os.getenv('AWS_REGION', 'NOT SET')}")
    print(f"AWS Access Key: {os.getenv('AWS_ACCESS_KEY_ID', 'NOT SET')[:10]}...")
    
    try:
        # Test basic DynamoDB connection
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.Table('zenith-hr-employees')
        
        print(f"✅ Connected to table: {table.table_name}")
        
        # Test querying by employee_id using GSI
        from boto3.dynamodb.conditions import Key
        
        response = table.query(
            IndexName='EmployeeIdIndex',
            KeyConditionExpression=Key('employee_id').eq('1307'),
            Limit=1
        )
        
        items = response.get('Items', [])
        if items:
            employee = items[0]
            print(f"✅ Found employee: {employee.get('name', 'NO NAME')}")
            print(f"   Employee ID: {employee.get('employee_id', 'NO ID')}")
            print(f"   Department: {employee.get('department', 'NO DEPT')}")
        else:
            print("❌ No employee found for ID 1307")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_dynamodb_connection()
