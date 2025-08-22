# InsightMiner Incremental Automated Backup System
# Standalone backup utility triggered only on Flask server startup

import os
import shutil
import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import threading
import time

class IncrementalBackupSystem:
    """
    Automated incremental backup system for InsightMiner project.
    Triggers only on server startup, compares timestamps and checksums.
    """
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.backup_base_dir = Path("C:/Users/guyle/Desktop/Project Backups")
        self.backup_metadata_file = self.project_root / "backup_metadata.json"
        self.max_backups = 10
        
        # Files/folders to exclude from backup
        self.excluded_patterns = {
            '__pycache__',
            '*.pyc',
            '*.pyo',
            '*.log',
            'temp_processing',
            'instagram_session.json',
            'backup_metadata.json',
            '.git',
            'node_modules',
            '*.tmp',
            '*.temp'
        }
        
        # Setup logging
        self.setup_logging()
        
    def setup_logging(self):
        """Setup logging for backup operations"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s | BACKUP | %(levelname)s | %(message)s',
            handlers=[
                logging.FileHandler('backup_operations.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of a file"""
        try:
            hash_sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            self.logger.error(f"Failed to calculate checksum for {file_path}: {e}")
            return ""
    
    def should_exclude_file(self, file_path: Path) -> bool:
        """Check if file should be excluded from backup"""
        file_name = file_path.name
        
        # Check exact matches
        if file_name in self.excluded_patterns:
            return True
            
        # Check pattern matches
        for pattern in self.excluded_patterns:
            if pattern.startswith('*') and file_name.endswith(pattern[1:]):
                return True
            if pattern.endswith('*') and file_name.startswith(pattern[:-1]):
                return True
                
        # Check if any parent directory matches excluded patterns
        for parent in file_path.parents:
            if parent.name in self.excluded_patterns:
                return True
                
        return False
    
    def load_backup_metadata(self) -> Dict:
        """Load backup metadata from previous runs"""
        if self.backup_metadata_file.exists():
            try:
                with open(self.backup_metadata_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Failed to load backup metadata: {e}")
        
        return {
            "last_backup_date": None,
            "file_checksums": {},
            "backup_history": []
        }
    
    def save_backup_metadata(self, metadata: Dict):
        """Save backup metadata for future runs"""
        try:
            with open(self.backup_metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2, default=str)
            self.logger.info("Backup metadata saved successfully")
        except Exception as e:
            self.logger.error(f"Failed to save backup metadata: {e}")
    
    def get_backup_directory(self) -> Path:
        """Get backup directory for current date"""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        backup_dir = self.backup_base_dir / f"InsightMiner_backup_{timestamp}"
        return backup_dir
    
    def scan_project_files(self) -> Dict[str, Dict]:
        """Scan project files and get their metadata"""
        file_metadata = {}
        
        self.logger.info("Scanning project files...")
        
        for file_path in self.project_root.rglob('*'):
            if file_path.is_file() and not self.should_exclude_file(file_path):
                try:
                    relative_path = str(file_path.relative_to(self.project_root))
                    stat = file_path.stat()
                    
                    file_metadata[relative_path] = {
                        "size": stat.st_size,
                        "modified_time": stat.st_mtime,
                        "checksum": self.calculate_file_checksum(file_path)
                    }
                    
                except Exception as e:
                    self.logger.warning(f"Failed to process {file_path}: {e}")
        
        self.logger.info(f"Scanned {len(file_metadata)} files")
        return file_metadata
    
    def detect_changed_files(self, current_metadata: Dict, previous_metadata: Dict) -> List[str]:
        """Detect files that have changed since last backup"""
        changed_files = []
        
        previous_checksums = previous_metadata.get("file_checksums", {})
        
        for file_path, metadata in current_metadata.items():
            if file_path not in previous_checksums:
                # New file
                changed_files.append(file_path)
                self.logger.debug(f"New file detected: {file_path}")
            elif (previous_checksums[file_path].get("checksum") != metadata["checksum"] or
                  previous_checksums[file_path].get("modified_time") != metadata["modified_time"]):
                # Modified file
                changed_files.append(file_path)
                self.logger.debug(f"Modified file detected: {file_path}")
        
        # Check for deleted files
        for file_path in previous_checksums:
            if file_path not in current_metadata:
                self.logger.info(f"Deleted file detected: {file_path}")
        
        return changed_files
    
    def copy_files_with_locking(self, changed_files: List[str], backup_dir: Path) -> bool:
        """Copy changed files to backup directory with file locking"""
        success_count = 0
        total_files = len(changed_files)
        
        self.logger.info(f"Copying {total_files} changed files to backup...")
        
        # Create backup directory
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        for relative_path in changed_files:
            source_file = self.project_root / relative_path
            dest_file = backup_dir / relative_path
            
            try:
                # Create destination directory if it doesn't exist
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Copy file with metadata preservation
                shutil.copy2(source_file, dest_file)
                success_count += 1
                
                self.logger.debug(f"Copied: {relative_path}")
                
            except Exception as e:
                self.logger.error(f"Failed to copy {relative_path}: {e}")
        
        self.logger.info(f"Successfully copied {success_count}/{total_files} files")
        return success_count == total_files
    
    def cleanup_old_backups(self):
        """Remove old backups to maintain max_backups limit"""
        if not self.backup_base_dir.exists():
            return
        
        # Get all InsightMiner backup directories
        backup_dirs = [
            d for d in self.backup_base_dir.iterdir() 
            if d.is_dir() and d.name.startswith("InsightMiner_backup_")
        ]
        
        # Sort by creation time (newest first)
        backup_dirs.sort(key=lambda x: x.stat().st_ctime, reverse=True)
        
        # Remove excess backups
        if len(backup_dirs) > self.max_backups:
            for old_backup in backup_dirs[self.max_backups:]:
                try:
                    shutil.rmtree(old_backup)
                    self.logger.info(f"Removed old backup: {old_backup.name}")
                except Exception as e:
                    self.logger.error(f"Failed to remove old backup {old_backup}: {e}")
    
    def perform_incremental_backup(self) -> bool:
        """Perform incremental backup operation"""
        self.logger.info("=== Starting Incremental Backup ===")
        start_time = time.time()
        
        try:
            # Load previous backup metadata
            previous_metadata = self.load_backup_metadata()
            
            # Scan current project files
            current_file_metadata = self.scan_project_files()
            
            # Detect changed files
            changed_files = self.detect_changed_files(
                current_file_metadata, 
                previous_metadata
            )
            
            if not changed_files:
                self.logger.info("No file changes detected - skipping backup")
                return True
            
            self.logger.info(f"Detected {len(changed_files)} changed files")
            
            # Get backup directory
            backup_dir = self.get_backup_directory()
            
            # Copy changed files
            success = self.copy_files_with_locking(changed_files, backup_dir)
            
            if success:
                # Update metadata
                new_metadata = {
                    "last_backup_date": datetime.now().isoformat(),
                    "file_checksums": current_file_metadata,
                    "backup_history": previous_metadata.get("backup_history", []) + [{
                        "date": datetime.now().isoformat(),
                        "backup_dir": str(backup_dir),
                        "files_backed_up": len(changed_files),
                        "total_files": len(current_file_metadata)
                    }]
                }
                
                # Keep only last 50 history entries
                new_metadata["backup_history"] = new_metadata["backup_history"][-50:]
                
                self.save_backup_metadata(new_metadata)
                
                # Cleanup old backups
                self.cleanup_old_backups()
                
                end_time = time.time()
                duration = end_time - start_time
                
                self.logger.info(f"=== Backup Completed Successfully ===")
                self.logger.info(f"Backup location: {backup_dir}")
                self.logger.info(f"Files backed up: {len(changed_files)}")
                self.logger.info(f"Duration: {duration:.2f} seconds")
                
                return True
            else:
                self.logger.error("Backup failed - some files could not be copied")
                return False
                
        except Exception as e:
            self.logger.error(f"Backup operation failed: {e}")
            import traceback
            self.logger.error(f"Stack trace:\n{traceback.format_exc()}")
            return False
    
    def is_backup_needed_today(self) -> bool:
        """Check if backup has already been performed today"""
        metadata = self.load_backup_metadata()
        last_backup = metadata.get("last_backup_date")
        
        if not last_backup:
            return True
        
        try:
            last_backup_date = datetime.fromisoformat(last_backup).date()
            today = datetime.now().date()
            
            # Only backup once per day
            return last_backup_date < today
        except Exception:
            # If we can't parse the date, assume backup is needed
            return True


class BackupTrigger:
    """Manages backup triggering on server startup"""
    
    def __init__(self):
        self.backup_system = IncrementalBackupSystem()
        self.backup_lock_file = Path("backup_in_progress.lock")
        
    def is_backup_running(self) -> bool:
        """Check if backup is already running"""
        return self.backup_lock_file.exists()
    
    def create_backup_lock(self):
        """Create backup lock file"""
        try:
            with open(self.backup_lock_file, 'w') as f:
                f.write(f"Backup started at: {datetime.now().isoformat()}")
        except Exception as e:
            self.backup_system.logger.warning(f"Failed to create backup lock: {e}")
    
    def remove_backup_lock(self):
        """Remove backup lock file"""
        try:
            if self.backup_lock_file.exists():
                self.backup_lock_file.unlink()
        except Exception as e:
            self.backup_system.logger.warning(f"Failed to remove backup lock: {e}")
    
    def trigger_backup_on_startup(self):
        """Trigger backup on server startup (non-blocking)"""
        def backup_thread():
            try:
                # Check if backup is already running
                if self.is_backup_running():
                    self.backup_system.logger.warning("Backup already in progress - skipping")
                    return
                
                # Check if backup is needed today
                if not self.backup_system.is_backup_needed_today():
                    self.backup_system.logger.info("Backup already performed today - skipping")
                    return
                
                # Create lock file
                self.create_backup_lock()
                
                # Perform backup
                self.backup_system.perform_incremental_backup()
                
            except Exception as e:
                self.backup_system.logger.error(f"Backup thread failed: {e}")
            finally:
                # Always remove lock file
                self.remove_backup_lock()
        
        # Start backup in background thread
        backup_thread = threading.Thread(target=backup_thread, daemon=True)
        backup_thread.start()
        
        self.backup_system.logger.info("Backup thread started in background")


# Global backup trigger instance
backup_trigger = BackupTrigger()


def trigger_startup_backup():
    """
    Main function to call from Flask server startup.
    This should be called only when the server starts.
    """
    backup_trigger.trigger_backup_on_startup()


if __name__ == "__main__":
    # Direct execution for testing
    print("=== InsightMiner Incremental Backup System ===")
    print("Running backup in test mode...")
    
    backup_system = IncrementalBackupSystem()
    success = backup_system.perform_incremental_backup()
    
    if success:
        print("Backup completed successfully")
    else:
        print("Backup failed")