#!/usr/bin/env python3
"""
TopoToImage Update Checker
Checks GitHub for new releases and notifies users
"""

import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
from packaging import version
from PyQt6.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTextEdit
from PyQt6.QtCore import QThread, pyqtSignal, QTimer, Qt
from PyQt6.QtGui import QPixmap, QIcon

class UpdateChecker(QThread):
    """Background thread to check for updates"""
    
    update_available = pyqtSignal(dict)  # Emits release info
    no_update = pyqtSignal()
    error_occurred = pyqtSignal(str)
    
    def __init__(self, current_version="4.0.0-beta.1", github_repo="yourusername/TopoToImage"):
        super().__init__()
        self.current_version = current_version
        self.github_repo = github_repo
        self.github_api_url = f"https://api.github.com/repos/{github_repo}/releases/latest"
        
    def run(self):
        """Check for updates in background thread"""
        try:
            # Check if we should skip (user preference or recent check)
            if self.should_skip_check():
                return
                
            # Fetch latest release info from GitHub
            release_info = self.fetch_latest_release()
            
            if release_info:
                latest_version = release_info['tag_name'].lstrip('v')
                
                if self.is_newer_version(latest_version):
                    self.update_available.emit(release_info)
                else:
                    self.no_update.emit()
            else:
                self.error_occurred.emit("Could not fetch release information")
                
        except Exception as e:
            self.error_occurred.emit(str(e))
    
    def fetch_latest_release(self):
        """Fetch latest release information from GitHub API"""
        try:
            # Create request with user agent (GitHub requires this)
            request = urllib.request.Request(
                self.github_api_url,
                headers={'User-Agent': 'TopoToImage/4.0 UpdateChecker'}
            )
            
            with urllib.request.urlopen(request, timeout=10) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode())
                    return data
                    
        except urllib.error.URLError as e:
            print(f"Network error checking for updates: {e}")
        except json.JSONDecodeError as e:
            print(f"Error parsing GitHub response: {e}")
        except Exception as e:
            print(f"Unexpected error checking for updates: {e}")
            
        return None
    
    def is_newer_version(self, latest_version):
        """Compare version numbers using semantic versioning"""
        try:
            return version.parse(latest_version) > version.parse(self.current_version)
        except Exception:
            # Fallback to string comparison if version parsing fails
            return latest_version != self.current_version
    
    def should_skip_check(self):
        """Check if we should skip the update check based on user preferences"""
        prefs_file = self.get_preferences_file()
        
        try:
            if prefs_file.exists():
                with open(prefs_file, 'r') as f:
                    prefs = json.load(f)
                
                # Skip if user disabled auto-update
                if not prefs.get('check_for_updates', True):
                    return True
                
                # Skip if checked recently (within 24 hours)
                last_check = prefs.get('last_update_check')
                if last_check:
                    last_check_date = datetime.fromisoformat(last_check)
                    if datetime.now() - last_check_date < timedelta(hours=24):
                        return True
                        
        except Exception:
            pass  # Continue with check if preferences can't be read
            
        return False
    
    def get_preferences_file(self):
        """Get path to user preferences file"""
        app_data_dir = Path.home() / "Library" / "Application Support" / "TopoToImage"
        app_data_dir.mkdir(parents=True, exist_ok=True)
        return app_data_dir / "preferences.json"
    
    def update_last_check_time(self):
        """Update the last check timestamp"""
        prefs_file = self.get_preferences_file()
        
        try:
            prefs = {}
            if prefs_file.exists():
                with open(prefs_file, 'r') as f:
                    prefs = json.load(f)
            
            prefs['last_update_check'] = datetime.now().isoformat()
            
            with open(prefs_file, 'w') as f:
                json.dump(prefs, f, indent=2)
                
        except Exception as e:
            print(f"Could not update last check time: {e}")

