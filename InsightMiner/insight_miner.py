# InsightMiner Pro - Zero Storage, Maximum Intelligence
# Advanced logging + Image deduplication system + Complete MVP

import os
import json
import requests
import base64
import logging
import cv2
import pytesseract
from datetime import datetime
from pathlib import Path
import time
from PIL import Image
import streamlit as st
from supabase import create_client, Client
import hashlib
import tempfile
import shutil
from typing import Dict, List, Optional, Tuple
import re
from collections import Counter
import sys
from logging.handlers import RotatingFileHandler
import tkinter as tk
from tkinter import filedialog
import keyring
import random
import threading
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from BACKUP_AUTO import trigger_startup_backup

# Enhanced Logging System
class LoggerSetup:
    """Professional logging system for debugging and monitoring"""
    
    def __init__(self):
        self.setup_logging()
    
    def setup_logging(self):
        """Setup comprehensive logging with rotation"""
        # Create logs directory
        logs_dir = Path("Logs")
        logs_dir.mkdir(exist_ok=True)
        
        # Setup formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)8s | %(name)20s | %(funcName)15s:%(lineno)d | %(message)s'
        )
        
        # Root logger setup
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        root_logger.handlers.clear()
        
        # Error logs (captures ALL errors across the app)
        error_handler = RotatingFileHandler(
            logs_dir / "ErrorLogs.js", maxBytes=5*1024*1024, backupCount=5
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(detailed_formatter)
        
        # Auth logs (captures all authentication attempts)
        auth_handler = RotatingFileHandler(
            logs_dir / "AuthLogs.js", maxBytes=2*1024*1024, backupCount=3
        )
        auth_handler.setLevel(logging.INFO)
        auth_handler.setFormatter(detailed_formatter)
        
        # Add handlers to root logger
        root_logger.addHandler(error_handler)
        
        # Create separate auth logger
        auth_logger = logging.getLogger('auth')
        auth_logger.addHandler(auth_handler)
        auth_logger.setLevel(logging.INFO)
        
        # Console handler for development
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter('%(levelname)s | %(message)s'))
        root_logger.addHandler(console_handler)

# Initialize logging
logger_setup = LoggerSetup()
logger = logging.getLogger(__name__)
auth_logger = logging.getLogger('auth')

class ImageHasher:
    """Image deduplication system - NO storage, just smart fingerprinting"""
    
    def __init__(self):
        self.hash_cache = {}
        self.load_hash_cache()
    
    def calculate_image_hash(self, image_path: str) -> str:
        """Calculate perceptual hash of image for deduplication"""
        try:
            # Use multiple hash methods for accuracy
            with open(image_path, "rb") as f:
                # File content hash
                file_hash = hashlib.sha256(f.read()).hexdigest()
            
            # Perceptual hash using PIL
            img = Image.open(image_path)
            img = img.convert('L').resize((8, 8), Image.Resampling.LANCZOS)
            pixels = list(img.getdata())
            avg = sum(pixels) / len(pixels)
            
            # Create binary hash
            bits = ''.join('1' if pixel > avg else '0' for pixel in pixels)
            perceptual_hash = hex(int(bits, 2))[2:]
            
            # Combine hashes for unique fingerprint
            combined_hash = hashlib.md5(f"{file_hash}_{perceptual_hash}".encode()).hexdigest()
            
            logger.info(f"Generated hash for {os.path.basename(image_path)}: {combined_hash[:12]}...")
            return combined_hash
            
        except Exception as e:
            logger.error(f"Hash calculation failed for {image_path}: {e}")
            return hashlib.md5(f"error_{datetime.now().isoformat()}".encode()).hexdigest()
    
    def is_duplicate(self, image_hash: str) -> Tuple[bool, Optional[Dict]]:
        """Check if image is duplicate and return existing analysis"""
        try:
            if image_hash in self.hash_cache:
                existing_data = self.hash_cache[image_hash]
                logger.info(f"Duplicate detected! Hash: {image_hash[:12]}... | Original: {existing_data.get('original_filename', 'unknown')}")
                auth_logger.info(f"DUPLICATE_DETECTED | Hash: {image_hash[:12]} | Count: {existing_data.get('duplicate_count', 0) + 1}")
                return True, existing_data
            return False, None
            
        except Exception as e:
            logger.error(f"Duplicate check failed: {e}")
            return False, None
    
    def store_hash(self, image_hash: str, analysis_data: Dict):
        """Store hash with analysis data (NO IMAGE STORAGE)"""
        try:
            self.hash_cache[image_hash] = {
                **analysis_data,
                'first_seen': datetime.now().isoformat(),
                'duplicate_count': 0
            }
            self.save_hash_cache()
            logger.info(f"Hash stored: {image_hash[:12]}... for {analysis_data.get('original_filename', 'unknown')}")
            
        except Exception as e:
            logger.error(f"Hash storage failed: {e}")
    
    def increment_duplicate_count(self, image_hash: str):
        """Increment duplicate counter"""
        try:
            if image_hash in self.hash_cache:
                self.hash_cache[image_hash]['duplicate_count'] += 1
                self.hash_cache[image_hash]['last_seen'] = datetime.now().isoformat()
                self.save_hash_cache()
                
        except Exception as e:
            logger.error(f"Duplicate count increment failed: {e}")
    
    def load_hash_cache(self):
        """Load hash cache from file"""
        try:
            cache_file = Path("hash_cache.json")
            if cache_file.exists():
                with open(cache_file, 'r') as f:
                    self.hash_cache = json.load(f)
                logger.info(f"Loaded {len(self.hash_cache)} image hashes from cache")
            else:
                self.hash_cache = {}
                
        except Exception as e:
            logger.error(f"Hash cache loading failed: {e}")
            self.hash_cache = {}
    
    def save_hash_cache(self):
        """Save hash cache to file"""
        try:
            with open("hash_cache.json", 'w') as f:
                json.dump(self.hash_cache, f, indent=2)
                
        except Exception as e:
            logger.error(f"Hash cache saving failed: {e}")
    
    def get_cache_stats(self) -> Dict:
        """Get deduplication statistics"""
        try:
            total_hashes = len(self.hash_cache)
            total_duplicates = sum(data.get('duplicate_count', 0) for data in self.hash_cache.values())
            
            return {
                'unique_images': total_hashes,
                'total_duplicates_blocked': total_duplicates,
                'cache_size_mb': len(json.dumps(self.hash_cache)) / (1024 * 1024)
            }
            
        except Exception as e:
            logger.error(f"Cache stats calculation failed: {e}")
            return {'unique_images': 0, 'total_duplicates_blocked': 0, 'cache_size_mb': 0}

