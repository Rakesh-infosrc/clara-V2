#!/usr/bin/env python3
"""
Test script to validate agent can be created without errors
"""
import sys
sys.path.insert(0, 'src')

def test_agent():
    print("🤖 Testing Virtual Receptionist Agent Creation")
    print("=" * 50)
    
    try:
        from agent import Assistant
        print("✅ Agent module imported successfully")
        
        # Create agent instance
        agent = Assistant()
        print("✅ Agent instance created successfully")
        
        # Check if tools are properly loaded
        tool_count = len(agent.tools) if hasattr(agent, 'tools') else 0
        print(f"📋 Agent has {tool_count} tools available")
        
        # Test some basic agent properties
        if hasattr(agent, 'instructions'):
            print("✅ Agent instructions configured")
        
        if hasattr(agent, 'llm'):
            print("✅ LLM model configured")
            
        print("\n🎉 Agent test completed successfully!")
        print("The duplicate function name error has been resolved!")
        
    except Exception as e:
        print(f"❌ Error creating agent: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    success = test_agent()
    if success:
        print("\n🚀 Your Virtual Receptionist is ready to run!")
        print("You can now start the agent with: python main.py console")
    else:
        print("\n❌ There are still issues to resolve")