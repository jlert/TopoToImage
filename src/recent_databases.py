#!/usr/bin/env python3
"""
Recent Databases Manager
Tracks the 10 most recently opened databases and provides startup database management.
"""

import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime

# Import bundle-aware path resolution functions
def get_writable_data_path(relative_path):
    """Get absolute path to writable data location, works for dev and PyInstaller bundled app"""
    if hasattr(sys, '_MEIPASS'):
        # Running as PyInstaller bundle - use writable home directory location
        data_dir = Path.home() / "TopoToImage_Data"
        data_dir.mkdir(exist_ok=True)
        return data_dir / relative_path
    else:
        # Running in development - use project assets directory (writable)
        project_root = Path(__file__).parent.parent  # Go up from src/ to project root
        return project_root / "assets" / relative_path

class RecentDatabasesManager:
    """Manages recent database history and startup database selection"""
    
    def __init__(self, max_recent: int = 10):
        self.max_recent = max_recent
        # Use bundle-aware path for recent databases config
        self.config_file = get_writable_data_path("recent_databases.json")
        self.recent_databases: List[Dict] = []
        self.load_recent_databases()
    
    def load_recent_databases(self):
        """Load recent databases from config file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    self.recent_databases = data.get('recent_databases', [])
                    # Validate that files still exist
                    self.recent_databases = [db for db in self.recent_databases if self._database_exists(db)]
        except Exception as e:
            print(f"Error loading recent databases: {e}")
            self.recent_databases = []
    
    def save_recent_databases(self):
        """Save recent databases to config file"""
        try:
            data = {
                'recent_databases': self.recent_databases,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving recent databases: {e}")
    
    def add_recent_database(self, database_path: str, database_type: str, display_name: str = None):
        """
        Add a database to the recent list
        
        Args:
            database_path: Full path to database file or folder
            database_type: 'single_file' or 'multi_file'
            display_name: Optional display name (defaults to filename/foldername)
        """
        database_path = str(Path(database_path).resolve())
        
        if not display_name:
            display_name = Path(database_path).name
        
        # Create database entry
        db_entry = {
            'path': database_path,
            'type': database_type,
            'display_name': display_name,
            'last_opened': datetime.now().isoformat()
        }
        
        # Remove if already exists (to move to top)
        self.recent_databases = [db for db in self.recent_databases if db['path'] != database_path]
        
        # Add to beginning
        self.recent_databases.insert(0, db_entry)
        
        # Limit to max_recent
        self.recent_databases = self.recent_databases[:self.max_recent]
        
        # Save to disk
        self.save_recent_databases()
    
    def get_recent_databases(self) -> List[Dict]:
        """Get list of recent databases (most recent first)"""
        # Filter out databases that no longer exist
        existing_databases = [db for db in self.recent_databases if self._database_exists(db)]
        if len(existing_databases) != len(self.recent_databases):
            self.recent_databases = existing_databases
            self.save_recent_databases()
        return self.recent_databases
    
    def get_last_database(self) -> Optional[Dict]:
        """Get the most recently opened database"""
        recent = self.get_recent_databases()
        return recent[0] if recent else None
    
    def clear_recent_databases(self):
        """Clear all recent databases"""
        self.recent_databases = []
        self.save_recent_databases()
    
    def remove_database(self, database_path: str):
        """Remove a specific database from recent list"""
        database_path = str(Path(database_path).resolve())
        self.recent_databases = [db for db in self.recent_databases if db['path'] != database_path]
        self.save_recent_databases()
    
    def _database_exists(self, db_entry: Dict) -> bool:
        """Check if a database still exists on disk"""
        path = Path(db_entry['path'])
        if db_entry['type'] == 'single_file':
            return path.is_file()
        elif db_entry['type'] == 'multi_file':
            return path.is_dir()
        return False
    
    def get_menu_items(self) -> List[Tuple[str, str, str]]:
        """
        Get recent databases formatted for menu display
        Returns: List of (display_text, path, type) tuples
        """
        menu_items = []
        recent = self.get_recent_databases()
        
        for i, db in enumerate(recent, 1):
            # Create display text with number and type indicator
            type_indicator = "📁" if db['type'] == 'multi_file' else "📄"
            display_text = f"{i}. {type_indicator} {db['display_name']}"
            menu_items.append((display_text, db['path'], db['type']))
        
        return menu_items


class StartupDatabaseDialog:
    """Dialog for selecting database type when no recent database is available"""
    
    @staticmethod
    def show_database_selection_dialog(parent=None):
        """
        Show dialog asking user to choose between Single File or Multi-File database
        Returns: ('single_file', path) or ('multi_file', path) or (None, None) if cancelled
        """
        try:
            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFileDialog, QMessageBox
            from PyQt6.QtCore import Qt
            from PyQt6.QtGui import QFont
        except ImportError:
            return None, None
        
        class DatabaseSelectionDialog(QDialog):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.setWindowTitle("TopoToImage - Select Database")
                self.setModal(True)
                self.resize(500, 250)
                
                # Result storage
                self.selected_type = None
                self.selected_path = None
                
                # Setup UI
                self.setup_ui()
            
            def setup_ui(self):
                layout = QVBoxLayout()
                
                # Subtitle
                subtitle = QLabel("Please select a database to get started:")
                subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
                font = QFont()
                font.setPointSize(12)
                subtitle.setFont(font)
                layout.addWidget(subtitle)
                
                layout.addStretch()
                
                # Buttons
                button_layout = QVBoxLayout()
                
                # Single file button
                single_file_btn = QPushButton("📄 Open Single DEM File")
                single_file_btn.setFixedHeight(50)
                font = QFont()
                font.setPointSize(14)
                single_file_btn.setFont(font)
                single_file_btn.clicked.connect(self.select_single_file)
                button_layout.addWidget(single_file_btn)
                
                # Multi file button
                multi_file_btn = QPushButton("📁 Open Multi-File Database Folder")
                multi_file_btn.setFixedHeight(50)
                font = QFont()
                font.setPointSize(14)
                multi_file_btn.setFont(font)
                multi_file_btn.clicked.connect(self.select_multi_file)
                button_layout.addWidget(multi_file_btn)
                
                layout.addLayout(button_layout)
                layout.addStretch()
                
                # Help text
                help_text = QLabel("Single File: Open one .dem, .bil, or .tif file\nMulti-File: Open a folder containing multiple DEM files")
                help_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
                help_text.setStyleSheet("color: gray;")
                layout.addWidget(help_text)
                
                self.setLayout(layout)
            
            def select_single_file(self):
                file_path, _ = QFileDialog.getOpenFileName(
                    self,
                    "Select DEM File",
                    "",
                    "DEM Files (*.dem *.bil *.tif *.tiff);;All Files (*)"
                )
                if file_path:
                    self.selected_type = 'single_file'
                    self.selected_path = file_path
                    self.accept()
            
            def select_multi_file(self):
                folder_path = QFileDialog.getExistingDirectory(
                    self,
                    "Select Database Folder"
                )
                if folder_path:
                    self.selected_type = 'multi_file'
                    self.selected_path = folder_path
                    self.accept()
        
        dialog = DatabaseSelectionDialog(parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.selected_type, dialog.selected_path
        else:
            return None, None


# Global instance
recent_db_manager = RecentDatabasesManager()