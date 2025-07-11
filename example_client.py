#!/usr/bin/env python3
"""
Example client for SwipingForJobs Backend API
This demonstrates how to use the API endpoints programmatically.
"""

import asyncio
import httpx
import json

API_BASE_URL = "http://localhost:8000"

async def test_api_client():
    """Test the API client functionality"""
    
    async with httpx.AsyncClient() as client:
        
        print("🚀 Testing SwipingForJobs API Client\n")
        
        # Test root endpoint
        print("1. Testing root endpoint...")
        try:
            response = await client.get(f"{API_BASE_URL}/")
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ API: {data['message']} (v{data['version']})")
            else:
                print(f"   ❌ Root endpoint failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Root endpoint error: {e}")
            print("   💡 Make sure the server is running: python start_server.py")
            return
        
        # Test RemoteOK endpoint
        print("\n2. Testing RemoteOK jobs endpoint...")
        try:
            response = await client.get(f"{API_BASE_URL}/jobs/remoteok")
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Found {data['count']} jobs from {data['source']}")
                if data['jobs']:
                    job = data['jobs'][0]
                    print(f"   📋 Sample: {job['title']} at {job['company']}")
                    print(f"   🏷️  Tags: {', '.join(job['tags'][:3])}...")
            else:
                print(f"   ❌ RemoteOK endpoint failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ RemoteOK endpoint error: {e}")
        
        # Test Gemini endpoint
        print("\n3. Testing Gemini AI jobs endpoint...")
        try:
            response = await client.get(f"{API_BASE_URL}/jobs/gemini")
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Generated {data['count']} jobs from {data['source']}")
                if data['jobs']:
                    job = data['jobs'][0]
                    print(f"   📋 Sample: {job['title']} at {job['company']}")
                    print(f"   🏷️  Tags: {', '.join(job['tags'][:3])}...")
            elif response.status_code == 503:
                print("   ⚠️  Gemini API key not configured")
                print("   💡 Add your GEMINI_API_KEY to .env file")
            else:
                print(f"   ❌ Gemini endpoint failed: {response.status_code}")
                error_detail = response.json().get('detail', 'Unknown error')
                print(f"   📄 Error: {error_detail}")
        except Exception as e:
            print(f"   ❌ Gemini endpoint error: {e}")
        
        # Test combined endpoint
        print("\n4. Testing combined jobs endpoint...")
        try:
            response = await client.get(f"{API_BASE_URL}/jobs/all")
            if response.status_code == 200:
                data = response.json()
                total_jobs = data['total_count']
                remoteok_jobs = data['remoteok']['count']
                gemini_jobs = data['gemini']['count']
                
                print(f"   ✅ Total jobs found: {total_jobs}")
                print(f"   📊 RemoteOK: {remoteok_jobs} jobs")
                print(f"   🤖 Gemini AI: {gemini_jobs} jobs")
                
                # Show any errors
                if data['remoteok'].get('error'):
                    print(f"   ⚠️  RemoteOK error: {data['remoteok']['error']}")
                if data['gemini'].get('error'):
                    print(f"   ⚠️  Gemini error: {data['gemini']['error']}")
                    
            else:
                print(f"   ❌ Combined endpoint failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Combined endpoint error: {e}")
        
        print("\n🎉 API client test completed!")
        print("\n💡 Next steps:")
        print("   • Visit http://localhost:8000/docs for interactive API docs")
        print("   • Configure GEMINI_API_KEY in .env for AI-generated jobs")
        print("   • Integrate these endpoints into your frontend application")

def print_usage_example():
    """Print example code for using the API"""
    example_code = '''
# Example: Fetch jobs in your Python application

import httpx
import asyncio

async def get_jobs():
    async with httpx.AsyncClient() as client:
        # Get jobs from RemoteOK
        response = await client.get("http://localhost:8000/jobs/remoteok")
        remoteok_jobs = response.json()
        
        # Get AI-generated jobs
        response = await client.get("http://localhost:8000/jobs/gemini")
        gemini_jobs = response.json()
        
        # Combine results
        all_jobs = remoteok_jobs['jobs'] + gemini_jobs['jobs']
        return all_jobs

# Run the function
jobs = asyncio.run(get_jobs())
print(f"Found {len(jobs)} total jobs!")
'''
    
    print("\n📝 Usage Example:")
    print(example_code)

async def main():
    """Main function"""
    await test_api_client()
    print_usage_example()

if __name__ == "__main__":
    asyncio.run(main())
