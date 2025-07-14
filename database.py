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
                    phone_number TEXT, -- Legacy compatibility
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
                    profile_completed BOOLEAN DEFAULT FALSE,
                    
                    -- Additional legacy fields
                    experience_level TEXT,
                    salary_min INTEGER,
                    salary_max INTEGER,
                    currency TEXT DEFAULT 'USD'
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
            
            # Create user projects table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS user_projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    project_name TEXT NOT NULL,
                    description TEXT,
                    technologies TEXT, -- JSON array
                    project_url TEXT,
                    github_url TEXT,
                    start_date DATE,
                    end_date DATE,
                    is_current BOOLEAN DEFAULT 0,
                    featured BOOLEAN DEFAULT 0,
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
            await db.execute("CREATE INDEX IF NOT EXISTS idx_projects_user ON user_projects(user_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_users_job_search_status ON users(job_search_status)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_users_work_mode ON users(work_mode)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_users_location ON users(location)")
            
            await db.commit()
            print("✅ Database initialized with enhanced schema")

    async def create_user(self, **kwargs):
        """Create a new user with enhanced profile data"""
        async with aiosqlite.connect(self.db_path) as db:
            try:
                # Generate login code
                login_code = str(random.randint(1000, 9999))
                
                # Hash password if provided, otherwise use empty string
                password = kwargs.get('password', '')
                password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                
                # Prepare user data with defaults
                user_data = {
                    'name': kwargs.get('name', ''),
                    'email': kwargs.get('email'),
                    'password_hash': password_hash,
                    'login_code': login_code,
                    'first_name': kwargs.get('first_name'),
                    'last_name': kwargs.get('last_name'),
                    'phone': kwargs.get('phone'),
                    'phone_number': kwargs.get('phone_number', kwargs.get('phone')), # Support both
                    'linkedin_url': kwargs.get('linkedin_url'),
                    'github_url': kwargs.get('github_url'),
                    'portfolio_url': kwargs.get('portfolio_url'),
                    'location': kwargs.get('location'),
                    'bio': kwargs.get('bio'),
                    'profile_picture_url': kwargs.get('profile_picture_url'),
                    'job_types': json.dumps(kwargs.get('job_types', [])),
                    'job_functions': json.dumps(kwargs.get('job_functions', [])),
                    'industries': json.dumps(kwargs.get('industries', [])),
                    'preferred_roles': json.dumps(kwargs.get('preferred_roles', [])),
                    'work_mode': json.dumps(kwargs.get('work_mode', [])),
                    'relocation_willingness': kwargs.get('relocation_willingness', False),
                    'preferred_locations': json.dumps(kwargs.get('preferred_locations', [])),
                    'total_years_experience': kwargs.get('total_years_experience'),
                    'years_in_relevant_field': kwargs.get('years_in_relevant_field'),
                    'key_technologies': json.dumps(kwargs.get('key_technologies', [])),
                    'has_managerial_experience': kwargs.get('has_managerial_experience', False),
                    'min_expected_salary': kwargs.get('min_expected_salary'),
                    'max_expected_salary': kwargs.get('max_expected_salary'),
                    'salary_currency': kwargs.get('salary_currency', 'USD'),
                    'salary_negotiable': kwargs.get('salary_negotiable', True),
                    'compensation_type': kwargs.get('compensation_type', 'yearly'),
                    'notice_period': kwargs.get('notice_period'),
                    'preferred_start_date': kwargs.get('preferred_start_date'),
                    'work_authorization_status': kwargs.get('work_authorization_status'),
                    'highest_degree': kwargs.get('highest_degree'),
                    'field_of_study': kwargs.get('field_of_study'),
                    'institution': kwargs.get('institution'),
                    'graduation_year': kwargs.get('graduation_year'),
                    'programming_languages': json.dumps(kwargs.get('programming_languages', {})),
                    'frameworks_libraries': json.dumps(kwargs.get('frameworks_libraries', {})),
                    'tools_platforms': json.dumps(kwargs.get('tools_platforms', {})),
                    'soft_skills': json.dumps(kwargs.get('soft_skills', [])),
                    'languages': json.dumps(kwargs.get('languages', {})),
                    'job_search_status': kwargs.get('job_search_status', 'actively_looking'),
                    'preferred_communication': json.dumps(kwargs.get('preferred_communication', ['email'])),
                    'resume_visibility': kwargs.get('resume_visibility', 'recruiters_only'),
                    'company_size_preference': json.dumps(kwargs.get('company_size_preference', [])),
                    'team_dynamics': json.dumps(kwargs.get('team_dynamics', [])),
                    'work_culture_keywords': json.dumps(kwargs.get('work_culture_keywords', [])),
                    'willing_to_travel': kwargs.get('willing_to_travel', False),
                    'travel_percentage': kwargs.get('travel_percentage', 0),
                    'security_clearance': kwargs.get('security_clearance'),
                    'accessibility_needs': kwargs.get('accessibility_needs'),
                    # Legacy fields
                    'skills': kwargs.get('skills', ''),
                    'preferences': json.dumps(kwargs.get('preferences', [])),
                    'resume_filename': kwargs.get('resume_filename', ''),
                    'resume_path': kwargs.get('resume_path', ''),
                    'linkedin_data': kwargs.get('linkedin_data', ''),
                    'github_data': kwargs.get('github_data', ''),
                    'resume_processed_data': kwargs.get('resume_processed_data', ''),
                    'profile_completed': kwargs.get('profile_completed', False),
                    'experience_level': kwargs.get('experience_level', ''),
                    'salary_min': kwargs.get('salary_min'),
                    'salary_max': kwargs.get('salary_max'),
                    'currency': kwargs.get('currency', 'USD')
                }
                
                # Build dynamic INSERT query
                columns = ', '.join(user_data.keys())
                placeholders = ', '.join(['?' for _ in user_data])
                query = f"INSERT INTO users ({columns}) VALUES ({placeholders})"
                
                cursor = await db.execute(query, list(user_data.values()))
                user_id = cursor.lastrowid
                
                await db.commit()
                return {'user_id': user_id, 'login_code': login_code}
                
            except Exception as e:
                print(f"Error creating user: {e}")
                raise e

    async def authenticate_user(self, name: str, login_code: str):
        """Authenticate user with name and login code"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT * FROM users WHERE name = ? AND login_code = ?",
                (name, login_code)
            )
            user = await cursor.fetchone()
            
            if user:
                # Convert to dict
                columns = [description[0] for description in cursor.description]
                user_dict = dict(zip(columns, user))
                
                # Parse JSON fields
                json_fields = [
                    'job_types', 'job_functions', 'industries', 'preferred_roles',
                    'work_mode', 'preferred_locations', 'key_technologies',
                    'programming_languages', 'frameworks_libraries', 'tools_platforms',
                    'soft_skills', 'languages', 'preferred_communication',
                    'company_size_preference', 'team_dynamics', 'work_culture_keywords',
                    'ai_extracted_skills', 'ai_extracted_experience', 'ai_extracted_education',
                    'ai_extracted_certifications', 'preferences'
                ]
                
                for field in json_fields:
                    if user_dict.get(field):
                        try:
                            user_dict[field] = json.loads(user_dict[field])
                        except json.JSONDecodeError:
                            user_dict[field] = []
                    else:
                        user_dict[field] = [] if field not in ['programming_languages', 'frameworks_libraries', 'tools_platforms', 'languages'] else {}
                
                return user_dict
            
            return None

    async def get_user_profile(self, user_id: int):
        """Get complete user profile with related data"""
        async with aiosqlite.connect(self.db_path) as db:
            # Get user data
            cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            user = await cursor.fetchone()
            
            if not user:
                return None
            
            # Convert to dict
            columns = [description[0] for description in cursor.description]
            user_dict = dict(zip(columns, user))
            
            # Parse JSON fields
            json_fields = [
                'job_types', 'job_functions', 'industries', 'preferred_roles',
                'work_mode', 'preferred_locations', 'key_technologies',
                'programming_languages', 'frameworks_libraries', 'tools_platforms',
                'soft_skills', 'languages', 'preferred_communication',
                'company_size_preference', 'team_dynamics', 'work_culture_keywords',
                'ai_extracted_skills', 'ai_extracted_experience', 'ai_extracted_education',
                'ai_extracted_certifications', 'preferences'
            ]
            
            for field in json_fields:
                if user_dict.get(field):
                    try:
                        user_dict[field] = json.loads(user_dict[field])
                    except json.JSONDecodeError:
                        user_dict[field] = []
                else:
                    user_dict[field] = [] if field not in ['programming_languages', 'frameworks_libraries', 'tools_platforms', 'languages'] else {}
            
            # Get education data
            cursor = await db.execute("SELECT * FROM user_education WHERE user_id = ? ORDER BY end_year DESC", (user_id,))
            education = await cursor.fetchall()
            user_dict['education'] = []
            if education:
                edu_columns = [description[0] for description in cursor.description]
                user_dict['education'] = [dict(zip(edu_columns, row)) for row in education]
            
            # Get certifications
            cursor = await db.execute("SELECT * FROM user_certifications WHERE user_id = ? ORDER BY year_achieved DESC", (user_id,))
            certifications = await cursor.fetchall()
            user_dict['certifications'] = []
            if certifications:
                cert_columns = [description[0] for description in cursor.description]
                user_dict['certifications'] = [dict(zip(cert_columns, row)) for row in certifications]
            
            # Get work experience
            cursor = await db.execute("SELECT * FROM user_work_experience WHERE user_id = ? ORDER BY start_date DESC", (user_id,))
            work_exp = await cursor.fetchall()
            user_dict['work_experience'] = []
            if work_exp:
                work_columns = [description[0] for description in cursor.description]
                for row in work_exp:
                    exp_dict = dict(zip(work_columns, row))
                    # Parse JSON fields
                    if exp_dict.get('technologies_used'):
                        try:
                            exp_dict['technologies_used'] = json.loads(exp_dict['technologies_used'])
                        except json.JSONDecodeError:
                            exp_dict['technologies_used'] = []
                    user_dict['work_experience'].append(exp_dict)
            
            # Get internships
            cursor = await db.execute("SELECT * FROM user_internships WHERE user_id = ? ORDER BY start_date DESC", (user_id,))
            internships = await cursor.fetchall()
            user_dict['internships'] = []
            if internships:
                int_columns = [description[0] for description in cursor.description]
                for row in internships:
                    int_dict = dict(zip(int_columns, row))
                    # Parse JSON fields
                    if int_dict.get('technologies_used'):
                        try:
                            int_dict['technologies_used'] = json.loads(int_dict['technologies_used'])
                        except json.JSONDecodeError:
                            int_dict['technologies_used'] = []
                    user_dict['internships'].append(int_dict)
            
            return user_dict

    async def update_user_profile(self, user_id: int, **kwargs):
        """Update user profile with new data"""
        async with aiosqlite.connect(self.db_path) as db:
            # Handle JSON fields
            json_fields = [
                'job_types', 'job_functions', 'industries', 'preferred_roles',
                'work_mode', 'preferred_locations', 'key_technologies',
                'programming_languages', 'frameworks_libraries', 'tools_platforms',
                'soft_skills', 'languages', 'preferred_communication',
                'company_size_preference', 'team_dynamics', 'work_culture_keywords',
                'ai_extracted_skills', 'ai_extracted_experience', 'ai_extracted_education',
                'ai_extracted_certifications', 'preferences'
            ]
            
            update_data = {}
            for key, value in kwargs.items():
                if key in json_fields:
                    update_data[key] = json.dumps(value) if value is not None else None
                else:
                    update_data[key] = value
            
            if update_data:
                update_data['updated_at'] = datetime.now().isoformat()
                
                # Build UPDATE query
                set_clause = ', '.join([f"{key} = ?" for key in update_data.keys()])
                query = f"UPDATE users SET {set_clause} WHERE id = ?"
                
                await db.execute(query, list(update_data.values()) + [user_id])
                await db.commit()
                return True
            
            return False

    async def cleanup_expired_sessions(self):
        """Remove expired sessions"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM user_sessions WHERE expires_at < ?", (datetime.now().isoformat(),))
            await db.commit()

    async def create_session(self, user_id: int, session_token: str, expires_at: datetime):
        """Create a new session for user"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO user_sessions (user_id, session_token, expires_at)
                VALUES (?, ?, ?)
            """, (user_id, session_token, expires_at.isoformat()))
            
            await db.commit()
            return session_token

    async def get_user_by_session(self, session_token: str):
        """Get user by session token"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT u.* FROM users u
                JOIN user_sessions s ON u.id = s.user_id
                WHERE s.session_token = ? AND s.expires_at > ?
            """, (session_token, datetime.now().isoformat()))
            
            user = await cursor.fetchone()
            
            if user:
                columns = [description[0] for description in cursor.description]
                user_dict = dict(zip(columns, user))
                
                # Parse JSON fields
                json_fields = [
                    'job_types', 'job_functions', 'industries', 'preferred_roles',
                    'work_mode', 'preferred_locations', 'key_technologies',
                    'programming_languages', 'frameworks_libraries', 'tools_platforms',
                    'soft_skills', 'languages', 'preferred_communication',
                    'company_size_preference', 'team_dynamics', 'work_culture_keywords',
                    'ai_extracted_skills', 'ai_extracted_experience', 'ai_extracted_education',
                    'ai_extracted_certifications', 'preferences'
                ]
                
                for field in json_fields:
                    if user_dict.get(field):
                        try:
                            user_dict[field] = json.loads(user_dict[field])
                        except json.JSONDecodeError:
                            user_dict[field] = []
                    else:
                        user_dict[field] = [] if field not in ['programming_languages', 'frameworks_libraries', 'tools_platforms', 'languages'] else {}
                
                return user_dict
            return None

    async def delete_session(self, session_token: str):
        """Delete a specific session"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM user_sessions WHERE session_token = ?", (session_token,))
            await db.commit()

    async def add_education(self, user_id: int, **education_data):
        """Add education record"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO user_education (user_id, degree, field_of_study, institution, 
                                          start_year, end_year, gpa, achievements, is_current)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                education_data.get('degree'),
                education_data.get('field_of_study'),
                education_data.get('institution'),
                education_data.get('start_year'),
                education_data.get('end_year'),
                education_data.get('gpa'),
                education_data.get('achievements'),
                education_data.get('is_current', False)
            ))
            
            await db.commit()
            return True

    async def add_certification(self, user_id: int, **cert_data):
        """Add certification record"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO user_certifications (user_id, certification_name, issuer, 
                                               year_achieved, credential_id, credential_url, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                cert_data.get('certification_name'),
                cert_data.get('issuer'),
                cert_data.get('year_achieved'),
                cert_data.get('credential_id'),
                cert_data.get('credential_url'),
                cert_data.get('expires_at')
            ))
            
            await db.commit()
            return True

    async def add_work_experience(self, user_id: int, **work_data):
        """Add work experience record"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO user_work_experience (user_id, position_title, company_name, 
                                                start_date, end_date, is_current, location,
                                                work_mode, technologies_used, responsibilities,
                                                achievements, employment_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                work_data.get('position_title'),
                work_data.get('company_name'),
                work_data.get('start_date'),
                work_data.get('end_date'),
                work_data.get('is_current', False),
                work_data.get('location'),
                work_data.get('work_mode'),
                json.dumps(work_data.get('technologies_used', [])),
                work_data.get('responsibilities'),
                work_data.get('achievements'),
                work_data.get('employment_type')
            ))
            
            await db.commit()
            return True

    async def add_internship(self, user_id: int, **internship_data):
        """Add internship record"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO user_internships (user_id, position_title, company_name, 
                                            start_date, end_date, location, work_mode,
                                            technologies_used, responsibilities, achievements,
                                            internship_type, stipend_amount, stipend_currency,
                                            certificate_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                internship_data.get('position_title'),
                internship_data.get('company_name'),
                internship_data.get('start_date'),
                internship_data.get('end_date'),
                internship_data.get('location'),
                internship_data.get('work_mode'),
                json.dumps(internship_data.get('technologies_used', [])),
                internship_data.get('responsibilities'),
                internship_data.get('achievements'),
                internship_data.get('internship_type'),
                internship_data.get('stipend_amount'),
                internship_data.get('stipend_currency'),
                internship_data.get('certificate_url')
            ))
            
            await db.commit()
            return True

    async def add_project(self, user_id: int, **project_data):
        """Add project record"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO user_projects (user_id, project_name, description, technologies,
                                         project_url, github_url, start_date, end_date,
                                         is_current, featured)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                project_data.get('project_name'),
                project_data.get('description'),
                json.dumps(project_data.get('technologies', [])),
                project_data.get('project_url'),
                project_data.get('github_url'),
                project_data.get('start_date'),
                project_data.get('end_date'),
                project_data.get('is_current', False),
                project_data.get('featured', False)
            ))
            
            await db.commit()
            return True

    async def get_user_projects(self, user_id: int):
        """Get all projects for a user"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT id, project_name, description, technologies, project_url, github_url,
                       start_date, end_date, is_current, featured, created_at
                FROM user_projects
                WHERE user_id = ?
                ORDER BY featured DESC, created_at DESC
            """, (user_id,))
            
            rows = await cursor.fetchall()
            projects = []
            for row in rows:
                projects.append({
                    'id': row[0],
                    'project_name': row[1],
                    'description': row[2],
                    'technologies': json.loads(row[3]) if row[3] else [],
                    'project_url': row[4],
                    'github_url': row[5],
                    'start_date': row[6],
                    'end_date': row[7],
                    'is_current': bool(row[8]),
                    'featured': bool(row[9]),
                    'created_at': row[10]
                })
            
            return projects

    async def update_project(self, project_id: int, **project_data):
        """Update project record"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE user_projects 
                SET project_name = ?, description = ?, technologies = ?, 
                    project_url = ?, github_url = ?, start_date = ?, 
                    end_date = ?, is_current = ?, featured = ?
                WHERE id = ?
            """, (
                project_data.get('project_name'),
                project_data.get('description'),
                json.dumps(project_data.get('technologies', [])),
                project_data.get('project_url'),
                project_data.get('github_url'),
                project_data.get('start_date'),
                project_data.get('end_date'),
                project_data.get('is_current', False),
                project_data.get('featured', False),
                project_id
            ))
            
            await db.commit()
            return True

    async def delete_project(self, project_id: int):
        """Delete project record"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM user_projects WHERE id = ?", (project_id,))
            await db.commit()
            return True

    async def clear_user_projects(self, user_id: int):
        """Clear all projects for a user (useful for resume re-processing)"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM user_projects WHERE user_id = ?", (user_id,))
            await db.commit()
            return True

# Global database manager instance
db_manager = DatabaseManager()
