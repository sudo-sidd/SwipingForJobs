import os
import logging
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager

import httpx
from google import genai
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
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

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await db_manager.init_database()
    logger.info("Database initialized successfully")
    yield
    # Shutdown
    logger.info("Application shutting down")

# Initialize FastAPI app
app = FastAPI(
    title="SwipingForJobs Backend",
    description="Fetch job listings from RemoteOK and Gemini AI",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware to allow frontend connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    allow_origin_regex=r"http://localhost:\d+",
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
    preferences: List[str] = []  # For backward compatibility
    job_types: List[str] = ["full-time"]  # full-time, part-time, internship, contract, etc.

class UserLogin(BaseModel):
    name: str
    login_code: str

class UserProfileUpdate(BaseModel):
    # Contact & Basic Info
    linkedin_url: str = ""
    github_url: str = ""
    portfolio_url: str = ""
    phone_number: str = ""
    location: str = ""
    bio: str = ""
    
    # Skills
    skills: str = ""
    technical_skills: str = ""  # JSON format: {skill: proficiency_level}
    soft_skills: str = ""  # JSON array
    
    # Job Preferences
    job_function: str = ""
    industry_preferences: str = ""  # JSON array
    preferred_roles: str = ""  # JSON array
    job_types: List[str] = []  # full-time, part-time, internship, contract, etc.
    
    # Work Mode
    work_mode: str = "remote"
    relocation_willingness: bool = False
    preferred_locations: str = ""  # JSON array
    
    # Experience
    total_experience_years: int = 0
    relevant_field_experience_years: int = 0
    key_technologies: str = ""  # JSON array
    managerial_experience: bool = False
    
    # Compensation
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    currency: str = "USD"
    salary_negotiable: bool = True
    compensation_type: str = "yearly"
    
    # Availability
    notice_period: str = "2_weeks"
    preferred_start_date: str = ""
    work_authorization_status: str = ""
    
    # Languages
    languages: str = ""  # JSON array
    
    # Job Search Preferences
    job_search_status: str = "actively_looking"
    preferred_communication: str = "email"
    resume_visibility: str = "recruiters_only"
    
    # Cultural Fit
    company_size_preference: str = ""  # JSON array
    team_dynamics_preference: str = ""  # JSON array
    work_culture_keywords: str = ""  # JSON array
    
    # Other
    travel_willingness: str = "no"
    security_clearance: str = ""
    accessibility_needs: str = ""

class EducationEntry(BaseModel):
    degree: str
    field_of_study: str = ""
    institution: str
    start_date: str  # YYYY-MM format
    end_date: Optional[str] = None  # YYYY-MM format or None for ongoing
    gpa: Optional[float] = None
    location: str = ""
    description: str = ""

class CertificationEntry(BaseModel):
    certification_name: str
    issuer: str
    year_achieved: Optional[int] = None
    credential_id: str = ""
    credential_url: str = ""
    expiry_date: Optional[str] = None

class WorkExperienceEntry(BaseModel):
    job_title: str
    company_name: str
    start_date: str  # YYYY-MM format
    end_date: Optional[str] = None  # YYYY-MM format or "current"
    location: str = ""
    work_mode: str = ""  # onsite, remote, hybrid
    responsibilities: str = ""  # JSON array or text
    achievements: str = ""  # JSON array or text
    technologies_used: str = ""  # JSON array

class InternshipEntry(BaseModel):
    position_title: str
    company_name: str
    start_date: str  # YYYY-MM format
    end_date: Optional[str] = None  # YYYY-MM format
    location: str = ""
    work_mode: str = ""  # onsite, remote, hybrid
    internship_type: str = ""  # full-time, part-time, virtual, industrial_training
    technologies_used: str = ""  # JSON array
    responsibilities: str = ""  # JSON array or text
    achievements: str = ""  # JSON array or text
    stipend_amount: Optional[float] = None
    stipend_currency: str = ""
    certificate_url: str = ""

class JobApplication(BaseModel):
    user_id: int
    user_email: str
    job_title: str
    company: str
    job_source: str
    job_url: str = ""

async def process_resume_with_gemini(file_path: str) -> Dict[str, Any]:
    """Process resume file using Gemini AI to extract information with graceful fallbacks"""
    # Return empty dict if no Gemini client available
    if not gemini_client:
        logger.warning("Gemini client not available for resume processing - skipping AI analysis")
        return {}
    
    try:
        # Extract text from resume file based on file type
        resume_content = ""
        file_extension = file_path.lower().split('.')[-1]
        
        logger.info(f"Processing file: {file_path}, extension: {file_extension}")
        
        if file_extension == 'pdf':
            try:
                import PyPDF2
                logger.info("Using PyPDF2 for PDF processing")
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    logger.info(f"PDF has {len(pdf_reader.pages)} pages")
                    for i, page in enumerate(pdf_reader.pages):
                        page_text = page.extract_text()
                        logger.info(f"Page {i+1} extracted {len(page_text)} characters")
                        resume_content += page_text + "\n"
            except ImportError:
                logger.warning("PyPDF2 not installed, trying alternative PDF reading method")
                try:
                    import pdfplumber
                    logger.info("Using pdfplumber for PDF processing")
                    with pdfplumber.open(file_path) as pdf:
                        logger.info(f"PDF has {len(pdf.pages)} pages")
                        for i, page in enumerate(pdf.pages):
                            text = page.extract_text()
                            if text:
                                logger.info(f"Page {i+1} extracted {len(text)} characters")
                                resume_content += text + "\n"
                except ImportError:
                    logger.error("No PDF processing library available. Please install PyPDF2 or pdfplumber")
                    return {}
        elif file_extension in ['txt', 'md']:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                resume_content = file.read()
        elif file_extension in ['doc', 'docx']:
            try:
                import docx
                doc = docx.Document(file_path)
                resume_content = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            except ImportError:
                logger.warning("python-docx not installed, cannot process Word documents")
                return {}
        else:
            logger.warning(f"Unsupported file type: {file_extension}")
            return {}
        
        logger.info(f"Total extracted content length: {len(resume_content)} characters")
        logger.info(f"First 200 characters: {resume_content[:200]}")
        
        # Check if resume content is too short or empty
        if not resume_content.strip() or len(resume_content.strip()) < 50:
            logger.warning("Resume content too short or empty - skipping AI analysis")
            return {}
        
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
        
        # Generate response from Gemini with timeout and retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"Attempting Gemini API call (attempt {attempt + 1}/{max_retries})")
                
                response = gemini_client.models.generate_content(
                    model="gemini-1.5-flash",
                    contents=prompt
                )
                
                if not response or not response.text:
                    logger.warning(f"Empty response from Gemini API (attempt {attempt + 1})")
                    if attempt < max_retries - 1:
                        continue
                    else:
                        logger.error("All Gemini API attempts failed - empty response")
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
                    logger.info(f"Successfully processed resume with Gemini (attempt {attempt + 1})")
                    return processed_data
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse Gemini response as JSON (attempt {attempt + 1}): {str(e)}")
                    if attempt < max_retries - 1:
                        continue
                    else:
                        logger.error(f"All JSON parsing attempts failed. Response: {response_text[:200]}...")
                        return {}
                        
            except Exception as api_error:
                logger.warning(f"Gemini API error (attempt {attempt + 1}): {str(api_error)}")
                
                # Check for specific error types
                if "403" in str(api_error) or "PERMISSION_DENIED" in str(api_error):
                    logger.error("Gemini API permissions error - API not enabled or quota exceeded")
                    return {}
                elif "401" in str(api_error) or "UNAUTHORIZED" in str(api_error):
                    logger.error("Gemini API authentication error - invalid API key")
                    return {}
                elif "429" in str(api_error) or "RATE_LIMIT" in str(api_error):
                    logger.warning("Gemini API rate limit reached - skipping AI analysis")
                    return {}
                elif "500" in str(api_error) or "INTERNAL_ERROR" in str(api_error):
                    logger.warning("Gemini API internal error - retrying...")
                    if attempt < max_retries - 1:
                        continue
                    else:
                        logger.error("All Gemini API retry attempts failed")
                        return {}
                else:
                    logger.warning(f"Unknown Gemini API error: {str(api_error)}")
                    if attempt < max_retries - 1:
                        continue
                    else:
                        return {}
        
        logger.error("All Gemini API attempts exhausted")
        return {}
            
    except FileNotFoundError:
        logger.error(f"Resume file not found: {file_path}")
        return {}
    except Exception as e:
        logger.error(f"Unexpected error processing resume with Gemini: {str(e)}")
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

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "SwipingForJobs Backend API", "version": "1.0.0"}

