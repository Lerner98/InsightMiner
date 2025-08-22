# InsightMiner Python Backend Changelog

All notable changes to this project will be documented in this file.

## [v3.2] - 2025-08-22 - Instagram Metadata Parsing Fallback System

### CRITICAL FALLBACK SYSTEM IMPLEMENTED
- **ValidationError Handling for Instagram Metadata**
  - Resolves Pydantic ValidationError crashes when Instagram API returns malformed metadata
  - Addresses issue with null clips_metadata.original_sound_info causing download failures
  - Implements comprehensive fallback system when metadata parsing fails
  - Ensures downloads succeed even with problematic Instagram posts (e.g., post DNBCksyivGK)

### FALLBACK ARCHITECTURE
- **Media Info Fallback Creation**
  - `_create_minimal_media_info()` method creates essential media objects when ValidationError occurs
  - `MinimalMediaInfo` class provides required fields (pk, media_type, code) for downloads
  - URL pattern detection for media type inference (/reel/, /reels/, /p/ paths)
  - Direct download probing to determine actual content type when URL analysis fails

- **Direct Download Methods**
  - `_fallback_download_direct()` bypasses metadata parsing completely
  - `_detect_media_type_fallback()` with multiple detection strategies
  - Maintains existing retry logic and timeout handling during fallback downloads
  - Automatic file path resolution and naming consistency

### POST-DOWNLOAD METADATA DETECTION
- **Comprehensive Content Analysis**
  - `_detect_post_download_metadata()` extracts missing metadata after successful download
  - Video property analysis (resolution, FPS, duration) using OpenCV
  - Audio transcription using faster-whisper for content with audio tracks
  - Frame-based OCR for subtitle/caption detection in video content
  - Image EXIF data extraction and OCR text detection

- **Audio Content Recovery**
  - `_detect_audio_content()` using faster-whisper tiny model for speed
  - Full transcript extraction with timestamp segments
  - Language detection and confidence scoring
  - Graceful degradation when faster-whisper unavailable

- **Text Content Extraction**
  - `_detect_video_text_content()` samples video frames for OCR analysis
  - `_detect_image_text_content()` for static image text extraction
  - Integration with existing OCR processor when available
  - Burned-in subtitle and caption detection

### ENHANCED ERROR HANDLING
- **Intelligent Error Classification**
  - ValidationError detection and automatic fallback activation
  - Non-validation errors continue normal error handling flow
  - Comprehensive logging for fallback system debugging
  - Success metrics for fallback vs normal download paths

- **Robust Download Workflow**
  - Fallback flag system prevents normal workflow when metadata fails
  - Post-download metadata enhancement for fallback cases only
  - Maintains backward compatibility with existing download logic
  - Zero impact on normal downloads without ValidationErrors

## [v3.1] - 2025-01-22 - Complete System Recovery & Instagram Video Timeout Resolution

### CRITICAL ISSUE RESOLVED
- **Instagram Video Download Timeout Fixed**
  - Resolved "HTTPSConnectionPool read timed out. (read timeout=1)" error that prevented video downloads
  - Media PK extraction confirmed working (3672271905135241578 extracted successfully)
  - Implemented environment-based timeout configuration via INSTAGRAM_TIMEOUT variable
  - Added configurable retry logic with INSTAGRAM_RETRY_ATTEMPTS setting
  - Successfully restored full Instagram content acquisition pipeline

### ARCHITECTURE IMPLEMENTATION (Rules.md v3.1 Compliance)
- **Environment-Based Configuration System**
  - Complete migration from config.json to .env file for all configuration
  - Added python-dotenv>=1.0.0 dependency for secure environment variable loading
  - All sensitive credentials externalized per Rules.md requirements
  - No hardcoded paths or credentials in Python files

### CORE COMPONENTS RESTORED
- **InstagramDownloader Class**
  - Session management with persistent login via instagram_session.json
  - Media PK extraction using client.media_pk_from_url() method
  - Environment-based timeout configuration (INSTAGRAM_TIMEOUT from .env)
  - Exponential backoff retry logic (INSTAGRAM_RETRY_ATTEMPTS from .env)
  - Rate limiting with client.delay_range = [1, 3] for human-like behavior
  - Comprehensive error handling for login failures and network issues

