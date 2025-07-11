#!/usr/bin/env python3
"""
Startup script for SwipingForJobs Backend
"""

import os
import sys

def check_environment():
    """Check if environment is properly configured"""
    print("🔍 Checking environment configuration...")
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("❌ .env file not found!")
        return False
    
    # Check if Gemini API key is configured
    from dotenv import load_dotenv
    load_dotenv()
    
    gemini_key = os.getenv('GEMINI_API_KEY')
    if not gemini_key or gemini_key == 'your_gemini_api_key_here':
        print("⚠️  GEMINI_API_KEY not configured in .env file")
        print("   RemoteOK endpoint will work, but Gemini endpoint will return an error")
    else:
        print("✅ GEMINI_API_KEY configured")
    
    return True

def main():
    """Main startup function"""
    print("🚀 Starting SwipingForJobs Backend Server")
    print("=" * 50)
    
    if not check_environment():
        print("\n❌ Environment check failed!")
        sys.exit(1)
    
    print("\n📋 Available endpoints:")
    print("  • GET  /                 - API information")
    print("  • GET  /jobs/remoteok    - Remote jobs from RemoteOK")
    print("  • GET  /jobs/gemini      - AI-generated jobs from Gemini")
    print("  • GET  /jobs/all         - Jobs from both sources")
    print("  • GET  /docs             - API documentation (Swagger)")
    print("  • GET  /redoc            - API documentation (ReDoc)")
    
    print("\n🌐 Server will start at: http://localhost:8000")
    print("📚 API docs available at: http://localhost:8000/docs")
    print("\nPress Ctrl+C to stop the server")
    print("=" * 50)
    
    # Import and run the FastAPI app
    import uvicorn
    from main import app
    
    try:
        uvicorn.run(
            app, 
            host="0.0.0.0", 
            port=8000,
            log_level="info",
            access_log=True
        )
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
