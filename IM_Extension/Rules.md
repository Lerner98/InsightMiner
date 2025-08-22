# InsightMiner Extension: HTTP Communication Architecture & Rules (v3.0)
## 1. Project Goal & Evolution
The extension acts as a seamless Instagram content acquisition interface that communicates with the local InsightMiner Python application via HTTP API. Instead of handling downloads directly, the extension triggers downloads through the established localhost HTTP server, leveraging authenticated Instagram sessions and existing processing infrastructure.

## 2. Core Principles
HTTP Communication: The extension sends Instagram URLs to the local Python app via HTTP POST requests to http://localhost:8502/download. No direct file downloads or storage.
Session Delegation: All Instagram authentication and download operations are handled by the Python app's InstagramDownloader class with persistent sessions.
Real-time Feedback: Button states reflect HTTP response status from the local server, providing immediate user feedback on download success/failure.
Zero Configuration: Extension requires no setup - all Instagram credentials and folder paths are managed in the Python application.

## 3. Updated File Architecture (Manifest V3)

manifest.json: Defines permissions for Instagram host access only. No download, storage, or notification permissions needed.
background.js: Simplified service worker that handles HTTP communication with localhost:8502. No storage management required.
content.js: Injects "Mine" buttons and sends Instagram URLs to background for HTTP transmission to Python app.
popup.html/popup.js: Optional status interface showing connection to local Python app and basic statistics.
styles.css: Button styling for injection and state management.

## 4. HTTP Communication Protocol
Primary Endpoint Communication:

POST http://localhost:8502/download: Send Instagram URL with JSON payload {url: string, type: "auto"}
Response Format: {success: boolean, message: string, folder?: string}

Extension Message Actions (Simplified):

sendToLocalApp: Sent from content.js to background.js with Instagram URL data
getServerStatus: Optional health check to verify Python app connectivity

## 5. Core Functionality Specification
Button Injection & URL Extraction:

Content Detection: Scan <article> tags for Instagram posts/reels
URL Extraction: Extract window.location.href as the Instagram post URL for API transmission
Button Placement: Inject into action bar near existing Instagram interaction buttons

HTTP Request Flow:

User clicks "Mine" button on Instagram content
content.js extracts current Instagram URL and media type
Background script sends POST request to http://localhost:8502/download
Python app handles authentication, download, and processing
HTTP response updates button state (✅ Mined / ❌ Failed)

State Management:

Default State: "⛏️ Mine" button ready for interaction
Processing State: "Mining..." with disabled button during HTTP request
Success State: "✅ Mined" with green styling after successful download
Error State: "❌ Failed" with red styling for connection/download failures

## 6. Error Handling & Fallbacks
Connection Failures:

Display clear error messages when Python app is not running
Graceful degradation when localhost:8502 is unreachable
Timeout handling for slow HTTP responses

Instagram Content Restrictions:

Handle private account errors from Python app responses
Display appropriate messages for geo-blocked or deleted content
Rate limiting feedback from Instagram API

## 7. Technical Integration
No Storage Requirements:

Extension stores no user data or configuration
All Instagram credentials managed in Python application
Download paths configured in Python app setup

Dependency on Python App:

Extension requires running InsightMiner Python application
Automatic detection of local server availability
Clear user guidance when Python app is offline

This architecture leverages the proven localhost HTTP communication pattern while maintaining the Instagram authentication and download capabilities established in the Python application's InstagramDownloader system.