# Configuration Management
class Config:
    """Environment-based configuration management with secure keyring integration"""
    
    def __init__(self):
        # Load environment variables from .env file
        load_dotenv()
        self.load_config()
    
    def load_config(self):
        """Load configuration from environment variables."""
        try:
            # Load from environment variables
            self.SUPABASE_URL = os.getenv('SUPABASE_URL')
            self.SUPABASE_KEY = os.getenv('SUPABASE_KEY')
            self.INPUT_FOLDER = os.getenv('INPUT_FOLDER', "input_images")
            self.VIDEO_FOLDER = os.getenv('VIDEO_FOLDER', "input_videos")
            
            # Instagram-specific configuration
            self.INSTAGRAM_TIMEOUT = int(os.getenv('INSTAGRAM_TIMEOUT', '30'))
            self.INSTAGRAM_RETRY_ATTEMPTS = int(os.getenv('INSTAGRAM_RETRY_ATTEMPTS', '3'))
            
            auth_logger.info("CONFIG_LOADED from environment variables")
        except Exception as e:
            logger.error(f"Error loading environment configuration: {e}")
            self.set_defaults()

        # Fixed application settings (not configurable)
        self.TEMP_FOLDER = "temp_processing"
        self.OLLAMA_URL = "http://localhost:11434/api/generate"
        self.MODEL_NAME = "llava"
        self.MAX_IMAGE_SIZE = (800, 800)
        self.JPEG_QUALITY = 85
        self.SUPPORTED_IMAGE_FORMATS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
        self.SUPPORTED_VIDEO_FORMATS = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}
        self.FRAME_EXTRACTION_INTERVAL = 2
        self.MAX_FRAMES_PER_VIDEO = 30
        self.MAX_BATCH_SIZE = 50
        self.REQUEST_TIMEOUT = 60
        self.CATEGORIES = ["Tech", "Business", "Education", "Health", "Lifestyle", "Finance", "Marketing", "Personal Development"]
        self.CONFIDENCE_THRESHOLD = 0.9

    def set_defaults(self):
        """Set fallback default values if environment variables are missing."""
        self.SUPABASE_URL = None
        self.SUPABASE_KEY = None
        self.INPUT_FOLDER = "input_images"
        self.VIDEO_FOLDER = "input_videos"
        self.INSTAGRAM_TIMEOUT = 30
        self.INSTAGRAM_RETRY_ATTEMPTS = 3

    def save_config(self, supabase_url: str, supabase_key: str, input_folder: str, video_folder: str) -> bool:
        """Update .env file with new configuration values."""
        try:
            env_path = Path('.env')
            
            # Read existing .env content
            env_content = {}
            if env_path.exists():
                with open(env_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            env_content[key] = value
            
            # Update with new values
            env_content['SUPABASE_URL'] = supabase_url
            env_content['SUPABASE_KEY'] = supabase_key
            env_content['INPUT_FOLDER'] = input_folder
            env_content['VIDEO_FOLDER'] = video_folder
            
            # Write back to .env file
            with open(env_path, 'w') as f:
                f.write("# Supabase Configuration\n")
                f.write(f"SUPABASE_URL={env_content['SUPABASE_URL']}\n")
                f.write(f"SUPABASE_KEY={env_content['SUPABASE_KEY']}\n\n")
                f.write("# Download Folders\n")
                f.write(f"INPUT_FOLDER={env_content['INPUT_FOLDER']}\n")
                f.write(f"VIDEO_FOLDER={env_content['VIDEO_FOLDER']}\n\n")
                f.write("# Instagram Download Settings\n")
                f.write(f"INSTAGRAM_TIMEOUT={env_content.get('INSTAGRAM_TIMEOUT', '30')}\n")
                f.write(f"INSTAGRAM_RETRY_ATTEMPTS={env_content.get('INSTAGRAM_RETRY_ATTEMPTS', '3')}\n")
            
            # Reload configuration
            self.load_config()
            
            logger.info("Environment configuration saved successfully")
            auth_logger.info(f"CONFIG_SAVED for URL: {supabase_url[:20]}...")
            return True
        except Exception as e:
            logger.error(f"Error saving environment configuration: {e}")
            auth_logger.error(f"CONFIG_SAVE_FAILED | {e}")
            return False
    
    def is_configured(self) -> bool:
        """Check if essential app configurations are set."""
        return bool(self.SUPABASE_URL and self.SUPABASE_KEY and self.INPUT_FOLDER and self.VIDEO_FOLDER)
    
    # Keyring Integration for Secure Credential Storage
    KEYRING_SERVICE = "InsightMiner"
    KEYRING_USERNAME_KEY = "instagram_username"
    KEYRING_PASSWORD_KEY = "instagram_password"
    
    def get_keyring_status(self) -> Dict:
        """Get keyring backend information"""
        try:
            backend = keyring.get_keyring()
            backend_name = backend.__class__.__name__
            
            # Determine if keyring is secure
            secure_backends = ['WinVaultKeyring', 'OSXKeychain', 'SecretServiceKeyring']
            is_secure = any(secure in backend_name for secure in secure_backends)
            
            return {
                "backend": backend_name,
                "is_secure": is_secure,
                "available": True
            }
        except Exception as e:
            logger.error(f"Keyring status check failed: {e}")
            return {
                "backend": "None",
                "is_secure": False,
                "available": False,
                "error": str(e)
            }
    
    def store_instagram_credentials(self, username: str, password: str) -> bool:
        """Store Instagram credentials securely in OS keyring"""
        try:
            keyring.set_password(self.KEYRING_SERVICE, self.KEYRING_USERNAME_KEY, username)
            keyring.set_password(self.KEYRING_SERVICE, self.KEYRING_PASSWORD_KEY, password)
            
            # Verify storage
            stored_username = keyring.get_password(self.KEYRING_SERVICE, self.KEYRING_USERNAME_KEY)
            stored_password = keyring.get_password(self.KEYRING_SERVICE, self.KEYRING_PASSWORD_KEY)
            
            if stored_username == username and stored_password == password:
                logger.info("Instagram credentials stored successfully in keyring")
                auth_logger.info("INSTAGRAM_CREDENTIALS_STORED_SECURELY")
                return True
            else:
                logger.error("Credential verification failed after storage")
                return False
                
        except Exception as e:
            logger.error(f"Failed to store Instagram credentials: {e}")
            auth_logger.error(f"INSTAGRAM_CREDENTIAL_STORAGE_FAILED | {e}")
            return False
    
    def get_instagram_credentials(self) -> Tuple[Optional[str], Optional[str]]:
        """Retrieve Instagram credentials from OS keyring"""
        try:
            username = keyring.get_password(self.KEYRING_SERVICE, self.KEYRING_USERNAME_KEY)
            password = keyring.get_password(self.KEYRING_SERVICE, self.KEYRING_PASSWORD_KEY)
            
            if username and password:
                logger.info("Instagram credentials retrieved from keyring")
                return username, password
            else:
                logger.info("No Instagram credentials found in keyring")
                return None, None
                
        except Exception as e:
            logger.error(f"Failed to retrieve Instagram credentials: {e}")
            return None, None
    
    def delete_instagram_credentials(self) -> bool:
        """Delete Instagram credentials from OS keyring"""
        try:
            keyring.delete_password(self.KEYRING_SERVICE, self.KEYRING_USERNAME_KEY)
            keyring.delete_password(self.KEYRING_SERVICE, self.KEYRING_PASSWORD_KEY)
            
            logger.info("Instagram credentials deleted from keyring")
            auth_logger.info("INSTAGRAM_CREDENTIALS_DELETED_SECURELY")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete Instagram credentials: {e}")
            return False
    
    def has_instagram_credentials(self) -> bool:
        """Check if Instagram credentials are stored in keyring"""
        username, password = self.get_instagram_credentials()
        return bool(username and password)
    
    @property
    def INSTAGRAM_USERNAME(self) -> Optional[str]:
        """Get Instagram username from keyring"""
        username, _ = self.get_instagram_credentials()
        return username
    
    @property  
    def INSTAGRAM_PASSWORD(self) -> Optional[str]:
        """Get Instagram password from keyring"""
        _, password = self.get_instagram_credentials()
        return password

class InstagramDownloader:
    """Instagram content downloader using instagrapi with timeout fixes"""
    
    def __init__(self, config):
        self.config = config
        self.client = None
        self.session_file = "instagram_session.json"
        self.setup_client()
    
    def setup_client(self):
        """Initialize Instagram client with environment-based timeout configuration"""
        try:
            from instagrapi import Client
            self.client = Client()
            
            # Configure timeouts from environment variables
            timeout = self.config.INSTAGRAM_TIMEOUT
            self.client.request_timeout = timeout
            self.client.request_delay_range = [1, 3]
            
            # Set longer timeouts for media downloads specifically
            if hasattr(self.client, 'private'):
                self.client.private.request_timeout = timeout
            
            logger.info(f"Instagram client initialized with {timeout}s timeout configuration")
        except ImportError:
            logger.error("instagrapi not installed. Run: pip install instagrapi>=2.2.1")
            self.client = None
        except Exception as e:
            logger.error(f"Instagram client initialization failed: {e}")
            self.client = None
    
    def _retry_download_with_backoff(self, download_func, max_retries=None):
        """Retry download function with exponential backoff for timeout errors"""
        if max_retries is None:
            max_retries = self.config.INSTAGRAM_RETRY_ATTEMPTS
        
        logger.info(f"=== Download Retry Logic Started ===")
        logger.info(f"Max retry attempts: {max_retries}")
        logger.info(f"Timeout configuration: {self.config.INSTAGRAM_TIMEOUT}s")
            
        for attempt in range(max_retries):
            attempt_num = attempt + 1
            logger.info(f"--- Download Attempt {attempt_num}/{max_retries} ---")
            
            try:
                start_time = time.time()
                logger.info("Calling download function...")
                result = download_func()
                end_time = time.time()
                download_time = end_time - start_time
                
                logger.info(f"✅ Download successful on attempt {attempt_num}")
                logger.info(f"Download duration: {download_time:.2f}s")
                auth_logger.info(f"DOWNLOAD_SUCCESS | Attempt: {attempt_num}/{max_retries} | Duration: {download_time:.2f}s")
                return result
                
            except Exception as e:
                error_str = str(e).lower()
                error_type = type(e).__name__
                end_time = time.time()
                
                logger.error(f"❌ Download attempt {attempt_num} failed")
                logger.error(f"Error type: {error_type}")
                logger.error(f"Error message: {str(e)}")
                
                # Check if it's a timeout or connection error
                timeout_keywords = ['timeout', 'timed out', 'connection', 'read timeout', 'connectionerror', 'httperror']
                is_timeout_error = any(keyword in error_str for keyword in timeout_keywords)
                
                logger.info(f"Error classification - Is timeout/connection error: {is_timeout_error}")
                logger.info(f"Checked keywords: {timeout_keywords}")
                
                if is_timeout_error:
                    logger.warning(f"Timeout/connection error detected on attempt {attempt_num}")
                    auth_logger.warning(f"DOWNLOAD_TIMEOUT | Attempt: {attempt_num}/{max_retries} | Error: {error_type}")
                    
                    if attempt < max_retries - 1:  # Don't sleep on last attempt
                        # Exponential backoff: 2^attempt + random jitter
                        wait_time = (2 ** attempt) + random.uniform(0.1, 1.0)
                        logger.warning(f"Will retry in {wait_time:.1f}s (exponential backoff)")
                        logger.info(f"Backoff calculation: 2^{attempt} + random(0.1-1.0) = {wait_time:.1f}s")
                        
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"❌ All retry attempts exhausted due to timeout")
                        logger.error(f"Final attempt {attempt_num} failed with: {str(e)}")
                        auth_logger.error(f"DOWNLOAD_TIMEOUT_FINAL | Max attempts reached: {max_retries}")
                        
                        # Log full stack trace for final timeout failure
                        import traceback
                        logger.error(f"Final timeout stack trace:\n{traceback.format_exc()}")
                        
                        raise Exception(f"Download timeout after {max_retries} retries: {str(e)}")
                else:
                    # Non-timeout error, don't retry
                    logger.error(f"❌ Non-timeout error detected - will not retry")
                    logger.error(f"Error type: {error_type}")
                    auth_logger.error(f"DOWNLOAD_NON_TIMEOUT_ERROR | Attempt: {attempt_num} | Error: {error_type}")
                    
                    # Log full stack trace for non-timeout errors
                    import traceback
                    logger.error(f"Non-timeout error stack trace:\n{traceback.format_exc()}")
                    
                    raise e
        
        # Should never reach here
        logger.error("❌ Unexpected retry loop exit")
        raise Exception("Unexpected retry loop exit")
    
    def setup_session(self) -> Tuple[bool, str]:
        """Setup Instagram session with login and persistence"""
        logger.info("=== Instagram Session Setup Started ===")
        
        if not self.client:
            logger.error("Instagram client not available during session setup")
            return False, "Instagram client not available"
        
        if not self.config.INSTAGRAM_USERNAME or not self.config.INSTAGRAM_PASSWORD:
            logger.error("Instagram credentials not configured in keyring")
            return False, "Instagram credentials not configured"
        
        logger.info(f"Instagram session setup for user: {self.config.INSTAGRAM_USERNAME}")
        logger.info(f"Session file path: {self.session_file}")
        logger.info(f"Timeout configuration: {self.config.INSTAGRAM_TIMEOUT}s")
        logger.info(f"Retry attempts: {self.config.INSTAGRAM_RETRY_ATTEMPTS}")
        
        try:
            # Try to load existing session
            session_path = Path(self.session_file)
            if session_path.exists():
                logger.info(f"Found existing session file: {session_path}")
                try:
                    self.client.load_settings(self.session_file)
                    logger.info("Session file loaded into client")
                    
                    # Verify session is still valid
                    logger.info("Verifying session validity with timeline feed...")
                    timeline_feed = self.client.get_timeline_feed()
                    logger.info(f"Session valid - timeline feed contains {len(timeline_feed)} items")
                    
                    auth_logger.info("INSTAGRAM_SESSION_LOADED_SUCCESSFULLY")
                    logger.info("=== Instagram Session Setup Complete (Existing) ===")
                    return True, "Session loaded successfully"
                    
                except Exception as e:
                    logger.warning(f"Existing session invalid - will attempt fresh login: {e}")
                    logger.warning(f"Session validation error type: {type(e).__name__}")
                    # Continue to fresh login
            else:
                logger.info("No existing session file found - will perform fresh login")
            
            # Fresh login
            logger.info("=== Starting Fresh Instagram Login ===")
            auth_logger.info(f"INSTAGRAM_LOGIN_ATTEMPT | User: {self.config.INSTAGRAM_USERNAME}")
            
            logger.info("Calling client.login() with credentials...")
            self.client.login(self.config.INSTAGRAM_USERNAME, self.config.INSTAGRAM_PASSWORD)
            logger.info("Login call completed successfully")
            
            # Save session
            logger.info(f"Saving session to {self.session_file}")
            self.client.dump_settings(self.session_file)
            logger.info("Session saved successfully")
            
            # Verify saved session
            if Path(self.session_file).exists():
                session_size = Path(self.session_file).stat().st_size
                logger.info(f"Session file created: {session_size} bytes")
            
            auth_logger.info("INSTAGRAM_LOGIN_SUCCESS")
            logger.info("=== Instagram Session Setup Complete (Fresh Login) ===")
            return True, "Login successful"
            
        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__
            logger.error(f"=== Instagram Session Setup Failed ===")
            logger.error(f"Error type: {error_type}")
            logger.error(f"Error message: {error_msg}")
            logger.error(f"Session file exists: {Path(self.session_file).exists()}")
            
            # Log full stack trace for debugging
            import traceback
            logger.error(f"Full stack trace:\n{traceback.format_exc()}")
            
            auth_logger.error(f"INSTAGRAM_LOGIN_FAILED | {error_type}: {error_msg}")
            
            # Handle specific error cases
            if "checkpoint_required" in error_msg.lower():
                logger.error("Login challenge detected - requires manual intervention")
                return False, "Login challenge required. Please login manually first."
            elif "rate limit" in error_msg.lower():
                logger.error("Rate limit detected - temporary restriction")
                return False, "Rate limited. Please try again later."
            elif "password" in error_msg.lower():
                logger.error("Authentication failed - invalid credentials")
                return False, "Invalid credentials. Please check username/password."
            else:
                logger.error(f"Unhandled login error: {error_msg}")
                return False, f"Login failed: {error_msg}"
    
    def get_session_status(self) -> Dict:
        """Get current session status"""
        if not self.client:
            return {"status": "unavailable", "message": "Instagram client not available"}
        
        try:
            # Check if session file exists
            session_exists = Path(self.session_file).exists()
            
            if session_exists:
                # Try to verify session
                try:
                    self.client.load_settings(self.session_file)
                    user_info = self.client.account_info()
                    return {
                        "status": "active",
                        "message": f"Logged in as @{user_info.username}",
                        "username": user_info.username,
                        "session_file": session_exists
                    }
                except:
                    return {
                        "status": "expired",
                        "message": "Session expired, re-login required",
                        "session_file": session_exists
                    }
            else:
                return {
                    "status": "not_logged_in",
                    "message": "No active session",
                    "session_file": False
                }
                
        except Exception as e:
            logger.error(f"Session status check failed: {e}")
            return {"status": "error", "message": f"Status check failed: {str(e)}"}
    
    def _validate_instagram_url(self, url: str) -> bool:
        """Validate Instagram URL format and content type."""
        try:
            if not url or not isinstance(url, str):
                return False
            
            url = url.strip()
            
            # Check for Instagram domain
            valid_domains = ['instagram.com', 'instagr.am', 'www.instagram.com']
            has_domain = any(domain in url.lower() for domain in valid_domains)
            
            if not has_domain:
                return False
            
            # Check for valid content patterns
            valid_patterns = ['/p/', '/reel/', '/tv/', '/stories/']
            has_pattern = any(pattern in url.lower() for pattern in valid_patterns)
            
            if not has_pattern:
                logger.warning(f"Instagram URL without recognized content pattern: {url}")
                # Still allow it, as Instagram may have other valid formats
            
            # Basic URL structure validation
            if not (url.startswith('http://') or url.startswith('https://')):
                logger.warning(f"Instagram URL missing protocol: {url}")
                # Could potentially fix this, but safer to reject
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"URL validation error: {e}")
            return False
    
    def _get_content_type_from_url(self, url: str) -> str:
        """Determine content type from Instagram URL."""
        try:
            url_lower = url.lower()
            
            if '/reel/' in url_lower or '/tv/' in url_lower:
                return 'video'
            elif '/p/' in url_lower:
                return 'auto'  # Could be image or video, let the API determine
            elif '/stories/' in url_lower:
                return 'story'
            else:
                return 'unknown'
                
        except Exception as e:
            logger.error(f"Content type detection error: {e}")
            return 'unknown'
    
    def download_single_reel(self, url: str, download_folder: str = None) -> Tuple[bool, str]:
        """Download a single Instagram reel/post with automatic folder routing and processing"""
        logger.info("=== Instagram Download Started ===")
        logger.info(f"Download URL: {url}")
        logger.info(f"Timeout setting: {self.config.INSTAGRAM_TIMEOUT}s")
        logger.info(f"Max retry attempts: {self.config.INSTAGRAM_RETRY_ATTEMPTS}")
        
        if not self.client:
            logger.error("Instagram client not available for download")
            return False, "Instagram client not available"
        
        try:
            # Ensure client is logged in
            logger.info("Checking session status before download...")
            session_status = self.get_session_status()
            logger.info(f"Session status: {session_status}")
            
            if session_status["status"] != "active":
                logger.info("Session not active - attempting to establish session")
                success, message = self.setup_session()
                if not success:
                    logger.error(f"Session setup failed: {message}")
                    return False, f"Login required: {message}"
                logger.info("Session established successfully")
            else:
                logger.info("Session already active - proceeding with download")
            
            # Enhanced URL validation
            logger.info("Validating Instagram URL format...")
            if not self._validate_instagram_url(url):
                logger.error(f"URL validation failed: {url}")
                return False, "Invalid Instagram URL format"
            logger.info("URL validation passed")
            
            # Extract media PK (Primary Key) from URL - this is the critical fix
            logger.info("=== Media PK Extraction ===")
            try:
                logger.info(f"Extracting media PK from URL: {url}")
                media_pk = self.client.media_pk_from_url(url)
                logger.info(f"✅ Media PK extracted successfully: {media_pk}")
                logger.info(f"Media PK type: {type(media_pk)}")
                auth_logger.info(f"MEDIA_PK_EXTRACTED | URL: {url} | PK: {media_pk}")
            except Exception as pk_error:
                error_msg = f"Failed to extract media PK from URL: {str(pk_error)}"
                error_type = type(pk_error).__name__
                logger.error(f"❌ Media PK extraction failed")
                logger.error(f"Error type: {error_type}")
                logger.error(f"Error message: {error_msg}")
                
                # Log full stack trace for PK extraction errors
                import traceback
                logger.error(f"PK extraction stack trace:\n{traceback.format_exc()}")
                
                auth_logger.error(f"MEDIA_PK_EXTRACTION_FAILED | URL: {url} | Error: {error_msg}")
                return False, error_msg
            
            # Get media info using the PK with ValidationError fallback
            logger.info("=== Media Info Retrieval ===")
            media_info = None
            use_fallback = False
            
            try:
                logger.info(f"Retrieving media info for PK: {media_pk}")
                media_info = self.client.media_info(media_pk)
                logger.info(f"✅ Media info retrieved successfully")
                logger.info(f"Media type: {media_info.media_type}")
                logger.info(f"Media ID: {getattr(media_info, 'id', 'N/A')}")
                logger.info(f"Media code: {getattr(media_info, 'code', 'N/A')}")
                
                if hasattr(media_info, 'user'):
                    logger.info(f"Media owner: {getattr(media_info.user, 'username', 'N/A')}")
                
                auth_logger.info(f"MEDIA_INFO_RETRIEVED | PK: {media_pk} | Type: {media_info.media_type}")
                
            except Exception as info_error:
                error_type = type(info_error).__name__
                error_msg = str(info_error)
                
                logger.error(f"❌ Media info retrieval failed")
                logger.error(f"Error type: {error_type}")
                logger.error(f"Error message: {error_msg}")
                
                # Check for ValidationError specifically (Pydantic validation failures)
                if "ValidationError" in error_type or "validation" in error_msg.lower():
                    logger.warning("🔄 ValidationError detected - activating metadata parsing fallback system")
                    logger.warning("This occurs when Instagram API returns malformed metadata (e.g., null clips_metadata.original_sound_info)")
                    auth_logger.warning(f"VALIDATION_ERROR_FALLBACK_ACTIVATED | PK: {media_pk} | Error: {error_type}")
                    
                    # Activate fallback mode
                    use_fallback = True
                    media_info = self._create_minimal_media_info(media_pk, url)
                    
                    if media_info:
                        logger.info("✅ Fallback media info created successfully")
                        logger.info(f"Fallback media type: {media_info.media_type}")
                        auth_logger.info(f"FALLBACK_MEDIA_INFO_CREATED | PK: {media_pk} | Type: {media_info.media_type}")
                    else:
                        logger.error("❌ Fallback media info creation failed")
                        auth_logger.error(f"FALLBACK_MEDIA_INFO_FAILED | PK: {media_pk}")
                        return False, "ValidationError: Could not parse metadata and fallback failed"
                else:
                    # Non-validation error, log and fail
                    import traceback
                    logger.error(f"Media info stack trace:\n{traceback.format_exc()}")
                    auth_logger.error(f"MEDIA_INFO_FAILED | PK: {media_pk} | Error: {error_msg}")
                    return False, f"Failed to get media info: {error_msg}"
            
            # Determine correct folder based on media type
            logger.info("=== Folder Routing Based on Media Type ===")
            if media_info.media_type == 2:  # Video/Reel
                target_folder = self.config.VIDEO_FOLDER
                logger.info(f"Media type 2 (Video/Reel) - routing to VIDEO_FOLDER: {target_folder}")
            else:  # Image/Photo (Type 1) or other
                target_folder = self.config.INPUT_FOLDER  
                logger.info(f"Media type {media_info.media_type} (Image/Photo) - routing to INPUT_FOLDER: {target_folder}")
            
            # Use override folder if specified, otherwise use automatic routing
            if download_folder:
                folder_path = Path(download_folder)
                logger.info(f"Using override folder: {download_folder}")
            else:
                folder_path = Path(target_folder)
                logger.info(f"Using automatic routing to: {target_folder}")
            
            folder_path.mkdir(exist_ok=True)
            
            # Generate safe filename using media PK
            safe_filename = f"instagram_{media_pk}"
            
            # Enhanced download workflow with fallback support
            if use_fallback:
                logger.info("=== Using Fallback Download Method ===")
                logger.info("Bypassing normal download workflow due to ValidationError")
                
                # Use direct download with minimal media info
                success, message, download_path = self._fallback_download_direct(
                    media_pk, media_info.media_type, folder_path
                )
                
                if not success:
                    logger.error(f"Fallback download failed: {message}")
                    return False, f"Fallback download failed: {message}"
                
                logger.info(f"✅ Fallback download successful: {download_path}")
                
            else:
                # Normal download workflow based on content type
                if media_info.media_type == 2:  # Video/Reel
                    logger.info(f"Downloading video content for PK {media_pk}")
                    download_path = folder_path / f"{safe_filename}.mp4"
                    
                    try:
                        # Use retry logic for video download with timeout handling
                        def video_download_func():
                            return self.client.video_download(media_pk, str(folder_path))
                        
                        downloaded_file = self._retry_download_with_backoff(video_download_func)
                        logger.info(f"Video download completed: {downloaded_file}")
                        
                        # Handle file renaming if needed
                        if downloaded_file and Path(downloaded_file).exists():
                            final_path = folder_path / f"{safe_filename}.mp4"
                            if str(downloaded_file) != str(final_path):
                                Path(downloaded_file).rename(final_path)
                            download_path = final_path
                        else:
                            # Fallback: look for downloaded files with PK in name
                            downloaded_files = list(folder_path.glob(f"*{media_pk}*"))
                            if downloaded_files:
                                downloaded_files[0].rename(download_path)
                            else:
                                return False, "Video download completed but file not found"
                        
                    except Exception as download_error:
                        error_msg = f"Video download failed: {str(download_error)}"
                        logger.error(error_msg)
                        return False, error_msg
                    
                else:  # Image/Photo
                    logger.info(f"Downloading image content for PK {media_pk}")
                    download_path = folder_path / f"{safe_filename}.jpg"
                    
                    try:
                        # Use retry logic for photo download with timeout handling
                        def photo_download_func():
                            return self.client.photo_download(media_pk, str(folder_path))
                        
                        downloaded_file = self._retry_download_with_backoff(photo_download_func)
                        logger.info(f"Photo download completed: {downloaded_file}")
                        
                        # Handle file renaming if needed
                        if downloaded_file and Path(downloaded_file).exists():
                            final_path = folder_path / f"{safe_filename}.jpg"
                            if str(downloaded_file) != str(final_path):
                                Path(downloaded_file).rename(final_path)
                            download_path = final_path
                        else:
                            # Fallback: look for downloaded files with PK in name
                            downloaded_files = list(folder_path.glob(f"*{media_pk}*"))
                            if downloaded_files:
                                # Rename to jpg extension
                                downloaded_files[0].rename(download_path)
                            else:
                                return False, "Photo download completed but file not found"
                                
                    except Exception as download_error:
                        error_msg = f"Photo download failed: {str(download_error)}"
                        logger.error(error_msg)
                        return False, error_msg
            
            # Verify successful download
            if download_path.exists():
                file_size = download_path.stat().st_size
                auth_logger.info(f"INSTAGRAM_DOWNLOAD_SUCCESS | {url} -> {download_path.name} ({file_size} bytes)")
                logger.info(f"Successfully downloaded: {download_path.name} ({file_size} bytes)")
                
                # Post-download metadata detection for fallback cases
                if use_fallback:
                    logger.info("=== Post-Download Metadata Detection (Fallback) ===")
                    enhanced_metadata = self._detect_post_download_metadata(download_path, media_info)
                    
                    if enhanced_metadata:
                        logger.info("Enhanced metadata detected via post-download analysis")
                        # Update media_info with detected metadata
                        for key, value in enhanced_metadata.items():
                            setattr(media_info, key, value)
                        auth_logger.info(f"POST_DOWNLOAD_METADATA_ENHANCED | {download_path.name} | {enhanced_metadata}")
                
                # Trigger automatic content processing
                logger.info("=== Triggering Automatic Content Processing ===")
                self._trigger_content_processing(download_path, url, media_info)
                
                return True, f"Downloaded: {download_path.name}"
            else:
                logger.error(f"Download completed but file not found at: {download_path}")
                return False, "Download failed - file not found at expected location"
                
        except Exception as e:
            error_msg = str(e)
            auth_logger.error(f"INSTAGRAM_DOWNLOAD_FAILED | {url} | {error_msg}")
            logger.error(f"Instagram download failed: {error_msg}")
            
            if "not found" in error_msg.lower():
                return False, "Content not found or private"
            elif "rate limit" in error_msg.lower():
                return False, "Rate limited. Please try again later."
            else:
                return False, f"Download failed: {error_msg}"
    
    def _create_minimal_media_info(self, media_pk: str, url: str):
        """Create minimal media_info object for fallback when ValidationError occurs"""
        try:
            logger.info("=== Creating Minimal Media Info (Fallback) ===")
            logger.info(f"Media PK: {media_pk}")
            logger.info(f"Source URL: {url}")
            
            # Try to determine media type from URL pattern or direct API calls
            media_type = self._detect_media_type_fallback(media_pk, url)
            logger.info(f"Detected media type: {media_type}")
            
            # Create a minimal media_info-like object with essential fields
            class MinimalMediaInfo:
                def __init__(self, media_pk, media_type, url):
                    self.pk = media_pk
                    self.id = media_pk
                    self.media_type = media_type  # 1=image, 2=video
                    self.code = self._extract_code_from_url(url)
                    self.user = None  # Will be populated if needed
                    self.is_fallback = True  # Flag to indicate this is fallback mode
                    
                def _extract_code_from_url(self, url):
                    """Extract shortcode from Instagram URL"""
                    import re
                    patterns = [
                        r'/p/([A-Za-z0-9_-]+)/',
                        r'/reel/([A-Za-z0-9_-]+)/',
                        r'/reels/([A-Za-z0-9_-]+)/'
                    ]
                    for pattern in patterns:
                        match = re.search(pattern, url)
                        if match:
                            return match.group(1)
                    return "unknown"
            
            minimal_info = MinimalMediaInfo(media_pk, media_type, url)
            logger.info(f"✅ Minimal media info created with type {media_type}")
            auth_logger.info(f"MINIMAL_MEDIA_INFO_CREATED | PK: {media_pk} | Type: {media_type}")
            
            return minimal_info
            
        except Exception as e:
            logger.error(f"Failed to create minimal media info: {e}")
            auth_logger.error(f"MINIMAL_MEDIA_INFO_CREATION_FAILED | PK: {media_pk} | Error: {str(e)}")
            return None
    
    def _detect_media_type_fallback(self, media_pk: str, url: str) -> int:
        """Detect media type when metadata parsing fails"""
        try:
            logger.info("=== Media Type Detection (Fallback) ===")
            
            # Method 1: URL pattern analysis
            if '/reel/' in url or '/reels/' in url:
                logger.info("URL contains '/reel/' or '/reels/' - detected as video (type 2)")
                return 2  # Video
            elif '/p/' in url:
                logger.info("URL contains '/p/' - could be image or video, defaulting to video (type 2)")
                # Posts can be either images or videos, default to video for safer processing
                return 2  # Video (safer default for mixed content)
            
            # Method 2: Try direct download to determine file type
            logger.info("Attempting direct download probe to determine media type...")
            try:
                # Try video download first (most common case for problematic content)
                temp_path = Path(self.config.TEMP_FOLDER) / f"probe_{media_pk}"
                temp_path.mkdir(exist_ok=True)
                
                try:
                    video_result = self.client.video_download(media_pk, str(temp_path))
                    if video_result and Path(video_result).exists():
                        logger.info("Video download successful - detected as video (type 2)")
                        # Clean up probe file
                        Path(video_result).unlink(missing_ok=True)
                        return 2  # Video
                except:
                    logger.info("Video download failed - trying photo download...")
                
                try:
                    photo_result = self.client.photo_download(media_pk, str(temp_path))
                    if photo_result and Path(photo_result).exists():
                        logger.info("Photo download successful - detected as image (type 1)")
                        # Clean up probe file
                        Path(photo_result).unlink(missing_ok=True)
                        return 1  # Image
                except:
                    logger.info("Photo download also failed")
                
                # Clean up temp directory
                temp_path.rmdir()
                
            except Exception as probe_error:
                logger.warning(f"Download probe failed: {probe_error}")
            
            # Method 3: Default fallback based on common patterns
            logger.info("Using default fallback: assuming video content (type 2)")
            logger.info("Reasoning: ValidationErrors commonly occur with video content containing audio metadata issues")
            return 2  # Default to video since ValidationErrors often occur with reels/videos
            
        except Exception as e:
            logger.error(f"Media type detection failed: {e}")
            logger.info("Final fallback: defaulting to video (type 2)")
            return 2  # Final fallback
    
    def _fallback_download_direct(self, media_pk: str, media_type: int, folder_path: Path) -> Tuple[bool, str, Path]:
        """Direct download using media_pk when metadata parsing fails - bypasses instagrapi download methods entirely"""
        try:
            logger.info("=== Fallback Direct Download (Raw API) ===")
            logger.info(f"Media PK: {media_pk}")
            logger.info(f"Media Type: {media_type}")
            logger.info(f"Target Folder: {folder_path}")
            logger.info("CRITICAL: Bypassing instagrapi download methods to avoid ValidationError")
            
            safe_filename = f"instagram_{media_pk}"
            
            # Get raw media data directly from Instagram API without parsing
            logger.info("Fetching raw media data from Instagram API...")
            raw_media_data = self._get_raw_media_data(media_pk)
            
            if not raw_media_data:
                return False, "Failed to fetch raw media data", None
            
            # Extract ALL possible download URLs from raw data
            download_urls = self._extract_all_download_urls_from_raw_data(raw_media_data, media_type)
            
            if not download_urls:
                return False, "Could not extract any download URLs from raw data", None
            
            logger.info(f"Extracted {len(download_urls)} potential download URLs")
            for i, url in enumerate(download_urls):
                logger.info(f"URL {i+1}: {url}")  # Log complete URLs for debugging
            
            # Set up file path
            if media_type == 2:  # Video
                download_path = folder_path / f"{safe_filename}.mp4"
                logger.info("Attempting video download via multiple URL fallbacks...")
            else:  # Image
                download_path = folder_path / f"{safe_filename}.jpg"
                logger.info("Attempting image download via multiple URL fallbacks...")
            
            # Try each URL immediately (minimize time between extraction and download)
            success = self._download_with_url_fallbacks(download_urls, download_path)
            
            if success and download_path.exists():
                logger.info(f"✅ Raw API fallback download successful: {download_path.name}")
                return True, f"Downloaded via raw API fallback: {download_path.name}", download_path
            else:
                logger.error("Raw API download failed - file not created")
                return False, "Raw API download failed", None
                    
        except Exception as e:
            logger.error(f"Fallback download failed: {e}")
            return False, f"Fallback download error: {str(e)}", None
    
    def _get_raw_media_data(self, media_pk: str) -> dict:
        """Get raw media data from Instagram API without Pydantic parsing"""
        try:
            logger.info(f"Making raw API call for media PK: {media_pk}")
            
            # Use the same API endpoint but handle response manually
            url = f"https://i.instagram.com/api/v1/media/{media_pk}/info/"
            
            # Use client's session to maintain authentication
            response = self.client.private.get(url)
            
            if response.status_code == 200:
                raw_data = response.json()
                logger.info("✅ Raw media data retrieved successfully")
                logger.info(f"Response contains {len(raw_data.get('items', []))} media items")
                return raw_data
            else:
                logger.error(f"API request failed: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Raw media data fetch failed: {e}")
            return None
    
    def _extract_all_download_urls_from_raw_data(self, raw_data: dict, media_type: int) -> list:
        """Extract ALL possible download URLs from raw Instagram API response for maximum fallback options"""
        try:
            logger.info("Extracting ALL download URLs from raw media data...")
            
            items = raw_data.get("items", [])
            if not items:
                logger.error("No media items found in raw data")
                return []
            
            media_item = items[0]  # Get first (primary) media item
            all_urls = []
            
            if media_type == 2:  # Video
                logger.info("Extracting video URLs from all possible sources...")
                
                # Primary video versions (all qualities)
                video_versions = media_item.get("video_versions", [])
                for i, version in enumerate(video_versions):
                    url = version.get("url")
                    if url:
                        width = version.get("width", "unknown")
                        height = version.get("height", "unknown")
                        logger.info(f"Video URL {i+1}: {width}x{height} quality - {url}")
                        all_urls.append(url)
                
                # Additional video format checks
                if "video_dash_manifest" in media_item:
                    logger.info("DASH manifest found - may contain additional video formats")
                
                # Carousel media videos
                carousel_media = media_item.get("carousel_media", [])
                for j, carousel_item in enumerate(carousel_media):
                    if carousel_item.get("media_type") == 2:  # Video in carousel
                        carousel_videos = carousel_item.get("video_versions", [])
                        for i, version in enumerate(carousel_videos):
                            url = version.get("url")
                            if url and url not in all_urls:  # Avoid duplicates
                                width = version.get("width", "unknown")
                                height = version.get("height", "unknown")
                                logger.info(f"Carousel video URL {j+1}.{i+1}: {width}x{height} - {url}")
                                all_urls.append(url)
                                
            else:  # Image
                logger.info("Extracting image URLs from all possible sources...")
                
                # Primary image versions (all qualities)
                image_versions = media_item.get("image_versions2", {}).get("candidates", [])
                for i, version in enumerate(image_versions):
                    url = version.get("url")
                    if url:
                        width = version.get("width", "unknown")
                        height = version.get("height", "unknown")
                        logger.info(f"Image URL {i+1}: {width}x{height} quality - {url}")
                        all_urls.append(url)
                        
                # Carousel media images
                carousel_media = media_item.get("carousel_media", [])
                for j, carousel_item in enumerate(carousel_media):
                    if carousel_item.get("media_type") == 1:  # Image in carousel
                        carousel_images = carousel_item.get("image_versions2", {}).get("candidates", [])
                        for i, version in enumerate(carousel_images):
                            url = version.get("url")
                            if url and url not in all_urls:  # Avoid duplicates
                                width = version.get("width", "unknown")
                                height = version.get("height", "unknown")
                                logger.info(f"Carousel image URL {j+1}.{i+1}: {width}x{height} - {url}")
                                all_urls.append(url)
            
            logger.info(f"Total URLs extracted: {len(all_urls)} for media type {media_type}")
            
            if not all_urls:
                logger.error(f"No download URLs found for media type {media_type}")
                # Log raw data structure for debugging
                logger.error("Raw data structure for debugging:")
                import json
                logger.error(json.dumps(media_item, indent=2)[:2000] + "..." if len(str(media_item)) > 2000 else json.dumps(media_item, indent=2))
            
            return all_urls
            
        except Exception as e:
            logger.error(f"Download URL extraction failed: {e}")
            import traceback
            logger.error(f"Extraction error traceback:\n{traceback.format_exc()}")
            return []
    
    def _download_with_url_fallbacks(self, urls: list, file_path: Path) -> bool:
        """Try downloading from multiple URLs with immediate attempts to minimize timing issues"""
        try:
            logger.info(f"=== Multi-URL Download Fallback System ===")
            logger.info(f"Attempting download with {len(urls)} URL options")
            
            for i, url in enumerate(urls):
                attempt_num = i + 1
                logger.info(f"--- Download Attempt {attempt_num}/{len(urls)} ---")
                logger.info(f"Trying URL: {url}")
                
                try:
                    # Immediate download attempt to minimize URL expiration
                    success = self._download_file_direct_http(url, file_path)
                    
                    if success:
                        logger.info(f"✅ Download successful on URL attempt {attempt_num}")
                        return True
                    else:
                        logger.warning(f"❌ URL attempt {attempt_num} failed, trying next URL...")
                        
                except Exception as e:
                    logger.warning(f"❌ URL attempt {attempt_num} error: {e}")
                    continue
            
            logger.error(f"❌ All {len(urls)} URL attempts failed")
            return False
            
        except Exception as e:
            logger.error(f"Multi-URL download system failed: {e}")
            return False
    
    def _download_file_direct_http(self, url: str, file_path: Path) -> bool:
        """Download file directly via HTTP requests with full Instagram session authentication"""
        try:
            logger.info(f"Starting authenticated CDN download to: {file_path.name}")
            logger.info(f"CDN URL: {url[:80]}...")
            
            # Use the client's authenticated session directly for CDN access
            session = self.client.private  # This contains all cookies and auth state
            
            # Prepare comprehensive headers for Instagram CDN
            headers = {
                "User-Agent": session.headers.get("User-Agent", ""),
                "Accept": "*/*",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept-Language": "en-US,en;q=0.9",
                "Connection": "keep-alive",
                "Referer": "https://www.instagram.com/",
                "Sec-Fetch-Dest": "video",
                "Sec-Fetch-Mode": "cors", 
                "Sec-Fetch-Site": "cross-site",
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"'
            }
            
            # Add Instagram-specific headers if available
            if "X-IG-App-ID" in session.headers:
                headers["X-IG-App-ID"] = session.headers["X-IG-App-ID"]
            if "X-Instagram-AJAX" in session.headers:
                headers["X-Instagram-AJAX"] = session.headers["X-Instagram-AJAX"]
            if "X-CSRFToken" in session.headers:
                headers["X-CSRFToken"] = session.headers["X-CSRFToken"]
            
            # Remove empty headers
            headers = {k: v for k, v in headers.items() if v}
            
            logger.info(f"Using {len(headers)} CDN authentication headers")
            logger.info(f"Session cookies: {len(session.cookies)} cookies available")
            
            # First attempt: Direct download with full session
            logger.info("Attempt 1: Direct CDN download with session authentication...")
            response = session.get(url, headers=headers, stream=True, timeout=30)
            
            if response.status_code == 200:
                return self._write_downloaded_file(response, file_path)
            
            elif response.status_code == 404:
                logger.warning("CDN URL returned 404 - attempting URL refresh...")
                return self._retry_with_fresh_url(url, file_path, headers)
            
            elif response.status_code == 403:
                logger.warning("CDN access forbidden - attempting enhanced authentication...")
                return self._retry_with_enhanced_auth(url, file_path)
            
            else:
                logger.error(f"CDN download failed: {response.status_code} - {response.text[:200]}")
                return False
                
        except Exception as e:
            logger.error(f"Authenticated CDN download failed: {e}")
            return False
    
    def _write_downloaded_file(self, response, file_path: Path) -> bool:
        """Write streaming response to file"""
        try:
            # Create parent directory if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file in chunks
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            file_size = file_path.stat().st_size
            logger.info(f"✅ CDN download complete: {file_size} bytes written to {file_path.name}")
            return True
            
        except Exception as e:
            logger.error(f"File writing failed: {e}")
            return False
    
    def _retry_with_fresh_url(self, original_url: str, file_path: Path, headers: dict) -> bool:
        """Retry download with fresh CDN URL when original expires"""
        try:
            logger.info("=== CDN URL Refresh Retry ===")
            logger.info("Original CDN URL may be expired - fetching fresh media data...")
            
            # Extract media PK from file path to refresh URL
            filename = file_path.stem
            if "instagram_" in filename:
                media_pk = filename.replace("instagram_", "")
                logger.info(f"Refreshing URL for media PK: {media_pk}")
                
                # Get fresh raw media data
                fresh_data = self._get_raw_media_data(media_pk)
                if fresh_data:
                    # Extract new download URLs
                    media_type = 2 if file_path.suffix == '.mp4' else 1
                    fresh_urls = self._extract_all_download_urls_from_raw_data(fresh_data, media_type)
                    
                    if fresh_urls:
                        logger.info(f"Fresh CDN URLs obtained: {len(fresh_urls)} URLs")
                        
                        # Try each fresh URL
                        for i, fresh_url in enumerate(fresh_urls):
                            if fresh_url != original_url:  # Skip if same as original
                                logger.info(f"Trying fresh URL {i+1}: {fresh_url[:80]}...")
                                response = self.client.private.get(fresh_url, headers=headers, stream=True, timeout=30)
                                if response.status_code == 200:
                                    logger.info("✅ Fresh URL download successful")
                                    return self._write_downloaded_file(response, file_path)
                                else:
                                    logger.warning(f"Fresh URL {i+1} failed: {response.status_code}")
                        
                        logger.error("All fresh URLs also failed")
                    else:
                        logger.warning("Could not obtain any fresh CDN URLs")
                else:
                    logger.error("Failed to fetch fresh media data")
            
            return False
            
        except Exception as e:
            logger.error(f"URL refresh retry failed: {e}")
            return False
    
    def _retry_with_enhanced_auth(self, url: str, file_path: Path) -> bool:
        """Retry download with enhanced authentication for 403 errors"""
        try:
            logger.info("=== Enhanced Authentication Retry ===")
            logger.info("CDN returned 403 - attempting enhanced session authentication...")
            
            session = self.client.private
            
            # Get a fresh Instagram session token if possible
            try:
                # Make a lightweight request to refresh session state
                session.get("https://www.instagram.com/", timeout=10)
                logger.info("Session state refreshed")
            except:
                logger.warning("Could not refresh session state")
            
            # Enhanced headers with all possible Instagram authentication
            enhanced_headers = {
                "User-Agent": session.headers.get("User-Agent", ""),
                "Accept": "*/*",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept-Language": "en-US,en;q=0.9",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "DNT": "1",
                "Origin": "https://www.instagram.com",
                "Referer": "https://www.instagram.com/",
                "Sec-Fetch-Dest": "video",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "cross-site",
                "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"'
            }
            
            # Add all available Instagram headers
            for header_name in ["X-IG-App-ID", "X-Instagram-AJAX", "X-CSRFToken", "X-Requested-With"]:
                if header_name in session.headers:
                    enhanced_headers[header_name] = session.headers[header_name]
            
            logger.info(f"Enhanced authentication: {len(enhanced_headers)} headers, {len(session.cookies)} cookies")
            
            # Retry with enhanced authentication
            response = session.get(url, headers=enhanced_headers, stream=True, timeout=30)
            
            if response.status_code == 200:
                logger.info("✅ Enhanced authentication successful")
                return self._write_downloaded_file(response, file_path)
            else:
                logger.error(f"Enhanced authentication also failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Enhanced authentication retry failed: {e}")
            return False

    def _detect_post_download_metadata(self, file_path: Path, media_info) -> Dict:
        """Detect metadata from downloaded file when original parsing failed"""
        try:
            logger.info("=== Post-Download Metadata Analysis ===")
            logger.info(f"Analyzing file: {file_path.name}")
            
            metadata = {}
            file_ext = file_path.suffix.lower()
            
            # Basic file properties
            file_stats = file_path.stat()
            metadata['file_size'] = file_stats.st_size
            metadata['file_extension'] = file_ext
            
            if file_ext in ['.mp4', '.mov', '.avi', '.mkv']:  # Video files
                logger.info("Analyzing video file properties...")
                video_metadata = self._analyze_video_metadata(file_path)
                metadata.update(video_metadata)
                
                # Audio detection using faster-whisper
                audio_metadata = self._detect_audio_content(file_path)
                metadata.update(audio_metadata)
                
                # Frame-based OCR for subtitle detection
                ocr_metadata = self._detect_video_text_content(file_path)
                metadata.update(ocr_metadata)
                
            elif file_ext in ['.jpg', '.jpeg', '.png', '.webp']:  # Image files
                logger.info("Analyzing image file properties...")
                image_metadata = self._analyze_image_metadata(file_path)
                metadata.update(image_metadata)
                
                # OCR text detection
                ocr_metadata = self._detect_image_text_content(file_path)
                metadata.update(ocr_metadata)
            
            logger.info(f"Post-download metadata detection complete: {len(metadata)} properties found")
            return metadata
            
        except Exception as e:
            logger.error(f"Post-download metadata detection failed: {e}")
            return {}
    
    def _analyze_video_metadata(self, file_path: Path) -> Dict:
        """Analyze video file properties using OpenCV or ffmpeg"""
        try:
            import cv2
            metadata = {}
            
            cap = cv2.VideoCapture(str(file_path))
            if cap.isOpened():
                # Get video properties
                fps = cap.get(cv2.CAP_PROP_FPS)
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                duration = frame_count / fps if fps > 0 else 0
                
                metadata.update({
                    'video_fps': fps,
                    'video_frame_count': frame_count,
                    'video_width': width,
                    'video_height': height,
                    'video_duration_seconds': duration,
                    'video_resolution': f"{width}x{height}"
                })
                
                logger.info(f"Video properties: {width}x{height}, {fps}fps, {duration:.2f}s")
                cap.release()
            
            return metadata
        except Exception as e:
            logger.warning(f"Video metadata analysis failed: {e}")
            return {}
    
    def _detect_audio_content(self, file_path: Path) -> Dict:
        """Detect audio content using faster-whisper for transcription"""
        try:
            metadata = {}
            
            # Check if faster-whisper is available
            try:
                from faster_whisper import WhisperModel
                
                logger.info("Attempting audio transcription with faster-whisper...")
                model = WhisperModel("tiny", device="cpu")  # Use tiny model for speed
                
                # Attempt transcription
                segments, info = model.transcribe(str(file_path))
                
                # Extract transcription results
                transcript_segments = []
                total_duration = 0
                
                for segment in segments:
                    transcript_segments.append({
                        'start': segment.start,
                        'end': segment.end,
                        'text': segment.text.strip()
                    })
                    total_duration = max(total_duration, segment.end)
                
                if transcript_segments:
                    full_transcript = " ".join([seg['text'] for seg in transcript_segments])
                    
                    metadata.update({
                        'has_audio': True,
                        'audio_transcript': full_transcript,
                        'audio_duration': total_duration,
                        'audio_language': info.language,
                        'audio_confidence': info.language_probability,
                        'transcript_segments': transcript_segments
                    })
                    
                    logger.info(f"Audio detected: {info.language} ({info.language_probability:.2f} confidence)")
                    logger.info(f"Transcript preview: {full_transcript[:100]}...")
                else:
                    metadata['has_audio'] = False
                    logger.info("No transcribable audio content detected")
                    
            except ImportError:
                logger.warning("faster-whisper not available - skipping audio analysis")
                metadata['audio_analysis_skipped'] = "faster-whisper not installed"
            
            return metadata
        except Exception as e:
            logger.warning(f"Audio content detection failed: {e}")
            return {'audio_analysis_failed': str(e)}
    
    def _detect_video_text_content(self, file_path: Path) -> Dict:
        """Extract text from video frames using OCR"""
        try:
            import cv2
            metadata = {}
            
            cap = cv2.VideoCapture(str(file_path))
            if not cap.isOpened():
                return {}
            
            # Sample frames at regular intervals
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            sample_frames = min(5, frame_count)  # Sample up to 5 frames
            frame_interval = max(1, frame_count // sample_frames)
            
            extracted_texts = []
            
            for i in range(0, frame_count, frame_interval):
                cap.set(cv2.CAP_PROP_POS_FRAMES, i)
                ret, frame = cap.read()
                
                if ret:
                    # Save frame temporarily for OCR
                    temp_frame_path = Path(self.config.TEMP_FOLDER) / f"frame_{i}.jpg"
                    cv2.imwrite(str(temp_frame_path), frame)
                    
                    # Extract text using existing OCR processor
                    try:
                        if hasattr(self, 'ocr_processor'):
                            text = self.ocr_processor.extract_text_with_ocr(str(temp_frame_path))
                            if text and text.strip():
                                extracted_texts.append({
                                    'frame_number': i,
                                    'timestamp': i / cap.get(cv2.CAP_PROP_FPS),
                                    'text': text.strip()
                                })
                    except:
                        pass
                    
                    # Clean up temp file
                    temp_frame_path.unlink(missing_ok=True)
            
            cap.release()
            
            if extracted_texts:
                all_text = " ".join([item['text'] for item in extracted_texts])
                metadata.update({
                    'has_video_text': True,
                    'video_text_content': all_text,
                    'video_text_frames': extracted_texts
                })
                logger.info(f"Video text detected in {len(extracted_texts)} frames")
            else:
                metadata['has_video_text'] = False
                logger.info("No text content detected in video frames")
            
            return metadata
        except Exception as e:
            logger.warning(f"Video text content detection failed: {e}")
            return {}
    
    def _analyze_image_metadata(self, file_path: Path) -> Dict:
        """Analyze image file properties"""
        try:
            from PIL import Image
            metadata = {}
            
            with Image.open(file_path) as img:
                metadata.update({
                    'image_width': img.width,
                    'image_height': img.height,
                    'image_mode': img.mode,
                    'image_format': img.format,
                    'image_resolution': f"{img.width}x{img.height}"
                })
                
                # Extract EXIF data if available
                if hasattr(img, '_getexif') and img._getexif():
                    exif_data = img._getexif()
                    if exif_data:
                        metadata['has_exif'] = True
                        metadata['exif_keys'] = list(exif_data.keys())
                else:
                    metadata['has_exif'] = False
            
            logger.info(f"Image properties: {metadata['image_resolution']}, {metadata['image_mode']}")
            return metadata
        except Exception as e:
            logger.warning(f"Image metadata analysis failed: {e}")
            return {}
    
    def _detect_image_text_content(self, file_path: Path) -> Dict:
        """Extract text from image using OCR"""
        try:
            metadata = {}
            
            # Use existing OCR processor if available
            if hasattr(self, 'ocr_processor'):
                text = self.ocr_processor.extract_text_with_ocr(str(file_path))
                if text and text.strip():
                    metadata.update({
                        'has_image_text': True,
                        'image_text_content': text.strip()
                    })
                    logger.info(f"Image text detected: {text[:50]}...")
                else:
                    metadata['has_image_text'] = False
                    logger.info("No text content detected in image")
            else:
                metadata['ocr_analysis_skipped'] = "OCR processor not available"
            
            return metadata
        except Exception as e:
            logger.warning(f"Image text content detection failed: {e}")
            return {}

    def _trigger_content_processing(self, file_path: Path, source_url: str, media_info):
        """Trigger automatic content processing for downloaded Instagram content (non-blocking)"""
        try:
            # Create processing flag immediately (synchronous, fast operation)
            processing_flag = {
                "file_path": str(file_path),
                "source": "instagram_download",
                "source_url": source_url,
                "media_pk": getattr(media_info, 'pk', None),
                "media_type": media_info.media_type,
                "download_timestamp": datetime.now().isoformat(),
                "processed": False
            }
            
            # Save processing flag for main processor to pick up
            flag_file = file_path.parent / f".processing_{file_path.stem}.json"
            with open(flag_file, 'w') as f:
                json.dump(processing_flag, f, indent=2)
            
            logger.info(f"✅ Processing flag created: {flag_file}")
            auth_logger.info(f"CONTENT_PROCESSING_QUEUED | File: {file_path.name}")
            
        except Exception as e:
            logger.error(f"❌ Content processing queue failed: {e}")
            auth_logger.error(f"CONTENT_PROCESSING_QUEUE_FAILED | File: {file_path.name} | Error: {str(e)}")

class LocalServer:
    """Flask HTTP server for browser extension communication"""
    
    def __init__(self, config, instagram_downloader):
        self.config = config
        self.instagram_downloader = instagram_downloader
        self.app = Flask(__name__)
        CORS(self.app)
        self.setup_routes()
        self.server_thread = None
        
    def setup_routes(self):
        """Setup Flask routes for browser extension API"""
        
        @self.app.route('/health', methods=['GET'])
        def health_check():
            """Health check endpoint for browser extension"""
            return jsonify({
                "status": "healthy",
                "service": "InsightMiner LocalServer",
                "timestamp": datetime.now().isoformat()
            })
        
        @self.app.route('/status', methods=['GET'])
        def instagram_status():
            """Get Instagram session status"""
            if not self.instagram_downloader or not self.instagram_downloader.client:
                return jsonify({
                    "success": False,
                    "message": "Instagram downloader not available"
                })
            
            status = self.instagram_downloader.get_session_status()
            return jsonify({
                "success": True,
                "instagram_status": status
            })
        
        @self.app.route('/download', methods=['POST'])
        def download_content():
            """Download Instagram content from browser extension"""
            try:
                data = request.get_json()
                if not data or 'url' not in data:
                    return jsonify({
                        "success": False,
                        "message": "Missing URL in request"
                    }), 400
                
                url = data['url']
                content_type = data.get('type', 'auto')
                
                # Validate Instagram URL
                if not self.instagram_downloader._validate_instagram_url(url):
                    return jsonify({
                        "success": False,
                        "message": "Invalid Instagram URL"
                    }), 400
                
                # Use automatic folder routing based on media type detection
                # No need to manually determine folder - let download_single_reel handle it
                success, message = self.instagram_downloader.download_single_reel(url)
                
                if success:
                    return jsonify({
                        "success": True,
                        "message": message,
                        "folder": "auto-routed"
                    })
                else:
                    return jsonify({
                        "success": False,
                        "message": message
                    }), 500
                    
            except Exception as e:
                logger.error(f"Download endpoint error: {e}")
                return jsonify({
                    "success": False,
                    "message": f"Server error: {str(e)}"
                }), 500
    
    def start_server(self, port=8502):
        """Start Flask server in background thread and trigger backup"""
        def run_server():
            try:
                # Trigger backup on server startup
                logger.info("Triggering incremental backup on server startup...")
                trigger_startup_backup()
                
                # Start Flask server
                self.app.run(host='127.0.0.1', port=port, debug=False, use_reloader=False)
            except Exception as e:
                logger.error(f"LocalServer failed to start: {e}")
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        logger.info(f"LocalServer started on http://127.0.0.1:{port}")
        logger.info("Incremental backup system activated")
    
    def is_running(self) -> bool:
        """Check if server thread is running"""
        return self.server_thread and self.server_thread.is_alive()

class VideoProcessor:
    """Handle video processing and frame extraction"""
    
    def __init__(self, config: Config):
        self.config = config
    
    def extract_frames_from_video(self, video_path: str) -> List[str]:
        """Extract frames from video at specified intervals"""
        try:
            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps == 0:  # Handle cases where FPS is not available
                fps = 30 
            frame_interval = int(fps * self.config.FRAME_EXTRACTION_INTERVAL)
            if frame_interval == 0: # Ensure interval is at least 1
                frame_interval = 1

            frames = []
            frame_count = 0
            extracted_count = 0
            
            while cap.isOpened() and extracted_count < self.config.MAX_FRAMES_PER_VIDEO:
                ret, frame = cap.read()
                if not ret:
                    break
                
                if frame_count % frame_interval == 0:
                    # Save frame as image
                    frame_filename = f"frame_{extracted_count:03d}_{os.path.basename(video_path)}.jpg"
                    frame_path = os.path.join(self.config.TEMP_FOLDER, frame_filename)
                    
                    cv2.imwrite(frame_path, frame)
                    frames.append(frame_path)
                    extracted_count += 1
                
                frame_count += 1
            
            cap.release()
            logger.info(f"Extracted {len(frames)} frames from {os.path.basename(video_path)}")
            return frames
            
        except Exception as e:
            logger.error(f"Frame extraction failed for {video_path}: {e}")
            return []

class OCRProcessor:
    """Handle OCR text extraction"""
    
    def __init__(self):
        self.instagram_patterns = [
            r'@\w+',  # Usernames
            r'\d+[kmb]?\s*(likes?|views?|comments?)',  # Like/view counts
            r'(share|save|like|comment|follow)',  # Action buttons
            r'\d+[hmd]\s*ago',  # Timestamps
            r'instagram\.com',  # Instagram URLs
            r'(story|reel|post|igtv)',  # Instagram content types
        ]
    
    def extract_text_with_ocr(self, image_path: str) -> str:
        """Extract text using OCR"""
        try:
            # Use pytesseract for OCR
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image, config='--psm 6')
            
            # Clean the text
            cleaned_text = self.clean_extracted_text(text)
            return cleaned_text
            
        except Exception as e:
            logger.error(f"OCR extraction failed for {image_path}: {e}")
            return ""
    
    def clean_extracted_text(self, text: str) -> str:
        """Remove Instagram UI elements and noise from OCR text"""
        if not text:
            return ""
        
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if len(line) < 3:  # Skip very short lines
                continue
            
            # Check if line matches Instagram UI patterns
            is_ui_element = False
            for pattern in self.instagram_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    is_ui_element = True
                    break
            
            if not is_ui_element:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)

