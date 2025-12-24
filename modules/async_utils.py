import os
import json
import logging
import asyncio
import aiofiles
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

class AsyncFileManager:
    """Utility class for async file operations"""
    
    @staticmethod
    async def read_json(file_path: str) -> Optional[Dict[str, Any]]:
        """Read JSON file asynchronously"""
        try:
            async with aiofiles.open(file_path, 'r') as f:
                content = await f.read()
                return json.loads(content)
        except FileNotFoundError:
            logging.warning(f"File not found: {file_path}")
            return None
        except json.JSONDecodeError as e:
            logging.error(f"Invalid JSON in {file_path}: {e}")
            return None
        except Exception as e:
            logging.error(f"Error reading {file_path}: {e}")
            return None
    
    @staticmethod
    async def write_json(file_path: str, data: Dict[str, Any], indent: int = 2) -> bool:
        """Write JSON file asynchronously"""
        try:
            # Ensure directory exists
            directory = os.path.dirname(file_path)
            if directory:
                await AsyncFileManager.ensure_directory(directory)
            
            async with aiofiles.open(file_path, 'w') as f:
                await f.write(json.dumps(data, indent=indent))
            return True
        except Exception as e:
            logging.error(f"Error writing {file_path}: {e}")
            return False
    
    @staticmethod
    async def read_text(file_path: str) -> Optional[str]:
        """Read text file asynchronously"""
        try:
            async with aiofiles.open(file_path, 'r') as f:
                return await f.read()
        except FileNotFoundError:
            logging.warning(f"File not found: {file_path}")
            return None
        except Exception as e:
            logging.error(f"Error reading {file_path}: {e}")
            return None
    
    @staticmethod
    async def write_text(file_path: str, content: str) -> bool:
        """Write text file asynchronously"""
        try:
            # Ensure directory exists
            directory = os.path.dirname(file_path)
            if directory:
                await AsyncFileManager.ensure_directory(directory)
            
            async with aiofiles.open(file_path, 'w') as f:
                await f.write(content)
            return True
        except Exception as e:
            logging.error(f"Error writing {file_path}: {e}")
            return False
    
    @staticmethod
    async def append_text(file_path: str, content: str) -> bool:
        """Append text to file asynchronously"""
        try:
            async with aiofiles.open(file_path, 'a') as f:
                await f.write(content)
            return True
        except Exception as e:
            logging.error(f"Error appending to {file_path}: {e}")
            return False
    
    @staticmethod
    async def file_exists(file_path: str) -> bool:
        """Check if file exists asynchronously"""
        try:
            return await asyncio.get_event_loop().run_in_executor(
                None, os.path.exists, file_path
            )
        except Exception:
            return False
    
    @staticmethod
    async def delete_file(file_path: str) -> bool:
        """Delete file asynchronously"""
        try:
            if await AsyncFileManager.file_exists(file_path):
                await asyncio.get_event_loop().run_in_executor(
                    None, os.remove, file_path
                )
                return True
            return False
        except Exception as e:
            logging.error(f"Error deleting {file_path}: {e}")
            return False
    
    @staticmethod
    async def ensure_directory(directory: str) -> bool:
        """Ensure directory exists asynchronously"""
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, os.makedirs, directory, True  # exist_ok=True
            )
            return True
        except Exception as e:
            logging.error(f"Error creating directory {directory}: {e}")
            return False
    
    @staticmethod
    async def get_file_stats(file_path: str) -> Optional[Dict[str, Any]]:
        """Get file statistics asynchronously"""
        try:
            if not await AsyncFileManager.file_exists(file_path):
                return None
            
            stat = await asyncio.get_event_loop().run_in_executor(
                None, os.stat, file_path
            )
            
            return {
                'size': stat.st_size,
                'modified': stat.st_mtime,
                'created': stat.st_ctime,
                'is_file': os.path.isfile(file_path),
                'is_dir': os.path.isdir(file_path)
            }
        except Exception as e:
            logging.error(f"Error getting stats for {file_path}: {e}")
            return None
    
    @staticmethod
    async def write_mixed_content(file_path: str, content: Union[str, Dict[str, Any]]) -> bool:
        """Write content that can be either string or dict"""
        try:
            if isinstance(content, dict):
                return await AsyncFileManager.write_json(file_path, content)
            else:
                return await AsyncFileManager.write_text(file_path, content)
        except Exception as e:
            logging.error(f"Error writing mixed content to {file_path}: {e}")
            return False

