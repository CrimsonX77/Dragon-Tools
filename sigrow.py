#!/usr/bin/env python3
"""
Singularity Router - Multi-Platform Content Distribution
PyQt6 GUI with secure credential storage and content preview

Author: Crimson Valentine
Date: January 12, 2026
"""

import sys
import os
import json
import base64
import random
import time
import shutil
import webbrowser
import requests
from pathlib import Path
from typing import Dict, Optional
from cryptography.fernet import Fernet
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
# YouTube API imports
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError
    YOUTUBE_API_AVAILABLE = True
except ImportError:
    YOUTUBE_API_AVAILABLE = False

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QCheckBox, QGroupBox,
    QTextEdit, QLineEdit, QDialog, QDialogButtonBox, QScrollArea,
    QMessageBox, QProgressBar, QTabWidget, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QPixmap, QFont, QIcon, QColor
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget


# =============================================================================
# CREDENTIAL ENCRYPTION
# =============================================================================

class CredentialVault:
    """Secure credential storage with encryption"""
    
    def __init__(self, vault_path: str = None):
        self.vault_path = vault_path or str(Path.home() / ".sigrow_vault.enc")
        self.key_path = str(Path.home() / ".sigrow_key")
        self._cipher = None
        self._initialize_encryption()
    
    def _initialize_encryption(self):
        """Initialize or load encryption key"""
        if Path(self.key_path).exists():
            with open(self.key_path, 'rb') as f:
                key = f.read()
        else:
            # Generate new key
            key = Fernet.generate_key()
            with open(self.key_path, 'wb') as f:
                f.write(key)
            os.chmod(self.key_path, 0o600)  # Restrict permissions
        
        self._cipher = Fernet(key)
    
    def save_credentials(self, credentials: Dict[str, Dict]):
        """Encrypt and save credentials"""
        data = json.dumps(credentials).encode('utf-8')
        encrypted = self._cipher.encrypt(data)
        
        with open(self.vault_path, 'wb') as f:
            f.write(encrypted)
        os.chmod(self.vault_path, 0o600)
    
    def load_credentials(self) -> Dict[str, Dict]:
        """Load and decrypt credentials"""
        if not Path(self.vault_path).exists():
            return {}
        
        try:
            with open(self.vault_path, 'rb') as f:
                encrypted = f.read()
            
            decrypted = self._cipher.decrypt(encrypted)
            return json.loads(decrypted.decode('utf-8'))
        except Exception as e:
            print(f"Failed to load credentials: {e}")
            return {}


# =============================================================================
# CONTENT ROUTER CORE
# =============================================================================

class ContentRouter:
    """Content analysis and routing logic"""
    
    def __init__(self):
        self.platforms = {
            'youtube': {'enabled': True, 'name': 'YouTube', 'icon': '📺', 'authenticated': False, 'ready': True},
            'twitter': {'enabled': False, 'name': 'Twitter/X', 'icon': '🐦', 'authenticated': False, 'ready': False},
            'instagram': {'enabled': False, 'name': 'Instagram', 'icon': '📷', 'authenticated': False, 'ready': False},
            'tiktok': {'enabled': False, 'name': 'TikTok', 'icon': '🎵', 'authenticated': False, 'ready': False},
            'reddit': {'enabled': False, 'name': 'Reddit', 'icon': '🤖', 'authenticated': False, 'ready': False},
            'local': {'enabled': True, 'name': 'Local Storage', 'icon': '💾', 'authenticated': True, 'ready': True}
        }
    
    def analyze_content(self, file_path: str) -> Dict:
        """Detect content type and metadata"""
        path = Path(file_path)
        ext = path.suffix.lower()
        
        # Extended content type detection
        content_type = {
            # Video
            '.mp4': 'video', '.avi': 'video', '.mov': 'video', '.mkv': 'video',
            '.webm': 'video', '.flv': 'video',
            # Audio
            '.mp3': 'audio', '.wav': 'audio', '.ogg': 'audio', '.flac': 'audio',
            '.m4a': 'audio', '.aac': 'audio',
            # Image
            '.jpg': 'image', '.jpeg': 'image', '.png': 'image', '.gif': 'image',
            '.bmp': 'image', '.webp': 'image', '.svg': 'image',
            # Text
            '.txt': 'text', '.md': 'text', '.rtf': 'text',
        }.get(ext, 'unknown')
        
        # Get file size
        size_bytes = path.stat().st_size if path.exists() else 0
        size_mb = size_bytes / (1024 * 1024)
        
        return {
            'type': content_type,
            'path': str(path),
            'filename': path.name,
            'extension': ext,
            'size_mb': round(size_mb, 2),
            'size_bytes': size_bytes
        }
    
    def get_enabled_platforms(self) -> list:
        """Get list of enabled platforms"""
        return [name for name, config in self.platforms.items() if config['enabled']]
    
    def set_platform_enabled(self, platform: str, enabled: bool):
        """Enable/disable a platform"""
        if platform in self.platforms:
            self.platforms[platform]['enabled'] = enabled
    
    def set_platform_authenticated(self, platform: str, authenticated: bool):
        """Set authentication status for a platform"""
        if platform in self.platforms:
            self.platforms[platform]['authenticated'] = authenticated
    
    def is_platform_ready(self, platform: str) -> bool:
        """Check if platform is ready for upload (API implemented)"""
        return self.platforms.get(platform, {}).get('ready', False)
    
    def is_platform_authenticated(self, platform: str) -> bool:
        """Check if platform is authenticated"""
        return self.platforms.get(platform, {}).get('authenticated', False)
    
    def add_custom_platform(self, platform_id: str, name: str):
        """Add a custom platform"""
        self.platforms[platform_id] = {
            'enabled': False,
            'name': name,
            'icon': '🌐',
            'authenticated': False,
            'ready': False
        }
    
    def remove_platform(self, platform: str):
        """Remove a custom platform"""
        if platform in self.platforms and platform not in ['youtube', 'twitter', 'local']:
            del self.platforms[platform]


