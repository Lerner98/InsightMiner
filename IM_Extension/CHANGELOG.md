# InsightMiner Extension Changelog

All notable changes to this project will be documented in this file.

## [6.0.0] - 2025-08-22

### 🔄 MAJOR: HTTP Communication Architecture Transformation

**BREAKING CHANGES**: Complete refactor from direct download system to HTTP communication with local Python Flask server.

#### 🗑️ Removed
- **Direct download functionality** - No longer attempts Instagram CDN downloads
- **chrome.downloads API** - Eliminated all download-related permissions and logic
- **chrome.notifications API** - Removed notification system
- **chrome.declarativeNetRequest** - No longer needed for header modification
- **rules.json** - Declarative net request rules removed
- **Folder path configuration** - Download paths now managed by Python app
- **XMLHttpRequest blob approach** - Simplified to URL-only messaging

#### ✨ Added
- **HTTP Communication System** - POST requests to `localhost:8502/download`
- **Python App Connection Monitoring** - Real-time connection status in popup
- **Health Check Endpoint** - GET requests to `localhost:8502/health`
- **Connection Status UI** - Visual indicator for Python app availability
- **Enhanced Error Handling** - Specific messaging for offline/connection issues
- **Button State Management** - Auto-reset for failed states with 3-second timeout

#### 🔧 Modified
- **manifest.json**: Reduced permissions to storage and Instagram host access only
- **background.js**: Replaced download logic with fetch() HTTP requests
- **content.js**: Simplified to send only Instagram post URLs to background
- **popup.html**: Removed folder configuration, added connection status display
- **popup.js**: Added connection checking and status management

#### 📡 Communication Protocol
```javascript
// Request to Python app
POST http://localhost:8502/download
{
  "url": "https://instagram.com/p/ABC123",
  "type": "auto"
}

// Response from Python app
{
  "success": boolean,
  "message": string,
  "folder": string (optional)
}
```

#### 🛡️ Error Handling
- **Connection refused**: "Python app not running. Please start InsightMiner application."
- **Timeout errors**: "Connection timeout"
- **HTTP errors**: "HTTP [status]: [statusText]"
- **Network errors**: "Connection error: [details]"

#### 🎯 Architectural Compliance
This version fully implements the HTTP communication architecture specified in Rules.md v3.0, transforming the extension into a simple HTTP client that delegates all Instagram operations to the local Python application.

---

## Previous Validation Report

### Final Validation Report

#### Part 1: Syntax & Lint Check Results

✅ background.js - PASS - No syntax errors or typos detected
✅ content.js - PASS - No syntax errors or typos detected  
✅ popup.js - PASS - No syntax errors or typos detected

#### Part 2: Architectural Compliance Check Results

✅ background.js - PASS - Fully compliant with Rules.md:
- Correctly handles all 4 required message actions (getData, saveSettings, resetStats, downloadContent)
- Uses proper storage APIs (chrome.storage.sync for settings, chrome.storage.local for stats)
- Implements correct filename generation format: [platform]_[type]_[contentId]_[timestamp].[extension]
- Proper error handling and async response patterns

✅ content.js - PASS - Fully compliant with Rules.md:
- Only targets Instagram content within <article> tags
- Uses robust selectors for media detection (div[role="img"] for images, video elements)
- Implements proper button state management (Mine → Mining... → ✅ Mined / ❌ Failed)
- Uses MutationObserver for efficient dynamic content detection
- Correctly sends downloadContent messages to background.js

✅ popup.js - PASS - Fully compliant with Rules.md:
- Correctly sends all required messages (getData, saveSettings, resetStats)
- Implements proper UI feedback and error handling
- Validates input (prevents empty paths)
- Handles async operations correctly with proper status updates

#### Summary

All three JavaScript files pass both syntax validation and architectural compliance checks. The extension code perfectly aligns with the specifications in Rules.md and contains no syntax errors or architectural violations.