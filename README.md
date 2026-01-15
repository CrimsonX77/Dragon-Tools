# Dragon-Tools
Collection of works
# 🐉 Dragon Tools

**A professional suite of PyQt6-based utilities for content creation and productivity**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PyQt6](https://img.shields.io/badge/GUI-PyQt6-green.svg)](https://www.riverbankcomputing.com/software/pyqt/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🎯 Overview

Dragon Tools is a collection of three powerful, interconnected desktop applications designed to streamline your content creation workflow:

### 🎙️ **Scribe** - Speech-to-Text Dictation
Multi-backend speech recognition with clipboard management and favorites system.

**Features:**
- Multiple recognition backends (Google Cloud, OpenAI Whisper, Local Offline)
- Real-time transcription with visual feedback
- Clipboard history with favorites
- Clean, deterministic state management
- Crimson/Gold theme

**Backends:**
- **Google Cloud Speech-to-Text** - High accuracy cloud service
- **OpenAI Whisper** - State-of-the-art local transcription
- **Local Offline** - Privacy-focused offline recognition

---

### 📺 **Sigrow** - Multi-Platform Content Router
Secure content distribution across multiple platforms with encrypted credential storage.

**Features:**
- Multi-platform content upload (YouTube, Twitter, Instagram, TikTok, Reddit)
- Encrypted credential vault using Fernet encryption
- Content preview (video, audio, images)
- Platform authentication management
- Progress tracking for uploads
- Local storage fallback

**Supported Platforms:**
- ✅ YouTube (fully implemented)
- 🚧 Twitter/X (placeholder)
- 🚧 Instagram (placeholder)
- 🚧 TikTok (placeholder)
- 🚧 Reddit (placeholder)
- ✅ Local Storage

---

### 🔊 **Speaker** - Edge-TTS Text-to-Speech
High-quality text-to-speech using Microsoft Edge TTS with extensive voice options.

**Features:**
- 200+ voices across multiple languages
- Adjustable rate, pitch, and volume
- Smart text chunking for long content
- Save audio to file or play directly
- Socket-based IPC for external control
- Text formatting options

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+** ([Download](https://www.python.org/downloads/))
- **pip** (Python package manager)
- **Git** ([Download](https://git-scm.com/downloads))

### Installation

```bash
# Clone the repository
git clone https://github.com/crimsonx77/Dragon-Tools.git
cd Dragon-Tools

# Install dependencies
pip install -r requirements.txt

# Linux/macOS: Make launcher executable
chmod +x launch_tools.sh
```

### Launch All Tools

**Windows:**
```cmd
launch_tools.bat
```

**Linux/macOS:**
```bash
./launch_tools.sh
```

### Launch Individual Tools

```bash
# Scribe - Speech-to-Text
python scribe.py

# Sigrow - Content Router
python sigrow.py

# Speaker - Text-to-Speech
python speaker.py
```

---

## 📦 Dependencies

Core libraries:
- **PyQt6** - Modern GUI framework
- **edge-tts** - Microsoft Edge TTS
- **SpeechRecognition** - Multi-backend speech recognition
- **cryptography** - Secure credential storage
- **google-cloud-speech** - Google Cloud Speech-to-Text
- **openai-whisper** - OpenAI Whisper transcription
- **pygame** - Audio playback

See [requirements.txt](requirements.txt) for complete list.

---

## 🎨 Theme

All tools feature the **Crimson/Gold/Black/Silver** theme for a consistent, professional appearance.

**Colors:**
- Primary: Crimson Red (`#8B0000`)
- Accent: Gold (`#FFD700`)
- Background: Dark (`#1a1a1a`)
- Text: Light Gray (`#e0e0e0`)

---

## 🔧 Configuration

### Scribe
Configuration is managed through the GUI. Speech recognition backends are automatically detected and enabled based on installed dependencies.

### Sigrow
Credentials are stored in encrypted vault files:
- Vault: `~/.sigrow_vault.enc`
- Key: `~/.sigrow_key`

Use the Settings dialog to configure platform credentials.

### Speaker
Configuration stored at: `~/.aetherion_tts_config.json`

Settings include:
- Last used voice
- Rate/volume preferences
- Chunk size

---

## 📖 Usage Examples

### Scribe - Dictation Workflow
1. Select recognition backend (Auto, Google, Whisper, Local)
2. Click "Start Listening"
3. Speak clearly into microphone
4. Click "Stop & Transcribe"
5. Copy output to clipboard or save to favorites

### Sigrow - Content Upload
1. Load content file (video, audio, image, text)
2. Preview content in player
3. Select target platforms
4. Authenticate with platforms (if needed)
5. Click "Upload to All Platforms"
6. View upload progress and results

### Speaker - Text-to-Speech
1. Enter or load text
2. Select voice from 200+ options
3. Adjust rate and volume
4. Click Play to hear immediately
5. Or save to audio file

---

## 🔐 Security

- **Credential Encryption**: Sigrow uses Fernet symmetric encryption for credential storage
- **Local Key Storage**: Encryption keys stored with restricted permissions (0600)
- **No Plaintext Secrets**: All API keys and tokens encrypted at rest

---

## 🛠️ Development

### Project Structure
```
Dragon-Tools/
├── scribe.py              # Speech-to-Text application
├── sigrow.py              # Content Router application
├── speaker.py             # Text-to-Speech application
├── foundations/           # Shared utilities
│   ├── __init__.py
│   └── crimson_theme.py   # PyQt6 theme styling
├── requirements.txt       # Python dependencies
├── launch_tools.bat       # Windows launcher
├── launch_tools.sh        # Linux/macOS launcher
├── README.md              # This file
└── .gitignore            # Git ignore patterns
```

### Contributing
Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

---

## 📝 Known Issues

- **Whisper Backend**: First load may be slow due to model download
- **Google Cloud**: Requires valid credentials and API key
- **PyAudio**: May require system audio libraries on Linux

### Linux Audio Setup
```bash
# Debian/Ubuntu
sudo apt install portaudio19-dev python3-pyaudio

# Fedora
sudo dnf install portaudio-devel

# Arch
sudo pacman -S portaudio
```

---

## 🗺️ Roadmap

- [ ] Complete Twitter/X API integration
- [ ] Complete Instagram API integration
- [ ] Complete TikTok API integration
- [ ] Complete Reddit API integration
- [ ] Add batch processing for multiple files
- [ ] Add scheduling for uploads
- [ ] Add macro recording for dictation
- [ ] Add custom vocabulary for speech recognition
- [ ] Add voice training profiles

---

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details.

---

## 👤 Author

**Crimson Valentine**
- GitHub: [@crimsonx77](https://github.com/crimsonx77)

---

## 🙏 Acknowledgments

- Built with assistance from AI tools
- PyQt6 for the excellent GUI framework
- Microsoft Edge TTS for high-quality voices
- OpenAI Whisper for accurate transcription
- Google Cloud for reliable speech services

---

## 📞 Support

For issues, questions, or suggestions:
- Open an issue on [GitHub](https://github.com/crimsonx77/Dragon-Tools/issues)
- Check existing issues for solutions

---

**Made with 🔥 by Crimson Valentine**