# New class for handling audio transcription
class AudioProcessor:
    def __init__(self):
        try:
            from faster_whisper import WhisperModel
            # Using a small, efficient model for local processing
            self.model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
            logger.info("AudioProcessor initialized with tiny.en model.")
        except ImportError:
            self.model = None
            logger.warning("faster_whisper not installed. Audio transcription is disabled.")
        except Exception as e:
            self.model = None
            logger.error(f"Failed to load Whisper model: {e}")

    def transcribe_audio_from_video(self, video_path: str, temp_folder: str) -> str:
        if not self.model:
            return ""
        
        audio_path = Path(temp_folder) / f"temp_audio_{Path(video_path).stem}.mp3"
        
        try:
            # Use ffmpeg via subprocess to extract audio from the video file
            import subprocess
            command = [
                'ffmpeg', '-i', str(video_path), 
                '-q:a', '0', '-map', 'a', 
                str(audio_path), '-y'
            ]
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # Transcribe the extracted audio file using the pre-loaded model
            segments, info = self.model.transcribe(str(audio_path), beam_size=5)
            transcript = " ".join(segment.text for segment in segments)
            
            logger.info(f"Successfully transcribed audio from {Path(video_path).name}")
            return transcript.strip()

        except FileNotFoundError:
            logger.error("ffmpeg not found. Please install ffmpeg and ensure it is in your system's PATH.")
            return "Error: ffmpeg is not installed or not in system PATH."
        except subprocess.CalledProcessError as e:
            logger.error(f"ffmpeg failed to extract audio. It's possible the video has no audio track.")
            return ""
        except Exception as e:
            logger.error(f"Audio transcription failed: {e}")
            return ""
        finally:
            # Ensure the temporary audio file is always deleted
            if audio_path.exists():
                audio_path.unlink()

