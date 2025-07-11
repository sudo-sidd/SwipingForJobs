import os
import uuid
import shutil
from datetime import datetime
from fastapi import UploadFile, HTTPException
from typing import Optional

RESUME_UPLOAD_DIR = "uploaded_resumes"
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_EXTENSIONS = {".pdf", ".tex", ".txt", ".doc", ".docx"}

class FileManager:
    def __init__(self, upload_dir: str = RESUME_UPLOAD_DIR):
        self.upload_dir = upload_dir
        os.makedirs(upload_dir, exist_ok=True)
    
    def get_file_extension(self, filename: str) -> str:
        """Get file extension"""
        return os.path.splitext(filename)[1].lower()
    
    def generate_unique_filename(self, original_filename: str) -> str:
        """Generate unique filename while preserving extension"""
        ext = self.get_file_extension(original_filename)
        unique_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{timestamp}_{unique_id}{ext}"
    
    async def save_resume(self, file: UploadFile, user_email: str) -> dict:
        """Save uploaded resume file"""
        try:
            # Validate file
            if not file.filename:
                raise HTTPException(status_code=400, detail="No file provided")
            
            # Check file extension
            ext = self.get_file_extension(file.filename)
            if ext not in ALLOWED_EXTENSIONS:
                raise HTTPException(
                    status_code=400, 
                    detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
                )
            
            # Check file size
            file_content = await file.read()
            if len(file_content) > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=400, 
                    detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"
                )
            
            # Generate unique filename
            unique_filename = self.generate_unique_filename(file.filename)
            file_path = os.path.join(self.upload_dir, unique_filename)
            
            # Save file
            with open(file_path, "wb") as buffer:
                buffer.write(file_content)
            
            return {
                "original_filename": file.filename,
                "saved_filename": unique_filename,
                "file_path": file_path,
                "file_size": len(file_content),
                "user_email": user_email
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    def delete_resume(self, file_path: str) -> bool:
        """Delete resume file"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception:
            return False
    
    def get_resume_path(self, filename: str) -> str:
        """Get full path to resume file"""
        return os.path.join(self.upload_dir, filename)
    
    def file_exists(self, filename: str) -> bool:
        """Check if file exists"""
        return os.path.exists(self.get_resume_path(filename))

# Global file manager instance
file_manager = FileManager()
