# InsightMiner

**Transform Instagram educational content into searchable knowledge with local AI processing**

InsightMiner is a personal content intelligence platform that extracts valuable insights from Instagram reels and posts using local AI, storing only analysis data in a secure database. Built for researchers, students, and professionals who want to study educational content without the noise of social media.

## Core Architecture
**Zero-Storage Backend | Local AI Processing | Browser Integration**

- Process media locally with Ollama vision models
- Store only text analysis, never original files
- One-click content acquisition via browser extension
- Search and categorize insights through Streamlit interface

## Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Backend | Python + Streamlit | Main application interface |
| AI Processing | Ollama (llava model) | Vision analysis & content extraction |
| Audio Processing | faster-whisper | Video transcription |
| OCR | pytesseract | Text extraction from images |
| Database | Supabase | Analysis storage with full-text search |
| Instagram API | instagrapi | Authenticated content acquisition |
| Browser Extension | Chrome Manifest V3 | One-click download interface |
| Security | OS Keyring | Encrypted credential storage |

## Key Features

### Intelligent Content Analysis
- **Hybrid Analysis**: Combines OCR, vision AI, and audio transcription
- **Content Categorization**: Automatically sorts by Tech, Business, Education, Health, etc.
- **Deduplication**: Prevents processing the same content twice
- **Quality Filtering**: Confidence scoring to surface valuable insights

### Secure Architecture
- **OS-Native Encryption**: Credentials stored in Windows Credential Manager/macOS Keychain
- **Local Processing**: All AI computation happens on your machine
- **Zero File Storage**: Only analysis text is saved, original media deleted immediately
- **Environment-Based Config**: All settings managed through secure environment variables

### Browser Integration
- **One-Click Mining**: Browser extension injects download buttons into Instagram
- **HTTP Communication**: Extension communicates with local Python app via localhost:8502
- **Real-Time Feedback**: Button states show download progress and results
- **Timeout Resilience**: Configurable timeouts and retry logic for reliable downloads

## Installation

### Prerequisites
- Python 3.9+
- Chrome browser
- Ollama with llava model
- FFmpeg (for video processing)

### Quick Start

1. **Clone and install dependencies**
```bash
git clone https://github.com/yourusername/insightminer.git
cd insightminer
pip install -r requirements.txt
```

2. **Install Ollama and llava model**
```bash
# Install Ollama from https://ollama.ai
ollama pull llava
```

3. **Configure environment variables**
```bash
# Create .env file with your configuration
SUPABASE_URL=your-supabase-url
SUPABASE_KEY=your-supabase-key
INPUT_FOLDER=path/to/images
VIDEO_FOLDER=path/to/videos
INSTAGRAM_TIMEOUT=30
INSTAGRAM_RETRY_ATTEMPTS=3
```

4. **Start the application**
```bash
streamlit run insight_miner.py
# Navigate to Settings to configure Instagram credentials
```

5. **Install browser extension**
- Load the `IM_EXTENSION` folder as an unpacked extension in Chrome
- Extension will communicate with your local Python app

## Usage

### Basic Workflow

1. **Start the application**
```bash
streamlit run insight_miner.py
```

2. **Configure Instagram credentials** (stored securely in OS keyring)
   - Go to Settings page
   - Enter Instagram username/password
   - Test connection

3. **Mine content from Instagram**
   - Browse Instagram normally
   - Click "Mine" button on educational content
   - Content automatically processed and categorized

4. **Search and analyze insights**
   - Use the Gallery to browse processed content
   - Search by keywords, categories, or confidence levels
   - Export insights for further research

## Architecture Diagram

```
Browser Extension → HTTP → Python Flask Server → Instagram API
                               ↓
                         Local AI Processing
                    (Ollama + OCR + Whisper)
                               ↓
                        Supabase Database
                               ↓
                       Streamlit Interface
```

## Configuration

### Environment Variables

The application uses environment variables for all configuration:

```env
# Database Configuration
SUPABASE_URL=your-supabase-project-url
SUPABASE_KEY=your-supabase-anon-key

# Download Folders
INPUT_FOLDER=C:/Users/username/Downloads/InsightMiner/images
VIDEO_FOLDER=C:/Users/username/Downloads/InsightMiner/videos

# Instagram Download Settings
INSTAGRAM_TIMEOUT=30
INSTAGRAM_RETRY_ATTEMPTS=3
```

**Security Note**: Instagram credentials are stored separately using your OS keyring system, never in environment variables or files.

### Processing Parameters
- **Confidence Threshold**: Adjust minimum confidence for content categorization
- **Batch Size**: Control number of files processed simultaneously
- **Frame Extraction**: Configure video frame sampling rate
- **Content Categories**: Tech, Business, Education, Health, Lifestyle, Finance, Marketing, Personal Development

## Security Features

### Credential Protection
- **OS Keyring Integration**: Uses Windows Credential Manager, macOS Keychain, or Linux GNOME Keyring
- **Zero Plaintext Storage**: No credentials stored in configuration files
- **Local-Only Access**: Credentials never transmitted over networks
- **Environment-Based Config**: All settings externalized to `.env` file

### Privacy Safeguards
- **No File Storage**: Original media files deleted after processing
- **Local AI**: All content analysis happens on your machine
- **Minimal Data**: Only text insights stored in database
- **Deduplication**: Prevents accidental reprocessing

## API Reference

### HTTP Endpoints (Local Server)

| Endpoint | Method | Purpose |
|----------|---------|---------|
| `/health` | GET | Server status and configuration |
| `/status` | GET | Instagram session status |
| `/download` | POST | Process Instagram URL |

#### Example Request
```javascript
POST http://localhost:8502/download
{
  "url": "https://instagram.com/p/ABC123",
  "type": "auto"
}
```

## Development

### Project Structure
```
insightminer/
├── insight_miner.py      # Main application
├── requirements.txt      # Python dependencies
├── .env                  # Environment configuration
├── IM_EXTENSION/         # Browser extension
│   ├── manifest.json
│   ├── background.js
│   ├── content.js
│   └── popup.html
└── README.md
```

### Key Classes
- **ContentProcessor**: Main orchestrator for analysis pipeline
- **InstagramDownloader**: Handles Instagram authentication and downloads
- **AudioProcessor**: Video transcription with faster-whisper
- **ImageHasher**: Deduplication system
- **LocalServer**: Flask HTTP server for browser communication

## Troubleshooting

### Common Issues

**Instagram Login Fails**
- Verify credentials in Settings page
- Check if account requires 2FA
- Ensure account isn't temporarily restricted

**Ollama Model Not Found**
- Install Ollama: `ollama pull llava`
- Verify Ollama service is running
- Check model compatibility

**Browser Extension Not Working**
- Reload extension in Chrome
- Check Python app is running on localhost:8502
- Verify extension permissions

**Download Timeouts**
- Check `INSTAGRAM_TIMEOUT` in `.env` file (should be 30+ seconds)
- Verify `INSTAGRAM_RETRY_ATTEMPTS` setting
- Check network connectivity

**Processing Fails**
- Check FFmpeg installation for video processing
- Verify sufficient disk space
- Review logs in Streamlit interface
- Ensure `.env` file is properly configured

## Contributing

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Install development dependencies
4. Run tests before submitting PRs

### Architecture Guidelines
- Maintain zero-storage principle
- Local-first processing for privacy
- Environment-based configuration only
- Comprehensive error handling
- Security-first credential management

## License

MIT License - see LICENSE file for details.

**Disclaimer**: This tool is for educational and research purposes. Users are responsible for complying with Instagram's Terms of Service and applicable laws regarding content usage.