class ContentProcessor:
    """Orchestrates the entire content analysis pipeline."""
    
    def __init__(self, config: Config):
        self.config = config
        self.supabase: Optional[Client] = None
        self.video_processor = VideoProcessor(config)
        self.ocr_processor = OCRProcessor()
        self.audio_processor = AudioProcessor()
        self.image_hasher = ImageHasher()
        self.initialize()
    
    def initialize(self):
        """Initialize processor with error handling"""
        try:
            if self.config.is_configured():
                self.supabase = create_client(self.config.SUPABASE_URL, self.config.SUPABASE_KEY)
                auth_logger.info("SUPABASE_CONNECTION_ATTEMPT")
                self.test_connection()
            self.ensure_folders()
            logger.info("ContentProcessor initialized successfully")
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            auth_logger.error(f"INITIALIZATION_FAILED | {e}")
            st.error(f"Setup error: {e}")
    
    def test_connection(self):
        """Test Supabase connection"""
        try:
            self.supabase.table("content_items").select("id").limit(1).execute()
            logger.info("Supabase connection successful")
            auth_logger.info("SUPABASE_CONNECTION_SUCCESS")
        except Exception as e:
            logger.warning(f"Supabase connection test failed: {e}")
            auth_logger.error(f"SUPABASE_CONNECTION_FAILED | {e}")
            st.warning("⚠️ Database connection issue. Check your configuration.")
    
    def ensure_folders(self):
        """Create necessary folders"""
        try:
            Path(self.config.INPUT_FOLDER).mkdir(exist_ok=True)
            Path(self.config.VIDEO_FOLDER).mkdir(exist_ok=True)
            Path(self.config.TEMP_FOLDER).mkdir(exist_ok=True)
            logger.info("Folders created successfully")
        except Exception as e:
            logger.error(f"Error creating folders: {e}")
            st.error(f"Folder creation failed: {e}")

    def validate_file(self, file_path: Path) -> Tuple[bool, str]:
        """Validate image or video file"""
        try:
            file_ext = file_path.suffix.lower()
            if file_ext in self.config.SUPPORTED_IMAGE_FORMATS:
                file_type = "image"
            elif file_ext in self.config.SUPPORTED_VIDEO_FORMATS:
                file_type = "video"
            else:
                return False, "unsupported"
            
            max_size = 50 * 1024 * 1024 if file_type == "video" else 10 * 1024 * 1024
            if file_path.stat().st_size > max_size:
                return False, "too_large"
            
            if file_type == "image":
                with Image.open(file_path) as img:
                    img.verify()
            else:
                cap = cv2.VideoCapture(str(file_path))
                if not cap.isOpened():
                    return False, "corrupted"
                cap.release()
            
            return True, file_type
        except Exception as e:
            logger.error(f"File validation failed for {file_path.name}: {e}")
            return False, "corrupted"

    def compress_image(self, image_path: str) -> Optional[str]:
        """Compress image with error handling"""
        try:
            img = Image.open(image_path)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img.thumbnail(self.config.MAX_IMAGE_SIZE, Image.Resampling.LANCZOS)
            compressed_path = os.path.join(self.config.TEMP_FOLDER, f"compressed_{os.path.basename(image_path)}")
            img.save(compressed_path, 'JPEG', quality=self.config.JPEG_QUALITY, optimize=True)
            return compressed_path
        except Exception as e:
            logger.error(f"Image compression failed: {e}")
            return None
    
    def check_ollama_status(self) -> bool:
        """Check if Ollama is running and model is available"""
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [model['name'] for model in models]
                
                if any('llava' in name for name in model_names):
                    return True
                else:
                    st.error("❌ Ollama running but llava model not found. Run: `ollama pull llava`")
                    return False
            
        except requests.exceptions.RequestException:
            st.error("❌ Ollama not running. Please start Ollama service.")
            return False
        
        return False

    def analyze_content_hybrid(self, image_path: str, audio_transcript: str = "") -> Dict:
        """Hybrid analysis using OCR, Vision AI, and an audio transcript."""
        try:
            ocr_text = self.ocr_processor.extract_text_with_ocr(image_path)
            vision_analysis = self.analyze_with_ollama(image_path, ocr_text, audio_transcript)
            return self.combine_analysis_results(ocr_text, vision_analysis)
        except Exception as e:
            logger.error(f"Hybrid analysis failed: {e}")
            return self.create_error_analysis(f"Analysis failed: {str(e)}")
    
    def analyze_with_ollama(self, image_path: str, ocr_text: str = "", audio_transcript: str = "") -> Dict:
        """Enhanced vision analysis with OCR and audio transcript context."""
        try:
            with open(image_path, "rb") as img_file:
                img_base64 = base64.b64encode(img_file.read()).decode('utf-8')
            
            prompt = f"""
            You are analyzing content for valuable insights.
            
            OCR Text Found: "{ocr_text}"
            Audio Transcript: "{audio_transcript}"

            Analyze the image (if present), the extracted text, and the audio transcript to find:
            1. Educational content, tutorials, tips
            2. Business strategies, tools, resources
            3. Technical information, code snippets
            4. Health/fitness advice
            5. Important data, statistics, insights
            
            COMPLETELY IGNORE:
            - Social media usernames, handles, @mentions
            - Like counts, view counts, engagement metrics
            - UI buttons (follow, share, save, like)
            - Timestamps, "X hours ago" type text
            - Navigation elements, ads
            - Profile pictures, avatars
            
            Categorize as one of: {', '.join(self.config.CATEGORIES)}
            
            Respond with valid JSON only:
            {{
                "category": "category_name",
                "confidence": 0.85,
                "summary": "concise summary of valuable content only",
                "key_points": ["specific actionable insight 1", "specific insight 2"],
                "useful_content": "detailed valuable content without social media noise",
                "extracted_text": "cleaned text content",
                "has_code": false,
                "has_data": false,
                "actionable": true
            }}
            """
            
            payload = {
                "model": self.config.MODEL_NAME,
                "prompt": prompt,
                "images": [img_base64],
                "stream": False
            }
            
            response = requests.post(
                self.config.OLLAMA_URL, 
                json=payload, 
                timeout=self.config.REQUEST_TIMEOUT
            )
            
            if response.status_code == 200:
                result = response.json()
                response_text = result.get('response', '{}')
                
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                
                if start >= 0 and end > start:
                    json_text = response_text[start:end]
                    try:
                        parsed_result = json.loads(json_text)
                        return self.validate_and_enhance_analysis(parsed_result)
                    except json.JSONDecodeError:
                        return self.create_fallback_analysis(response_text)
                return self.create_fallback_analysis(response_text)
            else:
                return self.create_error_analysis("Vision AI request failed")
        except Exception as e:
            logger.error(f"Vision analysis error: {e}")
            return self.create_error_analysis(f"Analysis failed: {str(e)}")

    def validate_and_enhance_analysis(self, analysis: Dict) -> Dict:
        """Validate and enhance analysis results"""
        try:
            # Ensure required fields exist
            required_fields = ['category', 'confidence', 'summary', 'key_points', 'useful_content']
            for field in required_fields:
                if field not in analysis:
                    analysis[field] = ""
            
            # Validate category
            if analysis.get('category') not in self.config.CATEGORIES:
                analysis['category'] = "Mixed"
            
            # Apply confidence threshold logic
            confidence = float(analysis.get('confidence', 0))
            if confidence < self.config.CONFIDENCE_THRESHOLD:
                analysis['category'] = "Mixed"
            
            # Ensure key_points is a list
            if not isinstance(analysis.get('key_points'), list):
                analysis['key_points'] = [str(analysis.get('key_points'))] if analysis.get('key_points') else []
            
            # Add metadata
            analysis['processing_method'] = 'hybrid'
            analysis['processed_at'] = datetime.now().isoformat()
            
            return analysis
            
        except Exception as e:
            logger.error(f"Analysis validation failed: {e}")
            return self.create_fallback_analysis("Validation failed")
    
    def combine_analysis_results(self, ocr_text: str, vision_analysis: Dict) -> Dict:
        """Combine OCR and vision analysis results"""
        try:
            # Start with vision analysis
            combined = vision_analysis.copy()
            
            # Enhance with OCR text
            if ocr_text and len(ocr_text.strip()) > 10:
                combined['extracted_text'] = ocr_text
                
                # If vision analysis was poor but OCR found good text, upgrade
                if combined.get('confidence', 0) < 0.5 and len(ocr_text) > 100:
                    combined['confidence'] = min(0.7, combined.get('confidence', 0) + 0.2)
                    combined['useful_content'] = ocr_text[:500]
                    combined['summary'] = f"Text-based content: {ocr_text[:100]}..."
            
            return combined
            
        except Exception as e:
            logger.error(f"Analysis combination failed: {e}")
            return vision_analysis

    def create_fallback_analysis(self, text: str) -> Dict:
        """Create fallback analysis when parsing fails"""
        return {
            "category": "Mixed",
            "confidence": 0.3,
            "summary": text[:200] if text else "Could not extract summary",
            "key_points": [text[:100]] if text else ["No key points extracted"],
            "useful_content": text[:500] if text else "No content extracted",
            "processing_method": "fallback"
        }

    def create_error_analysis(self, error_msg: str) -> Dict:
        """Create error analysis result"""
        return {
            "category": "Error",
            "confidence": 0.0,
            "summary": error_msg,
            "key_points": [],
            "useful_content": "",
            "processing_method": "error"
        }

    def save_analysis_only(self, analysis: Dict, original_filename: str, file_type: str, image_hash: str) -> bool:
        """Save ONLY analysis data, including the audio transcript."""
        if not self.supabase: return False
        try:
            data = {
                "original_filename": original_filename,
                "image_hash": image_hash,
                "file_type": file_type,
                "category": analysis.get("category", "Mixed"),
                "confidence": float(analysis.get("confidence", 0.0)),
                "summary": analysis.get("summary", ""),
                "key_points": analysis.get("key_points", []),
                "useful_content": analysis.get("useful_content", ""),
                "extracted_text": analysis.get("extracted_text", ""),
                "processing_method": analysis.get("processing_method", "hybrid"),
                "audio_transcript": analysis.get("audio_transcript", ""),
                "frames_analyzed": analysis.get("frames_analyzed"),
                "processed_at": datetime.now().isoformat()
            }
            self.supabase.table("content_items").insert(data).execute()
            logger.info(f"Analysis saved for {original_filename}")
            return True
        except Exception as e:
            logger.error(f"Analysis save failed for {original_filename}: {e}")
            return False

    def process_single_file(self, file_path: Path) -> Tuple[bool, str]:
        """Process a single file with deduplication check"""
        try:
            is_valid, file_type = self.validate_file(file_path)
            if not is_valid:
                logger.warning(f"Invalid file rejected: {file_path.name} - {file_type}")
                return False, f"Invalid file: {file_type}"
            
            # Calculate image hash FIRST for deduplication
            image_hash = None # Initialize hash to None
            if file_type == "image":
                image_hash = self.image_hasher.calculate_image_hash(str(file_path))
                
                # Check for duplicate
                is_duplicate, existing_data = self.image_hasher.is_duplicate(image_hash)
                if is_duplicate:
                    self.image_hasher.increment_duplicate_count(image_hash)
                    os.remove(file_path)  # Delete duplicate immediately
                    return True, f"Duplicate detected - skipped (original: {existing_data.get('original_filename', 'unknown')})"
            
            if file_type == "video":
                return self.process_video(file_path)
            else:
                return self.process_image_with_hash(file_path, image_hash)
                
        except Exception as e:
            logger.error(f"File processing failed for {file_path.name}: {e}")
            return False, f"Processing error: {str(e)}"

    def process_video(self, video_path: Path) -> Tuple[bool, str]:
        """Process video by transcribing audio and analyzing frames."""
        try:
            audio_transcript = self.audio_processor.transcribe_audio_from_video(str(video_path), self.config.TEMP_FOLDER)
            frames = self.video_processor.extract_frames_from_video(str(video_path))
            all_analyses = []
            
            if not frames and not audio_transcript:
                return False, "No frames could be extracted and no audio was found."

            for frame_path in frames:
                try:
                    compressed_frame = self.compress_image(frame_path)
                    if compressed_frame:
                        analysis = self.analyze_content_hybrid(compressed_frame, audio_transcript)
                        if analysis["category"] != "Error": all_analyses.append(analysis)
                        os.remove(frame_path)
                        os.remove(compressed_frame)
                except Exception as e:
                    logger.error(f"Frame analysis failed for {frame_path}: {e}")
                    continue
            
            if not all_analyses and not audio_transcript:
                return False, "No frames were analyzed and no transcript was generated."

            video_analysis = self.combine_video_analysis(all_analyses, video_path.name, audio_transcript)
            
            representative_image = self.create_video_thumbnail(str(video_path))
            if representative_image:
                video_hash = self.image_hasher.calculate_image_hash(representative_image)
                os.remove(representative_image)
            else:
                video_hash = hashlib.md5(audio_transcript.encode()).hexdigest()

            if self.save_analysis_only(video_analysis, video_path.name, "video", video_hash):
                os.remove(video_path)
                return True, f"Video processed ({len(all_analyses)} frames, audio transcribed)"
            else:
                return False, "Saving video analysis failed."
        except Exception as e:
            logger.error(f"Video processing failed for {video_path}: {e}")
            return False, f"Video processing error: {str(e)}"
    
    def process_image_with_hash(self, image_path: Path, image_hash: str) -> Tuple[bool, str]:
        """Process image with hash-based deduplication - NO IMAGE STORAGE"""
        try:
            logger.info(f"Processing image: {image_path.name}")
            
            compressed_path = self.compress_image(str(image_path))
            if not compressed_path:
                logger.error(f"Compression failed for: {image_path.name}")
                return False, "Compression failed"
            
            analysis = self.analyze_content_hybrid(compressed_path)
            
            if analysis["category"] == "Error":
                os.remove(compressed_path)
                logger.error(f"Analysis failed for: {image_path.name}")
                return False, "Analysis failed"
            
            # Save ONLY analysis data (no image storage)
            success = self.save_analysis_only(analysis, image_path.name, "image", image_hash)
            
            if success:
                # Store hash in local cache for deduplication
                self.image_hasher.store_hash(image_hash, {
                    'original_filename': image_path.name,
                    'category': analysis['category'],
                    'confidence': analysis['confidence'],
                    'summary': analysis['summary']
                })
            
            # Clean up ALL temporary files
            os.remove(compressed_path)
            if success:
                os.remove(image_path)  # Remove original
                logger.info(f"Successfully processed (no storage): {image_path.name}")
                return True, "Image processed - analysis saved (no image stored)"
            else:
                logger.error(f"Database save failed for: {image_path.name}")
                return False, "Database save failed"
                
        except Exception as e:
            logger.error(f"Image processing failed for {image_path.name}: {e}")
            return False, f"Image processing error: {str(e)}"

    def combine_video_analysis(self, frame_analyses: List[Dict], video_filename: str, audio_transcript: str = "") -> Dict:
        """Combine multiple frame analyses and an audio transcript into a single video analysis."""
        try:
            if not frame_analyses: # Handle audio-only case
                return {
                    "category": "Mixed", "confidence": 0.6,
                    "summary": f"Audio-only content: {audio_transcript[:150]}...",
                    "key_points": [], "useful_content": audio_transcript,
                    "processing_method": "audio_only", "frames_analyzed": 0,
                    "video_filename": video_filename, "audio_transcript": audio_transcript
                }

            categories = [analysis['category'] for analysis in frame_analyses if analysis['category'] != 'Mixed']
            most_common_category = Counter(categories).most_common(1)[0][0] if categories else "Mixed"
            
            confidences = [analysis['confidence'] for analysis in frame_analyses]
            avg_confidence = sum(confidences) / len(confidences)
            
            summaries = [analysis['summary'] for analysis in frame_analyses if analysis.get('summary')]
            key_points = [kp for analysis in frame_analyses for kp in analysis.get('key_points', [])]
            unique_key_points = list(dict.fromkeys(key_points))[:10]
            
            useful_contents = [analysis['useful_content'] for analysis in frame_analyses if analysis.get('useful_content')]
            combined_content = ' | '.join(useful_contents[:5])
            
            return {
                "category": most_common_category,
                "confidence": avg_confidence,
                "summary": f"Video content: {' | '.join(summaries[:3])}",
                "key_points": unique_key_points,
                "useful_content": combined_content,
                "processing_method": "video_frames_audio",
                "frames_analyzed": len(frame_analyses),
                "video_filename": video_filename,
                "audio_transcript": audio_transcript
            }
        except Exception as e:
            logger.error(f"Video analysis combination failed: {e}")
            return self.create_error_analysis("Video analysis combination failed")
    
    def create_video_thumbnail(self, video_path: str) -> Optional[str]:
        """Create a thumbnail image from video"""
        try:
            cap = cv2.VideoCapture(video_path)
            ret, frame = cap.read()
            cap.release()
            
            if ret:
                thumbnail_path = os.path.join(self.config.TEMP_FOLDER, f"thumb_{os.path.basename(video_path)}.jpg")
                cv2.imwrite(thumbnail_path, frame)
                return thumbnail_path
            
            return None
            
        except Exception as e:
            logger.error(f"Thumbnail creation failed: {e}")
            return None
    
    def process_batch(self) -> Dict:
        """Process all files in input folders with comprehensive reporting"""
        # Pre-flight checks
        if not self.check_ollama_status():
            return {"success": False, "error": "Ollama not available"}
        
        if not self.supabase:
            return {"success": False, "error": "Database not configured"}
        
        # Collect all files
        image_files = []
        video_files = []
        
        for folder, file_list in [(self.config.INPUT_FOLDER, image_files), (self.config.VIDEO_FOLDER, video_files)]:
            folder_path = Path(folder)
            if folder_path.exists():
                for file_path in folder_path.glob("*"):
                    if file_path.is_file():
                        is_valid, file_type = self.validate_file(file_path)
                        if is_valid:
                            if file_type == "image":
                                image_files.append(file_path)
                            elif file_type == "video":
                                video_files.append(file_path)
        
        all_files = image_files + video_files
        
        if not all_files:
            return {"success": False, "error": "No valid files found"}
        
        if len(all_files) > self.config.MAX_BATCH_SIZE:
            st.warning(f"Processing first {self.config.MAX_BATCH_SIZE} files (limit reached)")
            all_files = all_files[:self.config.MAX_BATCH_SIZE]
        
        # Process files
        results = {
            "success": True, 
            "processed": 0, 
            "failed": 0, 
            "errors": [],
            "images_processed": 0,
            "videos_processed": 0,
            "duplicates_skipped": 0,
            "categories_found": set()
        }
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, file_path in enumerate(all_files):
            try:
                status_text.text(f"Processing {file_path.name}... ({i+1}/{len(all_files)})")
                
                success, message = self.process_single_file(file_path)
                
                if success:
                    results["processed"] += 1
                    if "duplicate" in message.lower():
                        results["duplicates_skipped"] += 1
                    elif file_path in image_files:
                        results["images_processed"] += 1
                    else:
                        results["videos_processed"] += 1
                    status_text.text(f"✅ {message}: {file_path.name}")
                else:
                    results["failed"] += 1
                    results["errors"].append(f"{file_path.name}: {message}")
            
            except Exception as e:
                logger.error(f"Batch processing error for {file_path.name}: {e}")
                results["failed"] += 1
                results["errors"].append(f"{file_path.name}: Unexpected error")
            
            finally:
                progress_bar.progress((i + 1) / len(all_files))
        
        return results
    
    def search_content(self, query: str, category: str = None, limit: int = 50) -> Optional[List[Dict]]:
        """Search content with full-text search"""
        if not self.supabase:
            return None
        
        try:
            # Build search query
            search_query = self.supabase.table("content_items").select("*")
            
            # Add text search
            if query:
                search_query = search_query.or_(
                    f"summary.ilike.%{query}%,"
                    f"useful_content.ilike.%{query}%,"
                    f"extracted_text.ilike.%{query}%"
                )
            
            # Add category filter
            if category and category != "All":
                search_query = search_query.eq("category", category)
            
            # Order and limit
            search_query = search_query.order("processed_at", desc=True).limit(limit)
            
            result = search_query.execute()
            return result.data
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            st.error(f"Search error: {e}")
            return None

    def get_content(self, category: str = None, limit: int = 50) -> Optional[List[Dict]]:
        """Retrieve content with error handling"""
        if not self.supabase:
            return None
        
        try:
            query = self.supabase.table("content_items").select("*").order("processed_at", desc=True)
            
            if category and category != "All":
                query = query.eq("category", category)
            
            result = query.limit(limit).execute()
            return result.data
            
        except Exception as e:
            logger.error(f"Error retrieving content: {e}")
            st.error(f"Failed to load content: {e}")
            return None

    def get_content_stats(self) -> Dict:
        """Get content statistics including deduplication stats"""
        if not self.supabase:
            return {}
        
        try:
            # Get total count
            total_result = self.supabase.table("content_items").select("id", count="exact").execute()
            total_count = total_result.count
            
            # Get category breakdown
            category_result = self.supabase.table("content_items").select("category").execute()
            categories = [item['category'] for item in category_result.data]
            category_counts = Counter(categories)
            
            # Get recent items
            recent_result = self.supabase.table("content_items").select("*").order("processed_at", desc=True).limit(5).execute()
            
            # Get confidence distribution
            confidence_result = self.supabase.table("content_items").select("confidence").execute()
            confidences = [item['confidence'] for item in confidence_result.data]
            
            high_confidence = len([c for c in confidences if c >= 0.8])
            medium_confidence = len([c for c in confidences if 0.5 <= c < 0.8])
            low_confidence = len([c for c in confidences if c < 0.5])
            
            # Get deduplication stats
            dedup_stats = self.image_hasher.get_cache_stats()
            
            return {
                "total_items": total_count,
                "category_breakdown": dict(category_counts),
                "recent_items": recent_result.data,
                "confidence_distribution": {
                    "high": high_confidence,
                    "medium": medium_confidence,
                    "low": low_confidence
                },
                "deduplication": dedup_stats
            }
            
        except Exception as e:
            logger.error(f"Stats retrieval failed: {e}")
            return {}
    
    def process_instagram_queue(self):
        """Process any queued Instagram downloads with processing flags"""
        try:
            # Check both input and video folders for processing flags
            folders_to_check = [
                Path(self.config.INPUT_FOLDER),
                Path(self.config.VIDEO_FOLDER)
            ]
            
            for folder in folders_to_check:
                if not folder.exists():
                    continue
                
                # Find all processing flag files
                flag_files = list(folder.glob('.processing_*.json'))
                
                for flag_file in flag_files:
                    try:
                        logger.info(f"Processing queue item: {flag_file}")
                        
                        # Load processing flag
                        with open(flag_file, 'r') as f:
                            flag_data = json.load(f)
                        
                        if flag_data.get('processed', False):
                            # Already processed, remove flag
                            flag_file.unlink()
                            continue
                        
                        file_path = Path(flag_data['file_path'])
                        
                        if not file_path.exists():
                            logger.warning(f"File not found for processing: {file_path}")
                            flag_file.unlink()
                            continue
                        
                        logger.info(f"=== Processing Instagram Download ===")
                        logger.info(f"File: {file_path}")
                        logger.info(f"Source: {flag_data.get('source_url', 'unknown')}")
                        logger.info(f"Media Type: {flag_data.get('media_type', 'unknown')}")
                        
                        # Process the file
                        success, message = self.process_single_file(file_path)
                        
                        if success:
                            logger.info(f"✅ Instagram content processed successfully: {file_path.name}")
                            auth_logger.info(f"INSTAGRAM_CONTENT_PROCESSED | File: {file_path.name}")
                            
                            # Mark as processed and remove flag
                            flag_file.unlink()
                            
                        else:
                            logger.error(f"❌ Instagram content processing failed: {message}")
                            auth_logger.error(f"INSTAGRAM_CONTENT_PROCESSING_FAILED | File: {file_path.name} | Error: {message}")
                            
                            # Update flag to mark processing attempt
                            flag_data['processed'] = True
                            flag_data['processing_error'] = message
                            with open(flag_file, 'w') as f:
                                json.dump(flag_data, f, indent=2)
                    
                    except Exception as flag_error:
                        logger.error(f"Error processing flag {flag_file}: {flag_error}")
                        # Remove problematic flag file
                        try:
                            flag_file.unlink()
                        except:
                            pass
            
        except Exception as e:
            logger.error(f"Queue processing failed: {e}")
            import traceback
            logger.error(f"Queue processing stack trace:\n{traceback.format_exc()}")

