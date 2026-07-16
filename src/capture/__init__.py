"""
Screen Capture Module using DXcam/D3DShot for Windows Desktop Duplication API.
Captures frames at high FPS and pushes them to a thread-safe queue.
"""

import threading
import queue
import time
from typing import Optional, Tuple
import numpy as np

try:
    import dxcam
except ImportError:
    dxcam = None


class ScreenCapture:
    """
    High-performance screen capture engine using Windows Desktop Duplication API.
    Runs in a dedicated background thread and produces frames as NumPy arrays.
    """

    def __init__(self, region: Optional[Tuple[int, int, int, int]] = None, fps_target: int = 60):
        """
        Initialize the screen capture engine.
        
        Args:
            region: Optional capture region (x1, y1, x2, y2). If None, captures full screen.
            fps_target: Target frames per second.
        """
        self.region = region
        self.fps_target = fps_target
        self.frame_queue = queue.Queue(maxsize=10)  # Bounded queue to prevent memory issues
        self.running = False
        self.capture_thread = None
        self.camera = None
        self.last_frame_time = 0
        self.fps_counter = 0
        self.current_fps = 0

    def initialize(self) -> bool:
        """Initialize the DXcam capture device."""
        if dxcam is None:
            print("Warning: dxcam not available. Using mock capture mode.")
            return False
        
        try:
            self.camera = dxcam.create(device_idx=0, video_mode=True)
            if self.region:
                self.camera.set_region(self.region)
            return True
        except Exception as e:
            print(f"Failed to initialize DXcam: {e}")
            return False

    def _capture_loop(self):
        """Background thread loop for capturing frames."""
        frame_interval = 1.0 / self.fps_target
        last_capture_time = time.time()
        
        while self.running:
            current_time = time.time()
            
            # Frame rate limiting
            elapsed = current_time - last_capture_time
            if elapsed < frame_interval:
                time.sleep(frame_interval - elapsed)
                continue
            
            last_capture_time = current_time
            
            try:
                if self.camera:
                    frame = self.camera.grab(color_mode="RGB")
                    if frame is not None:
                        # Convert to numpy array if needed
                        if not isinstance(frame, np.ndarray):
                            frame = np.array(frame)
                        
                        # Non-blocking put, drop old frames if queue is full
                        try:
                            if not self.frame_queue.empty():
                                try:
                                    self.frame_queue.get_nowait()
                                except queue.Empty:
                                    pass
                            self.frame_queue.put(frame, block=False)
                            self.fps_counter += 1
                        except queue.Full:
                            pass
                else:
                    # Mock capture for testing without hardware
                    mock_frame = self._generate_mock_frame()
                    try:
                        if not self.frame_queue.empty():
                            try:
                                self.frame_queue.get_nowait()
                            except queue.Empty:
                                pass
                        self.frame_queue.put(mock_frame, block=False)
                        self.fps_counter += 1
                    except queue.Full:
                        pass
                        
            except Exception as e:
                print(f"Capture error: {e}")
                continue

    def _generate_mock_frame(self) -> np.ndarray:
        """Generate a mock frame for testing purposes."""
        height, width = 1080, 1920
        if self.region:
            x1, y1, x2, y2 = self.region
            width = x2 - x1
            height = y2 - y1
        
        # Create a simple gradient pattern with timestamp
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        for i in range(height):
            frame[i, :, 0] = int(255 * i / height)  # Blue gradient
            frame[i, :, 1] = int(255 * (height - i) / height)  # Green gradient
            frame[i, :, 2] = 128  # Constant red
        
        return frame

    def _fps_counter_loop(self):
        """Background thread to calculate FPS."""
        while self.running:
            time.sleep(1.0)
            self.current_fps = self.fps_counter
            self.fps_counter = 0

    def start(self):
        """Start the capture thread."""
        if self.running:
            return
        
        self.running = True
        
        # Initialize camera if not already done
        if not self.camera:
            self.initialize()
        
        # Start capture thread
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
        
        # Start FPS counter thread
        fps_thread = threading.Thread(target=self._fps_counter_loop, daemon=True)
        fps_thread.start()
        
        print(f"Screen capture started. Region: {self.region}, Target FPS: {self.fps_target}")

    def stop(self):
        """Stop the capture thread."""
        self.running = False
        if self.capture_thread:
            self.capture_thread.join(timeout=2.0)
        print("Screen capture stopped.")

    def get_frame(self, timeout: float = 0.1) -> Optional[np.ndarray]:
        """
        Get the latest captured frame.
        
        Args:
            timeout: Maximum time to wait for a frame.
            
        Returns:
            NumPy array of the frame (RGB format), or None if no frame available.
        """
        try:
            return self.frame_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def get_fps(self) -> int:
        """Get the current capture FPS."""
        return self.current_fps

    def set_region(self, region: Tuple[int, int, int, int]):
        """Update the capture region."""
        self.region = region
        if self.camera:
            self.camera.set_region(region)


# Singleton instance for global access
_capture_instance: Optional[ScreenCapture] = None


def get_capture_engine(region: Optional[Tuple[int, int, int, int]] = None, 
                       fps_target: int = 60) -> ScreenCapture:
    """Get or create the global screen capture engine instance."""
    global _capture_instance
    if _capture_instance is None:
        _capture_instance = ScreenCapture(region=region, fps_target=fps_target)
    return _capture_instance
