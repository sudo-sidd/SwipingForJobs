import aiosqlite
import os
import random
import bcrypt
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List

DATABASE_PATH = "swipingforjobs.db"
RESUME_UPLOAD_DIR = "uploaded_resumes"

# Ensure upload directory exists
os.makedirs(RESUME_UPLOAD_DIR, exist_ok=True)

class DatabaseManager:
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
    
    async def init_database(self):
        """Initialize database with enhanced schema"""
        async with aiosqlite.connect(self.db_path) as db:
            # Create enhanced users table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    login_code TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    -- Basic Profile
                    first_name TEXT,
                    last_name TEXT,
                    phone TEXT,
                    linkedin_url TEXT,
                    github_url TEXT,
                    portfolio_url TEXT,
                    location TEXT,
                    bio TEXT,
                    profile_picture_url TEXT,
                    
                    -- Job Type Preferences
                    job_types TEXT, -- JSON array: ["full-time", "part-time", "internship", "contract", "freelance", "apprenticeship", "volunteer", "temporary"]
                    job_functions TEXT, -- JSON array
                    industries TEXT, -- JSON array
                    preferred_roles TEXT, -- JSON array
                    
                    -- Work Mode
                    work_mode TEXT, -- JSON array: ["onsite", "remote", "hybrid"]
                    relocation_willingness BOOLEAN DEFAULT 0,
                    preferred_locations TEXT, -- JSON array
                    
                    -- Experience
                    total_years_experience INTEGER,
                    years_in_relevant_field INTEGER,
                    key_technologies TEXT, -- JSON array
                    has_managerial_experience BOOLEAN DEFAULT 0,
                    
                    -- Compensation
                    min_expected_salary DECIMAL,
                    max_expected_salary DECIMAL,
                    salary_currency TEXT DEFAULT 'USD',
                    salary_negotiable BOOLEAN DEFAULT 1,
                    compensation_type TEXT DEFAULT 'yearly', -- yearly, monthly, hourly, contract
                    
                    -- Availability
                    notice_period TEXT, -- immediate, 2weeks, 1month, custom
                    preferred_start_date DATE,
                    work_authorization_status TEXT,
                    
                    -- Education (primary/latest)
                    highest_degree TEXT,
                    field_of_study TEXT,
                    institution TEXT,
                    graduation_year INTEGER,
                    
                    -- Technical Skills
                    programming_languages TEXT, -- JSON with proficiency levels
                    frameworks_libraries TEXT, -- JSON with proficiency levels
                    tools_platforms TEXT, -- JSON with proficiency levels
                    
                    -- Soft Skills
                    soft_skills TEXT, -- JSON array
                    
                    -- Languages
                    languages TEXT, -- JSON with proficiency levels
                    
                    -- Job Search Preferences
                    job_search_status TEXT DEFAULT 'actively_looking', -- actively_looking, open_to_offers, not_looking
                    preferred_communication TEXT, -- JSON array: ["email", "phone", "linkedin"]
                    resume_visibility TEXT DEFAULT 'recruiters_only', -- public, recruiters_only, private
                    
                    -- Cultural Fit
                    company_size_preference TEXT, -- JSON array: ["startup", "mid_size", "enterprise"]
                    team_dynamics TEXT, -- JSON array
                    work_culture_keywords TEXT, -- JSON array
                    
                    -- Other
                    willing_to_travel BOOLEAN DEFAULT 0,
                    travel_percentage INTEGER DEFAULT 0,
                    security_clearance TEXT,
                    accessibility_needs TEXT,
                    
                    -- Resume Data Integration
                    resume_parsed BOOLEAN DEFAULT 0,
                    resume_filename TEXT,
                    resume_upload_date TIMESTAMP,
                    
                    -- AI Extracted Data (from resume)
                    ai_extracted_skills TEXT, -- JSON
                    ai_extracted_experience TEXT, -- JSON
                    ai_extracted_education TEXT, -- JSON
                    ai_extracted_certifications TEXT, -- JSON
                    ai_summary TEXT,
                    
                    -- Legacy fields for backward compatibility
                    skills TEXT,
                    preferences TEXT,
                    resume_path TEXT,
                    linkedin_data TEXT,
                    github_data TEXT,
                    resume_processed_data TEXT,
                    profile_completed BOOLEAN DEFAULT FALSE
                )
            ''')
            
            # Create education table for detailed education history
            await db.execute('''
                CREATE TABLE IF NOT EXISTS user_education (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    degree TEXT NOT NULL,
                    field_of_study TEXT,
                    institution TEXT NOT NULL,
                    start_year INTEGER,
                    end_year INTEGER,
                    gpa DECIMAL,
                    achievements TEXT,
                    is_current BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            ''')
            
            # Create certifications table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS user_certifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    certification_name TEXT NOT NULL,
                    issuer TEXT NOT NULL,
                    year_achieved INTEGER,
                    credential_id TEXT,
                    credential_url TEXT,
                    expires_at DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            ''')
            
            # Create work experience table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS user_work_experience (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    position_title TEXT NOT NULL,
                    company_name TEXT NOT NULL,
                    start_date DATE,
                    end_date DATE,
                    is_current BOOLEAN DEFAULT 0,
                    location TEXT,
                    work_mode TEXT, -- onsite, remote, hybrid
                    technologies_used TEXT, -- JSON array
                    responsibilities TEXT,
                    achievements TEXT,
                    employment_type TEXT, -- full-time, part-time, contract, freelance
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            ''')
            
            # Create internships table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS user_internships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    position_title TEXT NOT NULL,
                    company_name TEXT NOT NULL,
                    start_date DATE,
                    end_date DATE,
                    location TEXT,
                    work_mode TEXT, -- onsite, remote, hybrid
                    technologies_used TEXT, -- JSON array
                    responsibilities TEXT,
                    achievements TEXT,
                    internship_type TEXT, -- full-time, part-time, virtual, industrial_training
                    stipend_amount DECIMAL,
                    stipend_currency TEXT,
                    certificate_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            ''')
            
            # Create user sessions table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    session_token TEXT UNIQUE NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            ''')
            
            # Create indexes for better performance
            await db.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions(session_token)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_sessions_expires ON user_sessions(expires_at)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_education_user ON user_education(user_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_certifications_user ON user_certifications(user_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_work_experience_user ON user_work_experience(user_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_internships_user ON user_internships(user_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_users_job_search_status ON users(job_search_status)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_users_work_mode ON users(work_mode)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_users_location ON users(location)")
            
            await db.commit()
            print("✅ Database initialized with enhanced schema")
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create education table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS user_education (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    degree TEXT NOT NULL,
                    field_of_study TEXT,
                    institution TEXT NOT NULL,
                    start_date TEXT,  -- YYYY-MM format
                    end_date TEXT,    -- YYYY-MM format or "ongoing"
                    gpa REAL,
                    location TEXT,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            ''')
            
            # Create certifications table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS user_certifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    certification_name TEXT NOT NULL,
                    issuer TEXT NOT NULL,
                    year_achieved INTEGER,
                    credential_id TEXT,
                    credential_url TEXT,
                    expiry_date TEXT,  -- YYYY-MM format
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            ''')
            
            # Create work experience table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS user_work_experience (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    job_title TEXT NOT NULL,
                    company_name TEXT NOT NULL,
                    start_date TEXT NOT NULL,  -- YYYY-MM format
                    end_date TEXT,  -- YYYY-MM format or "current"
                    location TEXT,
                    work_mode TEXT,  -- onsite, remote, hybrid
                    responsibilities TEXT,  -- JSON array or text
                    achievements TEXT,  -- JSON array or text
                    technologies_used TEXT,  -- JSON array
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            ''')
            
            # Create internships table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS user_internships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    position_title TEXT NOT NULL,
                    company_name TEXT NOT NULL,
                    start_date TEXT NOT NULL,  -- YYYY-MM format
                    end_date TEXT,  -- YYYY-MM format
                    location TEXT,
                    work_mode TEXT,  -- onsite, remote, hybrid
                    internship_type TEXT,  -- full-time, part-time, virtual, industrial_training
                    technologies_used TEXT,  -- JSON array
                    responsibilities TEXT,  -- JSON array or text
                    achievements TEXT,  -- JSON array or text
                    stipend_amount REAL,
                    stipend_currency TEXT,
                    certificate_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            ''')

            # Create job_applications table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS job_applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    user_email TEXT NOT NULL,
                    job_title TEXT NOT NULL,
                    company TEXT NOT NULL,
                    job_source TEXT NOT NULL,
                    job_url TEXT,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Create sessions table for login management
            await db.execute('''
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    session_token TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Create indexes
            await db.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users (email)')
            await db.execute('CREATE INDEX IF NOT EXISTS idx_users_login_code ON users (login_code)')
            await db.execute('CREATE INDEX IF NOT EXISTS idx_applications_user_id ON job_applications (user_id)')
            await db.execute('CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions (session_token)')
            
            # Indexes for related tables
            await db.execute('CREATE INDEX IF NOT EXISTS idx_education_user_id ON user_education (user_id)')
            await db.execute('CREATE INDEX IF NOT EXISTS idx_certifications_user_id ON user_certifications (user_id)')
            await db.execute('CREATE INDEX IF NOT EXISTS idx_work_experience_user_id ON user_work_experience (user_id)')
            await db.execute('CREATE INDEX IF NOT EXISTS idx_internships_user_id ON user_internships (user_id)')
            
            await db.commit()
    
    def generate_login_code(self) -> str:
        """Generate a unique 4-digit login code"""
        return f"{random.randint(1000, 9999)}"
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    async def create_user(self, name: str, email: str, linkedin_url: str, github_url: str, 
                         skills: str, preferences: List[str], resume_filename: str = "", 
                         resume_path: str = "", linkedin_data: str = "", github_data: str = "",
                         resume_processed_data: str = "", **kwargs) -> Dict:
        """Create a new user with auto-generated login code and basic fields"""
        async with aiosqlite.connect(self.db_path) as db:
            # Generate unique login code
            login_code = self.generate_login_code()
            
            # Check if login code already exists (very unlikely but safety first)
            while True:
                cursor = await db.execute('SELECT id FROM users WHERE login_code = ?', (login_code,))
                if not await cursor.fetchone():
                    break
                login_code = self.generate_login_code()
            
            # Hash the login code as password
            password_hash = self.hash_password(login_code)
            
            # Convert preferences list to JSON string for backward compatibility
            preferences_str = ','.join(preferences) if preferences else ""
            
            # Convert job_types array to JSON if provided
            job_types_json = kwargs.get('job_types', '["full-time"]')
            if isinstance(job_types_json, list):
                import json
                job_types_json = json.dumps(job_types_json)
            
            try:
                cursor = await db.execute('''
                    INSERT INTO users (
                        name, email, password_hash, login_code, linkedin_url, github_url, 
                        skills, job_types, resume_filename, resume_path,
                        linkedin_data, github_data, resume_processed_data,
                        work_mode, salary_min, salary_max, currency, total_experience_years
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    name, email, password_hash, login_code, linkedin_url, github_url, 
                    skills, job_types_json, resume_filename, resume_path,
                    linkedin_data, github_data, resume_processed_data,
                    kwargs.get('work_mode', 'remote'),
                    kwargs.get('salary_min'),
                    kwargs.get('salary_max'),
                    kwargs.get('currency', 'USD'),
                    kwargs.get('total_experience_years', 0)
                ))
                
                user_id = cursor.lastrowid
                await db.commit()
                
                return {
                    "user_id": user_id,
                    "login_code": login_code,
                    "message": "User created successfully"
                }
                
            except aiosqlite.IntegrityError:
                raise ValueError("Email already exists")
    
    async def authenticate_user(self, name: str, login_code: str) -> Optional[Dict]:
        """Authenticate user with name and login code"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT id, name, email, password_hash, linkedin_url, github_url, portfolio_url,
                       phone_number, location, bio, skills, technical_skills, soft_skills,
                       job_function, industry_preferences, preferred_roles, job_types,
                       work_mode, relocation_willingness, preferred_locations,
                       total_experience_years, relevant_field_experience_years, key_technologies, managerial_experience,
                       salary_min, salary_max, currency, salary_negotiable, compensation_type,
                       notice_period, preferred_start_date, work_authorization_status,
                       languages, job_search_status, preferred_communication, resume_visibility,
                       company_size_preference, team_dynamics_preference, work_culture_keywords,
                       travel_willingness, security_clearance, accessibility_needs,
                       resume_filename, resume_path, linkedin_data, github_data, resume_processed_data, 
                       profile_completed
                FROM users 
                WHERE LOWER(name) = LOWER(?) AND login_code = ?
            ''', (name, login_code))
            
            user = await cursor.fetchone()
            if not user:
                return None
            
            # Convert to dictionary with all new fields
            user_data = {
                "id": user[0],
                "name": user[1],
                "email": user[2],
                "linkedin_url": user[4] or "",
                "github_url": user[5] or "",
                "portfolio_url": user[6] or "",
                "phone_number": user[7] or "",
                "location": user[8] or "",
                "bio": user[9] or "",
                "skills": user[10] or "",
                "technical_skills": user[11] or "",
                "soft_skills": user[12] or "",
                "job_function": user[13] or "",
                "industry_preferences": user[14] or "",
                "preferred_roles": user[15] or "",
                "job_types": user[16] or "",
                "work_mode": user[17] or "remote",
                "relocation_willingness": bool(user[18]) if user[18] is not None else False,
                "preferred_locations": user[19] or "",
                "total_experience_years": user[20] or 0,
                "relevant_field_experience_years": user[21] or 0,
                "key_technologies": user[22] or "",
                "managerial_experience": bool(user[23]) if user[23] is not None else False,
                "salary_min": user[24],
                "salary_max": user[25],
                "currency": user[26] or "USD",
                "salary_negotiable": bool(user[27]) if user[27] is not None else True,
                "compensation_type": user[28] or "yearly",
                "notice_period": user[29] or "2_weeks",
                "preferred_start_date": user[30] or "",
                "work_authorization_status": user[31] or "",
                "languages": user[32] or "",
                "job_search_status": user[33] or "actively_looking",
                "preferred_communication": user[34] or "email",
                "resume_visibility": user[35] or "recruiters_only",
                "company_size_preference": user[36] or "",
                "team_dynamics_preference": user[37] or "",
                "work_culture_keywords": user[38] or "",
                "travel_willingness": user[39] or "no",
                "security_clearance": user[40] or "",
                "accessibility_needs": user[41] or "",
                "resume_filename": user[42] or "",
                "resume_path": user[43] or "",
                "linkedin_data": user[44] or "",
                "github_data": user[45] or "",
                "resume_processed_data": user[46] or "",
                "profile_completed": bool(user[47])
            }
            
            return user_data
    
    async def update_user(self, user_id: int, **kwargs) -> bool:
        """Update user information"""
        async with aiosqlite.connect(self.db_path) as db:
            # Build dynamic update query
            set_clauses = []
            values = []
            
            for key, value in kwargs.items():
                if key == 'preferences' and isinstance(value, list):
                    value = ','.join(value)
                set_clauses.append(f"{key} = ?")
                values.append(value)
            
            if not set_clauses:
                return False
            
            values.append(user_id)
            query = f"UPDATE users SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
            
            await db.execute(query, values)
            await db.commit()
            return True
    
    async def record_job_application(self, user_id: int, user_email: str, job_title: str, 
                                   company: str, job_source: str, job_url: str = "") -> bool:
        """Record a job application"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO job_applications (user_id, user_email, job_title, company, job_source, job_url)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, user_email, job_title, company, job_source, job_url))
            
            await db.commit()
            return True
    
    async def get_user_applications(self, user_id: int) -> List[Dict]:
        """Get all applications for a user"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT job_title, company, job_source, job_url, applied_at
                FROM job_applications
                WHERE user_id = ?
                ORDER BY applied_at DESC
            ''', (user_id,))
            
            applications = await cursor.fetchall()
            return [
                {
                    "job_title": app[0],
                    "company": app[1],
                    "job_source": app[2],
                    "job_url": app[3] or "",
                    "applied_at": app[4]
                }
                for app in applications
            ]
    
    async def get_user_profile(self, user_id: int) -> Optional[Dict]:
        """Get complete user profile by ID including all related data"""
        async with aiosqlite.connect(self.db_path) as db:
            # Get main user data
            cursor = await db.execute('''
                SELECT id, name, email, linkedin_url, github_url, portfolio_url,
                       phone_number, location, bio, skills, technical_skills, soft_skills,
                       job_function, industry_preferences, preferred_roles, job_types,
                       work_mode, relocation_willingness, preferred_locations,
                       total_experience_years, relevant_field_experience_years, key_technologies, managerial_experience,
                       salary_min, salary_max, currency, salary_negotiable, compensation_type,
                       notice_period, preferred_start_date, work_authorization_status,
                       languages, job_search_status, preferred_communication, resume_visibility,
                       company_size_preference, team_dynamics_preference, work_culture_keywords,
                       travel_willingness, security_clearance, accessibility_needs,
                       resume_filename, resume_path, linkedin_data, github_data, resume_processed_data, 
                       profile_completed, created_at, updated_at
                FROM users 
                WHERE id = ?
            ''', (user_id,))
            
            user = await cursor.fetchone()
            if not user:
                return None
            
            # Get education data
            education_cursor = await db.execute('''
                SELECT degree, field_of_study, institution, start_date, end_date, gpa, location, description
                FROM user_education 
                WHERE user_id = ? 
                ORDER BY end_date DESC, start_date DESC
            ''', (user_id,))
            education_data = await education_cursor.fetchall()
            
            # Get certifications data
            cert_cursor = await db.execute('''
                SELECT certification_name, issuer, year_achieved, credential_id, credential_url, expiry_date
                FROM user_certifications 
                WHERE user_id = ? 
                ORDER BY year_achieved DESC
            ''', (user_id,))
            certifications_data = await cert_cursor.fetchall()
            
            # Get work experience data
            work_cursor = await db.execute('''
                SELECT job_title, company_name, start_date, end_date, location, work_mode, 
                       responsibilities, achievements, technologies_used
                FROM user_work_experience 
                WHERE user_id = ? 
                ORDER BY end_date DESC, start_date DESC
            ''', (user_id,))
            work_experience_data = await work_cursor.fetchall()
            
            # Get internships data
            intern_cursor = await db.execute('''
                SELECT position_title, company_name, start_date, end_date, location, work_mode,
                       internship_type, technologies_used, responsibilities, achievements,
                       stipend_amount, stipend_currency, certificate_url
                FROM user_internships 
                WHERE user_id = ? 
                ORDER BY end_date DESC, start_date DESC
            ''', (user_id,))
            internships_data = await intern_cursor.fetchall()
            
            # Convert to comprehensive dictionary
            profile_data = {
                "id": user[0],
                "name": user[1],
                "email": user[2],
                "linkedin_url": user[3] or "",
                "github_url": user[4] or "",
                "portfolio_url": user[5] or "",
                "phone_number": user[6] or "",
                "location": user[7] or "",
                "bio": user[8] or "",
                "skills": user[9] or "",
                "technical_skills": user[10] or "",
                "soft_skills": user[11] or "",
                "job_function": user[12] or "",
                "industry_preferences": user[13] or "",
                "preferred_roles": user[14] or "",
                "job_types": user[15] or "",
                "work_mode": user[16] or "remote",
                "relocation_willingness": bool(user[17]) if user[17] is not None else False,
                "preferred_locations": user[18] or "",
                "total_experience_years": user[19] or 0,
                "relevant_field_experience_years": user[20] or 0,
                "key_technologies": user[21] or "",
                "managerial_experience": bool(user[22]) if user[22] is not None else False,
                "salary_min": user[23],
                "salary_max": user[24],
                "currency": user[25] or "USD",
                "salary_negotiable": bool(user[26]) if user[26] is not None else True,
                "compensation_type": user[27] or "yearly",
                "notice_period": user[28] or "2_weeks",
                "preferred_start_date": user[29] or "",
                "work_authorization_status": user[30] or "",
                "languages": user[31] or "",
                "job_search_status": user[32] or "actively_looking",
                "preferred_communication": user[33] or "email",
                "resume_visibility": user[34] or "recruiters_only",
                "company_size_preference": user[35] or "",
                "team_dynamics_preference": user[36] or "",
                "work_culture_keywords": user[37] or "",
                "travel_willingness": user[38] or "no",
                "security_clearance": user[39] or "",
                "accessibility_needs": user[40] or "",
                "resume_filename": user[41] or "",
                "resume_path": user[42] or "",
                "linkedin_data": user[43] or "",
                "github_data": user[44] or "",
                "resume_processed_data": user[45] or "",
                "profile_completed": bool(user[46]),
                "created_at": user[47],
                "updated_at": user[48],
                
                # Related data
                "education": [
                    {
                        "degree": edu[0],
                        "field_of_study": edu[1],
                        "institution": edu[2],
                        "start_date": edu[3],
                        "end_date": edu[4],
                        "gpa": edu[5],
                        "location": edu[6],
                        "description": edu[7]
                    } for edu in education_data
                ],
                "certifications": [
                    {
                        "certification_name": cert[0],
                        "issuer": cert[1],
                        "year_achieved": cert[2],
                        "credential_id": cert[3],
                        "credential_url": cert[4],
                        "expiry_date": cert[5]
                    } for cert in certifications_data
                ],
                "work_experience": [
                    {
                        "job_title": work[0],
                        "company_name": work[1],
                        "start_date": work[2],
                        "end_date": work[3],
                        "location": work[4],
                        "work_mode": work[5],
                        "responsibilities": work[6],
                        "achievements": work[7],
                        "technologies_used": work[8]
                    } for work in work_experience_data
                ],
                "internships": [
                    {
                        "position_title": intern[0],
                        "company_name": intern[1],
                        "start_date": intern[2],
                        "end_date": intern[3],
                        "location": intern[4],
                        "work_mode": intern[5],
                        "internship_type": intern[6],
                        "technologies_used": intern[7],
                        "responsibilities": intern[8],
                        "achievements": intern[9],
                        "stipend_amount": intern[10],
                        "stipend_currency": intern[11],
                        "certificate_url": intern[12]
                    } for intern in internships_data
                ]
            }
            
            return profile_data
    
    async def create_session(self, user_id: int, session_token: str, expires_at) -> bool:
        """Create a new session for a user"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('''
                    INSERT INTO user_sessions (user_id, session_token, expires_at)
                    VALUES (?, ?, ?)
                ''', (user_id, session_token, expires_at.isoformat()))
                await db.commit()
                return True
        except Exception as e:
            print(f"Error creating session: {e}")
            return False

    async def get_session(self, session_token: str) -> Optional[Dict]:
        """Get session data by token"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute('''
                    SELECT s.*, u.name, u.email
                    FROM user_sessions s
                    JOIN users u ON s.user_id = u.id
                    WHERE s.session_token = ?
                ''', (session_token,))
                row = await cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            print(f"Error getting session: {e}")
            return None

    async def delete_session(self, session_token: str) -> bool:
        """Delete a session"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('''
                    DELETE FROM user_sessions WHERE session_token = ?
                ''', (session_token,))
                await db.commit()
                return True
        except Exception as e:
            print(f"Error deleting session: {e}")
            return False

    async def delete_user_sessions(self, user_id: int) -> bool:
        """Delete all sessions for a user"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('''
                    DELETE FROM user_sessions WHERE user_id = ?
                ''', (user_id,))
                await db.commit()
                return True
        except Exception as e:
            print(f"Error deleting user sessions: {e}")
            return False

    async def cleanup_expired_sessions(self) -> bool:
        """Clean up expired sessions"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('''
                    DELETE FROM user_sessions WHERE expires_at < ?
                ''', (datetime.now().isoformat(),))
                await db.commit()
                return True
        except Exception as e:
            print(f"Error cleaning up expired sessions: {e}")
            return False

    # Education management methods
    async def add_user_education(self, user_id: int, degree: str, field_of_study: str, 
                                institution: str, start_date: str, end_date: str = None,
                                gpa: float = None, location: str = "", description: str = "") -> bool:
        """Add education record for a user"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO user_education 
                (user_id, degree, field_of_study, institution, start_date, end_date, gpa, location, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, degree, field_of_study, institution, start_date, end_date, gpa, location, description))
            await db.commit()
            return True
    
    async def update_user_education(self, education_id: int, **kwargs) -> bool:
        """Update education record"""
        async with aiosqlite.connect(self.db_path) as db:
            set_clauses = []
            values = []
            
            for key, value in kwargs.items():
                set_clauses.append(f"{key} = ?")
                values.append(value)
            
            if not set_clauses:
                return False
            
            values.append(education_id)
            query = f"UPDATE user_education SET {', '.join(set_clauses)} WHERE id = ?"
            
            await db.execute(query, values)
            await db.commit()
            return True
    
    async def delete_user_education(self, education_id: int) -> bool:
        """Delete education record"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('DELETE FROM user_education WHERE id = ?', (education_id,))
            await db.commit()
            return True
    
    # Certification management methods
    async def add_user_certification(self, user_id: int, certification_name: str, issuer: str,
                                   year_achieved: int = None, credential_id: str = "",
                                   credential_url: str = "", expiry_date: str = None) -> bool:
        """Add certification record for a user"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO user_certifications 
                (user_id, certification_name, issuer, year_achieved, credential_id, credential_url, expiry_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, certification_name, issuer, year_achieved, credential_id, credential_url, expiry_date))
            await db.commit()
            return True
    
    async def update_user_certification(self, cert_id: int, **kwargs) -> bool:
        """Update certification record"""
        async with aiosqlite.connect(self.db_path) as db:
            set_clauses = []
            values = []
            
            for key, value in kwargs.items():
                set_clauses.append(f"{key} = ?")
                values.append(value)
            
            if not set_clauses:
                return False
            
            values.append(cert_id)
            query = f"UPDATE user_certifications SET {', '.join(set_clauses)} WHERE id = ?"
            
            await db.execute(query, values)
            await db.commit()
            return True
    
    async def delete_user_certification(self, cert_id: int) -> bool:
        """Delete certification record"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('DELETE FROM user_certifications WHERE id = ?', (cert_id,))
            await db.commit()
            return True
    
    # Work experience management methods
    async def add_user_work_experience(self, user_id: int, job_title: str, company_name: str,
                                     start_date: str, end_date: str = None, location: str = "",
                                     work_mode: str = "", responsibilities: str = "",
                                     achievements: str = "", technologies_used: str = "") -> bool:
        """Add work experience record for a user"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO user_work_experience 
                (user_id, job_title, company_name, start_date, end_date, location, work_mode, 
                 responsibilities, achievements, technologies_used)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, job_title, company_name, start_date, end_date, location, work_mode,
                  responsibilities, achievements, technologies_used))
            await db.commit()
            return True
    
    async def update_user_work_experience(self, work_id: int, **kwargs) -> bool:
        """Update work experience record"""
        async with aiosqlite.connect(self.db_path) as db:
            set_clauses = []
            values = []
            
            for key, value in kwargs.items():
                set_clauses.append(f"{key} = ?")
                values.append(value)
            
            if not set_clauses:
                return False
            
            values.append(work_id)
            query = f"UPDATE user_work_experience SET {', '.join(set_clauses)} WHERE id = ?"
            
            await db.execute(query, values)
            await db.commit()
            return True
    
    async def delete_user_work_experience(self, work_id: int) -> bool:
        """Delete work experience record"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('DELETE FROM user_work_experience WHERE id = ?', (work_id,))
            await db.commit()
            return True
    
    # Internship management methods
    async def add_user_internship(self, user_id: int, position_title: str, company_name: str,
                                start_date: str, end_date: str = None, location: str = "",
                                work_mode: str = "", internship_type: str = "",
                                technologies_used: str = "", responsibilities: str = "",
                                achievements: str = "", stipend_amount: float = None,
                                stipend_currency: str = "", certificate_url: str = "") -> bool:
        """Add internship record for a user"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO user_internships 
                (user_id, position_title, company_name, start_date, end_date, location, work_mode,
                 internship_type, technologies_used, responsibilities, achievements,
                 stipend_amount, stipend_currency, certificate_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, position_title, company_name, start_date, end_date, location, work_mode,
                  internship_type, technologies_used, responsibilities, achievements,
                  stipend_amount, stipend_currency, certificate_url))
            await db.commit()
            return True
    
    async def update_user_internship(self, internship_id: int, **kwargs) -> bool:
        """Update internship record"""
        async with aiosqlite.connect(self.db_path) as db:
            set_clauses = []
            values = []
            
            for key, value in kwargs.items():
                set_clauses.append(f"{key} = ?")
                values.append(value)
            
            if not set_clauses:
                return False
            
            values.append(internship_id)
            query = f"UPDATE user_internships SET {', '.join(set_clauses)} WHERE id = ?"
            
            await db.execute(query, values)
            await db.commit()
            return True
    
    async def delete_user_internship(self, internship_id: int) -> bool:
        """Delete internship record"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('DELETE FROM user_internships WHERE id = ?', (internship_id,))
            await db.commit()
            return True
    
    # Combined data management for AI processing
    async def combine_user_and_resume_data(self, user_id: int, resume_extracted_data: Dict) -> bool:
        """Combine user-provided data with AI-extracted resume data"""
        async with aiosqlite.connect(self.db_path) as db:
            try:
                # Get current user data
                user_profile = await self.get_user_profile(user_id)
                if not user_profile:
                    return False
                
                # Combine skills
                current_skills = user_profile.get('skills', '').split(',') if user_profile.get('skills') else []
                resume_skills = resume_extracted_data.get('skills', [])
                combined_skills = list(set(current_skills + resume_skills))
                
                # Combine technical skills
                current_tech_skills = user_profile.get('technical_skills', '{}')
                resume_tech_skills = resume_extracted_data.get('technical_skills', {})
                import json
                try:
                    current_tech_dict = json.loads(current_tech_skills) if current_tech_skills else {}
                except:
                    current_tech_dict = {}
                
                # Merge technical skills (resume data takes precedence for proficiency levels)
                combined_tech_skills = {**current_tech_dict, **resume_tech_skills}
                
                # Update main user record with combined data
                update_data = {
                    'skills': ','.join(combined_skills),
                    'technical_skills': json.dumps(combined_tech_skills),
                    'resume_processed_data': json.dumps(resume_extracted_data)
                }
                
                # Add other extracted fields if available
                if 'total_experience_years' in resume_extracted_data:
                    update_data['total_experience_years'] = resume_extracted_data['total_experience_years']
                
                if 'key_technologies' in resume_extracted_data:
                    update_data['key_technologies'] = json.dumps(resume_extracted_data['key_technologies'])
                
                await self.update_user(user_id, **update_data)
                
                # Add extracted education data
                for edu in resume_extracted_data.get('education', []):
                    await self.add_user_education(
                        user_id=user_id,
                        degree=edu.get('degree', ''),
                        field_of_study=edu.get('field_of_study', ''),
                        institution=edu.get('institution', ''),
                        start_date=edu.get('start_date', ''),
                        end_date=edu.get('end_date', ''),
                        gpa=edu.get('gpa'),
                        location=edu.get('location', ''),
                        description=edu.get('description', '')
                    )
                
                # Add extracted work experience
                for work in resume_extracted_data.get('work_experience', []):
                    await self.add_user_work_experience(
                        user_id=user_id,
                        job_title=work.get('job_title', ''),
                        company_name=work.get('company_name', ''),
                        start_date=work.get('start_date', ''),
                        end_date=work.get('end_date', ''),
                        location=work.get('location', ''),
                        work_mode=work.get('work_mode', ''),
                        responsibilities=json.dumps(work.get('responsibilities', [])),
                        achievements=json.dumps(work.get('achievements', [])),
                        technologies_used=json.dumps(work.get('technologies_used', []))
                    )
                
                # Add extracted internships
                for internship in resume_extracted_data.get('internships', []):
                    await self.add_user_internship(
                        user_id=user_id,
                        position_title=internship.get('position_title', ''),
                        company_name=internship.get('company_name', ''),
                        start_date=internship.get('start_date', ''),
                        end_date=internship.get('end_date', ''),
                        location=internship.get('location', ''),
                        work_mode=internship.get('work_mode', ''),
                        internship_type=internship.get('internship_type', ''),
                        technologies_used=json.dumps(internship.get('technologies_used', [])),
                        responsibilities=json.dumps(internship.get('responsibilities', [])),
                        achievements=json.dumps(internship.get('achievements', [])),
                        stipend_amount=internship.get('stipend_amount'),
                        stipend_currency=internship.get('stipend_currency', ''),
                        certificate_url=internship.get('certificate_url', '')
                    )
                
                # Add extracted certifications
                for cert in resume_extracted_data.get('certifications', []):
                    await self.add_user_certification(
                        user_id=user_id,
                        certification_name=cert.get('certification_name', ''),
                        issuer=cert.get('issuer', ''),
                        year_achieved=cert.get('year_achieved'),
                        credential_id=cert.get('credential_id', ''),
                        credential_url=cert.get('credential_url', ''),
                        expiry_date=cert.get('expiry_date', '')
                    )
                
                return True
                
            except Exception as e:
                print(f"Error combining user and resume data: {e}")
                return False

# Global database manager instance
db_manager = DatabaseManager()