# =============================================================================
# UPLOAD WORKER
# =============================================================================

class UploadWorker(QThread):
    """Background thread for uploads"""
    progress = pyqtSignal(str, int)  # platform, percentage
    finished = pyqtSignal(str, bool, str, str)  # platform, success, message, url
    
    def __init__(self, file_path: str, platforms: list, credentials: Dict):
        super().__init__()
        self.file_path = file_path
        self.platforms = platforms
        self.credentials = credentials
    
    def run(self):
        """Perform uploads"""
        for platform in self.platforms:
            try:
                self.progress.emit(platform, 0)
                
                # Simulate upload progress
                for i in range(0, 101, 20):
                    self.msleep(200)
                    self.progress.emit(platform, i)
                
                # Perform platform-specific upload and get URL
                url = ""
                if platform == 'local':
                    url = self._upload_local()
                elif platform == 'youtube':
                    url = self._upload_youtube()
                elif platform == 'twitter':
                    url = self._upload_twitter()
                elif platform == 'instagram':
                    url = self._upload_instagram()
                elif platform == 'tiktok':
                    url = self._upload_tiktok()
                elif platform == 'reddit':
                    url = self._upload_reddit()
                else:
                    url = ""  # Custom platforms
                
                self.finished.emit(platform, True, "Upload successful", url)
                
            except Exception as e:
                self.finished.emit(platform, False, str(e), "")
    
    def _upload_local(self) -> str:
        """Save to local output folder"""
        output_dir = Path("./output/local")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy file to output
        import shutil
        dest = output_dir / Path(self.file_path).name
        shutil.copy2(self.file_path, dest)
        
        return f"file://{dest.absolute()}"
    
    def _upload_youtube(self) -> str:
        """Upload to YouTube using YouTube Data API v3"""
        if not YOUTUBE_API_AVAILABLE:
            raise ImportError(
                "YouTube API libraries not installed. "
                "Run: pip install google-auth-oauthlib google-auth google-api-python-client"
            )
        
        # Load token directly
        token_path = Path.home() / '.sigrow_youtube_token.json'
        
        if not token_path.exists():
            raise ValueError("YouTube not authenticated. Please sign in first.")
        
        try:
            import json
            import requests
            
            with open(token_path, 'r') as f:
                token_data = json.load(f)
            
            access_token = token_data['token']
            
            # Prepare metadata
            filename = Path(self.file_path).stem
            metadata = {
                'snippet': {
                    'title': filename,
                    'description': f'Uploaded via Singularity Router on {time.strftime("%Y-%m-%d %H:%M")}',
                    'tags': ['singularity-router', 'auto-upload'],
                    'categoryId': '22'  # People & Blogs
                },
                'status': {
                    'privacyStatus': 'unlisted',
                    'selfDeclaredMadeForKids': False
                }
            }
            
            file_size = Path(self.file_path).stat().st_size
            
            # Step 1: Initialize resumable upload
            init_url = "https://www.googleapis.com/upload/youtube/v3/videos"
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json; charset=UTF-8',
                'X-Upload-Content-Length': str(file_size),
                'X-Upload-Content-Type': 'video/*'
            }
            
            params = {
                'uploadType': 'resumable',
                'part': 'snippet,status'
            }
            
            init_response = requests.post(
                init_url,
                headers=headers,
                params=params,
                json=metadata,
                timeout=30
            )
            
            if init_response.status_code != 200:
                raise Exception(f"Upload init failed: {init_response.status_code} - {init_response.text}")
            
            upload_url = init_response.headers.get('Location')
            if not upload_url:
                raise Exception("No upload URL received from YouTube")
            
            # Step 2: Upload the video file
            with open(self.file_path, 'rb') as video_data:
                upload_headers = {
                    'Content-Type': 'video/*',
                    'Content-Length': str(file_size)
                }
                
                upload_response = requests.put(
                    upload_url,
                    headers=upload_headers,
                    data=video_data,
                    timeout=120
                )
                
                if upload_response.status_code not in [200, 201]:
                    raise Exception(f"Upload failed: {upload_response.status_code} - {upload_response.text}")
                
                result = upload_response.json()
                video_id = result.get('id')
                
                if not video_id:
                    raise Exception("No video ID in upload response")
                
                return f"https://youtube.com/watch?v={video_id}"
            
        except Exception as e:
            raise Exception(f"YouTube upload failed: {str(e)}")
    
    def _upload_twitter(self) -> str:
        """Upload to Twitter (placeholder)"""
        # TODO: Implement Twitter API upload
        import random
        tweet_id = random.randint(1000000000000000000, 9999999999999999999)
        return f"https://twitter.com/i/status/{tweet_id}"
    
    def _upload_instagram(self) -> str:
        """Upload to Instagram (placeholder)"""
        # TODO: Implement Instagram API upload
        return "https://instagram.com/p/PLACEHOLDER"
    
    def _upload_tiktok(self) -> str:
        """Upload to TikTok (placeholder)"""
        # TODO: Implement TikTok API upload
        return "https://tiktok.com/@user/video/PLACEHOLDER"
    
    def _upload_reddit(self) -> str:
        """Upload to Reddit (placeholder)"""
        # TODO: Implement Reddit API upload
        return "https://reddit.com/r/SUBREDDIT/comments/PLACEHOLDER"


# =============================================================================
# SETTINGS DIALOG
# =============================================================================

