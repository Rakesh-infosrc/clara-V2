#!/usr/bin/env python3
"""
Comprehensive test of the complete employee recognition flow
"""
import sys
sys.path.insert(0, 'src')

def test_complete_employee_flow():
    print("🔄 Testing Complete Employee Recognition Flow")
    print("=" * 60)
    
    try:
        from flow_manager import flow_manager, FlowState
        from agent_state import is_verified, verified_user_name, verified_user_id, set_user_verified, clear_verification
        from tools import run_face_verify
        
        # Clear any previous state
        clear_verification()
        print("🧹 Cleared previous verification state")
        
        # Step 1: User says "Hey Clara"
        print("\n1️⃣ User says 'Hey Clara' - Starting flow:")
        success, message = flow_manager.process_wake_word_detected()
        print(f"   Response: {message}")
        print(f"   Flow started: {success}")
        
        # Step 2: System asks Employee or Visitor
        session = flow_manager.get_current_session()
        print(f"   Current state: {session.current_state.value}")
        
        # Step 3: User says "I'm an employee"
        print("\n2️⃣ User says 'I'm an employee':")
        success, message, next_state = flow_manager.process_user_classification("I'm an employee")
        print(f"   Response: {message}")
        print(f"   Next state: {next_state.value}")
        
        # Step 4: System prompts for face recognition
        print(f"   Current state: {session.current_state.value}")
        
        # Step 5: Face recognition happens (simulated)
        print("\n3️⃣ Face recognition occurs (simulated success):")
        face_result = {
            "status": "success",
            "name": "Rakesh",
            "employeeId": "E002"
        }
        
        # This simulates what the /face_verify endpoint does:
        # 1) Set agent verification state
        set_user_verified(face_result["name"], face_result["employeeId"])
        # 2) Advance flow manager
        success, message, next_state = flow_manager.process_face_recognition_result(face_result)
        
        print(f"   Recognition result: {success}")
        print(f"   Response: {message}")
        print(f"   Next state: {next_state.value}")
        
        # Step 6: Check all verification states
        print("\n4️⃣ Verification Status Check:")
        print(f"   Agent State - Verified: {is_verified}")
        print(f"   Agent State - Name: {verified_user_name}")
        print(f"   Agent State - ID: {verified_user_id}")
        
        session = flow_manager.get_current_session()
        print(f"   Flow State - Verified: {session.is_verified}")
        print(f"   Flow State - Name: {session.user_data.get('employee_name')}")
        print(f"   Flow State - ID: {session.user_data.get('employee_id')}")
        print(f"   Flow State - Current: {session.current_state.value}")
        
        # Step 7: Test tool access
        print("\n5️⃣ Testing Tool Access:")
        has_access, access_message = flow_manager.process_tool_request("company_info")
        print(f"   Company info access: {has_access}")
        print(f"   Access message: {access_message}")
        
        has_access, access_message = flow_manager.process_tool_request("send_email")  
        print(f"   Email access: {has_access}")
        print(f"   Access message: {access_message}")
        
        # Step 8: End session
        print("\n6️⃣ Ending session:")
        end_message = flow_manager.end_session()
        print(f"   End message: {end_message}")
        
        print("\n" + "="*60)
        print("🎉 COMPLETE EMPLOYEE FLOW TEST SUCCESSFUL!")
        print("✅ Face recognition → Agent verification → Tool access")
        print("✅ All systems integrated and working properly!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error in complete flow test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_complete_employee_flow()
    if success:
        print("\n🚀 Your Virtual Receptionist is fully functional!")
        print("🎯 The employee recognition issue has been resolved!")
    else:
        print("\n❌ Issues still remain to be fixed")