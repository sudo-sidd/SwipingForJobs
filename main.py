import os
import logging
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional

import httpx
from google import genai
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, Request, Cookie
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
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
gemini_client = None
if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
    logger.warning("GEMINI_API_KEY not properly configured")
else:
    try:
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
        logger.info("Gemini AI client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Gemini client: {e}")
        gemini_client = None

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

class UserProfileUpdate(BaseModel):
    linkedin_url: str = ""
    github_url: str = ""
    portfolio_url: str = ""
    phone_number: str = ""
    location: str = ""
    bio: str = ""
    work_mode: str = "remote"
    experience_level: str = "entry"
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    currency: str = "USD"
    skills: str = ""
    preferences: List[str] = []

class JobApplication(BaseModel):
    user_id: int
    user_email: str
    job_title: str
    company: str
    job_source: str
    job_url: str = ""

class SessionData(BaseModel):
    user_id: int
    email: str
    name: str
    expires_at: datetime

# Security setup
security = HTTPBearer(auto_error=False)

# Session management functions
def generate_session_token() -> str:
    """Generate a secure session token"""
    return secrets.token_urlsafe(32)

async def create_session(user_id: int) -> Dict[str, Any]:
    """Create a new session for a user"""
    session_token = generate_session_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)  # 7 days expiration
    
    await db_manager.create_session(user_id, session_token, expires_at)
    
    return {
        "session_token": session_token,
        "expires_at": expires_at.isoformat()
    }

