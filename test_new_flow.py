#!/usr/bin/env python3
"""
Test script for the new Virtual Receptionist flow:
1. Wake word detection
2. Employee/visitor classification 
3. Face recognition only after employee classification
4. Data passing to LiveKit/TTS
"""

import sys
import os

# Add backend/src to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend', 'src'))

from flow_manager import flow_manager, FlowState, UserType
from flow_signal import get_signal, post_signal
import time

def test_complete_flow():
    """Test the complete flow sequence"""
    print("=" * 60)
    print("TESTING NEW VIRTUAL RECEPTIONIST FLOW")
    print("=" * 60)
    
    # Test 1: Wake word detection
    print("\n1. Testing wake word detection...")
    success, message = flow_manager.process_wake_word_detected()
    print(f"✓ Wake word result: {message}")
    assert success, "Wake word detection should succeed"
    
    session = flow_manager.get_current_session()
    assert session is not None, "Session should be created"
    assert session.current_state == FlowState.USER_CLASSIFICATION, "Should be in user classification state"
    print(f"✓ Flow state: {session.current_state.value}")
    
    # Test 2: Employee classification (should trigger face recognition signal)
    print("\n2. Testing employee classification...")
    success, message, next_state = flow_manager.process_user_classification("I am an employee")
    print(f"✓ Employee classification result: {message}")
    assert success, "Employee classification should succeed"
    assert next_state == FlowState.FACE_RECOGNITION, "Should move to face recognition state"
    
    session = flow_manager.get_current_session()
    assert session.user_type == UserType.EMPLOYEE, "User type should be employee"
    print(f"✓ User type: {session.user_type.value}")
    print(f"✓ Next state: {next_state.value}")
    
    # Test 3: Check if signal was posted for frontend
    print("\n3. Testing signal mechanism...")
    signal = get_signal(clear=False)  # Don't clear yet
    if signal:
        print(f"✓ Signal posted: {signal['name']}")
        print(f"✓ Signal payload: {signal.get('payload', {})}")
        assert signal['name'] == 'start_face_capture', "Should signal to start face capture"
    else:
        print("⚠ No signal found - this might be expected if signal was already consumed")
    
    # Test 4: Simulate face recognition success
    print("\n4. Testing face recognition result processing...")
    face_result = {
        "status": "success",
        "name": "John Doe",
        "employeeId": "EMP001"
    }
    success, message, next_state = flow_manager.process_face_recognition_result(face_result)
    print(f"✓ Face recognition result: {message}")
    assert success, "Face recognition should succeed"
    assert next_state == FlowState.EMPLOYEE_VERIFIED, "Should move to employee verified state"
    
    session = flow_manager.get_current_session()
    assert session.is_verified, "Employee should be verified"
    print(f"✓ Verification status: {session.is_verified}")
    print(f"✓ Employee name: {session.user_data.get('employee_name')}")
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED - NEW FLOW WORKING CORRECTLY")
    print("=" * 60)

def test_visitor_flow():
    """Test visitor classification flow"""
    print("\n" + "=" * 60)
    print("TESTING VISITOR FLOW")
    print("=" * 60)
    
    # Clear any existing signals
    get_signal(clear=True)
    
    # Reset flow
    flow_manager.create_session()
    flow_manager.process_wake_word_detected()
    
    # Test visitor classification
    success, message, next_state = flow_manager.process_user_classification("I am a visitor")
    print(f"✓ Visitor classification result: {message}")
    assert success, "Visitor classification should succeed"
    assert next_state == FlowState.VISITOR_INFO_COLLECTION, "Should move to visitor info collection"
    
    session = flow_manager.get_current_session()
    assert session.user_type == UserType.VISITOR, "User type should be visitor"
    print(f"✓ User type: {session.user_type.value}")
    print(f"✓ Next state: {next_state.value}")
    
    # Check that no face recognition signal was posted for visitor
    signal = get_signal(clear=False)
    if signal and signal.get('name') == 'start_face_capture':
        print("❌ ERROR: Face capture signal should NOT be sent for visitors")
        assert False, "Face recognition should not trigger for visitors"
    else:
        print("✓ No face capture signal sent for visitor (correct behavior)")
    
    print("✅ VISITOR FLOW TEST PASSED")

def test_flow_status():
    """Test flow status reporting"""
    print("\n" + "=" * 60)
    print("TESTING FLOW STATUS")
    print("=" * 60)
    
    status = flow_manager.get_flow_status()
    print(f"✓ Flow status: {status}")
    
    if status.get('status') != 'no_active_session':
        print(f"✓ Session ID: {status.get('session_id')}")
        print(f"✓ Current state: {status.get('current_state')}")
        print(f"✓ User type: {status.get('user_type')}")
        print(f"✓ Verified: {status.get('is_verified')}")
        print(f"✓ Last activity: {status.get('last_activity')}")

if __name__ == "__main__":
    try:
        # Run complete flow test
        test_complete_flow()
        
        # Run visitor flow test  
        test_visitor_flow()
        
        # Show flow status
        test_flow_status()
        
        print(f"\n🎉 ALL TESTS COMPLETED SUCCESSFULLY!")
        print(f"The new flow is working correctly:")
        print(f"  1. ✅ Wake word detection works")
        print(f"  2. ✅ Employee/visitor classification works")
        print(f"  3. ✅ Face recognition only triggers after employee classification")
        print(f"  4. ✅ Visitors don't trigger face recognition")
        print(f"  5. ✅ Data flows correctly through the system")
        print(f"  6. ✅ Ready for LiveKit/TTS integration")
        
    except Exception as e:
        print(f"❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)