class AsyncLogger:
    """Async logging utilities"""
    
    @staticmethod
    async def log_to_file(file_path: str, message: str, level: str = "INFO"):
        """Log message to file asynchronously"""
        try:
            timestamp = asyncio.get_event_loop().time()
            log_entry = f"[{timestamp}] {level}: {message}\n"
            
            await AsyncFileManager.append_text(file_path, log_entry)
        except Exception as e:
            logging.error(f"Error logging to {file_path}: {e}")
    
    @staticmethod
    async def rotate_log_file(file_path: str, max_size: int = 10 * 1024 * 1024):
        """Rotate log file if it exceeds max size"""
        try:
            stats = await AsyncFileManager.get_file_stats(file_path)
            if stats and stats['size'] > max_size:
                # Rename current log to .old
                old_path = f"{file_path}.old"
                await asyncio.get_event_loop().run_in_executor(
                    None, os.rename, file_path, old_path
                )
                logging.info(f"Rotated log file: {file_path}")
        except Exception as e:
            logging.error(f"Error rotating log file {file_path}: {e}")

class AsyncBackupManager:
    """Manages async backup operations"""
    
    def __init__(self, backup_dir: str = "backups"):
        self.backup_dir = backup_dir
    
    async def create_backup(self, source_files: List[str], backup_name: str) -> bool:
        """Create backup of multiple files"""
        try:
            await AsyncFileManager.ensure_directory(self.backup_dir)
            
            backup_data = {
                'backup_name': backup_name,
                'timestamp': asyncio.get_event_loop().time(),
                'files': {}
            }
            
            # Read all source files
            for file_path in source_files:
                if await AsyncFileManager.file_exists(file_path):
                    if file_path.endswith('.json'):
                        content = await AsyncFileManager.read_json(file_path)
                    else:
                        content = await AsyncFileManager.read_text(file_path)
                    
                    backup_data['files'][file_path] = content
            
            # Save backup
            backup_file = os.path.join(self.backup_dir, f"{backup_name}.json")
            return await AsyncFileManager.write_json(backup_file, backup_data)
            
        except Exception as e:
            logging.error(f"Error creating backup {backup_name}: {e}")
            return False
    
    async def restore_backup(self, backup_name: str) -> bool:
        """Restore files from backup"""
        try:
            backup_file = os.path.join(self.backup_dir, f"{backup_name}.json")
            backup_data = await AsyncFileManager.read_json(backup_file)
            
            if not backup_data:
                return False
            
            # Restore all files
            for file_path, content in backup_data['files'].items():
                success = await AsyncFileManager.write_mixed_content(file_path, content)
                if not success:
                    logging.error(f"Failed to restore file: {file_path}")
                    return False
            
            logging.info(f"Restored backup: {backup_name}")
            return True
            
        except Exception as e:
            logging.error(f"Error restoring backup {backup_name}: {e}")
            return False
    
    async def list_backups(self) -> List[Dict[str, Any]]:
        """List available backups"""
        try:
            backup_files = await AsyncFileManager.list_files(self.backup_dir, "*.json")
            backups = []
            
            for backup_file in backup_files:
                backup_data = await AsyncFileManager.read_json(backup_file)
                if backup_data:
                    backups.append({
                        'name': backup_data.get('backup_name', 'Unknown'),
                        'timestamp': backup_data.get('timestamp', 0),
                        'file_count': len(backup_data.get('files', {})),
                        'file_path': backup_file
                    })
            
            return sorted(backups, key=lambda x: x['timestamp'], reverse=True)
            
        except Exception as e:
            logging.error(f"Error listing backups: {e}")
            return [] 
   
    @staticmethod
    async def list_files(directory: str, pattern: str = "*") -> List[str]:
        """List files in directory asynchronously"""
        try:
            path = Path(directory)
            if not await AsyncFileManager.file_exists(directory):
                return []
            
            files = await asyncio.get_event_loop().run_in_executor(
                None, lambda: list(path.glob(pattern))
            )
            
            return [str(f) for f in files if f.is_file()]
        except Exception as e:
            logging.error(f"Error listing files in {directory}: {e}")
            return []