import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import json

import httpx
import google.generativeai as genai
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# Import our database and file management modules
from database import db_manager
from file_manager import file_manager

# Load environment variables
load_dotenv()

# Configure logging (avoid logging sensitive data)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="SwipingForJobs Backend",
    description="Fetch job listings from RemoteOK and Gemini AI",
    version="1.0.0"
)

# Add CORS middleware to allow frontend connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Configure Gemini AI
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
    logger.warning("GEMINI_API_KEY not properly configured")
else:
    genai.configure(api_key=GEMINI_API_KEY)

# Pydantic models for request/response validation
class UserRegistration(BaseModel):
    name: str
    email: str
    linkedin_url: str = ""
    github_url: str = ""
    skills: str
    preferences: List[str]

class UserLogin(BaseModel):
    name: str
    login_code: str

class JobApplication(BaseModel):
    user_id: int
    user_email: str
    job_title: str
    company: str
    job_source: str
    job_url: str = ""

# Startup event to initialize database
@app.on_event("startup")
async def startup_event():
    await db_manager.init_database()
    logger.info("Database initialized successfully")

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "SwipingForJobs Backend API", "version": "1.0.0"}

@app.post("/users/register")
async def register_user(
    name: str = Form(...),
    email: str = Form(...),
    linkedin_url: str = Form(""),
    github_url: str = Form(""),
    skills: str = Form(...),
    preferences: str = Form(...),  # comma-separated string
    resume: Optional[UploadFile] = File(None)
):
    """Register a new user with optional resume upload"""
    try:
        # Parse preferences
        preferences_list = [p.strip() for p in preferences.split(',') if p.strip()]
        
        # Handle resume upload if provided
        resume_filename = ""
        resume_path = ""
        
        if resume and resume.filename:
            file_info = await file_manager.save_resume(resume, email)
            resume_filename = file_info["original_filename"]
            resume_path = file_info["file_path"]
        
        # Create user in database
        result = await db_manager.create_user(
            name=name,
            email=email,
            linkedin_url=linkedin_url,
            github_url=github_url,
            skills=skills,
            preferences=preferences_list,
            resume_filename=resume_filename,
            resume_path=resume_path
        )
        
        logger.info(f"User registered: {email} with login code: {result['login_code']}")
        
        return {
            "message": "Registration successful! Save your login code.",
            "user_id": result["user_id"],
            "login_code": result["login_code"],
            "name": name,
            "email": email,
            "resume_uploaded": bool(resume_filename)
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(status_code=500, detail="Registration failed")

@app.post("/users/login")
async def login_user(login_data: UserLogin):
    """Login user with name and 4-digit code"""
    try:
        user = await db_manager.authenticate_user(login_data.name, login_data.login_code)
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid name or login code")
        
        logger.info(f"User logged in: {user['email']}")
        
        return {
            "message": "Login successful",
            "user": {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "linkedin_url": user["linkedin_url"],
                "github_url": user["github_url"],
                "skills": user["skills"],
                "preferences": user["preferences"],
                "resume_filename": user["resume_filename"],
                "has_resume": bool(user["resume_filename"])
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(status_code=500, detail="Login failed")

@app.get("/users/profile/{user_id}")
async def get_user_profile(user_id: int):
    """Get user profile by ID"""
    # This would typically require authentication in production
    # For now, we'll skip session validation for simplicity
    return {"message": "Use login endpoint to get user profile"}

@app.post("/users/apply")
async def apply_to_job(application: JobApplication):
    """Record job application"""
    try:
        success = await db_manager.record_job_application(
            user_id=application.user_id,
            user_email=application.user_email,
            job_title=application.job_title,
            company=application.company,
            job_source=application.job_source,
            job_url=application.job_url
        )
        
        if success:
            logger.info(f"Application recorded: {application.user_email} -> {application.job_title} at {application.company}")
            return {
                "message": "Application recorded successfully",
                "application": {
                    "job_title": application.job_title,
                    "company": application.company,
                    "applied_at": datetime.now().isoformat()
                }
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to record application")
            
    except Exception as e:
        logger.error(f"Error recording application: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to record application")

@app.get("/users/applications/{user_id}")
async def get_user_applications(user_id: int):
    """Get all applications for a user"""
    try:
        applications = await db_manager.get_user_applications(user_id)
        
        return {
            "applications": applications,
            "count": len(applications)
        }
        
    except Exception as e:
        logger.error(f"Error fetching applications: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch applications")

@app.get("/users/resume/{user_id}")
async def download_resume(user_id: int):
    """Download user's resume file"""
    try:
        # In production, add proper authentication
        # For now, this is a placeholder
        return {"message": "Resume download endpoint - requires authentication"}
        
    except Exception as e:
        logger.error(f"Error downloading resume: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to download resume")

@app.get("/jobs/remoteok")
async def get_remoteok_jobs():
    """
    Fetch job listings from RemoteOK API and filter for intern/junior positions
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://remoteok.com/api",
                headers={"User-Agent": "SwipingForJobs-Backend/1.0"},
                timeout=30.0
            )
            response.raise_for_status()
            
            # RemoteOK API returns a list where first item is metadata
            jobs_data = response.json()
            if isinstance(jobs_data, list) and len(jobs_data) > 1:
                jobs = jobs_data[1:]  # Skip the first metadata item
            else:
                jobs = jobs_data if isinstance(jobs_data, list) else []
            
            # Filter for intern/junior positions
            filtered_jobs = []
            for job in jobs:
                if not isinstance(job, dict):
                    continue
                    
                position = job.get("position", "").lower()
                if "intern" in position or "junior" in position:
                    # Structure the job data
                    structured_job = {
                        "title": job.get("position", ""),
                        "company": job.get("company", ""),
                        "tags": job.get("tags", []),
                        "location": job.get("location", "Remote"),
                        "apply_url": job.get("apply_url") or job.get("url", ""),
                        "description": job.get("description", ""),
                        "salary": job.get("salary_min", ""),
                        "date": job.get("date", ""),
                        "source": "RemoteOK"
                    }
                    filtered_jobs.append(structured_job)
                    
                    if len(filtered_jobs) >= 10:
                        break
            
            logger.info(f"Found {len(filtered_jobs)} intern/junior jobs from RemoteOK")
            return {"jobs": filtered_jobs, "count": len(filtered_jobs), "source": "RemoteOK"}
            
    except httpx.TimeoutException:
        logger.error("Timeout while fetching RemoteOK jobs")
        raise HTTPException(status_code=504, detail="Timeout while fetching jobs from RemoteOK")
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error while fetching RemoteOK jobs: {e.response.status_code}")
        raise HTTPException(status_code=502, detail="Error fetching jobs from RemoteOK")
    except Exception as e:
        logger.error(f"Unexpected error while fetching RemoteOK jobs: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error while fetching RemoteOK jobs")

@app.get("/jobs/gemini")
async def get_gemini_jobs():
    """
    Use Gemini AI to search for recent remote internships and junior developer roles
    """
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
        raise HTTPException(
            status_code=503, 
            detail="Gemini API key not configured. Please set GEMINI_API_KEY in your .env file"
        )
    
    try:
        # Initialize the model with the correct model name
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Create the prompt for finding recent job listings
        current_date = datetime.now().strftime("%Y-%m-%d")
        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        
        prompt = f"""
        You are a job search assistant. Find 10 recent remote internships or junior developer roles 
        (frontend, backend, ML/AI) posted between {week_ago} and {current_date}.
        
        Return the results as a valid JSON array with exactly this structure:
        [
          {{
            "title": "Job Title",
            "company": "Company Name",
            "tags": ["tag1", "tag2", "tag3"],
            "location": "Remote" or specific location,
            "apply_url": "https://example.com/apply",
            "description": "Brief job description (2-3 sentences)"
          }}
        ]
        
        Focus on:
        - Remote positions only
        - Entry-level roles (intern, junior, graduate, entry-level)
        - Technology roles (software engineering, web development, data science, ML/AI)
        - Recent postings (last 7 days)
        - Real companies and realistic job descriptions
        
        Ensure the JSON is valid and contains exactly 10 job listings.
        """
        
        # Generate response from Gemini
        response = model.generate_content(prompt)
        
        if not response.text:
            raise HTTPException(status_code=502, detail="Empty response from Gemini API")
        
        # Extract JSON from the response
        response_text = response.text.strip()
        
        # Remove markdown code blocks if present
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        
        response_text = response_text.strip()
        
        # Parse the JSON response
        try:
            jobs_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {str(e)}")
            logger.error(f"Response text: {response_text[:500]}...")
            raise HTTPException(status_code=502, detail="Invalid JSON response from Gemini API")
        
        # Validate the structure
        if not isinstance(jobs_data, list):
            raise HTTPException(status_code=502, detail="Gemini response is not a list")
        
        # Ensure each job has the required fields and add source
        structured_jobs = []
        for job in jobs_data:
            if isinstance(job, dict):
                structured_job = {
                    "title": job.get("title", ""),
                    "company": job.get("company", ""),
                    "tags": job.get("tags", []),
                    "location": job.get("location", "Remote"),
                    "apply_url": job.get("apply_url", ""),
                    "description": job.get("description", ""),
                    "source": "Gemini AI"
                }
                structured_jobs.append(structured_job)
        
        logger.info(f"Generated {len(structured_jobs)} jobs from Gemini AI")
        return {"jobs": structured_jobs, "count": len(structured_jobs), "source": "Gemini AI"}
        
    except Exception as e:
        logger.error(f"Error with Gemini API: {str(e)}")
        if "API key" in str(e).lower():
            raise HTTPException(status_code=401, detail="Invalid Gemini API key")
        raise HTTPException(status_code=500, detail="Error generating jobs with Gemini AI")

@app.get("/jobs/all")
async def get_all_jobs():
    """
    Fetch jobs from both RemoteOK and Gemini AI sources
    """
    results = {
        "remoteok": {"jobs": [], "count": 0, "error": None},
        "gemini": {"jobs": [], "count": 0, "error": None},
        "total_count": 0
    }
    
    # Fetch from RemoteOK
    try:
        remoteok_response = await get_remoteok_jobs()
        results["remoteok"] = remoteok_response
    except HTTPException as e:
        results["remoteok"]["error"] = e.detail
    except Exception as e:
        results["remoteok"]["error"] = str(e)
    
    # Fetch from Gemini
    try:
        gemini_response = await get_gemini_jobs()
        results["gemini"] = gemini_response
    except HTTPException as e:
        results["gemini"]["error"] = e.detail
    except Exception as e:
        results["gemini"]["error"] = str(e)
    
    # Calculate total count
    results["total_count"] = results["remoteok"]["count"] + results["gemini"]["count"]
    
    return results

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
