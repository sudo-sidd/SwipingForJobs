import os
import secrets
import logging
from typing import Optional, Dict, Any
from urllib.parse import urlencode, parse_qs
from datetime import datetime, timedelta

import httpx
from cryptography.fernet import Fernet
from fastapi import HTTPException
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class GitHubOAuthService:
    """Service for handling GitHub OAuth authentication and API interactions"""
    
    def __init__(self):
        self.client_id = os.getenv('GITHUB_CLIENT_ID')
        self.client_secret = os.getenv('GITHUB_CLIENT_SECRET') 
        self.redirect_uri = os.getenv('GITHUB_REDIRECT_URI')
        self.encryption_key = os.getenv('GITHUB_TOKEN_ENCRYPTION_KEY')
        
        if not all([self.client_id, self.client_secret, self.redirect_uri]):
            raise ValueError("Missing GitHub OAuth configuration in .env file")
        
        # Initialize encryption
        if self.encryption_key:
            self.cipher = Fernet(self.encryption_key.encode())
        else:
            # Generate a new encryption key if none provided
            self.cipher = Fernet(Fernet.generate_key())
            logger.warning("No encryption key provided, using generated key. This should be set in production.")
    
    def generate_auth_url(self, state: Optional[str] = None) -> str:
        """Generate GitHub OAuth authorization URL"""
        if not state:
            state = secrets.token_urlsafe(32)
        
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': 'read:user repo',
            'state': state,
            'response_type': 'code'
        }
        
        return f"https://github.com/login/oauth/authorize?{urlencode(params)}"
    
    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token"""
        token_url = "https://github.com/login/oauth/access_token"
        
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'redirect_uri': self.redirect_uri
        }
        
        headers = {
            'Accept': 'application/json',
            'User-Agent': 'SwipingForJobs/1.0'
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=data, headers=headers)
            
            if response.status_code != 200:
                logger.error(f"GitHub token exchange failed: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=400, 
                    detail="Failed to exchange authorization code for token"
                )
            
            token_data = response.json()
            
            if 'error' in token_data:
                logger.error(f"GitHub OAuth error: {token_data}")
                raise HTTPException(
                    status_code=400, 
                    detail=f"GitHub OAuth error: {token_data.get('error_description', 'Unknown error')}"
                )
            
            return token_data
    
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information from GitHub API"""
        headers = {
            'Authorization': f'token {access_token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'SwipingForJobs/1.0'
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get('https://api.github.com/user', headers=headers)
            
            if response.status_code != 200:
                logger.error(f"GitHub user info failed: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=400, 
                    detail="Failed to fetch user information from GitHub"
                )
            
            return response.json()
    
    async def get_user_repos(self, access_token: str, page: int = 1, per_page: int = 100) -> Dict[str, Any]:
        """Get user's repositories from GitHub API"""
        headers = {
            'Authorization': f'token {access_token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'SwipingForJobs/1.0'
        }
        
        params = {
            'page': page,
            'per_page': per_page,
            'sort': 'updated',
            'direction': 'desc'
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                'https://api.github.com/user/repos',
                headers=headers,
                params=params
            )
            
            if response.status_code != 200:
                logger.error(f"GitHub repos fetch failed: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=400, 
                    detail="Failed to fetch repositories from GitHub"
                )
            
            return response.json()
    
    async def get_repo_content(self, access_token: str, repo_full_name: str, path: str = "") -> Dict[str, Any]:
        """Get repository content from GitHub API"""
        headers = {
            'Authorization': f'token {access_token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'SwipingForJobs/1.0'
        }
        
        url = f'https://api.github.com/repos/{repo_full_name}/contents/{path}'
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            
            if response.status_code != 200:
                logger.error(f"GitHub repo content fetch failed: {response.status_code} - {response.text}")
                return None
            
            return response.json()
    
    async def get_repo_readme(self, access_token: str, repo_full_name: str) -> Optional[str]:
        """Get repository README content"""
        readme_files = ['README.md', 'README.rst', 'README.txt', 'README']
        
        for readme_file in readme_files:
            content = await self.get_repo_content(access_token, repo_full_name, readme_file)
            if content and isinstance(content, dict) and 'content' in content:
                try:
                    import base64
                    readme_content = base64.b64decode(content['content']).decode('utf-8')
                    return readme_content
                except Exception as e:
                    logger.warning(f"Failed to decode README for {repo_full_name}: {e}")
                    continue
        
        return None
    
    async def get_repo_languages(self, access_token: str, repo_full_name: str) -> Dict[str, int]:
        """Get repository languages from GitHub API"""
        headers = {
            'Authorization': f'token {access_token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'SwipingForJobs/1.0'
        }
        
        url = f'https://api.github.com/repos/{repo_full_name}/languages'
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            
            if response.status_code != 200:
                logger.error(f"GitHub languages fetch failed: {response.status_code} - {response.text}")
                return {}
            
            return response.json()
    
    def encrypt_token(self, token: str) -> str:
        """Encrypt GitHub access token for storage"""
        return self.cipher.encrypt(token.encode()).decode()
    
    def decrypt_token(self, encrypted_token: str) -> str:
        """Decrypt GitHub access token from storage"""
        return self.cipher.decrypt(encrypted_token.encode()).decode()
    
    async def validate_token(self, access_token: str) -> bool:
        """Validate if GitHub access token is still valid"""
        headers = {
            'Authorization': f'token {access_token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'SwipingForJobs/1.0'
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get('https://api.github.com/user', headers=headers)
            return response.status_code == 200
    
    async def refresh_user_repos(self, access_token: str, user_id: int) -> Dict[str, Any]:
        """Refresh user's repository data and store in database"""
        from database import db_manager
        
        try:
            # Get all user repos
            repos = await self.get_user_repos(access_token)
            
            # Process each repository
            processed_repos = []
            for repo in repos:
                repo_data = {
                    'github_id': repo['id'],
                    'name': repo['name'],
                    'full_name': repo['full_name'],
                    'description': repo.get('description', ''),
                    'url': repo['html_url'],
                    'clone_url': repo['clone_url'],
                    'language': repo.get('language', ''),
                    'stars': repo.get('stargazers_count', 0),
                    'forks': repo.get('forks_count', 0),
                    'is_fork': repo.get('fork', False),
                    'is_private': repo.get('private', False),
                    'created_at': repo.get('created_at', ''),
                    'updated_at': repo.get('updated_at', ''),
                    'topics': repo.get('topics', [])
                }
                
                # Get languages
                languages = await self.get_repo_languages(access_token, repo['full_name'])
                repo_data['languages'] = languages
                
                # Get README
                readme = await self.get_repo_readme(access_token, repo['full_name'])
                repo_data['readme'] = readme
                
                processed_repos.append(repo_data)
            
            # Store in database
            await db_manager.store_github_repos(user_id, processed_repos)
            
            return {
                'success': True,
                'repos_count': len(processed_repos),
                'processed_repos': processed_repos
            }
            
        except Exception as e:
            logger.error(f"Error refreshing user repos: {e}")
            return {
                'success': False,
                'error': str(e)
            }

# Create singleton instance
github_oauth_service = GitHubOAuthService()