- **Flask LocalServer (localhost:8502)**
  - HTTP /download POST endpoint for browser extension communication
  - JSON payload processing for Instagram URLs and content types
  - Automatic folder routing (INPUT_FOLDER vs VIDEO_FOLDER)
  - CORS handling for Chrome extension origin support

- **Enhanced Config Class**
  - Environment variable loading from .env file using load_dotenv()
  - OS keyring integration for secure Instagram credential storage
  - Configurable timeout and retry parameters
  - Session persistence management for instagram_session.json

### SECURITY ARCHITECTURE RESTORED
- **OS Keyring Integration**
  - Zero plaintext credential storage (Instagram credentials never in .env)
  - Cross-platform support: Windows Credential Manager, macOS Keychain, Linux GNOME Keyring
  - Secure credential storage, retrieval, and deletion operations
  - Real-time keyring backend detection and security level indication

- **Environment Security**
  - All configuration externalized to .env file with .gitignore protection
  - Supabase credentials in .env, Instagram credentials in OS keyring only
  - No sensitive data hardcoded in Python source files

### COMPLETE DATA FLOW IMPLEMENTATION
1. **Initial Setup**: User configures Instagram credentials via OS keyring (one-time)
2. **Session Establishment**: InstagramDownloader creates persistent session using instagrapi
3. **Browser Extension**: User browses Instagram, clicks extension button on content
4. **HTTP Communication**: Extension sends POST to localhost:8502/download with URL
5. **URL Processing**: LocalServer validates and extracts Instagram URL
6. **Media PK Extraction**: Convert URL to numeric media PK using client.media_pk_from_url()
7. **Authenticated Retrieval**: Download content with configured timeout/retry logic
8. **Pipeline Integration**: ContentProcessor handles files using existing analysis workflow
9. **Zero-Storage Cleanup**: Original files deleted after database insertion

### TECHNICAL FIXES IMPLEMENTED
- **Timeout Configuration**: Environment-based INSTAGRAM_TIMEOUT (default 30s, configurable 10-120s)
- **Retry Logic**: INSTAGRAM_RETRY_ATTEMPTS with exponential backoff and random jitter
- **Error Detection**: Specific timeout keyword matching ('timeout', 'timed out', 'connection', 'read timeout')
- **Media PK Fix**: Proper media_pk_from_url() usage instead of media_id() for URL processing
- **Client Configuration**: Dynamic timeout setting from environment variables

### USER INTERFACE ENHANCEMENTS
- **Enhanced Setup Page**
  - Real-time configuration status display
  - Environment variable management for timeout/retry settings
  - Instagram credential configuration with keyring security indicators
  - .env file updates with proper formatting and comments

- **Upload Center Integration**
  - Instagram Quick Download with real-time session status
  - Automatic folder routing based on content type detection
  - Download progress and error feedback
  - Test login functionality for credential validation

- **System Status Monitoring**
  - LocalServer running status in sidebar
  - Keyring backend security level display
  - Real-time timeout and retry configuration visibility

### DEPENDENCIES UPDATED
- Added python-dotenv>=1.0.0 for environment variable loading
- Maintained instagrapi>=2.2.1 for Instagram API access
- Preserved flask>=2.3.0 and flask-cors>=4.0.0 for HTTP server
- Continued keyring>=24.0.0 for OS-native credential storage

### VERIFICATION COMPLETED
- Environment configuration loading verified working
- Instagram timeout settings configurable and functional
- OS keyring credential storage operational
- Flask HTTP API endpoints responsive
- Complete system integration confirmed

## Previous Versions

### v2.0.0 - Architecture Upgrade
- **Added `faster-whisper` to `requirements.txt`**: Included the necessary library for local audio transcription.
- **Added `AudioProcessor` class**: Created a new class to handle audio extraction via FFmpeg and transcription via `faster-whisper`.
- **Upgraded `Config` & `setup_page`**: Implemented a flexible configuration system using `config.json` for both credentials and absolute folder paths.
- **Finalized `ContentProcessor`**: Replaced the entire class with a fully integrated version that handles the complete audio and video processing pipeline.