# InsightMiner

**Transform Instagram educational content into searchable knowledge with local AI processing**

InsightMiner is a personal content intelligence platform that extracts valuable insights from Instagram reels and posts using local AI, storing only analysis data in a secure database. Built for researchers, students, and professionals who want to study educational content without the noise of social media.

## Core Architecture

**Zero-Storage Backend** | **Local AI Processing** | **Browser Integration**

- Process media locally with Ollama vision models
- Store only text analysis, never original files
- One-click content acquisition via browser extension
- Search and categorize insights through Streamlit interface

## Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Backend** | Python + Streamlit | Main application interface |
| **AI Processing** | Ollama (llava model) | Vision analysis & content extraction |
| **Audio Processing** | faster-whisper | Video transcription |
| **OCR** | pytesseract | Text extraction from images |
| **Database** | Supabase | Analysis storage with full-text search |
| **Instagram API** | instagrapi | Authenticated content acquisition |
| **Browser Extension** | Chrome Manifest V3 | One-click download interface |
| **Security** | OS Keyring | Encrypted credential storage |

## Key Features

### Intelligent Content Analysis
- **Hybrid Analysis**: Combines OCR, vision AI, and audio transcription
- **Content Categorization**: Automatically sorts by Tech, Business, Education, Health, etc.
- **Deduplication**: Prevents processing the same content twice
- **Quality Filtering**: Confidence scoring to surface valuable insights

### Secure Architecture
- **OS-Native Encryption**: Credentials stored in Windows Credential Manager/macOS Keychain
- **Local Processing**: All AI computation happens on your machine
