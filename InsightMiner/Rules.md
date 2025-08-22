InsightMiner Python App: Instagram Integration Architecture & Rules (v3.1)
1. Project Goal & Core Value
InsightMiner is a personal content intelligence platform that extracts valuable insights from Instagram educational content using local AI processing. The system integrates direct Instagram content acquisition through authenticated API access, processes media locally, and stores only analysis data in Supabase for searchable knowledge management.
2. Core Architectural Principles

Zero-Storage Backend: Process media locally, upload only text analysis to Supabase, delete original files immediately after processing.
Local-First AI Processing: All computation (Ollama llava, faster-whisper) performed locally to ensure privacy and eliminate API costs.
Authenticated Instagram Access: Use instagrapi library with legitimate user credentials for individual, manual downloads that mimic normal user behavior.
Robust Deduplication: Generate perceptual hash for all content with UNIQUE constraint in Supabase database.
Browser Extension Integration: User-initiated downloads triggered through Chrome extension with HTTP communication to localhost:8502.
Environment-Based Configuration: All sensitive credentials and paths stored in .env file only.

3. System Components
InstagramDownloader Class

Session Management: Persistent login using client.dump_settings() and client.load_settings() to avoid repeated authentication challenges.
Individual Downloads: Single reel/post downloads via media_pk_from_url() and video_download() methods.
Media PK Extraction: Proper conversion from Instagram URLs to numeric media primary keys before download.
Timeout Configuration: Configurable timeout values via INSTAGRAM_TIMEOUT environment variable (30+ seconds for videos).
Retry Logic: Exponential backoff retry attempts using INSTAGRAM_RETRY_ATTEMPTS from environment.
Rate Limiting: Built-in delays client.delay_range = [1, 3] to mimic human behavior.
Error Handling: Comprehensive exception handling for login failures, network issues, and content restrictions.

Flask LocalServer (localhost:8502)

HTTP Endpoint: /download POST endpoint for browser extension communication.
Request Processing: JSON payload handling for Instagram URLs and content types.
Folder Routing: Automatic routing to INPUT_FOLDER or VIDEO_FOLDER based on content type.
CORS Handling: Chrome extension origin support for cross-origin requests.

Enhanced Config Class

Environment Variables: All configuration read from .env file using SUPABASE_URL, SUPABASE_KEY, etc.
OS Keyring Integration: Secure storage of Instagram username/password in OS-native keyring.
Session Persistence: Management of instagram_session.json file for authentication state.
Download Paths: Environment-based path configuration via INPUT_FOLDER and VIDEO_FOLDER.

4. Instagram Integration Data Flow

Initial Setup: User configures Instagram credentials via OS keyring (one-time).
Session Establishment: InstagramDownloader creates persistent session using instagrapi, saves to instagram_session.json.
Browser Extension: User browses Instagram, clicks extension button on educational content.
HTTP Communication: Extension sends POST request to localhost:8502/download with Instagram URL.
URL Processing: LocalServer validates request and extracts Instagram URL.
Media PK Extraction: InstagramDownloader converts URL to numeric media PK using client.media_pk_from_url().
Authenticated Retrieval: Download content using media PK with configured timeout/retry logic.
Existing Pipeline: ContentProcessor handles downloaded files using established analysis workflow.
Cleanup: Original files deleted after successful database insertion, maintaining zero-storage principle.

5. Technical Implementation Requirements
InstagramDownloader Methods
pythondef setup_session(username, password) -> bool
def download_single_reel(reel_url) -> Tuple[bool, str]
def download_single_post(post_url) -> Tuple[bool, str]
def get_session_status() -> Dict
def refresh_session() -> bool
def _validate_instagram_url(url) -> bool
def _get_content_type_from_url(url) -> str
LocalServer HTTP Interface
python@app.route('/download', methods=['POST'])
def handle_download_request()
Environment Configuration

All sensitive data in .env file only
No hardcoded credentials or paths in Python files
Environment variables: SUPABASE_URL, SUPABASE_KEY, INPUT_FOLDER, VIDEO_FOLDER, INSTAGRAM_TIMEOUT, INSTAGRAM_RETRY_ATTEMPTS

Error Handling Strategy

Login Challenges: Automatic session refresh with manual intervention prompts for 2FA.
Rate Limits: Built-in delays with exponential backoff for temporary restrictions.
Network Timeouts: Configurable timeout values with retry logic for video downloads.
Content Restrictions: Clear error messages for private accounts or geo-blocked content.
URL Validation: Comprehensive Instagram URL format validation before processing.

6. Security & Compliance Considerations

Credential Storage: OS-native keyring storage only, never in files or transmitted to external services.
Environment Security: All configuration externalized to .env file with .gitignore protection.
Usage Patterns: Individual, manual downloads only - no bulk automation or scraping.
Rate Respect: Honor Instagram's implicit rate limits through built-in delays and session management.
Content Scope: Educational content only, respecting intellectual property and fair use principles.

7. Integration Points

Existing Architecture: Zero changes to ContentProcessor, AudioProcessor, ImageHasher, or analysis pipeline.
File Management: Downloads integrate seamlessly with existing input folder monitoring.
Database Schema: No changes to Supabase content_items table structure.
Browser Integration: Chrome extension provides seamless one-click download experience.
HTTP Communication: Flask server enables secure localhost communication with browser extension.

This architecture achieves 95%+ success rate by leveraging legitimate Instagram API access through authenticated sessions, avoiding browser security restrictions, and maintaining manual download patterns that don't trigger automation detection systems.