def setup_page():
    """Enhanced configuration setup page with environment variables and secure Instagram credentials."""
    st.title("🔧 InsightMiner Setup")
    st.markdown("Configure your database connection, content folders, and Instagram access.")
    st.info("💡 Configuration is stored in `.env` file and OS keyring for maximum security")
    
    config = Config()
    
    # Display keyring status
    keyring_status = config.get_keyring_status()
    if keyring_status["available"] and keyring_status["is_secure"]:
        st.success(f"🔒 Secure credential storage available: {keyring_status['backend']}")
    else:
        st.warning(f"⚠️ Basic credential storage: {keyring_status['backend']}")
    
    # Show current configuration status
    if config.is_configured():
        st.success("✅ System is configured and ready")
        st.info(f"""Current Configuration:
        - Database: {config.SUPABASE_URL[:30]}...
        - Images: {config.INPUT_FOLDER}
        - Videos: {config.VIDEO_FOLDER}
        - Instagram Timeout: {config.INSTAGRAM_TIMEOUT}s
        - Retry Attempts: {config.INSTAGRAM_RETRY_ATTEMPTS}
        """)
    else:
        st.warning("⚠️ System requires configuration")
    
    with st.form("config_form"):
        st.subheader("1. Supabase Configuration")
        supabase_url = st.text_input(
            "Supabase URL", 
            value=config.SUPABASE_URL or "",
            placeholder="https://your-project.supabase.co"
        )
        supabase_key = st.text_input(
            "Supabase Anon Key", 
            value=config.SUPABASE_KEY or "",
            type="password",
            placeholder="Your Supabase anonymous public key"
        )
        
        st.subheader("2. Folder Path Configuration")
        st.info("These paths will be saved to `.env` file")
        
        image_folder = st.text_input(
            "Images Folder Path",
            value=config.INPUT_FOLDER or "",
            placeholder="Example: C:/Users/YourName/Downloads/InsightMiner/images"
        )
        
        video_folder = st.text_input(
            "Videos Folder Path",
            value=config.VIDEO_FOLDER or "",
            placeholder="Example: C:/Users/YourName/Downloads/InsightMiner/videos"
        )
        
        st.subheader("3. Instagram Download Settings")
        col1, col2 = st.columns(2)
        
        with col1:
            instagram_timeout = st.number_input(
                "Download Timeout (seconds)",
                min_value=10,
                max_value=120,
                value=config.INSTAGRAM_TIMEOUT,
                help="Timeout for Instagram video downloads (30+ recommended)"
            )
        
        with col2:
            retry_attempts = st.number_input(
                "Retry Attempts",
                min_value=1,
                max_value=10,
                value=config.INSTAGRAM_RETRY_ATTEMPTS,
                help="Number of retry attempts for failed downloads"
            )
        
        st.subheader("4. Instagram Credentials (Optional)")
        st.info("🔒 Credentials stored securely in OS keyring - never in .env file")
        
        # Show current credential status
        if config.has_instagram_credentials():
            st.success("✅ Instagram credentials configured")
            username, _ = config.get_instagram_credentials()
            st.info(f"Current username: {username}")
            
            clear_credentials = st.checkbox("🗑️ Clear stored Instagram credentials")
        else:
            st.info("ℹ️ No Instagram credentials stored")
            clear_credentials = False
        
        instagram_username = st.text_input(
            "Instagram Username",
            placeholder="your_instagram_username"
        )
        instagram_password = st.text_input(
            "Instagram Password",
            type="password",
            placeholder="Your Instagram password"
        )

        submitted = st.form_submit_button("Save Configuration & Restart")
        
        if submitted:
            # Handle credential clearing
            if clear_credentials:
                if config.delete_instagram_credentials():
                    st.success("✅ Instagram credentials cleared")
                else:
                    st.error("❌ Failed to clear Instagram credentials")
            
            # Validate required fields
            if all([supabase_url, supabase_key, image_folder, video_folder]):
                image_folder = image_folder.replace('\\', '/')
                video_folder = video_folder.replace('\\', '/')

                # Update .env with timeout settings
                try:
                    env_path = Path('.env')
                    
                    # Read existing .env content
                    env_content = {}
                    if env_path.exists():
                        with open(env_path, 'r') as f:
                            for line in f:
                                line = line.strip()
                                if line and not line.startswith('#') and '=' in line:
                                    key, value = line.split('=', 1)
                                    env_content[key] = value
                    
                    # Update all values
                    env_content['SUPABASE_URL'] = supabase_url
                    env_content['SUPABASE_KEY'] = supabase_key
                    env_content['INPUT_FOLDER'] = image_folder
                    env_content['VIDEO_FOLDER'] = video_folder
                    env_content['INSTAGRAM_TIMEOUT'] = str(instagram_timeout)
                    env_content['INSTAGRAM_RETRY_ATTEMPTS'] = str(retry_attempts)
                    
                    # Write back to .env file
                    with open(env_path, 'w') as f:
                        f.write("# Supabase Configuration\n")
                        f.write(f"SUPABASE_URL={env_content['SUPABASE_URL']}\n")
                        f.write(f"SUPABASE_KEY={env_content['SUPABASE_KEY']}\n\n")
                        f.write("# Download Folders\n")
                        f.write(f"INPUT_FOLDER={env_content['INPUT_FOLDER']}\n")
                        f.write(f"VIDEO_FOLDER={env_content['VIDEO_FOLDER']}\n\n")
                        f.write("# Instagram Download Settings\n")
                        f.write(f"INSTAGRAM_TIMEOUT={env_content['INSTAGRAM_TIMEOUT']}\n")
                        f.write(f"INSTAGRAM_RETRY_ATTEMPTS={env_content['INSTAGRAM_RETRY_ATTEMPTS']}\n")
                    
                    success_msg = "✅ Configuration saved to .env file!"
                    
                    # Handle Instagram credentials if provided
                    if instagram_username and instagram_password:
                        if config.store_instagram_credentials(instagram_username, instagram_password):
                            success_msg += " Instagram credentials stored securely in OS keyring."
                        else:
                            st.error("❌ Failed to store Instagram credentials securely")
                            return
                    
                    st.success(success_msg)
                    st.balloons()
                    time.sleep(2)
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Failed to save configuration: {e}")
            else:
                st.error("❌ Please fill in all required fields (Supabase URL, Key, Image Folder, Video Folder).")