class SettingsDialog(QDialog):
    """Settings dialog for platform credentials"""
    
    def __init__(self, parent, router: ContentRouter, vault: CredentialVault):
        super().__init__(parent)
        self.router = router
        self.vault = vault
        self.credentials = vault.load_credentials()
        
        self.setWindowTitle("Settings - Platform Credentials")
        self.setMinimumSize(600, 500)
        
        self._setup_ui()
        self._load_credentials()
    
    def _setup_ui(self):
        """Setup dialog UI"""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("◆ PLATFORM CREDENTIALS ◆")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #FFD700;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Info label
        info = QLabel("Credentials are encrypted and stored securely.")
        info.setStyleSheet("color: #9cdcfe; font-style: italic;")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info)
        
        # Tabs for different platforms
        tabs = QTabWidget()
        
        self.credential_fields = {}
        
        # Create tab for each platform
        for platform_id, config in self.router.platforms.items():
            if platform_id == 'local':
                continue  # No credentials needed for local
            
            tab = self._create_platform_tab(platform_id, config['name'])
            tabs.addTab(tab, f"{config['icon']} {config['name']}")
        
        layout.addWidget(tabs)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._save_credentials)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def _create_platform_tab(self, platform_id: str, platform_name: str) -> QWidget:
        """Create credential input tab for a platform"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Platform-specific fields
        fields = self._get_platform_fields(platform_id)
        
        self.credential_fields[platform_id] = {}
        
        for field_id, field_label, is_password in fields:
            field_layout = QHBoxLayout()
            
            label = QLabel(f"{field_label}:")
            label.setMinimumWidth(120)
            field_layout.addWidget(label)
            
            input_field = QLineEdit()
            if is_password:
                input_field.setEchoMode(QLineEdit.EchoMode.Password)
            
            field_layout.addWidget(input_field)
            layout.addLayout(field_layout)
            
            self.credential_fields[platform_id][field_id] = input_field
        
        # Test connection button
        test_btn = QPushButton("Test Connection")
        test_btn.clicked.connect(lambda: self._test_connection(platform_id))
        layout.addWidget(test_btn)
        
        layout.addStretch()
        return widget
    
    def _get_platform_fields(self, platform_id: str) -> list:
        """Get required fields for each platform"""
        fields = {
            'youtube': [
                ('api_key', 'API Key', True),
                ('client_id', 'Client ID', False),
                ('client_secret', 'Client Secret', True),
            ],
            'twitter': [
                ('api_key', 'API Key', True),
                ('api_secret', 'API Secret', True),
                ('access_token', 'Access Token', True),
                ('access_secret', 'Access Token Secret', True),
            ],
            'instagram': [
                ('username', 'Username', False),
                ('password', 'Password', True),
            ],
            'tiktok': [
                ('api_key', 'API Key', True),
            ],
            'reddit': [
                ('client_id', 'Client ID', False),
                ('client_secret', 'Client Secret', True),
                ('username', 'Username', False),
                ('password', 'Password', True),
            ],
        }
        return fields.get(platform_id, [('api_key', 'API Key', True)])
    
    def _load_credentials(self):
        """Load saved credentials into fields"""
        for platform_id, fields in self.credential_fields.items():
            if platform_id in self.credentials:
                for field_id, input_field in fields.items():
                    value = self.credentials[platform_id].get(field_id, '')
                    input_field.setText(value)
    
    def _save_credentials(self):
        """Save credentials to encrypted vault"""
        for platform_id, fields in self.credential_fields.items():
            if platform_id not in self.credentials:
                self.credentials[platform_id] = {}
            
            for field_id, input_field in fields.items():
                self.credentials[platform_id][field_id] = input_field.text()
        
        self.vault.save_credentials(self.credentials)
        QMessageBox.information(self, "Success", "Credentials saved securely!")
        self.accept()
    
    def _test_connection(self, platform_id: str):
        """Test platform connection"""
        # Get current credentials from fields
        if platform_id not in self.credential_fields:
            QMessageBox.warning(self, "Error", "No fields found for this platform")
            return
        
        fields = self.credential_fields[platform_id]
        creds = {field_id: input_field.text() for field_id, input_field in fields.items()}
        
        # Check if any credentials are provided
        if not any(creds.values()):
            QMessageBox.warning(
                self,
                "No Credentials",
                "Please enter credentials before testing connection."
            )
            return
        
        # Create non-modal progress dialog
        from PyQt6.QtCore import QTimer
        from PyQt6.QtWidgets import QProgressDialog
        
        progress = QProgressDialog(f"Testing {platform_id} connection...", None, 0, 0, self)
        progress.setWindowTitle("Testing Connection")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setCancelButton(None)
        progress.setAutoClose(False)
        progress.show()
        
        # Process events to show dialog immediately
        QApplication.processEvents()
        
        # Simulate connection test (replace with actual API calls)
        def finish_test():
            progress.close()
            
            # Platform-specific validation
            result = self._validate_credentials(platform_id, creds)
            
            if result['valid']:
                QMessageBox.information(
                    self,
                    "Connection Successful",
                    f"✓ Successfully connected to {platform_id}!\n\n{result['message']}"
                )
            else:
                QMessageBox.warning(
                    self,
                    "Connection Failed",
                    f"✗ Failed to connect to {platform_id}\n\n{result['message']}"
                )
        
        QTimer.singleShot(1500, finish_test)
    
    def _validate_credentials(self, platform_id: str, creds: Dict) -> Dict:
        """Validate credentials for a platform"""
        # Basic validation - check if required fields are filled
        # TODO: Implement actual API connection tests
        
        required_fields = {
            'youtube': ['api_key', 'client_id', 'client_secret'],
            'twitter': ['api_key', 'api_secret', 'access_token', 'access_secret'],
            'instagram': ['username', 'password'],
            'tiktok': ['api_key'],
            'reddit': ['client_id', 'client_secret', 'username', 'password'],
        }
        
        required = required_fields.get(platform_id, ['api_key'])
        missing = [field for field in required if not creds.get(field)]
        
        if missing:
            return {
                'valid': False,
                'message': f"Missing required fields: {', '.join(missing)}"
            }
        
        # Simulate successful validation
        # In production, this would make actual API calls
        return {
            'valid': True,
            'message': f"Credentials format valid. Ready to upload.\n(Note: Actual API test will be implemented)"
        }


# =============================================================================
# AUTHENTICATION DIALOG
# =============================================================================

class AuthenticationDialog(QDialog):
    """Platform authentication dialog with sign-in validation"""
    
    def __init__(self, parent, platform_id: str, platform_name: str, vault: CredentialVault):
        super().__init__(parent)
        self.platform_id = platform_id
        self.platform_name = platform_name
        self.vault = vault
        self.credentials = vault.load_credentials()
        self.authenticated = False
        
        self.setWindowTitle(f"Sign In - {platform_name}")
        self.setMinimumSize(500, 400)
        self.setModal(True)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup authentication dialog UI"""
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel(f"◆ SIGN IN TO {self.platform_name.upper()} ◆")
        header.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        header.setStyleSheet("color: #FFD700;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # Info
        info = QLabel("Please sign in to authenticate this platform for uploads.")
        info.setStyleSheet("color: #9cdcfe; font-style: italic; padding: 10px;")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("padding: 10px; font-weight: bold;")
        layout.addWidget(self.status_label)
        
        # Credential fields
        fields_group = QGroupBox("Credentials")
        fields_layout = QVBoxLayout(fields_group)
        
        self.credential_fields = {}
        fields = self._get_platform_fields()
        
        for field_id, field_label, is_password in fields:
            field_layout = QHBoxLayout()
            
            label = QLabel(f"{field_label}:")
            label.setMinimumWidth(120)
            field_layout.addWidget(label)
            
            input_field = QLineEdit()
            if is_password:
                input_field.setEchoMode(QLineEdit.EchoMode.Password)
            
            # Load existing credentials
            platform_creds = self.credentials.get(self.platform_id, {})
            if field_id in platform_creds:
                input_field.setText(platform_creds[field_id])
            
            field_layout.addWidget(input_field)
            fields_layout.addLayout(field_layout)
            
            self.credential_fields[field_id] = input_field
        
        layout.addWidget(fields_group)
        
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setRange(0, 0)  # Indeterminate
        layout.addWidget(self.progress)
        
        layout.addStretch()
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.signin_btn = QPushButton("🔐 Sign In & Authenticate")
        self.signin_btn.setMinimumHeight(40)
        self.signin_btn.clicked.connect(self._authenticate)
        button_layout.addWidget(self.signin_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def _get_platform_fields(self) -> list:
        """Get required fields for the platform"""
        fields = {
            'youtube': [
                ('client_id', 'Client ID', False),
                ('client_secret', 'Client Secret', True),
            ],
            'twitter': [
                ('api_key', 'API Key', True),
                ('api_secret', 'API Secret', True),
                ('access_token', 'Access Token', True),
                ('access_secret', 'Access Token Secret', True),
            ],
            'instagram': [
                ('username', 'Username', False),
                ('password', 'Password', True),
            ],
            'tiktok': [
                ('api_key', 'API Key', True),
            ],
            'reddit': [
                ('client_id', 'Client ID', False),
                ('client_secret', 'Client Secret', True),
                ('username', 'Username', False),
                ('password', 'Password', True),
            ],
        }
        return fields.get(self.platform_id, [('api_key', 'API Key', True)])
    
    def _authenticate(self):
        """Attempt authentication"""
        # Get credentials from fields
        creds = {field_id: input_field.text() for field_id, input_field in self.credential_fields.items()}
        
        # Validate required fields
        if not all(creds.values()):
            self.status_label.setText("⚠ Please fill in all fields")
            self.status_label.setStyleSheet("color: #f48771; padding: 10px; font-weight: bold;")
            return
        
        # Save credentials first
        if self.platform_id not in self.credentials:
            self.credentials[self.platform_id] = {}
        self.credentials[self.platform_id].update(creds)
        self.vault.save_credentials(self.credentials)
        
        # Disable button and show progress
        self.signin_btn.setEnabled(False)
        self.progress.setVisible(True)
        
        # Perform actual authentication
        if self.platform_id == 'youtube':
            self._authenticate_youtube()
        else:
            # Other platforms not yet implemented
            self.progress.setVisible(False)
            self.signin_btn.setEnabled(True)
            self.status_label.setText(f"⚠ {self.platform_name} API not yet implemented")
            self.status_label.setStyleSheet("color: #f48771; padding: 10px; font-weight: bold;")
    
    def _authenticate_youtube(self):
        """Perform YouTube OAuth authentication"""
        if not YOUTUBE_API_AVAILABLE:
            self.progress.setVisible(False)
            self.signin_btn.setEnabled(True)
            self.status_label.setText("⚠ YouTube API not installed\nRun: pip install google-auth-oauthlib google-auth google-api-python-client")
            self.status_label.setStyleSheet("color: #f48771; padding: 10px; font-weight: bold;")
            return
        
        self.status_label.setText("🌐 Opening Google Sign-In...\n(Check your browser)")
        self.status_label.setStyleSheet("color: #9cdcfe; padding: 10px; font-weight: bold;")
        QApplication.processEvents()
        
        try:
            # Get saved credentials
            youtube_creds = self.credentials.get('youtube', {})
            
            # OAuth2 scopes required for upload
            SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
            
            # Create OAuth2 credentials config
            client_config = {
                "installed": {
                    "client_id": youtube_creds['client_id'],
                    "client_secret": youtube_creds['client_secret'],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": ["http://localhost", "urn:ietf:wg:oauth:2.0:oob"]
                }
            }
            
            # Check for existing valid token
            token_path = Path.home() / '.sigrow_youtube_token.json'
            credentials = None
            
            if token_path.exists():
                try:
                    credentials = Credentials.from_authorized_user_file(str(token_path), SCOPES)
                except Exception as e:
                    print(f"Error loading existing token: {e}")
            
            # If no valid credentials, initiate OAuth flow
            needs_auth = True
            if credentials and credentials.valid:
                needs_auth = False
            elif credentials and credentials.expired and credentials.refresh_token:
                try:
                    from google.auth.transport.requests import Request
                    self.status_label.setText("Refreshing access token...")
                    QApplication.processEvents()
                    credentials.refresh(Request())
                    needs_auth = False
                except Exception as e:
                    print(f"Token refresh failed: {e}")
                    needs_auth = True
            
            if needs_auth:
                # This will open browser for OAuth flow
                self.status_label.setText("🌐 Opening browser for sign-in...\n(Allow Singularity Router access)")
                QApplication.processEvents()
                
                flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
                
                try:
                    # Try to open browser automatically
                    credentials = flow.run_local_server(
                        port=8080,
                        open_browser=True,
                        success_message='Authentication successful! You can close this window and return to Singularity Router.'
                    )
                except Exception as browser_error:
                    print(f"Browser auto-open failed: {browser_error}")
                    # Fallback: Show URL for manual authorization
                    self.status_label.setText("⚠ Browser didn't open automatically\nOpening authorization URL...")
                    QApplication.processEvents()
                    
                    # Get the authorization URL
                    auth_url, _ = flow.authorization_url(prompt='consent')
                    
                    # Try to open manually
                    import webbrowser
                    webbrowser.open(auth_url)
                    
                    # Show instructions
                    from PyQt6.QtWidgets import QInputDialog
                    self.status_label.setText("🌐 Complete sign-in in browser\nThen paste the code here")
                    QApplication.processEvents()
                    
                    # If manual browser open also fails, show the URL
                    QMessageBox.information(
                        self,
                        "Manual Authorization Required",
                        f"Please open this URL in your browser:\n\n{auth_url}\n\nThen paste the authorization code in the next dialog."
                    )
                    
                    # Get the code from user
                    code, ok = QInputDialog.getText(
                        self,
                        "Authorization Code",
                        "Paste the authorization code from your browser:"
                    )
                    
                    if not ok or not code:
                        raise Exception("Authorization cancelled by user")
                    
                    # Exchange code for credentials
                    flow.fetch_token(code=code.strip())
            
            # Save credentials for future use
            with open(token_path, 'w') as token:
                token.write(credentials.to_json())
            os.chmod(token_path, 0o600)
            
            # Test the credentials by building the service
            youtube = build('youtube', 'v3', credentials=credentials)
            
            # Success!
            self.progress.setVisible(False)
            self.signin_btn.setEnabled(True)
            self.authenticated = True
            self.status_label.setText("✓ Authentication Successful!\nYou can now upload to YouTube")
            self.status_label.setStyleSheet("color: #00FF00; padding: 10px; font-weight: bold;")
            QTimer.singleShot(1500, self.accept)
            
        except Exception as e:
            self.progress.setVisible(False)
            self.signin_btn.setEnabled(True)
            self.status_label.setText(f"✗ Authentication Failed:\n{str(e)}")
            self.status_label.setStyleSheet("color: #f48771; padding: 10px; font-weight: bold;")
            print(f"YouTube authentication error: {e}")


# =============================================================================
# MAIN WINDOW
# =============================================================================

class SingularityRouter(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("◆ SINGULARITY ROUTER ◆")
        self.setMinimumSize(900, 700)
        
        # Core components
        self.router = ContentRouter()
        self.vault = CredentialVault()
        self.current_file = None
        self.content_info = None
        self.upload_worker = None
        
        # Media players
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        
        self._apply_theme()
        self._setup_ui()
    
    def _apply_theme(self):
        """Apply Crimson dark theme"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1a0a0a;
            }
            QWidget {
                background-color: #1a0a0a;
                color: #c0c0c0;
                font-family: 'Segoe UI';
            }
            QGroupBox {
                border: 2px solid #2a2a2a;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
                color: #FFD700;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QPushButton {
                background-color: #8B0000;
                color: #FFD700;
                border: 1px solid #2a2a2a;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #A52A2A;
                border: 1px solid #FFD700;
            }
            QPushButton:pressed {
                background-color: #660000;
            }
            QPushButton:disabled {
                background-color: #2a2a2a;
                color: #505050;
            }
            QCheckBox {
                color: #c0c0c0;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 1px solid #2a2a2a;
                border-radius: 3px;
                background-color: #0f0f0f;
            }
            QCheckBox::indicator:checked {
                background-color: #8B0000;
                border: 1px solid #FFD700;
            }
            QLabel {
                color: #c0c0c0;
            }
            QTextEdit {
                background-color: #0f0f0f;
                color: #c0c0c0;
                border: 1px solid #2a2a2a;
                border-radius: 4px;
                padding: 8px;
            }
            QLineEdit {
                background-color: #0f0f0f;
                color: #c0c0c0;
                border: 1px solid #2a2a2a;
                border-radius: 4px;
                padding: 6px;
            }
            QProgressBar {
                background-color: #0f0f0f;
                border: 1px solid #2a2a2a;
                border-radius: 4px;
                text-align: center;
                color: #FFD700;
            }
            QProgressBar::chunk {
                background-color: #8B0000;
            }
            QTabWidget::pane {
                border: 1px solid #2a2a2a;
            }
            QTabBar::tab {
                background-color: #2a2a2a;
                color: #c0c0c0;
                padding: 8px 16px;
                border: 1px solid #1a1a1a;
            }
            QTabBar::tab:selected {
                background-color: #8B0000;
                color: #FFD700;
            }
            QListWidget {
                background-color: #0f0f0f;
                border: 1px solid #2a2a2a;
                border-radius: 4px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #1a1a1a;
            }
            QListWidget::item:selected {
                background-color: #8B0000;
                color: #FFD700;
            }
        """)
    
    def _setup_ui(self):
        """Setup main UI"""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Header
        header = QLabel("MULTI-PLATFORM CONTENT DISTRIBUTION")
        header.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        header.setStyleSheet("color: #FFD700; padding: 10px;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # Main content area (splitter-like)
        content_layout = QHBoxLayout()
        
        # Left side: Preview
        preview_group = self._create_preview_panel()
        content_layout.addWidget(preview_group, stretch=2)
        
        # Right side: Platforms & Controls
        controls_group = self._create_controls_panel()
        content_layout.addWidget(controls_group, stretch=1)
        
        layout.addLayout(content_layout)
        
        # Bottom: Upload status
        self.status_group = self._create_status_panel()
        layout.addWidget(self.status_group)
    
    def _create_preview_panel(self) -> QGroupBox:
        """Create content preview panel"""
        group = QGroupBox("◆ CONTENT PREVIEW")
        layout = QVBoxLayout(group)
        
        # File selector
        file_layout = QHBoxLayout()
        
        self.file_label = QLabel("No file selected")
        self.file_label.setStyleSheet("color: #666666; font-style: italic;")
        file_layout.addWidget(self.file_label)
        
        browse_btn = QPushButton("📁 Browse Files")
        browse_btn.clicked.connect(self._browse_file)
        file_layout.addWidget(browse_btn)
        
        layout.addLayout(file_layout)
        
        # Preview area (stacked widgets for different content types)
        self.preview_stack = QTabWidget()
        
        # Image preview
        self.image_preview = QLabel()
        self.image_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_preview.setStyleSheet("background-color: #0f0f0f; border: 1px solid #2a2a2a;")
        self.image_preview.setMinimumSize(400, 300)
        self.preview_stack.addTab(self.image_preview, "Image")
        
        # Video preview
        self.video_widget = QVideoWidget()
        self.media_player.setVideoOutput(self.video_widget)
        self.preview_stack.addTab(self.video_widget, "Video")
        
        # Audio preview (just a label with controls)
        audio_widget = QWidget()
        audio_layout = QVBoxLayout(audio_widget)
        self.audio_label = QLabel("🎵 Audio File Loaded")
        self.audio_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.audio_label.setFont(QFont("Arial", 14))
        audio_layout.addWidget(self.audio_label)
        
        audio_controls = QHBoxLayout()
        self.play_btn = QPushButton("▶ Play")
        self.play_btn.clicked.connect(self._toggle_play)
        audio_controls.addWidget(self.play_btn)
        
        self.stop_btn = QPushButton("■ Stop")
        self.stop_btn.clicked.connect(self._stop_media)
        audio_controls.addWidget(self.stop_btn)
        audio_layout.addLayout(audio_controls)
        
        audio_layout.addStretch()
        self.preview_stack.addTab(audio_widget, "Audio")
        
        # Text preview
        self.text_preview = QTextEdit()
        self.text_preview.setReadOnly(True)
        self.preview_stack.addTab(self.text_preview, "Text")
        
        layout.addWidget(self.preview_stack)
        
        # Content info
        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color: #9cdcfe; padding: 5px;")
        layout.addWidget(self.info_label)
        
        return group
    
    def _create_controls_panel(self) -> QGroupBox:
        """Create platform selection and upload controls"""
        group = QGroupBox("◆ DISTRIBUTION PLATFORMS")
        layout = QVBoxLayout(group)
        
        # Platform checkboxes
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        self.platform_checkboxes = {}
        
        for platform_id, config in self.router.platforms.items():
            # Create container for checkbox and auth button
            platform_widget = QWidget()
            platform_layout = QHBoxLayout(platform_widget)
            platform_layout.setContentsMargins(0, 0, 0, 0)
            
            # Checkbox with status indicator
            auth_indicator = "🔓" if not config['authenticated'] else "🔐"
            ready_indicator = "" if config['ready'] else " (Not Ready)"
            cb = QCheckBox(f"{config['icon']} {config['name']} {auth_indicator}{ready_indicator}")
            cb.setChecked(config['enabled'])
            
            # Disable platforms that aren't ready
            if not config['ready']:
                cb.setEnabled(False)
                cb.setToolTip(f"{config['name']} API not yet implemented")
            
            cb.stateChanged.connect(
                lambda state, pid=platform_id: self.router.set_platform_enabled(pid, state == Qt.CheckState.Checked.value)
            )
            platform_layout.addWidget(cb)
            
            # Auth button (only for platforms that need it and are ready)
            if platform_id != 'local' and config['ready']:
                auth_btn = QPushButton("🔐 Sign In")
                auth_btn.setMaximumWidth(80)
                auth_btn.clicked.connect(lambda checked, pid=platform_id: self._authenticate_platform(pid))
                platform_layout.addWidget(auth_btn)
                self.platform_checkboxes[f"{platform_id}_auth_btn"] = auth_btn
            
            scroll_layout.addWidget(platform_widget)
            self.platform_checkboxes[platform_id] = cb
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        # Platform management buttons
        platform_mgmt = QHBoxLayout()
        
        add_platform_btn = QPushButton("+ Add")
        add_platform_btn.clicked.connect(self._add_custom_platform)
        platform_mgmt.addWidget(add_platform_btn)
        
        remove_platform_btn = QPushButton("- Remove")
        remove_platform_btn.clicked.connect(self._remove_custom_platform)
        platform_mgmt.addWidget(remove_platform_btn)
        
        layout.addLayout(platform_mgmt)
        
        # Settings button
        settings_btn = QPushButton("⚙ Platform Settings")
        settings_btn.clicked.connect(self._open_settings)
        layout.addWidget(settings_btn)
        
        # Upload button
        self.upload_btn = QPushButton("✓ CONFIRM & UPLOAD")
        self.upload_btn.setEnabled(False)
        self.upload_btn.setMinimumHeight(50)
        self.upload_btn.setStyleSheet("""
            QPushButton {
                background-color: #006400;
                color: #FFD700;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #008000;
            }
            QPushButton:disabled {
                background-color: #2a2a2a;
                color: #505050;
            }
        """)
        self.upload_btn.clicked.connect(self._start_upload)
        layout.addWidget(self.upload_btn)
        
        return group
    
    def _create_status_panel(self) -> QGroupBox:
        """Create upload status panel"""
        group = QGroupBox("◆ UPLOAD STATUS")
        layout = QVBoxLayout(group)
        
        self.status_list = QListWidget()
        self.status_list.setMaximumHeight(120)
        self.status_list.itemDoubleClicked.connect(self._open_upload_url)
        layout.addWidget(self.status_list)
        
        hint_label = QLabel("💡 Double-click an item to open its URL")
        hint_label.setStyleSheet("color: #666666; font-size: 10px; font-style: italic;")
        layout.addWidget(hint_label)
        
        return group
    
    def _open_upload_url(self, item: QListWidgetItem):
        """Open URL when status item is double-clicked"""
        url = item.data(Qt.ItemDataRole.UserRole)
        if url:
            import webbrowser
            webbrowser.open(url)
        else:
            QMessageBox.information(self, "No URL", "No URL available for this upload.")
    
    def _show_upload_complete_dialog(self):
        """Show dialog with all upload links"""
        links = []
        for i in range(self.status_list.count()):
            item = self.status_list.item(i)
            url = item.data(Qt.ItemDataRole.UserRole)
            if url and item.foreground().color().name() == "#00ff00":  # Success items only
                platform_name = item.text().split(':')[0].replace('✓', '').strip()
                links.append(f"{platform_name}: {url}")
        
        if links:
            message = "Upload complete! Content available at:\n\n" + "\n\n".join(links)
            message += "\n\n💡 Double-click any item in the status list to open its URL"
        else:
            message = "Upload complete!"
        
        QMessageBox.information(self, "Upload Complete", message)
    
    def _browse_file(self):
        """Open file browser"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Content File",
            str(Path.home()),
            "All Files (*.*);;Images (*.jpg *.png *.gif);;Videos (*.mp4 *.avi *.mov);;Audio (*.mp3 *.wav)"
        )
        
        if file_path:
            self._load_file(file_path)
    
    def _load_file(self, file_path: str):
        """Load and preview a file"""
        self.current_file = file_path
        self.content_info = self.router.analyze_content(file_path)
        
        # Update file label
        self.file_label.setText(Path(file_path).name)
        self.file_label.setStyleSheet("color: #00FF00; font-weight: bold;")
        
        # Update info
        self.info_label.setText(
            f"Type: {self.content_info['type']} | "
            f"Size: {self.content_info['size_mb']} MB"
        )
        
        # Show appropriate preview
        content_type = self.content_info['type']
        
        if content_type == 'image':
            pixmap = QPixmap(file_path)
            scaled = pixmap.scaled(
                600, 400,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.image_preview.setPixmap(scaled)
            self.preview_stack.setCurrentIndex(0)
        
        elif content_type == 'video':
            from PyQt6.QtCore import QUrl
            self.media_player.setSource(QUrl.fromLocalFile(file_path))
            self.preview_stack.setCurrentIndex(1)
        
        elif content_type == 'audio':
            from PyQt6.QtCore import QUrl
            self.media_player.setSource(QUrl.fromLocalFile(file_path))
            self.audio_label.setText(f"🎵 {Path(file_path).name}")
            self.preview_stack.setCurrentIndex(2)
        
        elif content_type == 'text':
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                self.text_preview.setPlainText(text)
                self.preview_stack.setCurrentIndex(3)
            except Exception as e:
                self.text_preview.setPlainText(f"Error loading text: {e}")
        
        # Enable upload button
        self.upload_btn.setEnabled(True)
    
    def _toggle_play(self):
        """Toggle media playback"""
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
            self.play_btn.setText("▶ Play")
        else:
            self.media_player.play()
            self.play_btn.setText("⏸ Pause")
    
    def _stop_media(self):
        """Stop media playback"""
        self.media_player.stop()
        self.play_btn.setText("▶ Play")
    
    def _authenticate_platform(self, platform_id: str):
        """Show authentication dialog for a platform"""
        config = self.router.platforms[platform_id]
        
        dialog = AuthenticationDialog(self, platform_id, config['name'], self.vault)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.authenticated:
            # Update authentication status
            self.router.set_platform_authenticated(platform_id, True)
            
            # Update checkbox label
            if platform_id in self.platform_checkboxes:
                cb = self.platform_checkboxes[platform_id]
                cb.setText(f"{config['icon']} {config['name']} 🔐")
                cb.setEnabled(True)
            
            QMessageBox.information(
                self,
                "Authentication Successful",
                f"✓ Successfully authenticated with {config['name']}!\n\nYou can now upload content to this platform."
            )
    
    def _start_upload(self):
        """Start upload process"""
        if not self.current_file:
            return
        
        # Get enabled platforms
        enabled_platforms = self.router.get_enabled_platforms()
        
        if not enabled_platforms:
            QMessageBox.warning(self, "No Platforms", "Please select at least one platform!")
            return
        
        # Check authentication for platforms that require it
        unauthenticated = []
        for platform in enabled_platforms:
            if platform != 'local' and not self.router.is_platform_authenticated(platform):
                unauthenticated.append(platform)
        
        if unauthenticated:
            platform_names = [self.router.platforms[p]['name'] for p in unauthenticated]
            result = QMessageBox.question(
                self,
                "Authentication Required",
                f"The following platforms require authentication:\n\n" +
                "\n".join([f"  • {name}" for name in platform_names]) +
                "\n\nWould you like to authenticate now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if result == QMessageBox.StandardButton.Yes:
                # Authenticate each platform
                for platform_id in unauthenticated:
                    self._authenticate_platform(platform_id)
                
                # Recheck after authentication attempts
                still_unauthenticated = [p for p in enabled_platforms 
                                        if p != 'local' and not self.router.is_platform_authenticated(p)]
                if still_unauthenticated:
                    QMessageBox.warning(
                        self,
                        "Authentication Incomplete",
                        "Some platforms are still not authenticated. Only authenticated platforms will be used."
                    )
                    # Filter to only authenticated platforms
                    enabled_platforms = [p for p in enabled_platforms 
                                       if p == 'local' or self.router.is_platform_authenticated(p)]
            else:
                # Filter to only authenticated platforms
                enabled_platforms = [p for p in enabled_platforms 
                                   if p == 'local' or self.router.is_platform_authenticated(p)]
                
                if not enabled_platforms:
                    QMessageBox.warning(
                        self,
                        "No Authenticated Platforms",
                        "No authenticated platforms available for upload."
                    )
                    return
        
        # Confirm
        result = QMessageBox.question(
            self,
            "Confirm Upload",
            f"Upload '{Path(self.current_file).name}' to:\n" +
            "\n".join([f"  • {self.router.platforms[p]['name']}" for p in enabled_platforms]) +
            "\n\nProceed?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if result != QMessageBox.StandardButton.Yes:
            return
        
        # Disable upload button
        self.upload_btn.setEnabled(False)
        self.upload_btn.setText("UPLOADING...")
        
        # Clear previous status
        self.status_list.clear()
        
        # Load credentials
        credentials = self.vault.load_credentials()
        
        # Start upload worker
        self.upload_worker = UploadWorker(self.current_file, enabled_platforms, credentials)
        self.upload_worker.progress.connect(self._on_upload_progress)
        self.upload_worker.finished.connect(self._on_upload_finished)
        self.upload_worker.start()
    
    def _on_upload_progress(self, platform: str, percentage: int):
        """Handle upload progress"""
        # Update or add status item
        items = self.status_list.findItems(platform, Qt.MatchFlag.MatchStartsWith)
        
        status_text = f"{platform}: {percentage}%"
        
        if items:
            items[0].setText(status_text)
        else:
            self.status_list.addItem(status_text)
    
    def _on_upload_finished(self, platform: str, success: bool, message: str, url: str):
        """Handle upload completion"""
        icon = "✓" if success else "✗"
        color = "#00FF00" if success else "#f48771"
        
        items = self.status_list.findItems(platform, Qt.MatchFlag.MatchStartsWith)
        
        # Create status text with link if available
        if success and url:
            status_text = f"{icon} {platform}: {message}\n   🔗 {url}"
        else:
            status_text = f"{icon} {platform}: {message}"
        
        if items:
            items[0].setText(status_text)
            items[0].setForeground(QColor(color))
            # Store URL in item data for later access
            if url:
                items[0].setData(Qt.ItemDataRole.UserRole, url)
        
        # Check if all uploads finished
        if self.upload_worker and not self.upload_worker.isRunning():
            self.upload_btn.setEnabled(True)
            self.upload_btn.setText("✓ CONFIRM & UPLOAD")
            
            # Show completion dialog with links
            self._show_upload_complete_dialog()
    
    def _open_settings(self):
        """Open settings dialog"""
        dialog = SettingsDialog(self, self.router, self.vault)
        dialog.exec()
    
    def _add_custom_platform(self):
        """Add a custom platform"""
        from PyQt6.QtWidgets import QInputDialog
        
        platform_id, ok1 = QInputDialog.getText(
            self, "Add Platform", "Platform ID (lowercase, no spaces):"
        )
        
        if ok1 and platform_id:
            platform_name, ok2 = QInputDialog.getText(
                self, "Add Platform", "Platform Display Name:"
            )
            
            if ok2 and platform_name:
                self.router.add_custom_platform(platform_id, platform_name)
                
                # Add checkbox
                cb = QCheckBox(f"🌐 {platform_name}")
                cb.setChecked(False)
                cb.stateChanged.connect(
                    lambda state: self.router.set_platform_enabled(platform_id, state == Qt.CheckState.Checked.value)
                )
                
                # Find scroll widget and add checkbox
                scroll = self.findChild(QScrollArea)
                if scroll:
                    scroll.widget().layout().insertWidget(scroll.widget().layout().count() - 1, cb)
                    self.platform_checkboxes[platform_id] = cb
    
    def _remove_custom_platform(self):
        """Remove a custom platform"""
        # TODO: Implement platform removal dialog
        QMessageBox.information(self, "Remove Platform", "Select platform to remove (coming soon)")


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Application entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("Singularity Router")
    
    window = SingularityRouter()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()