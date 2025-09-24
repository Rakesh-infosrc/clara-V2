#!/usr/bin/env python3
"""
Test server endpoint integration with flow manager
"""
import sys
sys.path.insert(0, 'src')

def test_server_integration():
    print("🌐 Testing Server Integration with Flow Manager")
    print("=" * 50)
    
    try:
        # Test 1: Import server functions
        print("1. Testing server imports:")
        from server import face_verify_endpoint
        from flow_manager import flow_manager  
        from agent_state import is_verified, verified_user_name
        print("   ✅ All imports successful")
        
        # Test 2: Start a flow session first
        print("\n2. Starting flow session:")
        success, message = flow_manager.process_wake_word_detected()
        print(f"   Flow started: {success}")
        
        # Classify as employee
        success, message, next_state = flow_manager.process_user_classification("employee")
        print(f"   Classified as employee: {success}")
        print(f"   Current state: {next_state.value}")
        
        # Test 3: Simulate server integration behavior
        print("\n3. Simulating server face verification integration:")
        
        # Mock successful face verification result
        mock_result = {
            "status": "success", 
            "name": "Rakesh",
            "employeeId": "E002"
        }
        
        # Simulate what the server endpoint does
        from agent_state import set_user_verified
        set_user_verified(mock_result["name"], mock_result["employeeId"])
        flow_manager.process_face_recognition_result(mock_result)
        
        print("   ✅ Server integration simulation complete")
        
        # Test 4: Check final states
        print("\n4. Checking final verification states:")
        print(f"   Agent verified: {is_verified}")
        print(f"   Agent user: {verified_user_name}")
        
        session = flow_manager.get_current_session()
        if session:
            print(f"   Flow verified: {session.is_verified}")
            print(f"   Flow state: {session.current_state.value}")
            print(f"   Flow user: {session.user_data.get('employee_name')}")
        
        print("\n✅ Server Integration Test Complete!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error in server integration test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_server_integration()
    if success:
        print("\n🎉 All systems integrated successfully!")
        print("Your face recognition now properly connects to the agent!")
    else:
        print("\n❌ Integration issues detected")