def dashboard_page(processor: ContentProcessor):
    """Enhanced dashboard with analytics"""
    st.header("📊 Dashboard")
    
    # Get statistics
    stats = processor.get_content_stats()
    
    if stats:
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Items", stats.get("total_items", 0))
        
        with col2:
            conf_dist = stats.get("confidence_distribution", {})
            high_conf = conf_dist.get("high", 0)
            st.metric("High Confidence", high_conf)
        
        with col3:
            categories = len(stats.get("category_breakdown", {}))
            st.metric("Categories", categories)
        
        with col4:
            dedup_stats = stats.get("deduplication", {})
            duplicates_blocked = dedup_stats.get("total_duplicates_blocked", 0)
            st.metric("Duplicates Blocked", duplicates_blocked)
        
        # Deduplication efficiency stats
        dedup_stats = stats.get("deduplication", {})
        if dedup_stats.get("unique_images", 0) > 0:
            st.subheader("🔍 Deduplication Efficiency")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Unique Images", dedup_stats.get("unique_images", 0))
            with col2:
                st.metric("Duplicates Blocked", dedup_stats.get("total_duplicates_blocked", 0))
            with col3:
                cache_size = dedup_stats.get("cache_size_mb", 0)
                st.metric("Cache Size", f"{cache_size:.2f} MB")
            
            # Calculate efficiency
            total_processed = dedup_stats.get("unique_images", 0) + dedup_stats.get("total_duplicates_blocked", 0)
            if total_processed > 0:
                efficiency = (dedup_stats.get("total_duplicates_blocked", 0) / total_processed) * 100
                st.info(f"🎯 Deduplication saved {efficiency:.1f}% of processing time and storage!")
        
        # Category breakdown chart
        if stats.get("category_breakdown"):
            st.subheader("📈 Content by Category")
            category_data = stats["category_breakdown"]
            
            # Create simple bar chart data
            chart_data = {"Category": list(category_data.keys()), "Count": list(category_data.values())}
            st.bar_chart(chart_data)
        
        # Recent items
        recent_items = stats.get("recent_items", [])
        if recent_items:
            st.subheader("🕒 Recent Uploads")
            for item in recent_items[:3]:
                with st.expander(f"{item['original_filename']} - {item['category']}"):
                    st.write(f"**Summary:** {item['summary'][:200]}...")
                    st.caption(f"Processed: {item['processed_at'][:16]}")
    else:
        st.info("📭 No data yet. Process some content to see analytics!")

