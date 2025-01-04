import logging
import os
from typing import Optional
import PyPDF2
from io import BytesIO
import time
from functools import wraps

def setup_logging(log_file: str) -> None:
    """Configure logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

def rate_limit(max_per_minute: int):
    """Rate limiting decorator"""
    min_interval = 60.0 / max_per_minute
    last_called = {}
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            key = f"{func.__name__}"
            
            if key in last_called:
                elapsed = now - last_called[key]
                if elapsed < min_interval:
                    time.sleep(min_interval - elapsed)
            
            result = func(*args, **kwargs)
            last_called[key] = time.time()
            return result
        return wrapper
    return decorator

def extract_pdf_text(pdf_content: bytes) -> Optional[str]:
    """Extract text content from PDF"""
    try:
        pdf_file = BytesIO(pdf_content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        
        return text
    except Exception as e:
        logging.error(f"Error extracting PDF text: {str(e)}")
        return None

def ensure_directory_exists(directory: str) -> None:
    """Create directory if it doesn't exist"""
    if not os.path.exists(directory):
        os.makedirs(directory)

def is_valid_attachment(filename: str, size: int) -> bool:
    """Validate attachment filename and size"""
    from config import Config
    
    extension = os.path.splitext(filename.lower())[1]
    return (
        extension in Config.ALLOWED_EXTENSIONS and 
        size <= Config.MAX_ATTACHMENT_SIZE
    )
