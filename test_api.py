#!/usr/bin/env python3
"""
Test script for SwipingForJobs Backend API
"""

import asyncio
import httpx
from main import app

async def test_remoteok_endpoint():
    """Test the RemoteOK endpoint directly"""
    print("Testing RemoteOK API endpoint...")
    try:
        # Import and call the function directly
        from main import get_remoteok_jobs
        result = await get_remoteok_jobs()
        print(f"✅ RemoteOK endpoint working! Found {result['count']} jobs")
        if result['jobs']:
            print(f"Sample job: {result['jobs'][0]['title']} at {result['jobs'][0]['company']}")
        return True
    except Exception as e:
        print(f"❌ RemoteOK endpoint failed: {str(e)}")
        return False

async def test_api_structure():
    """Test that the API structure is correct"""
    print("\nTesting API structure...")
    try:
        from main import app
        routes = [route.path for route in app.routes]
        expected_routes = ["/", "/jobs/remoteok", "/jobs/gemini", "/jobs/all"]
        
        for route in expected_routes:
            if route in routes:
                print(f"✅ Route {route} exists")
            else:
                print(f"❌ Route {route} missing")
        
        return True
    except Exception as e:
        print(f"❌ API structure test failed: {str(e)}")
        return False

async def test_user_endpoints():
    """Test user profile and application endpoints"""
    print("\nTesting user endpoints...")
    try:
        from main import app
        import json
        
        # Test data
        test_user = {
            "name": "Test User",
            "email": "test@example.com",
            "linkedin_url": "https://linkedin.com/in/testuser",
            "github_url": "https://github.com/testuser",
            "skills": "React, Python, Node.js",
            "preferences": ["frontend", "backend"],
            "resume_filename": "test_resume.pdf"
        }
        
        # Import endpoints directly for testing
        from main import create_user_profile, get_user_profile, apply_to_job, UserProfile, JobApplication
        from datetime import datetime
        
        # Test profile creation
        profile = UserProfile(**test_user)
        result = await create_user_profile(profile)
        print(f"✅ Profile creation: {result['message']}")
        
        # Test profile retrieval
        profile_result = await get_user_profile(test_user["email"])
        print(f"✅ Profile retrieval: Found user {profile_result['user']['name']}")
        
        # Test job application
        application = JobApplication(
            user_email=test_user["email"],
            job_title="Test Developer",
            company="Test Company",
            job_source="Test Source"
        )
        app_result = await apply_to_job(application)
        print(f"✅ Job application: {app_result['message']}")
        
        return True
    except Exception as e:
        print(f"❌ User endpoints test failed: {str(e)}")
        return False

async def main():
    """Run all tests"""
    print("🚀 Starting SwipingForJobs Backend Tests\n")
    
    # Test API structure
    await test_api_structure()
    
    # Test RemoteOK endpoint
    await test_remoteok_endpoint()
    
    # Test user endpoints
    await test_user_endpoints()
    
    print("\n📝 Notes:")
    print("- To test Gemini endpoint, add your GEMINI_API_KEY to .env file")
    print("- User data is now stored in backend (in-memory for development)")
    print("- Start the server with: python start_server.py")
    print("- Access API docs at: http://localhost:8000/docs")
    print("- Frontend connects at: http://localhost:3000")

if __name__ == "__main__":
    asyncio.run(main())