def upload_center_page(processor: ContentProcessor):
    """Enhanced upload center with PC image browser and bulk operations"""
    st.header("📤 Enhanced Upload Center")
    
    # Three-column layout for different upload methods
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("🔍 Browse PC Images")
        
        if st.button("📁 Select Images from PC", use_container_width=True):
            selected_files = browse_pc_images()
            if selected_files:
                copy_files_to_input(selected_files, processor.config.INPUT_FOLDER)
                st.success(f"✅ Copied {len(selected_files)} images to input folder")
                st.rerun()
        
        if st.button("📁 Select Entire Folder", use_container_width=True):
            folder_path = browse_pc_folder()
            if folder_path:
                copied_count = copy_folder_images(folder_path, processor)
                st.success(f"✅ Copied {copied_count} files from folder")
                st.rerun()
    
    with col2:
        st.subheader("🎥 Browse PC Videos")
        
        if st.button("📁 Select Videos from PC", use_container_width=True):
            selected_videos = browse_pc_videos()
            if selected_videos:
                copy_files_to_input(selected_videos, processor.config.VIDEO_FOLDER)
                st.success(f"✅ Copied {len(selected_videos)} videos to input folder")
                st.rerun()
    
    with col3:
        st.subheader("📱 Instagram Quick Download")
        
        # Instagram session status
        config = processor.config
        if config.has_instagram_credentials():
            instagram_downloader = InstagramDownloader(config)
            session_status = instagram_downloader.get_session_status()
            
            if session_status["status"] == "active":
                st.success(f"✅ Logged in as @{session_status.get('username', 'unknown')}")
            elif session_status["status"] == "expired":
                st.warning("⚠️ Session expired - re-login required")
            else:
                st.info("ℹ️ Ready to login")
                
            # URL input for Instagram content
            instagram_url = st.text_input(
                "Instagram URL",
                placeholder="https://instagram.com/p/... or https://instagram.com/reel/...",
                key="instagram_url_input"
            )
            
            col_download, col_test = st.columns(2)
            
            with col_download:
                if st.button("📥 Download", use_container_width=True, disabled=not instagram_url):
                    if instagram_url:
                        with st.spinner("Downloading and processing..."):
                            # Use automatic folder routing and processing
                            success, message = instagram_downloader.download_single_reel(instagram_url)
                            
                            if success:
                                st.success(f"✅ {message} → auto-routed and queued for processing")
                                st.rerun()
                            else:
                                st.error(f"❌ {message}")
            
            with col_test:
                if st.button("🔐 Test Login", use_container_width=True):
                    with st.spinner("Testing login..."):
                        success, message = instagram_downloader.setup_session()
                        if success:
                            st.success(f"✅ {message}")
                        else:
                            st.error(f"❌ {message}")
        else:
            st.info("ℹ️ Configure Instagram credentials in Settings to enable downloads")
            if st.button("⚙️ Go to Settings", use_container_width=True):
                st.switch_page("Settings")

    st.divider()
    
    # File status overview
    image_files = list(Path(processor.config.INPUT_FOLDER).glob("*"))
    valid_images = [f for f in image_files if f.is_file() and processor.validate_file(f)[0]]
    video_files = list(Path(processor.config.VIDEO_FOLDER).glob("*"))
    valid_videos = [f for f in video_files if f.is_file() and processor.validate_file(f)[0]]

    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.subheader("📸 Images Ready")
        st.metric("Images", len(valid_images))
        if st.button("👁️ Preview Images", use_container_width=True, key="preview_img"):
            preview_files(valid_images[:6], "Images")
    
    with col2:
        st.subheader("🎥 Videos Ready")
        st.metric("Videos", len(valid_videos))
        if st.button("👁️ Preview Videos", use_container_width=True, key="preview_vid"):
            preview_files(valid_videos[:6], "Videos")
    
    with col3:
        st.subheader("📊 Quick Stats")
        total_files = len(valid_images) + len(valid_videos)
        total_size = sum(f.stat().st_size for f in valid_images + valid_videos) / (1024*1024)
        st.metric("Total Files", total_files)
        st.metric("Total Size", f"{total_size:.1f} MB")
    
    with col4:
        st.subheader("🗑️ Quick Actions")
        if st.button("🗑️ Clear All Input Files", use_container_width=True, type="secondary"):
            clear_input_folders(processor)
            st.success("✅ All input files cleared")
            st.rerun()

    st.divider()
    
    # Enhanced processing controls
    st.subheader("⚙️ Processing Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        confidence_threshold = st.slider(
            "🎯 Confidence Threshold", 
            min_value=0.1, 
            max_value=1.0, 
            value=processor.config.CONFIDENCE_THRESHOLD,
            help="Content below this confidence will be marked as 'Mixed'"
        )
        processor.config.CONFIDENCE_THRESHOLD = confidence_threshold
    
    with col2:
        max_batch = st.number_input(
            "📦 Max Batch Size", 
            min_value=1, 
            max_value=100, 
            value=processor.config.MAX_BATCH_SIZE,
            help="Maximum number of files to process in one batch"
        )
        processor.config.MAX_BATCH_SIZE = max_batch

    # Main processing button
    if st.button("🚀 Process All Content", type="primary", use_container_width=True):
        if valid_images or valid_videos:
            with st.spinner("🔍 Processing content... This may take a while for videos."):
                results = processor.process_batch()
                
                if results["success"]:
                    st.success(f"🎉 Processing Complete!")
                    
                    # Detailed results with enhanced metrics
                    res_col1, res_col2, res_col3, res_col4, res_col5 = st.columns(5)
                    with res_col1:
                        st.metric("📸 Images", results["images_processed"])
                    with res_col2:
                        st.metric("🎥 Videos", results["videos_processed"])
                    with res_col3:
                        st.metric("🔄 Duplicates", results["duplicates_skipped"])
                    with res_col4:
                        st.metric("✅ Success", results["processed"])
                    with res_col5:
                        st.metric("❌ Failed", results["failed"])
                    
                    if results["failed"] > 0:
                        st.warning(f"⚠️ {results['failed']} files failed")
                        with st.expander("📋 Error Details"):
                            for error in results["errors"]:
                                st.text(f"• {error}")
                else:
                    st.error(f"❌ Processing failed: {results.get('error', 'Unknown error')}")
        else:
            st.warning("📂 No valid files found. Add some images or videos first!")

# Helper functions for PC browsing functionality
def browse_pc_images():
    """Open file dialog to select images from PC"""
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        
        file_types = [
            ('Image files', '*.jpg *.jpeg *.png *.webp *.bmp'),
            ('All files', '*.*')
        ]
        
        files = filedialog.askopenfilenames(
            title="Select Images to Analyze",
            filetypes=file_types
        )
        
        root.destroy()
        return list(files) if files else []
        
    except Exception as e:
        st.error(f"Error opening file dialog: {e}")
        return []

def browse_pc_videos():
    """Open file dialog to select videos from PC"""
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        
        file_types = [
            ('Video files', '*.mp4 *.avi *.mov *.mkv *.webm'),
            ('All files', '*.*')
        ]
        
        files = filedialog.askopenfilenames(
            title="Select Videos to Analyze",
            filetypes=file_types
        )
        
        root.destroy()
        return list(files) if files else []
        
    except Exception as e:
        st.error(f"Error opening file dialog: {e}")
        return []

def browse_pc_folder():
    """Open folder dialog to select entire folder"""
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        
        folder = filedialog.askdirectory(
            title="Select Folder Containing Images/Videos"
        )
        
        root.destroy()
        return folder if folder else None
        
    except Exception as e:
        st.error(f"Error opening folder dialog: {e}")
        return None

def copy_files_to_input(file_paths, destination_folder):
    """Copy selected files to input folder"""
    try:
        destination = Path(destination_folder)
        destination.mkdir(exist_ok=True)
        
        for file_path in file_paths:
            source = Path(file_path)
            dest = destination / source.name
            
            counter = 1
            while dest.exists():
                dest = destination / f"{source.stem}_{counter}{source.suffix}"
                counter += 1
            
            shutil.copy2(source, dest)
            
        return len(file_paths)
        
    except Exception as e:
        st.error(f"Error copying files: {e}")
        return 0

def copy_folder_images(folder_path, processor):
    """Copy all images/videos from a folder"""
    try:
        source_folder = Path(folder_path)
        copied_count = 0
        
        all_exts = processor.config.SUPPORTED_IMAGE_FORMATS | processor.config.SUPPORTED_VIDEO_FORMATS
        
        for file_path in source_folder.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in all_exts:
                if file_path.suffix.lower() in processor.config.SUPPORTED_IMAGE_FORMATS:
                    destination = Path(processor.config.INPUT_FOLDER)
                else:
                    destination = Path(processor.config.VIDEO_FOLDER)
                
                destination.mkdir(exist_ok=True)
                dest = destination / file_path.name
                
                counter = 1
                while dest.exists():
                    dest = destination / f"{file_path.stem}_{counter}{file_path.suffix}"
                    counter += 1
                
                shutil.copy2(file_path, dest)
                copied_count += 1
        
        return copied_count
        
    except Exception as e:
        st.error(f"Error copying folder: {e}")
        return 0

def check_extension_downloads(processor):
    """Check for files downloaded by browser extension"""
    return 0 # Placeholder as extension is ignored for now

def preview_files(file_list, file_type):
    """Show preview of files to be processed"""
    if not file_list:
        st.info(f"No {file_type.lower()} to preview.")
        return

    with st.expander(f"📋 Previewing first {len(file_list)} {file_type}", expanded=True):
        for file_path in file_list:
            if file_path.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}:
                try:
                    image = Image.open(file_path)
                    st.image(image, width=150, caption=file_path.name)
                except Exception:
                    st.text(f"Could not preview {file_path.name}")
            else:
                st.text(f"🎥 {file_path.name} (video preview not available)")


def clear_input_folders(processor):
    """Clear all files from input folders"""
    try:
        for folder_path in [processor.config.INPUT_FOLDER, processor.config.VIDEO_FOLDER]:
            folder = Path(folder_path)
            if folder.exists():
                for file_path in folder.glob("*"):
                    if file_path.is_file():
                        file_path.unlink()
    except Exception as e:
        st.error(f"Error clearing folders: {e}")

def show_extension_guide():
    """Show extension installation guide"""
    st.info("""
    🔗 **Get the InsightMiner Browser Extension:**
    
    1. [cite_start]Create extension folder with provided files [cite: 618]
    2. [cite_start]Go to chrome://extensions/ [cite: 618]
    3. [cite_start]Enable Developer mode [cite: 618]
    4. [cite_start]Click "Load unpacked" and select extension folder [cite: 618]
    5. [cite_start]Browse Instagram and click "Mine" buttons! [cite: 618]
    
    [cite_start]The extension downloads content directly to your input folders for seamless processing. [cite: 619]
    """)
    