class UpdateDialog(QDialog):
    """Dialog to show update information to user"""
    
    def __init__(self, release_info, parent=None):
        super().__init__(parent)
        self.release_info = release_info
        self.setup_ui()
        
    def setup_ui(self):
        """Create the update dialog UI"""
        self.setWindowTitle("TopoToImage Update Available")
        self.setFixedSize(500, 400)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # Header with icon and title
        header_layout = QHBoxLayout()
        
        # Update icon (you could add a custom icon here)
        icon_label = QLabel("🔄")
        icon_label.setStyleSheet("font-size: 24px;")
        header_layout.addWidget(icon_label)
        
        # Title and version info
        title_layout = QVBoxLayout()
        title = QLabel("Update Available")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        
        version_info = QLabel(f"Version {self.release_info['tag_name']} is now available")
        version_info.setStyleSheet("color: #666; font-size: 14px;")
        
        title_layout.addWidget(title)
        title_layout.addWidget(version_info)
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Release notes
        notes_label = QLabel("What's new:")
        notes_label.setStyleSheet("font-weight: bold; margin-top: 15px;")
        layout.addWidget(notes_label)
        
        # Release notes text area
        notes_text = QTextEdit()
        notes_text.setMaximumHeight(200)
        notes_text.setReadOnly(True)
        
        # Format release notes (convert markdown basics to HTML)
        release_notes = self.release_info.get('body', 'Release notes not available.')
        formatted_notes = self.format_release_notes(release_notes)
        notes_text.setHtml(formatted_notes)
        
        layout.addWidget(notes_text)
        
        # Download info
        download_label = QLabel("Downloads available:")
        download_label.setStyleSheet("font-weight: bold; margin-top: 15px;")
        layout.addWidget(download_label)
        
        # List download assets
        for asset in self.release_info.get('assets', []):
            if asset['name'].endswith('.dmg'):
                asset_info = QLabel(f"• {asset['name']} ({self.format_file_size(asset['size'])})")
                asset_info.setStyleSheet("color: #444; margin-left: 20px;")
                layout.addWidget(asset_info)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        # Don't ask again checkbox could go here
        
        button_layout.addStretch()
        
        later_button = QPushButton("Later")
        later_button.clicked.connect(self.reject)
        button_layout.addWidget(later_button)
        
        download_button = QPushButton("Download Update")
        download_button.setStyleSheet("""
            QPushButton {
                background-color: #0066cc;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        download_button.clicked.connect(self.open_download_page)
        button_layout.addWidget(download_button)
        
        layout.addLayout(button_layout)
        
    def format_release_notes(self, notes):
        """Convert basic markdown to HTML for display"""
        # Simple markdown to HTML conversion
        html_notes = notes.replace('\n', '<br>')
        html_notes = html_notes.replace('**', '<b>').replace('**', '</b>')
        html_notes = html_notes.replace('## ', '<h3>').replace('\n', '</h3><br>')
        html_notes = html_notes.replace('- ', '• ')
        
        return f"<div style='font-family: system-ui; font-size: 12px;'>{html_notes}</div>"
    
    def format_file_size(self, size_bytes):
        """Format file size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    def open_download_page(self):
        """Open the GitHub release page in the default browser"""
        import webbrowser
        webbrowser.open(self.release_info['html_url'])
        self.accept()

class UpdateNotification:
    """Simple notification for updates"""
    
    @staticmethod
    def show_notification(release_info):
        """Show a simple notification about available update"""
        try:
            # On macOS, we could use native notifications
            # For now, using a simple message box
            msg = QMessageBox()
            msg.setWindowTitle("TopoToImage Update")
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setText(f"TopoToImage {release_info['tag_name']} is available!")
            msg.setInformativeText("Click 'Update' to download the latest version.")
            msg.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
            msg.setDefaultButton(QMessageBox.StandardButton.Ok)
            
            result = msg.exec()
            if result == QMessageBox.StandardButton.Ok:
                import webbrowser
                webbrowser.open(release_info['html_url'])
                
        except Exception as e:
            print(f"Error showing update notification: {e}")

class UpdateManager:
    """Main update manager for integration into TopoToImage"""
    
    def __init__(self, main_window, current_version="4.0", repo="yourusername/TopoToImage"):
        self.main_window = main_window
        self.current_version = current_version
        self.repo = repo
        self.checker = None
        
    def check_for_updates_async(self, show_no_update_message=False):
        """Check for updates asynchronously"""
        if self.checker and self.checker.isRunning():
            return  # Already checking
            
        self.show_no_update_message = show_no_update_message
        
        self.checker = UpdateChecker(self.current_version, self.repo)
        self.checker.update_available.connect(self.on_update_available)
        self.checker.no_update.connect(self.on_no_update)
        self.checker.error_occurred.connect(self.on_error)
        self.checker.start()
    
    def check_for_updates_startup(self):
        """Check for updates on application startup (respects user preferences)"""
        # Only check if user hasn't disabled it and it's been a while
        self.check_for_updates_async(show_no_update_message=False)
    
    def check_for_updates_manual(self):
        """Manual update check triggered by user (always shows result)"""
        self.check_for_updates_async(show_no_update_message=True)
    
    def on_update_available(self, release_info):
        """Handle update available"""
        try:
            dialog = UpdateDialog(release_info, self.main_window)
            dialog.exec()
        except Exception as e:
            print(f"Error showing update dialog: {e}")
            # Fallback to simple notification
            UpdateNotification.show_notification(release_info)
        
        # Update last check time
        if self.checker:
            self.checker.update_last_check_time()
    
    def on_no_update(self):
        """Handle no update available"""
        if hasattr(self, 'show_no_update_message') and self.show_no_update_message:
            msg = QMessageBox(self.main_window)
            msg.setWindowTitle("No Updates")
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setText("You're running the latest version of TopoToImage!")
            msg.exec()
        
        # Update last check time
        if self.checker:
            self.checker.update_last_check_time()
    
    def on_error(self, error_message):
        """Handle update check error"""
        if hasattr(self, 'show_no_update_message') and self.show_no_update_message:
            msg = QMessageBox(self.main_window)
            msg.setWindowTitle("Update Check Failed")
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setText("Could not check for updates.")
            msg.setInformativeText(f"Error: {error_message}")
            msg.exec()

# Example integration into main window
def integrate_update_checker(main_window_class):
    """Example of how to integrate update checker into main window"""
    
    def __init__(self, *args, **kwargs):
        super(main_window_class, self).__init__(*args, **kwargs)
        
        # Initialize update manager
        self.update_manager = UpdateManager(self, current_version="4.0.0-beta.1", repo="yourusername/TopoToImage")
        
        # Add update check to Help menu
        self.add_update_menu_items()
        
        # Check for updates on startup (after a delay)
        QTimer.singleShot(5000, self.update_manager.check_for_updates_startup)  # 5 second delay
    
    def add_update_menu_items(self):
        """Add update-related menu items"""
        # This would be added to your existing menu setup
        # help_menu.addAction("Check for Updates...", self.update_manager.check_for_updates_manual)
        pass
    
    # Monkey patch the class (not recommended, but shows the concept)
    main_window_class.__init__ = __init__
    main_window_class.add_update_menu_items = add_update_menu_items

if __name__ == "__main__":
    # Test the update checker
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # Test with a fake release info
    test_release = {
        'tag_name': 'v4.1',
        'html_url': 'https://github.com/yourusername/TopoToImage/releases/tag/v4.1',
        'body': '## What\'s New\n\n- Fixed gradient loading bug\n- Added new terrain export formats\n- Improved performance\n\n## Bug Fixes\n\n- Fixed memory leak in preview generation\n- Resolved crash when loading large DEM files',
        'assets': [
            {
                'name': 'TopoToImage-v4.1-macOS.dmg',
                'size': 415000000
            }
        ]
    }
    
    dialog = UpdateDialog(test_release)
    dialog.exec()
    
    sys.exit(app.exec())