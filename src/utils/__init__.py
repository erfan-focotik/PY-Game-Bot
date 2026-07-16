"""
Utility Module.
Process management, file utilities, and helper functions.
"""

import psutil
from typing import List, Dict, Optional, Tuple
import os


def list_game_processes() -> List[Dict[str, any]]:
    """
    List all running processes that could be game targets.
    
    Returns:
        List of process info dictionaries (pid, name, exe).
    """
    games = []
    
    for proc in psutil.process_iter(['pid', 'name', 'exe']):
        try:
            info = proc.info
            
            # Filter out system processes
            if not info['name'] or info['name'].startswith('.'):
                continue
            
            # Common game-related keywords (optional filtering)
            # You can customize this based on needs
            games.append({
                'pid': info['pid'],
                'name': info['name'],
                'exe': info['exe'] or ''
            })
            
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    return sorted(games, key=lambda x: x['name'])


def find_process_by_name(name_pattern: str) -> Optional[Dict[str, any]]:
    """
    Find a process by name pattern (case-insensitive partial match).
    
    Args:
        name_pattern: Process name to search for.
        
    Returns:
        Process info dict or None if not found.
    """
    name_pattern = name_pattern.lower()
    
    for proc in psutil.process_iter(['pid', 'name', 'exe']):
        try:
            if name_pattern in proc.info['name'].lower():
                return {
                    'pid': proc.info['pid'],
                    'name': proc.info['name'],
                    'exe': proc.info['exe'] or ''
                }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    return None


def get_process_window_rect(pid: int) -> Optional[Tuple[int, int, int, int]]:
    """
    Get the bounding rectangle of a process window.
    
    Args:
        pid: Process ID.
        
    Returns:
        Tuple (x1, y1, x2, y2) or None if not found.
    """
    try:
        import ctypes
        from ctypes import wintypes
        
        EnumWindows = ctypes.windll.user32.EnumWindows
        GetWindowTextW = ctypes.windll.user32.GetWindowTextW
        GetWindowTextLengthW = ctypes.windll.user32.GetWindowTextLengthW
        GetWindowThreadProcessId = ctypes.windll.user32.GetWindowThreadProcessId
        GetWindowRect = ctypes.windll.user32.GetWindowRect
        IsWindowVisible = ctypes.windll.user32.IsWindowVisible
        
        result = [None]
        
        def callback(hwnd, lparam):
            if IsWindowVisible(hwnd):
                window_pid = wintypes.DWORD()
                GetWindowThreadProcessId(hwnd, ctypes.byref(window_pid))
                
                if window_pid.value == pid:
                    length = GetWindowTextLengthW(hwnd)
                    if length > 0:
                        rect = wintypes.RECT()
                        GetWindowRect(hwnd, ctypes.byref(rect))
                        result[0] = (rect.left, rect.top, rect.right, rect.bottom)
                        return False  # Stop enumeration
            
            return True  # Continue enumeration
        
        EnumWindows(callback, 0)
        return result[0]
        
    except Exception as e:
        print(f"Failed to get window rect: {e}")
        return None


class ProcessManager:
    """
    Manages target game process selection and monitoring.
    """

    def __init__(self):
        self.target_process = None
        self.target_pid = None
        self.window_rect = None

    def select_process(self, pid: int = None, name: str = None) -> bool:
        """
        Select a target process by PID or name.
        
        Args:
            pid: Process ID (preferred).
            name: Process name (used if PID not provided).
            
        Returns:
            True if successfully selected.
        """
        if pid:
            process_info = None
            try:
                proc = psutil.Process(pid)
                process_info = {
                    'pid': proc.pid,
                    'name': proc.name(),
                    'exe': proc.exe() or ''
                }
            except psutil.NoSuchProcess:
                print(f"Process with PID {pid} not found")
                return False
                
        elif name:
            process_info = find_process_by_name(name)
            if not process_info:
                print(f"Process '{name}' not found")
                return False
        else:
            print("Either PID or name must be provided")
            return False
        
        self.target_process = process_info
        self.target_pid = process_info['pid']
        self.window_rect = get_process_window_rect(self.target_pid)
        
        print(f"Selected process: {self.target_process['name']} (PID: {self.target_pid})")
        if self.window_rect:
            print(f"Window rect: {self.window_rect}")
        
        return True

    def is_running(self) -> bool:
        """Check if the target process is still running."""
        if self.target_pid is None:
            return False
        
        try:
            proc = psutil.Process(self.target_pid)
            return proc.is_running()
        except psutil.NoSuchProcess:
            return False

    def get_window_region(self) -> Optional[Tuple[int, int, int, int]]:
        """Get the current window region for screen capture."""
        if not self.window_rect:
            self.window_rect = get_process_window_rect(self.target_pid)
        return self.window_rect

    def refresh_window_rect(self):
        """Refresh the cached window rectangle."""
        self.window_rect = get_process_window_rect(self.target_pid)


def load_script_file(filepath: str) -> str:
    """
    Load a script file content.
    
    Args:
        filepath: Path to the script file.
        
    Returns:
        Script content as string.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Script file not found: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()


def save_config_file(filepath: str, config: Dict[str, any]):
    """
    Save configuration to a JSON file.
    
    Args:
        filepath: Output file path.
        config: Configuration dictionary.
    """
    import json
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)


def load_config_file(filepath: str) -> Dict[str, any]:
    """
    Load configuration from a JSON file.
    
    Args:
        filepath: Config file path.
        
    Returns:
        Configuration dictionary.
    """
    import json
    
    if not os.path.exists(filepath):
        return {}
    
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def setup_template_folders(base_path: str) -> Dict[str, str]:
    """
    Setup standard template folder structure.
    
    Args:
        base_path: Base directory for templates.
        
    Returns:
        Dictionary of folder names to paths.
    """
    folders = {
        'targets': os.path.join(base_path, 'Boss', 'Target'),
        'items': os.path.join(base_path, 'Items'),
        'ui_elements': os.path.join(base_path, 'UI'),
        'custom': os.path.join(base_path, 'Custom')
    }
    
    for name, path in folders.items():
        os.makedirs(path, exist_ok=True)
    
    return folders


# Singleton instance
_process_manager: Optional[ProcessManager] = None


def get_process_manager() -> ProcessManager:
    """Get or create the global process manager instance."""
    global _process_manager
    if _process_manager is None:
        _process_manager = ProcessManager()
    return _process_manager
