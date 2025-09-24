#!/usr/bin/env python3
"""
Test script for Virtual Receptionist Flow Manager
"""
import sys
sys.path.insert(0, 'src')

from flow_manager import flow_manager, FlowState, UserType

def test_flow():
    print("🧪 Testing Virtual Receptionist Flow Manager")
    print("=" * 50)
    
    # Test 1: Initial status
    print("1. Testing initial flow status:")
    status = flow_manager.get_flow_status()
    print(f"   Status: {status}")
    
    # Test 2: Start flow
    print("\n2. Testing flow start:")
    success, message = flow_manager.process_wake_word_detected()
    print(f"   Success: {success}")
    print(f"   Message: {message}")
    
    # Test 3: Check session after start
    print("\n3. Testing session after start:")
    session = flow_manager.get_current_session()
    if session:
        print(f"   Session ID: {session.session_id}")
        print(f"   Current State: {session.current_state.value}")
        print(f"   User Type: {session.user_type.value}")
    else:
        print("   No active session found")
    
    # Test 4: User classification - Employee
    print("\n4. Testing employee classification:")
    success, message, next_state = flow_manager.process_user_classification("I am an employee")
    print(f"   Success: {success}")
    print(f"   Message: {message}")
    print(f"   Next State: {next_state.value if next_state else 'None'}")
    
    # Test 5: Check session after classification
    print("\n5. Testing session after classification:")
    status = flow_manager.get_flow_status()
    print(f"   Status: {status}")
    
    # Test 6: End session
    print("\n6. Testing session end:")
    message = flow_manager.end_session()
    print(f"   Message: {message}")
    
    print("\n✅ Flow Manager Test Complete!")

if __name__ == "__main__":
    test_flow()