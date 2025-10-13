import os
import sys
from dotenv import load_dotenv

def check_environment():
    print("🔍 Checking environment configuration...")
    
    # Load .env file
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
        print(f"✅ Loaded .env file from: {env_path}")
    else:
        print(f"⚠️  Warning: No .env file found at {env_path}")
    
    # Check required environment variables
    required_vars = [
        'LIVEKIT_URL',
        'LIVEKIT_API_KEY',
        'LIVEKIT_API_SECRET',
        'OPENAI_API_KEY',
        'ELEVENLABS_API_KEY'
    ]
    
    print("\n📋 Environment Variables:")
    print("-" * 50)
    
    all_good = True
    for var in required_vars:
        value = os.getenv(var)
        status = "✅" if value else "❌"
        print(f"{status} {var}: {'[SET]' if value else '[MISSING]'}")
        if not value:
            all_good = False
    
    print("\n" + "="*50)
    if all_good:
        print("✅ All required environment variables are set!")
    else:
        print("❌ Some required environment variables are missing!")
    
    # Check network connectivity
    print("\n🌐 Checking network connectivity...")
    try:
        import urllib.request
        urllib.request.urlopen('https://google.com', timeout=5)
        print("✅ Internet connection is working")
    except Exception as e:
        print(f"❌ No internet connection: {str(e)}")

if __name__ == "__main__":
    check_environment()
