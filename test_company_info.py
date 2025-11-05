#!/usr/bin/env python3
"""
Test script to verify company information and web search functionality
"""
import asyncio
import sys
import os
from pathlib import Path

# Add the backend src directory to Python path
backend_src = Path(__file__).parent / "backend" / "src"
sys.path.insert(0, str(backend_src))

async def test_company_info():
    """Test the company_info tool"""
    print("🧪 Testing company_info tool...")
    try:
        from tools.company_info import company_info
        
        # Test general company info
        print("\n📋 Testing general company information:")
        result = await company_info(None, "general")
        print(f"Result: {result[:200]}..." if len(result) > 200 else f"Result: {result}")
        
        # Test specific query
        print("\n🔍 Testing specific query (services):")
        result = await company_info(None, "services")
        print(f"Result: {result[:200]}..." if len(result) > 200 else f"Result: {result}")
        
    except Exception as e:
        print(f"❌ Company info test failed: {e}")
        import traceback
        traceback.print_exc()

async def test_web_search():
    """Test the web search tool"""
    print("\n🧪 Testing web_search tool...")
    try:
        from tools.web_search import search_web
        
        # Test web search
        print("\n🌐 Testing web search:")
        result = await search_web(None, "Info Services company")
        print(f"Result: {result[:300]}..." if len(result) > 300 else f"Result: {result}")
        
    except Exception as e:
        print(f"❌ Web search test failed: {e}")
        import traceback
        traceback.print_exc()

async def test_enhanced_company_info():
    """Test the enhanced get_company_information tool"""
    print("\n🧪 Testing enhanced get_company_information tool...")
    try:
        # Import the function from agent.py
        sys.path.insert(0, str(backend_src))
        from agent import get_company_information
        
        # Test general company info
        print("\n📋 Testing enhanced company information:")
        result = await get_company_information("general")
        print(f"Result: {result[:300]}..." if len(result) > 300 else f"Result: {result}")
        
    except Exception as e:
        print(f"❌ Enhanced company info test failed: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Run all tests"""
    print("🚀 Starting Clara Company Information Tests")
    print("=" * 50)
    
    await test_company_info()
    await test_web_search() 
    await test_enhanced_company_info()
    
    print("\n" + "=" * 50)
    print("✅ Tests completed!")

if __name__ == "__main__":
    asyncio.run(main())
