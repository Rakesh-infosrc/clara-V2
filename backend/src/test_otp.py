#!/usr/bin/env python3
"""
Test OTP verification directly
"""
import asyncio
from tools.employee_verification import get_employee_details

async def test_otp():
    print("=== OTP VERIFICATION TEST ===")
    
    # Test with a known employee (adjust these values)
    name = "Rakesh"  # Replace with actual employee name
    employee_id = "E001"  # Replace with actual employee ID
    
    print(f"Testing with: {name}, {employee_id}")
    
    # Step 1: Send OTP
    print("\n1. Sending OTP...")
    result1 = await get_employee_details(None, name, employee_id, None)
    print(f"Result: {result1}")
    
    # Step 2: Test OTP verification (you'll need to get the OTP from email or dev mode)
    if "DEV MODE" in result1:
        # Extract OTP from dev mode response
        import re
        otp_match = re.search(r'Use this OTP to verify: (\d+)', result1)
        if otp_match:
            test_otp = otp_match.group(1)
            print(f"\n2. Testing OTP verification with: {test_otp}")
            result2 = await get_employee_details(None, name, employee_id, test_otp)
            print(f"Result: {result2}")
        else:
            print("Could not extract OTP from dev mode response")
    else:
        print("Not in dev mode - check your email for OTP")

if __name__ == "__main__":
    asyncio.run(test_otp())
