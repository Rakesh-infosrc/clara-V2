#!/usr/bin/env python3
"""
Test script for face verification integration with flow manager
"""
import sys
sys.path.insert(0, 'src')

def test_face_verification_flow():
    print("🔍 Testing Face Verification Flow Integration")
    print("=" * 50)
    
    # Test 1: Start flow and classify as employee
    print("1. Starting flow and classifying as employee:")
    from flow_manager import flow_manager
    
    # Start flow
    success, message = flow_manager.process_wake_word_detected()
    print(f"   Flow started: {message}")
    
    # Classify as employee
    success, message, next_state = flow_manager.process_user_classification("I am an employee")
    print(f"   Classified: {message}")
    print(f"   Next state: {next_state.value}")
    
    # Test 2: Simulate successful face recognition
    print("\n2. Simulating successful face recognition:")
    face_result = {
        "status": "success",
        "name": "Rakesh",
        "employeeId": "E002"
    }
    success, message, next_state = flow_manager.process_face_recognition_result(face_result)
    print(f"   Success: {success}")
    print(f"   Message: {message}")
    print(f"   Next state: {next_state.value}")
    
    # Test 3: Check verification status
    print("\n3. Checking verification status:")
    session = flow_manager.get_current_session()
    if session:
        print(f"   User verified: {session.is_verified}")
        print(f"   Employee name: {session.user_data.get('employee_name', 'N/A')}")
        print(f"   Employee ID: {session.user_data.get('employee_id', 'N/A')}")
        print(f"   Current state: {session.current_state.value}")
    
    # Test 4: Test agent state integration
    print("\n4. Testing agent state integration:")
    try:
        from agent_state import is_verified, verified_user_name, verified_user_id
        print(f"   Agent verified: {is_verified}")
        print(f"   Agent user name: {verified_user_name}")
        print(f"   Agent user ID: {verified_user_id}")
    except Exception as e:
        print(f"   Error checking agent state: {e}")
    
    # Test 5: End session
    print("\n5. Ending session:")
    message = flow_manager.end_session()
    print(f"   End message: {message}")
    
    print("\n✅ Face Verification Flow Test Complete!")

if __name__ == "__main__":
    test_face_verification_flow()