@app.options("/{path:path}")
async def options_handler(path: str):
    """Handle all OPTIONS requests for CORS"""
    return {"message": "OK"}

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
        
        return {
            "message": "Login successful",
            "user": {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "linkedin_url": user.get("linkedin_url", ""),
                "github_url": user.get("github_url", ""),
                "portfolio_url": user.get("portfolio_url", ""),
                "phone_number": user.get("phone_number", ""),
                "location": user.get("location", ""),
                "bio": user.get("bio", ""),
                "skills": user.get("skills", ""),
                "preferences": user.get("preferences", []),
                "work_mode": user.get("work_mode", []),
                "experience_level": user.get("experience_level", ""),
                "salary_min": user.get("salary_min"),
                "salary_max": user.get("salary_max"),
                "currency": user.get("currency", "USD"),
                "resume_filename": user.get("resume_filename", ""),
                "linkedin_data": user.get("linkedin_data", ""),
                "github_data": user.get("github_data", ""),
                "resume_processed_data": user.get("resume_processed_data", ""),
                "profile_completed": user.get("profile_completed", False),
                "has_resume": bool(user.get("resume_filename"))
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
    try:        
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
    profile_data: UserProfileUpdate
):
    """Update user profile"""
    try:        
        # Convert to dict and handle preferences
        update_data = profile_data.dict()
        
        # Update in database
        success = await db_manager.update_user_profile(user_id, **update_data)
        
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
async def process_user_resume(user_id: int):
    """Process/reprocess user's resume with Gemini AI"""
    try:
        
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
        
        logger.info(f"Processed data from Gemini: {processed_data}")
        
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
            logger.info(f"Updated skills: {update_data['skills']}")
        
        if processed_data.get("phone") and not profile.get("phone_number"):
            update_data["phone_number"] = processed_data["phone"]
            logger.info(f"Updated phone: {update_data['phone_number']}")
            
        if processed_data.get("location") and not profile.get("location"):
            update_data["location"] = processed_data["location"]
            logger.info(f"Updated location: {update_data['location']}")
            
        if processed_data.get("summary") and not profile.get("bio"):
            update_data["bio"] = processed_data["summary"]
            logger.info(f"Updated bio: {update_data['bio'][:100]}...")
            
        if processed_data.get("linkedin") and not profile.get("linkedin_url"):
            update_data["linkedin_url"] = processed_data["linkedin"]
            logger.info(f"Updated linkedin: {update_data['linkedin_url']}")
            
        if processed_data.get("github") and not profile.get("github_url"):
            update_data["github_url"] = processed_data["github"]
            logger.info(f"Updated github: {update_data['github_url']}")
            
        if processed_data.get("portfolio") and not profile.get("portfolio_url"):
            update_data["portfolio_url"] = processed_data["portfolio"]
            logger.info(f"Updated portfolio: {update_data['portfolio_url']}")
        
        logger.info(f"Final update_data: {update_data}")
        
        # Update the user profile
        success = await db_manager.update_user_profile(user_id, **update_data)
        
        logger.info(f"Update success: {success}")
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update user profile")
        
        # Process and save projects if they exist
        if processed_data.get("projects"):
            logger.info(f"Processing {len(processed_data['projects'])} projects")
            
            # Clear existing projects for this user (to avoid duplicates on re-processing)
            await db_manager.clear_user_projects(user_id)
            
            # Add new projects
            for project in processed_data["projects"]:
                try:
                    project_data = {
                        'project_name': project.get('name', ''),
                        'description': project.get('description', ''),
                        'technologies': project.get('technologies', []),
                        'project_url': project.get('url', ''),
                        'github_url': project.get('github', ''),
                        'start_date': project.get('start_date'),
                        'end_date': project.get('end_date'),
                        'is_current': project.get('is_current', False),
                        'featured': False  # Can be set later by user
                    }
                    
                    await db_manager.add_project(user_id, **project_data)
                    logger.info(f"Added project: {project.get('name', '')}")
                    
                except Exception as e:
                    logger.error(f"Error adding project {project.get('name', '')}: {str(e)}")
                    continue
        
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

# Project endpoints
@app.get("/users/projects/{user_id}")
async def get_user_projects(user_id: int):
    """Get all projects for a user"""
    try:
        projects = await db_manager.get_user_projects(user_id)
        
        return {
            "projects": projects,
            "message": f"Found {len(projects)} projects"
        }
        
    except Exception as e:
        logger.error(f"Error getting projects: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get projects")

@app.post("/users/projects/{user_id}")
async def add_user_project(user_id: int, project_data: dict):
    """Add a new project for a user"""
    try:
        success = await db_manager.add_project(user_id, **project_data)
        
        if success:
            projects = await db_manager.get_user_projects(user_id)
            return {
                "message": "Project added successfully",
                "projects": projects
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to add project")
            
    except Exception as e:
        logger.error(f"Error adding project: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to add project")

@app.put("/users/projects/{project_id}")
async def update_user_project(project_id: int, project_data: dict):
    """Update a project"""
    try:
        success = await db_manager.update_project(project_id, **project_data)
        
        if success:
            return {
                "message": "Project updated successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to update project")
            
    except Exception as e:
        logger.error(f"Error updating project: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update project")

@app.delete("/users/projects/{project_id}")
async def delete_user_project(project_id: int):
    """Delete a project"""
    try:
        success = await db_manager.delete_project(project_id)
        
        if success:
            return {
                "message": "Project deleted successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to delete project")
            
    except Exception as e:
        logger.error(f"Error deleting project: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete project")

# Session endpoints removed as requested
# User requested to remove all session system code
