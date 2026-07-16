"""
Computer Vision Pipeline Module.
Handles object recognition (template matching) and text recognition (OCR).
Uses ThreadPoolExecutor for parallel frame processing.

Template Matching System:
- Objects are detected by matching template images against the screen
- Template images are loaded from the template_folder directory
- File naming convention: <object_label>.png (e.g., "enemy.png", "loot_item.png")
- Multiple scales are tested automatically for size variations
- Confidence threshold filters out weak matches
"""

import threading
import queue
import time
import os
from typing import List, Dict, Optional, Any, Tuple
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import cv2
from dataclasses import dataclass


@dataclass
class DetectionResult:
    """Represents a detection result from the vision pipeline."""
    label: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2)
    center: Tuple[int, int]  # (cx, cy)
    timestamp: float


@dataclass
class TextRecognitionResult:
    """Represents OCR result."""
    text: str
    confidence: float
    bbox: Tuple[int, int, int, int]
    position: Tuple[int, int]  # Center position


class TemplateMatcher:
    """
    Multi-scale template matching for object detection.
    
    How it works:
    1. Load template images from the template_folder directory
    2. Each image file name becomes the object label (without extension)
    3. For each frame, search for all loaded templates at multiple scales
    4. Return matches that exceed the confidence threshold
    
    Example:
    - Place "enemy.png" in assets/templates/ folder
    - In script: enemy = find_object("enemy", 0.75)
    - The system will search for enemy.png template on screen
    """

    def __init__(self, template_folder: str):
        """
        Initialize template matcher.
        
        Args:
            template_folder: Path to folder containing template images.
                            Template files should be named after the object label
                            (e.g., "enemy.png" for label "enemy")
        """
        self.template_folder = template_folder
        self.templates: Dict[str, List[Tuple[np.ndarray, str]]] = {}  # label -> [(template, filepath)]
        self.scales = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3]  # Multi-scale factors
        self.load_templates()

    def load_templates(self):
        """
        Load all template images from the template folder.
        
        File naming convention:
        - enemy.png -> label "enemy"
        - loot_item.jpg -> label "loot_item"
        - health_bar.bmp -> label "health_bar"
        
        Subdirectories are scanned recursively for organized templates.
        """
        if not os.path.exists(self.template_folder):
            print(f"Template folder not found: {self.template_folder}")
            print(f"Please create the folder and add template images.")
            print(f"Example: {self.template_folder}/enemy.png")
            return
        
        loaded_count = 0
        
        # Walk through directory and subdirectories
        for root, dirs, files in os.walk(self.template_folder):
            for filename in files:
                if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.webp')):
                    # Skip hidden files
                    if filename.startswith('.'):
                        continue
                        
                    # Extract label from filename (without extension)
                    name = os.path.splitext(filename)[0]
                    template_path = os.path.join(root, filename)
                    
                    try:
                        template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
                        if template is not None and template.size > 0:
                            if name not in self.templates:
                                self.templates[name] = []
                            self.templates[name].append((template, template_path))
                            print(f"✓ Loaded template: '{name}' from {template_path} ({template.shape})")
                            loaded_count += 1
                        else:
                            print(f"⚠ Warning: Empty or invalid template: {template_path}")
                    except Exception as e:
                        print(f"✗ Failed to load template {filename}: {e}")
        
        if loaded_count == 0:
            print(f"\n⚠ No templates loaded from {self.template_folder}")
            print("Add template images to enable object detection.")
            print("Example: Save a screenshot of your target object as 'enemy.png' in this folder.\n")
        else:
            print(f"\n✓ Successfully loaded {loaded_count} template(s)\n")

    def reload_templates(self):
        """Reload all templates (useful for adding new templates at runtime)."""
        self.templates.clear()
        self.load_templates()

    def match(self, frame: np.ndarray, threshold: float = 0.8) -> List[DetectionResult]:
        """
        Perform multi-scale template matching on the frame.
        
        Args:
            frame: Input frame (RGB or BGR format).
            threshold: Minimum match threshold (0.0 to 1.0).
                      Higher values = more strict matching.
                      Recommended: 0.7 to 0.9 depending on template quality.
            
        Returns:
            List of DetectionResult objects sorted by confidence (highest first).
        """
        if not self.templates:
            return []
        
        results = []
        
        # Convert to grayscale if needed
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        else:
            gray = frame
        
        frame_h, frame_w = gray.shape
        
        for label, template_list in self.templates.items():
            for template, _ in template_list:
                template_h, template_w = template.shape
                
                # Skip if template is larger than frame at full scale
                if template_h > frame_h or template_w > frame_w:
                    continue
                
                best_match = None
                best_confidence = 0.0
                
                # Multi-scale matching
                for scale in self.scales:
                    # Calculate scaled dimensions
                    scaled_w = int(template_w * scale)
                    scaled_h = int(template_h * scale)
                    
                    # Skip if scaled template is too small or too large
                    if scaled_w < 8 or scaled_h < 8:
                        continue
                    if scaled_w > frame_w or scaled_h > frame_h:
                        continue
                    
                    # Resize template for this scale
                    scaled_template = cv2.resize(
                        template,
                        (scaled_w, scaled_h),
                        interpolation=cv2.INTER_AREA
                    )
                    
                    # Template matching using normalized cross-correlation
                    result = cv2.matchTemplate(gray, scaled_template, cv2.TM_CCOEFF_NORMED)
                    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                    
                    # Keep best match across all scales
                    if max_val > best_confidence:
                        best_confidence = max_val
                        best_match = (max_loc, scaled_w, scaled_h)
                
                # Check if best match meets threshold
                if best_match and best_confidence >= threshold:
                    (x1, y1), w, h = best_match
                    x2, y2 = x1 + w, y1 + h
                    
                    detection = DetectionResult(
                        label=label,
                        confidence=float(best_confidence),
                        bbox=(int(x1), int(y1), int(x2), int(y2)),
                        center=(int(x1 + w / 2), int(y1 + h / 2)),
                        timestamp=time.time()
                    )
                    results.append(detection)
        
        # Sort by confidence (highest first)
        results.sort(key=lambda r: r.confidence, reverse=True)
        return results

    def match_single(self, frame: np.ndarray, label: str, threshold: float = 0.8) -> Optional[DetectionResult]:
        """
        Match a specific template label only (optimized for single-object search).
        
        Args:
            frame: Input frame.
            label: Specific template label to search for.
            threshold: Minimum confidence threshold.
            
        Returns:
            Best matching DetectionResult or None if not found.
        """
        if label not in self.templates or not self.templates[label]:
            return None
        
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        else:
            gray = frame
        
        frame_h, frame_w = gray.shape
        best_result = None
        best_confidence = 0.0
        
        for template, _ in self.templates[label]:
            template_h, template_w = template.shape
            
            if template_h > frame_h or template_w > frame_w:
                continue
            
            for scale in self.scales:
                scaled_w = int(template_w * scale)
                scaled_h = int(template_h * scale)
                
                if scaled_w < 8 or scaled_h < 8:
                    continue
                if scaled_w > frame_w or scaled_h > frame_h:
                    continue
                
                scaled_template = cv2.resize(
                    template,
                    (scaled_w, scaled_h),
                    interpolation=cv2.INTER_AREA
                )
                
                result = cv2.matchTemplate(gray, scaled_template, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(result)
                
                if max_val > best_confidence:
                    best_confidence = max_val
                    (x1, y1) = max_loc
                    x2, y2 = x1 + scaled_w, y1 + scaled_h
                    
                    best_result = DetectionResult(
                        label=label,
                        confidence=float(max_val),
                        bbox=(int(x1), int(y1), int(x2), int(y2)),
                        center=(int(x1 + scaled_w / 2), int(y1 + scaled_h / 2)),
                        timestamp=time.time()
                    )
        
        if best_result and best_confidence >= threshold:
            return best_result
        
        return None


class PaddleOCREngine:
    """
    Text recognition using PaddleOCR (ONNX version for CPU efficiency).
    Includes preprocessing for enhanced accuracy.
    """

    def __init__(self, use_gpu: bool = False, lang: str = 'en'):
        """
        Initialize PaddleOCR engine.
        
        Args:
            use_gpu: Whether to use GPU acceleration.
            lang: Language code for OCR.
        """
        self.use_gpu = use_gpu
        self.lang = lang
        self.ocr_system = None
        self._initialize_ocr()

    def _initialize_ocr(self):
        """Initialize PaddleOCR system."""
        try:
            from paddleocr import PaddleOCR
            
            self.ocr_system = PaddleOCR(
                use_gpu=self.use_gpu,
                lang=self.lang,
                show_log=False,
                det_model_dir=None,  # Use default
                rec_model_dir=None,  # Use default
            )
            print("PaddleOCR initialized successfully")
            
        except ImportError:
            print("PaddleOCR not installed. OCR functionality disabled.")
        except Exception as e:
            print(f"Failed to initialize PaddleOCR: {e}")
            self.ocr_system = None

    def recognize(self, frame: np.ndarray, region: Optional[Tuple[int, int, int, int]] = None) -> List[TextRecognitionResult]:
        """
        Perform OCR on the frame.
        
        Args:
            frame: Input frame (RGB or BGR).
            region: Optional region of interest (x1, y1, x2, y2).
            
        Returns:
            List of TextRecognitionResult objects.
        """
        if self.ocr_system is None:
            return []
        
        results = []
        
        try:
            # Crop to region if specified
            if region:
                x1, y1, x2, y2 = region
                cropped = frame[y1:y2, x1:x2]
            else:
                cropped = frame
                x1, y1 = 0, 0
            
            # Preprocessing for better OCR accuracy
            preprocessed = self._preprocess_for_ocr(cropped)
            
            # Run OCR
            ocr_results = self.ocr_system.ocr(preprocessed, cls=True)
            
            if ocr_results and ocr_results[0]:
                for result in ocr_results[0]:
                    if len(result) >= 2:
                        bbox_points = result[0]
                        text, confidence = result[1]
                        
                        # Convert bbox points to rectangle
                        x_coords = [p[0] for p in bbox_points]
                        y_coords = [p[1] for p in bbox_points]
                        
                        bbox_x1 = min(x_coords) + x1
                        bbox_y1 = min(y_coords) + y1
                        bbox_x2 = max(x_coords) + x1
                        bbox_y2 = max(y_coords) + y1
                        
                        results.append(TextRecognitionResult(
                            text=text,
                            confidence=float(confidence),
                            bbox=(bbox_x1, bbox_y1, bbox_x2, bbox_y2),
                            position=((bbox_x1 + bbox_x2) // 2, (bbox_y1 + bbox_y2) // 2)
                        ))
                        
        except Exception as e:
            print(f"OCR error: {e}")
        
        return results

    def _preprocess_for_ocr(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess image for better OCR accuracy.
        Applies binarization and noise reduction.
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image
        
        # Noise reduction
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
        
        # Adaptive thresholding for binarization
        binary = cv2.adaptiveThreshold(
            denoised,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11,
            2
        )
        
        return binary


class VisionPipeline:
    """
    Main vision pipeline that orchestrates capture consumption and detection.
    Uses ThreadPoolExecutor for parallel processing.
    
    The pipeline processes frames from the capture engine and runs:
    1. Template matching - finds objects based on template images
    2. OCR - reads text from screen (optional, can be resource-intensive)
    
    Results are queued for the scripting engine to consume via find_object(),
    text_exists(), etc.
    """

    def __init__(
        self,
        template_folder: Optional[str] = None,
        use_gpu: bool = False,
        max_workers: int = 3,
        enable_ocr: bool = True
    ):
        """
        Initialize the vision pipeline.
        
        Args:
            template_folder: Path to template images folder.
                            Templates should be named after object labels.
            use_gpu: Whether to use GPU for OCR (template matching is CPU-based).
            max_workers: Maximum number of worker threads for parallel processing.
                        Default is 3 (template matching + OCR + buffer).
            enable_ocr: Whether to enable OCR text recognition.
                       Disable for better performance if not using text detection.
        """
        self.template_matcher = TemplateMatcher(template_folder) if template_folder else None
        self.ocr_engine = PaddleOCREngine(use_gpu=use_gpu) if enable_ocr else None
        self.enable_ocr = enable_ocr
        
        self.result_queue = queue.Queue(maxsize=50)
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.running = False
        self.process_thread = None

    def start(self, capture_queue: queue.Queue):
        """
        Start the vision pipeline.
        
        Args:
            capture_queue: Queue containing captured frames.
        """
        self.running = True
        self.process_thread = threading.Thread(
            target=self._process_loop,
            args=(capture_queue,),
            daemon=True
        )
        self.process_thread.start()
        print("Vision pipeline started")

    def stop(self):
        """Stop the vision pipeline."""
        self.running = False
        if self.process_thread:
            self.process_thread.join(timeout=2.0)
        self.executor.shutdown(wait=False)
        print("Vision pipeline stopped")

    def _process_loop(self, capture_queue: queue.Queue):
        """Main processing loop that consumes frames from capture queue."""
        while self.running:
            try:
                # Get frame with timeout
                frame = capture_queue.get(timeout=0.1)
                
                # Submit processing tasks to thread pool
                futures = []
                
                # Template matching (always enabled if templates loaded)
                if self.template_matcher:
                    future = self.executor.submit(self.template_matcher.match, frame, 0.8)
                    futures.append(('template', future))
                
                # OCR (only if enabled and engine initialized)
                if self.enable_ocr and self.ocr_engine:
                    ocr_future = self.executor.submit(self.ocr_engine.recognize, frame)
                    futures.append(('ocr', ocr_future))
                
                # Collect results
                all_detections = []
                all_text = []
                
                for task_type, future in futures:
                    try:
                        result = future.result(timeout=1.0)
                        if task_type == 'template':
                            all_detections.extend(result)
                        elif task_type == 'ocr':
                            all_text.extend(result)
                    except Exception as e:
                        print(f"Task error ({task_type}): {e}")
                
                # Push combined results to result queue
                combined_result = {
                    'detections': all_detections,
                    'text': all_text,
                    'timestamp': time.time()
                }
                
                try:
                    if not self.result_queue.full():
                        self.result_queue.put(combined_result, block=False)
                except queue.Full:
                    pass
                    
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Pipeline error: {e}")
                time.sleep(0.01)

    def get_results(self, timeout: float = 0.1) -> Optional[Dict[str, Any]]:
        """
        Get latest vision results.
        
        Args:
            timeout: Maximum time to wait for results.
            
        Returns:
            Dictionary containing detections and text results, or None.
        """
        try:
            return self.result_queue.get(timeout=timeout)
        except queue.Empty:
            return None


# Singleton instance
_vision_pipeline: Optional[VisionPipeline] = None


def get_vision_pipeline(
    template_folder: Optional[str] = None,
    use_gpu: bool = False,
    enable_ocr: bool = True
) -> VisionPipeline:
    """
    Get or create the global vision pipeline instance.
    
    Args:
        template_folder: Path to template images folder.
        use_gpu: Whether to use GPU for OCR.
        enable_ocr: Whether to enable OCR text recognition.
        
    Returns:
        VisionPipeline instance.
    """
    global _vision_pipeline
    if _vision_pipeline is None:
        _vision_pipeline = VisionPipeline(
            template_folder=template_folder,
            use_gpu=use_gpu,
            enable_ocr=enable_ocr
        )
    return _vision_pipeline