async def get_current_user(request: Request, credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[Dict[str, Any]]:
    """Get current user from session token"""
    session_token = None
    
    # Try to get token from Authorization header
    if credentials:
        session_token = credentials.credentials
    
    # Try to get token from cookie as fallback
    if not session_token:
        session_token = request.cookies.get("session_token")
    
    if not session_token:
        return None
    
    try:
        session_data = await db_manager.get_session(session_token)
        if not session_data:
            return None
        
        # Check if session is expired
        expires_at_str = session_data["expires_at"]
        if isinstance(expires_at_str, str):
            expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
        else:
            expires_at = datetime.fromisoformat(str(expires_at_str))
            
        # Ensure both datetimes have timezone info for comparison
        now = datetime.now(timezone.utc)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
            
        if expires_at < now:
            await db_manager.delete_session(session_token)
            return None
        
        return session_data
    except Exception as e:
        logger.error(f"Error getting current user: {str(e)}")
        return None

async def require_auth(current_user: Optional[Dict[str, Any]] = Depends(get_current_user)) -> Dict[str, Any]:
    """Dependency that requires authentication"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return current_user

async def process_resume_with_gemini(file_path: str) -> Dict[str, Any]:
    """Process resume file using Gemini AI to extract information"""
    if not gemini_client:
        logger.warning("Gemini client not available for resume processing")
        return {}
    
    try:
        # Read the resume file
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            resume_content = file.read()
        
        # Create prompt for resume analysis
        prompt = f"""
        Analyze the following resume and extract structured information. Return the result as a valid JSON object with these fields:
        
        {{
            "name": "Full name",
            "email": "Email address",
            "phone": "Phone number",
            "location": "Location/Address", 
            "linkedin": "LinkedIn URL if found",
            "github": "GitHub URL if found",
            "portfolio": "Portfolio/website URL if found",
            "summary": "Professional summary/objective",
            "skills": ["skill1", "skill2", "skill3"],
            "experience": [
                {{
                    "title": "Job title",
                    "company": "Company name",
                    "duration": "Duration",
                    "description": "Brief description"
                }}
            ],
            "education": [
                {{
                    "degree": "Degree",
                    "institution": "Institution name",
                    "year": "Year/Duration"
                }}
            ],
            "projects": [
                {{
                    "name": "Project name",
                    "description": "Brief description",
                    "technologies": ["tech1", "tech2"]
                }}
            ],
            "certifications": ["certification1", "certification2"],
            "languages": ["language1", "language2"]
        }}
        
        Resume content:
        {resume_content}
        
        Return only the JSON object, no additional text.
        """
        
        # Generate response from Gemini
        response = gemini_client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt
        )
        
        if not response.text:
            logger.error("Empty response from Gemini API for resume processing")
            return {}
        
        # Clean and parse the response
        response_text = response.text.strip()
        
        # Remove markdown code blocks if present
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        
        response_text = response_text.strip()
        
        # Parse JSON
        try:
            processed_data = json.loads(response_text)
            logger.info(f"Successfully processed resume with Gemini")
            return processed_data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini resume response as JSON: {str(e)}")
            logger.error(f"Response text: {response_text[:500]}...")
            return {}
            
    except Exception as e:
        logger.error(f"Error processing resume with Gemini: {str(e)}")
        return {}

async def extract_linkedin_github_info(linkedin_url: str = "", github_url: str = "") -> Dict[str, str]:
    """Extract additional info from LinkedIn and GitHub URLs using Gemini"""
    if not gemini_client or (not linkedin_url and not github_url):
        return {"linkedin_data": "", "github_data": ""}
    
    try:
        info = {}
        
        if linkedin_url:
            # For now, just store the URL - in production you'd use LinkedIn API
            info["linkedin_data"] = json.dumps({
                "url": linkedin_url,
                "extracted_at": datetime.now().isoformat(),
                "status": "url_provided"
            })
        
        if github_url:
            # For now, just store the URL - in production you'd use GitHub API
            info["github_data"] = json.dumps({
                "url": github_url,
                "extracted_at": datetime.now().isoformat(),
                "status": "url_provided"
            })
        
        return info
        
    except Exception as e:
        logger.error(f"Error extracting LinkedIn/GitHub info: {str(e)}")
        return {"linkedin_data": "", "github_data": ""}

# Startup event to initialize database
@app.on_event("startup")
async def startup_event():
    await db_manager.init_database()
    # Clean up expired sessions on startup
    await db_manager.cleanup_expired_sessions()
    logger.info("Database initialized successfully")

# Scheduled task to clean up expired sessions periodically
import asyncio
from threading import Thread

def cleanup_sessions_periodically():
    """Background task to clean up expired sessions"""
    async def cleanup_loop():
        while True:
            try:
                await db_manager.cleanup_expired_sessions()
                logger.info("Cleaned up expired sessions")
            except Exception as e:
                logger.error(f"Error cleaning up sessions: {e}")
            # Wait 1 hour before next cleanup
            await asyncio.sleep(3600)
    
    # Run in background
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(cleanup_loop())

# Start cleanup thread
cleanup_thread = Thread(target=cleanup_sessions_periodically, daemon=True)
cleanup_thread.start()

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
        resume_processed_data = ""
        
        if resume and resume.filename:
            file_info = await file_manager.save_resume(resume, email)
            resume_filename = file_info["original_filename"]
            resume_path = file_info["file_path"]
            
            # Process resume with Gemini AI
            logger.info(f"Processing resume with Gemini AI for user: {email}")
            processed_data = await process_resume_with_gemini(resume_path)
            if processed_data:
                resume_processed_data = json.dumps(processed_data)
                logger.info(f"Successfully processed resume for user: {email}")
        
        # Extract LinkedIn/GitHub information
        social_data = await extract_linkedin_github_info(linkedin_url, github_url)
        
        # Create user in database
        result = await db_manager.create_user(
            name=name,
            email=email,
            linkedin_url=linkedin_url,
            github_url=github_url,
            skills=skills,
            preferences=preferences_list,
            resume_filename=resume_filename,
            resume_path=resume_path,
            linkedin_data=social_data.get("linkedin_data", ""),
            github_data=social_data.get("github_data", ""),
            resume_processed_data=resume_processed_data
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
        
        # Create session for the user
        session_data = await create_session(user["id"])
        
        return {
            "message": "Login successful",
            "user": {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "linkedin_url": user["linkedin_url"],
                "github_url": user["github_url"],
                "portfolio_url": user["portfolio_url"],
                "phone_number": user["phone_number"],
                "location": user["location"],
                "bio": user["bio"],
                "skills": user["skills"],
                "preferences": user["preferences"],
                "work_mode": user["work_mode"],
                "experience_level": user["experience_level"],
                "salary_min": user["salary_min"],
                "salary_max": user["salary_max"],
                "currency": user["currency"],
                "resume_filename": user["resume_filename"],
                "linkedin_data": user["linkedin_data"],
                "github_data": user["github_data"],
                "resume_processed_data": user["resume_processed_data"],
                "profile_completed": user["profile_completed"],
                "has_resume": bool(user["resume_filename"])
            },
            "session": {
                "token": session_data["session_token"],
                "expires_at": session_data["expires_at"]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(status_code=500, detail="Login failed")

@app.get("/users/profile/{user_id}")
async def get_user_profile(user_id: int, current_user: Dict[str, Any] = Depends(require_auth)):
    """Get user profile by ID (authenticated users only)"""
    try:
        # Users can only view their own profile
        if current_user["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        profile = await db_manager.get_user_profile(user_id)
        
        if not profile:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "user": profile,
            "message": "Profile retrieved successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get profile error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get user profile")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving profile: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve profile")

@app.put("/users/profile/{user_id}")
async def update_user_profile(
    user_id: int,
    profile_data: UserProfileUpdate,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """Update user profile (authenticated users only)"""
    try:
        # Users can only update their own profile
        if current_user["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Convert to dict and handle preferences
        update_data = profile_data.dict()
        
        # Update in database
        success = await db_manager.update_user(user_id, **update_data)
        
        if not success:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get updated profile
        updated_profile = await db_manager.get_user_profile(user_id)
        
        return {
            "message": "Profile updated successfully",
            "user": updated_profile
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating profile: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update profile")

@app.post("/users/process-resume/{user_id}")
async def process_user_resume(user_id: int, current_user: Dict[str, Any] = Depends(require_auth)):
    """Process/reprocess user's resume with Gemini AI (authenticated users only)"""
    try:
        # Users can only process their own resume
        if current_user["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get user profile to find resume path
        profile = await db_manager.get_user_profile(user_id)
        
        if not profile:
            raise HTTPException(status_code=404, detail="User not found")
        
        if not profile.get("resume_path"):
            raise HTTPException(status_code=400, detail="No resume found for this user")
        
        # Check if resume file exists
        if not os.path.exists(profile["resume_path"]):
            raise HTTPException(status_code=404, detail="Resume file not found")
        
        # Process resume with Gemini
        logger.info(f"Processing resume for user ID: {user_id}")
        processed_data = await process_resume_with_gemini(profile["resume_path"])
        
        if not processed_data:
            raise HTTPException(status_code=500, detail="Failed to process resume")
        
        # Update user with processed data
        update_data = {
            "resume_processed_data": json.dumps(processed_data)
        }
        
        # If resume contains better information, update profile fields
        if processed_data.get("skills"):
            # Merge existing skills with resume skills
            existing_skills = profile.get("skills", "").split(",")
            resume_skills = processed_data.get("skills", [])
            all_skills = list(set([s.strip() for s in existing_skills + resume_skills if s.strip()]))
            update_data["skills"] = ", ".join(all_skills)
        
        if processed_data.get("phone") and not profile.get("phone_number"):
            update_data["phone_number"] = processed_data["phone"]
            
        if processed_data.get("location") and not profile.get("location"):
            update_data["location"] = processed_data["location"]
            
        if processed_data.get("summary") and not profile.get("bio"):
            update_data["bio"] = processed_data["summary"]
            
        if processed_data.get("linkedin") and not profile.get("linkedin_url"):
            update_data["linkedin_url"] = processed_data["linkedin"]
            
        if processed_data.get("github") and not profile.get("github_url"):
            update_data["github_url"] = processed_data["github"]
            
        if processed_data.get("portfolio") and not profile.get("portfolio_url"):
            update_data["portfolio_url"] = processed_data["portfolio"]
        
        # Update the user profile
        success = await db_manager.update_user(user_id, **update_data)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update user profile")
        
        # Get updated profile
        updated_profile = await db_manager.get_user_profile(user_id)
        
        return {
            "message": "Resume processed successfully",
            "processed_data": processed_data,
            "user": updated_profile
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing resume: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process resume")

@app.post("/users/apply")
async def apply_to_job(application: JobApplication, current_user: Dict[str, Any] = Depends(require_auth)):
    """Record job application (authenticated users only)"""
    try:
        # Verify the user is applying for themselves
        if current_user["user_id"] != application.user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
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
async def get_user_applications(user_id: int, current_user: Dict[str, Any] = Depends(require_auth)):
    """Get all applications for a user (authenticated users only)"""
    try:
        # Users can only view their own applications
        if current_user["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        applications = await db_manager.get_user_applications(user_id)
        
        return {
            "applications": applications,
            "count": len(applications)
        }
        
    except HTTPException:
        raise
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

@app.get("/debug/user/{user_id}")
async def debug_user_data(user_id: int):
    """Debug endpoint to check user data"""
    try:
        profile = await db_manager.get_user_profile(user_id)
        if not profile:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "raw_profile": profile,
            "resume_filename": profile.get("resume_filename"),
            "resume_processed_data_length": len(profile.get("resume_processed_data", "")),
            "linkedin_url": profile.get("linkedin_url"),
            "github_url": profile.get("github_url")
        }
    except Exception as e:
        logger.error(f"Debug error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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
    if not gemini_client:
        raise HTTPException(
            status_code=503, 
            detail="Gemini API not available. Please check your configuration"
        )
    
    try:
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
        response = gemini_client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt
        )
        
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

@app.post("/auth/logout")
async def logout_user(current_user: Dict[str, Any] = Depends(require_auth), session_token: str = Cookie(None)):
    """Logout user and invalidate session"""
    try:
        # Get session token from authorization header or cookie
        token = session_token
        if not token and hasattr(current_user, 'session_token'):
            token = current_user.get('session_token')
        
        if token:
            await db_manager.delete_session(token)
        
        return {"message": "Logged out successfully"}
        
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        raise HTTPException(status_code=500, detail="Logout failed")

@app.get("/auth/me")
async def get_current_user_info(current_user: Dict[str, Any] = Depends(require_auth)):
    """Get current authenticated user information"""
    try:
        user = await db_manager.get_user_profile(current_user["user_id"])
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "user": user,
            "session": {
                "expires_at": current_user["expires_at"]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get current user error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get user info")

@app.post("/auth/refresh")
async def refresh_session(current_user: Dict[str, Any] = Depends(require_auth)):
    """Refresh user session"""
    try:
        # Delete old session
        if hasattr(current_user, 'session_token'):
            await db_manager.delete_session(current_user['session_token'])
        
        # Create new session
        session_info = await create_session(current_user["user_id"])
        
        return {
            "message": "Session refreshed successfully",
            "session": {
                "token": session_info["session_token"],
                "expires_at": session_info["expires_at"]
            }
        }
        
    except Exception as e:
        logger.error(f"Refresh session error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to refresh session")
