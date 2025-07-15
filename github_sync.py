import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

from database import db_manager
from github_oauth import github_oauth_service

logger = logging.getLogger(__name__)

class GitHubSyncProcessor:
    """Background processor for syncing GitHub data"""
    
    def __init__(self):
        self.sync_interval = 3600  # 1 hour in seconds
        self.retry_delay = 300     # 5 minutes in seconds
        self.max_retries = 3
    
    async def sync_all_users(self):
        """Sync GitHub data for all users with linked accounts"""
        logger.info("Starting GitHub sync for all users")
        
        try:
            # Get all users with GitHub accounts
            users_with_github = await self._get_users_with_github()
            
            logger.info(f"Found {len(users_with_github)} users with GitHub accounts")
            
            sync_results = []
            
            for user in users_with_github:
                try:
                    result = await self._sync_user_github_data(user)
                    sync_results.append(result)
                    
                    # Add delay between users to respect rate limits
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Failed to sync GitHub data for user {user['id']}: {e}")
                    sync_results.append({
                        'user_id': user['id'],
                        'success': False,
                        'error': str(e)
                    })
            
            successful_syncs = sum(1 for result in sync_results if result['success'])
            logger.info(f"GitHub sync completed: {successful_syncs}/{len(sync_results)} users synced successfully")
            
            return {
                'total_users': len(users_with_github),
                'successful_syncs': successful_syncs,
                'failed_syncs': len(sync_results) - successful_syncs,
                'results': sync_results
            }
            
        except Exception as e:
            logger.error(f"Error in sync_all_users: {e}")
            raise
    
    async def sync_user(self, user_id: int):
        """Sync GitHub data for a specific user"""
        logger.info(f"Starting GitHub sync for user {user_id}")
        
        try:
            # Get user with GitHub info
            user = await db_manager.get_user_profile(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")
            
            github_info = await db_manager.get_user_github_info(user_id)
            if not github_info:
                raise ValueError(f"User {user_id} has no linked GitHub account")
            
            user_with_github = {
                'id': user_id,
                'github_info': github_info
            }
            
            result = await self._sync_user_github_data(user_with_github)
            
            if result['success']:
                logger.info(f"GitHub sync successful for user {user_id}")
            else:
                logger.error(f"GitHub sync failed for user {user_id}: {result['error']}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error syncing user {user_id}: {e}")
            raise
    
    async def _get_users_with_github(self) -> List[Dict[str, Any]]:
        """Get all users with linked GitHub accounts"""
        # This would be implemented in the database manager
        # For now, we'll create a simple implementation
        
        import aiosqlite
        
        async with aiosqlite.connect(db_manager.db_path) as db:
            cursor = await db.execute("""
                SELECT id, github_id, github_access_token, github_username, github_oauth_linked_at
                FROM users 
                WHERE github_id IS NOT NULL AND github_access_token IS NOT NULL
            """)
            
            users = []
            rows = await cursor.fetchall()
            
            for row in rows:
                users.append({
                    'id': row[0],
                    'github_info': {
                        'github_id': row[1],
                        'github_access_token': row[2],
                        'github_username': row[3],
                        'github_oauth_linked_at': row[4]
                    }
                })
            
            return users
    
    async def _sync_user_github_data(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """Sync GitHub data for a single user"""
        user_id = user['id']
        github_info = user['github_info']
        
        try:
            # Decrypt access token
            encrypted_token = github_info['github_access_token']
            access_token = github_oauth_service.decrypt_token(encrypted_token)
            
            # Validate token
            if not await github_oauth_service.validate_token(access_token):
                # Token is invalid, clear it
                await db_manager.unlink_github_account(user_id)
                return {
                    'user_id': user_id,
                    'success': False,
                    'error': 'GitHub token is invalid or expired'
                }
            
            # Refresh repository data
            result = await github_oauth_service.refresh_user_repos(access_token, user_id)
            
            return {
                'user_id': user_id,
                'success': result['success'],
                'repos_count': result.get('repos_count', 0),
                'error': result.get('error')
            }
            
        except Exception as e:
            return {
                'user_id': user_id,
                'success': False,
                'error': str(e)
            }
    
    async def cleanup_expired_tokens(self):
        """Clean up expired or invalid GitHub tokens"""
        logger.info("Starting cleanup of expired GitHub tokens")
        
        try:
            users_with_github = await self._get_users_with_github()
            
            expired_count = 0
            
            for user in users_with_github:
                try:
                    github_info = user['github_info']
                    encrypted_token = github_info['github_access_token']
                    access_token = github_oauth_service.decrypt_token(encrypted_token)
                    
                    # Check if token is valid
                    if not await github_oauth_service.validate_token(access_token):
                        # Token is invalid, unlink account
                        await db_manager.unlink_github_account(user['id'])
                        expired_count += 1
                        logger.info(f"Removed expired GitHub token for user {user['id']}")
                    
                    # Add delay to respect rate limits
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"Error checking token for user {user['id']}: {e}")
            
            logger.info(f"Cleanup completed: {expired_count} expired tokens removed")
            
            return {
                'total_checked': len(users_with_github),
                'expired_removed': expired_count
            }
            
        except Exception as e:
            logger.error(f"Error in cleanup_expired_tokens: {e}")
            raise
    
    async def run_periodic_sync(self):
        """Run periodic sync of GitHub data"""
        logger.info("Starting periodic GitHub sync")
        
        while True:
            try:
                await self.sync_all_users()
                
                # Wait for next sync
                await asyncio.sleep(self.sync_interval)
                
            except Exception as e:
                logger.error(f"Error in periodic sync: {e}")
                # Wait before retrying
                await asyncio.sleep(self.retry_delay)
    
    async def run_periodic_cleanup(self):
        """Run periodic cleanup of expired tokens"""
        logger.info("Starting periodic GitHub token cleanup")
        
        # Run cleanup every 24 hours
        cleanup_interval = 86400  # 24 hours in seconds
        
        while True:
            try:
                await self.cleanup_expired_tokens()
                
                # Wait for next cleanup
                await asyncio.sleep(cleanup_interval)
                
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")
                # Wait before retrying
                await asyncio.sleep(self.retry_delay)

# Create singleton instance
github_sync_processor = GitHubSyncProcessor()

# Background task runner
async def run_background_tasks():
    """Run background tasks for GitHub sync"""
    tasks = [
        asyncio.create_task(github_sync_processor.run_periodic_sync()),
        asyncio.create_task(github_sync_processor.run_periodic_cleanup())
    ]
    
    try:
        await asyncio.gather(*tasks)
    except Exception as e:
        logger.error(f"Error in background tasks: {e}")
        raise

if __name__ == "__main__":
    # For testing purposes
    asyncio.run(run_background_tasks())
