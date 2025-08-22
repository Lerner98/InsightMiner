# InsightMiner Incremental Automated Backup System

## Overview
The InsightMiner project now includes a comprehensive incremental backup system (`BACKUP_AUTO.py`) that automatically creates backups only when files have changed, triggered exclusively on Flask server startup.

## Key Features

### ✅ **Incremental Backup Logic**
- **File Change Detection**: Compares modification timestamps AND SHA256 checksums
- **Smart Filtering**: Automatically excludes temporary files, logs, cache, and session files
- **Metadata Tracking**: Maintains detailed backup history in `backup_metadata.json`

### ✅ **Backup Triggering**
- **Server Startup Only**: Triggered automatically when Flask LocalServer starts
- **Once Per Day**: Backup runs maximum once per day to avoid redundancy
- **Background Processing**: Runs in separate thread, doesn't block server startup
- **Lock File Protection**: Prevents multiple simultaneous backup operations

### ✅ **Backup Rotation**
- **Maximum 10 Backups**: Automatically removes oldest backups when limit exceeded
- **Date-based Naming**: `InsightMiner_backup_YYYY-MM-DD_HH-MM` format
- **Storage Location**: `C:\Users\guyle\Desktop\Project Backups\`

## File Structure

```
BACKUP_AUTO.py              # Main backup utility script
backup_metadata.json        # Backup metadata and history
backup_operations.log       # Backup operation logs
backup_in_progress.lock     # Lock file during backup operations
```

## Excluded Files/Patterns
The system automatically excludes:
- `__pycache__` directories and `*.pyc` files
- Log files (`*.log`)
- Temporary files (`*.tmp`, `*.temp`)
- Session files (`instagram_session.json`)
- Cache directories (`temp_processing`)
- Git directories (`.git`)
- The backup metadata itself

## Integration with InsightMiner

### Automatic Trigger
The backup system is integrated into the `LocalServer` class in `insight_miner.py`:

```python
from BACKUP_AUTO import trigger_startup_backup

def start_server(self, port=8502):
    def run_server():
        # Trigger backup on server startup
        trigger_startup_backup()
        # Start Flask server
        self.app.run(...)
```

### Configuration
No additional configuration required - the system uses:
- Project root: Automatically detected from script location
- Backup location: `C:\Users\guyle\Desktop\Project Backups\`
- Max backups: 10 (configurable in `IncrementalBackupSystem.__init__()`)

## Backup Process Flow

1. **Server Startup Detection**: Triggered when Flask LocalServer starts
2. **Lock Check**: Verifies no backup currently in progress
3. **Daily Check**: Confirms backup hasn't already run today
4. **File Scanning**: Scans project directory for all relevant files
5. **Change Detection**: Compares with previous backup metadata
6. **Incremental Copy**: Copies only changed/new files
7. **Metadata Update**: Updates backup history and file checksums
8. **Cleanup**: Removes old backups if exceeding limit

## Backup Metadata Structure

```json
{
  "last_backup_date": "2025-08-22T06:26:55.331455",
  "file_checksums": {
    "insight_miner.py": {
      "size": 125827,
      "modified_time": 1755832525.0568426,
      "checksum": "a6e0ac5e6924fba930fdc71d4041d59275201d57ff23d67e563f61aa0be7886c"
    }
  },
  "backup_history": [
    {
      "date": "2025-08-22T06:26:55.331461",
      "backup_dir": "C:\\Users\\guyle\\Desktop\\Project Backups\\InsightMiner_backup_2025-08-22_06-26",
      "files_backed_up": 3,
      "total_files": 9
    }
  ]
}
```

## Manual Testing

Run backup directly for testing:
```bash
cd "C:\Users\guyle\Desktop\IM Folder\InsightMiner"
python BACKUP_AUTO.py
```

## Logging
All backup operations are logged to `backup_operations.log` with detailed information about:
- File scanning progress
- Change detection results
- Copy operations success/failure
- Backup completion status
- Error handling and stack traces

## Performance
- **Fast Scanning**: Only calculates checksums for potentially changed files
- **Efficient Copying**: Only copies files that have actually changed
- **Background Operation**: Doesn't impact server startup time
- **Memory Efficient**: Processes files incrementally

## Recovery Benefits
- **Comprehensive Protection**: Backs up all critical project files
- **Change Tracking**: Maintains history of what changed when
- **Quick Restoration**: Organized by date for easy file recovery
- **No Large File Recreation**: Avoids copying unchanged 2600+ line files

## Error Handling
- **Graceful Failures**: Continues operation even if individual files fail to copy
- **Lock File Cleanup**: Automatically removes lock files on completion/failure
- **Detailed Logging**: Full stack traces for debugging issues
- **Atomic Operations**: Backup either completes fully or rolls back safely

This backup system provides robust protection against accidental file deletion while maintaining high performance through intelligent incremental backup logic.