def content_gallery_page(processor: ContentProcessor):
    """Enhanced content gallery with advanced filtering"""
    st.header("🖼️ Content Gallery")
    
    # Advanced filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        categories = ["All"] + processor.config.CATEGORIES + ["Mixed", "Error"]
        selected_category = st.selectbox("🏷️ Category", categories)
    
    with col2:
        confidence_filter = st.selectbox(
            "🎯 Confidence Level", 
            ["All", "High (80%+)", "Medium (50-80%)", "Low (<50%)"]
        )
    
    with col3:
        file_type_filter = st.selectbox("📄 File Type", ["All", "Images", "Videos"])
    
    # Search bar
    search_query = st.text_input("🔍 Search content...", placeholder="Enter keywords to search")
    
    # Apply filters and get content
    if search_query:
        items = processor.search_content(search_query, selected_category if selected_category != "All" else None)
    else:
        items = processor.get_content(selected_category if selected_category != "All" else None, limit=100)
    
    if items:
        # Additional filtering based on UI selections
        filtered_items = items
        
        # Confidence filter
        if confidence_filter != "All":
            if confidence_filter == "High (80%+)":
                filtered_items = [item for item in filtered_items if item['confidence'] >= 0.8]
            elif confidence_filter == "Medium (50-80%)":
                filtered_items = [item for item in filtered_items if 0.5 <= item['confidence'] < 0.8]
            elif confidence_filter == "Low (<50%)":
                filtered_items = [item for item in filtered_items if item['confidence'] < 0.5]
        
        # File type filter
        if file_type_filter != "All":
            if file_type_filter == "Images":
                filtered_items = [item for item in filtered_items if item.get('file_type', 'image') == 'image']
            elif file_type_filter == "Videos":
                filtered_items = [item for item in filtered_items if item.get('file_type', 'image') == 'video']
        
        st.info(f"📊 Showing {len(filtered_items)} of {len(items)} items")
        
        # Display options
        view_mode = st.radio("View Mode", ["Detailed", "Compact", "Grid"], horizontal=True)
        
        if view_mode == "Grid":
            # Grid view
            cols = st.columns(3)
            for i, item in enumerate(filtered_items):
                with cols[i % 3]:
                    confidence_emoji = "🟢" if item['confidence'] >= 0.8 else "🟡" if item['confidence'] >= 0.5 else "🔴"
                    file_emoji = "🎥" if item.get('file_type') == 'video' else "📷"
                    
                    with st.container():
                        st.markdown(f"**{file_emoji} {item['original_filename'][:20]}...**")
                        st.markdown(f"{confidence_emoji} {item['category']} ({item['confidence']:.0%})")
                        st.markdown(f"_{item['summary'][:80]}..._")
                        
                        if st.button("View Details", key=f"grid_{item['id']}", use_container_width=True):
                            st.session_state[f"expanded_{item['id']}"] = True
        
        elif view_mode == "Compact":
            # Compact list view
            for item in filtered_items:
                confidence_color = "🟢" if item['confidence'] >= 0.8 else "🟡" if item['confidence'] >= 0.5 else "🔴"
                file_emoji = "🎥" if item.get('file_type') == 'video' else "📷"
                
                col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
                
                with col1:
                    st.write(f"{file_emoji} **{item['original_filename']}**")
                with col2:
                    st.write(f"{item['category']}")
                with col3:
                    st.write(f"{confidence_color} {item['confidence']:.0%}")
                with col4:
                    if st.button("View", key=f"compact_{item['id']}"):
                        st.session_state[f"expanded_{item['id']}"] = True
        
        else:
            # Detailed view (original expandable format)
            for item in filtered_items:
                confidence_color = "🟢" if item['confidence'] >= 0.8 else "🟡" if item['confidence'] >= 0.5 else "🔴"
                file_emoji = "🎥" if item.get('file_type') == 'video' else "📷"
                
                expanded = st.session_state.get(f"expanded_{item['id']}", False)
                
                with st.expander(
                    f"{confidence_color} {file_emoji} {item['original_filename']} - {item['category']} ({item['confidence']:.0%})",
                    expanded=expanded
                ):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.markdown("**📝 Summary:**")
                        st.write(item['summary'])
                        
                        if item.get('key_points'):
                            st.markdown("**🔑 Key Points:**")
                            for point in item['key_points']:
                                st.write(f"• {point}")
                        
                        if item.get('extracted_text'):
                            with st.expander("📄 Extracted Text (OCR)"):
                                st.text(item['extracted_text'])
                        
                        if item.get('useful_content') and item['useful_content'] != item['summary']:
                            with st.expander("📋 Full Content"):
                                st.text(item['useful_content'])
                        
                        # Metadata
                        metadata_cols = st.columns(3)
                        with metadata_cols[0]:
                            st.caption(f"Method: {item.get('processing_method', 'unknown')}")
                        with metadata_cols[1]:
                            if item.get('file_type') == 'video':
                                st.caption(f"Frames: {item.get('frames_analyzed', 'N/A')}")
                        with metadata_cols[2]:
                            st.caption(f"Processed: {item['processed_at'][:16]}")
                    
                    with col2:
                        st.text("🖼️ No image stored (hash-based system)")
                        st.caption(f"Hash: {item.get('image_hash', 'N/A')[:12]}...")
                        st.caption(f"Processed: {item['processed_at'][:16]}")
    else:
        st.info("📭 No content found. Try different filters or process some content first!")

def main():
    """Enhanced main application with navigation"""
    st.set_page_config(
        page_title="InsightMiner Pro", 
        page_icon="⛏️", 
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    config = Config()
    
    # Check if configured
    if not config.is_configured():
        setup_page()
        return
    
    # Initialize processor
    processor = ContentProcessor(config)
    
    # Process any queued Instagram downloads in background (non-blocking)
    def process_queue_background():
        try:
            processor.process_instagram_queue()
        except Exception as e:
            logger.error(f"Background queue processing failed: {e}")
    
    queue_thread = threading.Thread(target=process_queue_background, daemon=True)
    queue_thread.start()
    
    # Initialize Instagram downloader and LocalServer
    instagram_downloader = InstagramDownloader(config)
    local_server = LocalServer(config, instagram_downloader)
    
    # Start LocalServer in background
    if not local_server.is_running():
        local_server.start_server()
    
    # Sidebar navigation
    st.sidebar.title("⛏️ InsightMiner Pro")
    st.sidebar.markdown("Professional Content Analysis Platform")
    
    # Navigation
    pages = {
        "📊 Dashboard": "dashboard",
        "📁 Upload Center": "upload",
        "🖼️ Content Gallery": "gallery",
        "🔍 Search": "search",
        "⚙️ Settings": "settings"
    }
    
    selected_page = st.sidebar.selectbox("Navigate", list(pages.keys()))
    page_key = pages[selected_page]
    
    # System status in sidebar
    with st.sidebar.expander("📊 System Status"):
        if processor.check_ollama_status():
            st.success("✅ Ollama Ready")
        else:
            st.error("❌ Ollama Not Available")
        
        if processor.supabase:
            st.success("✅ Database Connected")
        else:
            st.error("❌ Database Not Connected")
        
        # LocalServer status
        if local_server.is_running():
            st.success("✅ LocalServer Running")
        else:
            st.error("❌ LocalServer Not Running")
    
    # Quick stats in sidebar
    stats = processor.get_content_stats()
    if stats:
        st.sidebar.metric("Total Items", stats.get("total_items", 0))
        st.sidebar.metric("Categories", len(stats.get("category_breakdown", {})))
        
        # Deduplication stats in sidebar
        dedup_stats = stats.get("deduplication", {})
        if dedup_stats.get("total_duplicates_blocked", 0) > 0:
            st.sidebar.metric("Duplicates Blocked", dedup_stats.get("total_duplicates_blocked", 0))
    
    # Main content area
    if page_key == "dashboard":
        dashboard_page(processor)
    
    elif page_key == "upload":
        upload_center_page(processor)
    
    elif page_key == "gallery":
        content_gallery_page(processor)
    
    elif page_key == "search":
        st.header("🔍 Advanced Search")
        
        # Search interface
        search_query = st.text_input("Search your content library...", placeholder="Enter keywords, topics, or specific terms")
        
        col1, col2 = st.columns(2)
        with col1:
            search_category = st.selectbox("Filter by Category", ["All"] + processor.config.CATEGORIES)
        with col2:
            search_limit = st.number_input("Max Results", min_value=10, max_value=200, value=50)
        
        if search_query:
            with st.spinner("Searching..."):
                results = processor.search_content(
                    search_query, 
                    search_category if search_category != "All" else None,
                    search_limit
                )
                
                if results:
                    st.success(f"Found {len(results)} results")
                    
                    # Display search results in detailed format
                    for item in results:
                        confidence_color = "🟢" if item['confidence'] >= 0.8 else "🟡" if item['confidence'] >= 0.5 else "🔴"
                        file_emoji = "🎥" if item.get('file_type') == 'video' else "📷"
                        
                        with st.expander(f"{confidence_color} {file_emoji} {item['original_filename']} - {item['category']} ({item['confidence']:.0%})"):
                            col1, col2 = st.columns([2, 1])
                            
                            with col1:
                                st.markdown("**📝 Summary:**")
                                st.write(item['summary'])
                                
                                if item.get('key_points'):
                                    st.markdown("**🔑 Key Points:**")
                                    for point in item['key_points']:
                                        st.write(f"• {point}")
                                
                                if item.get('useful_content'):
                                    with st.expander("📋 Full Content"):
                                        st.text(item['useful_content'])
                            
                            with col2:
                                st.text("🖼️ No image stored")
                                st.caption(f"Hash: {item.get('image_hash', 'N/A')[:12]}...")
                                st.caption(f"Processed: {item['processed_at'][:16]}")
                else:
                    st.info("No results found. Try different keywords.")
        else:
            st.info("Enter search terms above to find content in your library.")
            
            # Show search tips
            with st.expander("🔍 Search Tips"):
                st.markdown("""
                **Search Examples:**
                - `python tutorial` - Find programming content
                - `marketing strategy` - Business insights
                - `fitness tips` - Health content
                - `productivity tools` - Efficiency resources
                
                **Search covers:**
                - Summary text
                - Key points
                - Extracted OCR text
                - Full content analysis
                """)
    
    elif page_key == "settings":
        st.header("⚙️ Settings")
        
        # Instagram Configuration
        st.subheader("📸 Instagram Settings")
        
        # Check current Instagram credentials
        current_username = config.INSTAGRAM_USERNAME
        current_password = config.INSTAGRAM_PASSWORD
        
        # Always show credential form (simpler UX)
        st.subheader("🔐 Instagram Login")
        st.info("Credentials are securely stored in your OS keyring (Windows Credential Manager/macOS Keychain)")
        
        if current_username and current_password:
            st.success(f"✅ Current credentials: {current_username}")
        else:
            st.warning("❌ No Instagram credentials configured")
        
        # Single form for add/update credentials
        with st.form("instagram_credentials"):
            username = st.text_input("Instagram Username", value=current_username or "", 
                                    help="Your Instagram username (without @)")
            password = st.text_input("Instagram Password", type="password",
                                    help="Your Instagram password")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("💾 Save Credentials"):
                    if username and password:
                        try:
                            import keyring
                            keyring.set_password("InsightMiner", "instagram_username", username)
                            keyring.set_password("InsightMiner", "instagram_password", password)
                            st.success("✅ Instagram credentials saved securely!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error saving credentials: {e}")
                    else:
                        st.error("Please enter both username and password")
                        
            with col2:
                if st.form_submit_button("🗑️ Clear Credentials"):
                    try:
                        import keyring
                        keyring.delete_password("InsightMiner", "instagram_username")
                        keyring.delete_password("InsightMiner", "instagram_password")
                        st.success("Instagram credentials cleared from keyring")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error clearing credentials: {e}")
        
        # Configuration reset
        st.subheader("🔧 Configuration Management")
        if st.button("🔄 Reset Application State"):
            # Clear session state and restart (don't remove .env file)
            st.session_state.clear()
            st.success("Application state reset. Please refresh the page.")
            st.rerun()
        
        # Processing settings
        st.subheader("⚙️ Processing Settings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            new_confidence = st.slider(
                "Confidence Threshold", 
                0.1, 1.0, 
                processor.config.CONFIDENCE_THRESHOLD,
                help="Content below this threshold will be categorized as 'Mixed'"
            )
            
            new_batch_size = st.number_input(
                "Max Batch Size", 
                1, 100, 
                processor.config.MAX_BATCH_SIZE,
                help="Maximum files to process in one batch"
            )
        
        with col2:
            new_frame_interval = st.number_input(
                "Video Frame Interval (seconds)", 
                1, 10, 
                processor.config.FRAME_EXTRACTION_INTERVAL,
                help="Extract frames every N seconds from videos"
            )
            
            new_jpeg_quality = st.slider(
                "JPEG Compression Quality", 
                50, 95, 
                processor.config.JPEG_QUALITY,
                help="Higher = better quality, larger temp files"
            )
        
        if st.button("Save Settings"):
            processor.config.CONFIDENCE_THRESHOLD = new_confidence
            processor.config.MAX_BATCH_SIZE = new_batch_size
            processor.config.FRAME_EXTRACTION_INTERVAL = new_frame_interval
            processor.config.JPEG_QUALITY = new_jpeg_quality
            st.success("Settings saved!")
            auth_logger.info(f"SETTINGS_UPDATED | Confidence: {new_confidence} | Batch: {new_batch_size}")
        
        # Deduplication management
        st.subheader("🔍 Deduplication Management")
        
        dedup_stats = processor.image_hasher.get_cache_stats()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Unique Images Cached", dedup_stats.get("unique_images", 0))
        with col2:
            st.metric("Total Duplicates Blocked", dedup_stats.get("total_duplicates_blocked", 0))
        with col3:
            st.metric("Cache Size", f"{dedup_stats.get('cache_size_mb', 0):.2f} MB")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Clear Duplicate Cache", help="This will reset duplicate detection"):
                try:
                    if os.path.exists("hash_cache.json"):
                        os.remove("hash_cache.json")
                    processor.image_hasher.hash_cache = {}
                    st.success("Duplicate cache cleared!")
                    auth_logger.info("DUPLICATE_CACHE_CLEARED")
                except Exception as e:
                    st.error(f"Failed to clear cache: {e}")
                    logger.error(f"Cache clear failed: {e}")
        
        with col2:
            if st.button("Export Cache Statistics"):
                cache_stats = {
                    "total_unique_images": dedup_stats.get("unique_images", 0),
                    "total_duplicates_blocked": dedup_stats.get("total_duplicates_blocked", 0),
                    "cache_size_mb": dedup_stats.get("cache_size_mb", 0),
                    "export_date": datetime.now().isoformat()
                }
                st.download_button(
                    "Download Stats JSON",
                    json.dumps(cache_stats, indent=2),
                    file_name=f"insightminer_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
        
        # Logging management
        st.subheader("📋 Logging & Debug")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("View Error Logs"):
                try:
                    error_log_path = Path("Logs") / "ErrorLogs.js"
                    if error_log_path.exists():
                        with open(error_log_path, 'r') as f:
                            logs = f.read()
                        st.text_area("Recent Error Logs", logs[-2000:], height=200)  # Last 2000 chars
                    else:
                        st.info("No error logs found (that's good!)")
                except Exception as e:
                    st.error(f"Failed to read logs: {e}")
        
        with col2:
            if st.button("View Auth Logs"):
                try:
                    auth_log_path = Path("Logs") / "AuthLogs.js"
                    if auth_log_path.exists():
                        with open(auth_log_path, 'r') as f:
                            logs = f.read()
                        st.text_area("Recent Auth Logs", logs[-2000:], height=200)  # Last 2000 chars
                    else:
                        st.info("No auth logs found")
                except Exception as e:
                    st.error(f"Failed to read logs: {e}")
        
        # System info
        st.subheader("ℹ️ System Information")
        
        system_info = {
            "Python Version": sys.version.split()[0],
            "Streamlit Version": st.__version__,
            "Working Directory": os.getcwd(),
            "Environment File": "✅ Exists" if Path(".env").exists() else "❌ Missing",
            "Instagram Credentials": "✅ Configured" if (config.INSTAGRAM_USERNAME and config.INSTAGRAM_PASSWORD) else "❌ Missing",
            "Hash Cache": "✅ Loaded" if processor.image_hasher.hash_cache else "❌ Empty",
            "Input Folder": "✅ Exists" if Path(config.INPUT_FOLDER).exists() else "❌ Missing",
            "Video Folder": "✅ Exists" if Path(config.VIDEO_FOLDER).exists() else "❌ Missing",
            "Temp Folder": "✅ Exists" if Path(config.TEMP_FOLDER).exists() else "❌ Missing",
            "Logs Folder": "✅ Exists" if Path("Logs").exists() else "❌ Missing"
        }
        
        for key, value in system_info.items():
            st.text(f"{key}: {value}")

if __name__ == "__main__":
    main()