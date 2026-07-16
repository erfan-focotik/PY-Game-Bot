"""
Computer Vision Pipeline Module.
Handles object recognition (template matching + YOLO) and text recognition (OCR).
Uses ThreadPoolExecutor for parallel frame processing.
"""

import threading
import queue
import time
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
    Multi-scale template matching for static target detection.
    Loads templates from user-defined folders.
    """

    def __init__(self, template_folder: str):
        """
        Initialize template matcher.
        
        Args:
            template_folder: Path to folder containing template images.
        """
        self.template_folder = template_folder
        self.templates: Dict[str, List[np.ndarray]] = {}
        self.load_templates()

    def load_templates(self):
        """Load all template images from the folder."""
        import os
        
        if not os.path.exists(self.template_folder):
            print(f"Template folder not found: {self.template_folder}")
            return
        
        for filename in os.listdir(self.template_folder):
            if filename.endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                name = os.path.splitext(filename)[0]
                template_path = os.path.join(self.template_folder, filename)
                
                try:
                    template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
                    if template is not None:
                        if name not in self.templates:
                            self.templates[name] = []
                        self.templates[name].append(template)
                        print(f"Loaded template: {name} ({template.shape})")
                except Exception as e:
                    print(f"Failed to load template {filename}: {e}")

    def match(self, frame: np.ndarray, threshold: float = 0.8) -> List[DetectionResult]:
        """
        Perform multi-scale template matching on the frame.
        
        Args:
            frame: Input frame (RGB or BGR).
            threshold: Minimum match threshold.
            
        Returns:
            List of DetectionResult objects.
        """
        results = []
        
        # Convert to grayscale
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        else:
            gray = frame
        
        for label, templates in self.templates.items():
            for template in templates:
                # Multi-scale matching
                for scale in [1.0, 0.75, 0.5, 0.25]:
                    if scale != 1.0:
                        scaled_template = cv2.resize(
                            template, 
                            None, 
                            fx=scale, 
                            fy=scale, 
                            interpolation=cv2.INTER_AREA
                        )
                    else:
                        scaled_template = template
                    
                    # Skip if template is larger than frame
                    if scaled_template.shape[0] > gray.shape[0] or \
                       scaled_template.shape[1] > gray.shape[1]:
                        continue
                    
                    # Template matching
                    result = cv2.matchTemplate(gray, scaled_template, cv2.TM_CCOEFF_NORMED)
                    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                    
                    if max_val >= threshold:
                        h, w = scaled_template.shape
                        x1, y1 = max_loc
                        x2, y2 = x1 + w, y1 + h
                        
                        detection = DetectionResult(
                            label=label,
                            confidence=float(max_val),
                            bbox=(int(x1), int(y1), int(x2), int(y2)),
                            center=(int(x1 + w/2), int(y1 + h/2)),
                            timestamp=time.time()
                        )
                        results.append(detection)
        
        return results


class YOLODetector:
    """
    YOLO-based object detection using ONNX Runtime.
    Supports YOLOv10n/v12n models for lightweight, fast detection.
    """

    def __init__(self, model_path: Optional[str] = None, confidence_threshold: float = 0.5):
        """
        Initialize YOLO detector.
        
        Args:
            model_path: Path to ONNX model file. If None, uses default model.
            confidence_threshold: Minimum confidence for detections.
        """
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.session = None
        self.input_size = (640, 640)
        self.class_names = []
        self._initialize_model()

    def _initialize_model(self):
        """Initialize the ONNX runtime session."""
        try:
            import onnxruntime as ort
            
            if self.model_path is None:
                print("No model path provided. YOLO detector disabled.")
                return
            
            # Configure session options
            session_options = ort.SessionOptions()
            session_options.intra_op_num_threads = 4
            session_options.inter_op_num_threads = 4
            
            # Use GPU if available
            providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
            self.session = ort.InferenceSession(
                self.model_path, 
                sess_options=session_options,
                providers=providers
            )
            
            # Get input/output info
            inputs = self.session.get_inputs()
            self.input_shape = inputs[0].shape
            print(f"YOLO model loaded: {self.model_path}")
            
        except ImportError:
            print("ONNX Runtime not installed. YOLO detector disabled.")
        except Exception as e:
            print(f"Failed to load YOLO model: {e}")
            self.session = None

    def detect(self, frame: np.ndarray) -> List[DetectionResult]:
        """
        Run YOLO detection on the frame.
        
        Args:
            frame: Input frame (RGB format).
            
        Returns:
            List of DetectionResult objects.
        """
        if self.session is None:
            return []
        
        results = []
        
        try:
            # Preprocess
            input_blob = self._preprocess(frame)
            
            # Inference
            outputs = self.session.run(None, {self.session.get_inputs()[0].name: input_blob})
            
            # Postprocess
            detections = self._postprocess(outputs[0], frame.shape)
            results.extend(detections)
            
        except Exception as e:
            print(f"YOLO detection error: {e}")
        
        return results

    def _preprocess(self, frame: np.ndarray) -> np.ndarray:
        """Preprocess frame for YOLO inference."""
        # Resize
        resized = cv2.resize(frame, self.input_size)
        
        # Normalize
        normalized = resized.astype(np.float32) / 255.0
        
        # HWC to CHW
        transposed = np.transpose(normalized, (2, 0, 1))
        
        # Add batch dimension
        blob = np.expand_dims(transposed, axis=0)
        
        return blob

    def _postprocess(self, output: np.ndarray, original_shape: Tuple) -> List[DetectionResult]:
        """Postprocess YOLO output to detection results."""
        results = []
        
        # Simplified postprocessing - adjust based on actual model output format
        for detection in output[0]:
            if len(detection) < 5:
                continue
                
            confidence = float(detection[4])
            if confidence < self.confidence_threshold:
                continue
            
            # Extract bounding box and class info
            # Note: This is simplified - real implementation depends on model format
            x1 = int(detection[0] * original_shape[1] / self.input_size[0])
            y1 = int(detection[1] * original_shape[0] / self.input_size[1])
            x2 = int(detection[2] * original_shape[1] / self.input_size[0])
            y2 = int(detection[3] * original_shape[0] / self.input_size[1])
            
            class_id = int(detection[5]) if len(detection) > 5 else 0
            
            results.append(DetectionResult(
                label=f"class_{class_id}",
                confidence=confidence,
                bbox=(x1, y1, x2, y2),
                center=((x1 + x2) // 2, (y1 + y2) // 2),
                timestamp=time.time()
            ))
        
        return results


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
    """

    def __init__(
        self,
        template_folder: Optional[str] = None,
        yolo_model_path: Optional[str] = None,
        use_gpu: bool = False,
        max_workers: int = 4
    ):
        """
        Initialize the vision pipeline.
        
        Args:
            template_folder: Path to template images folder.
            yolo_model_path: Path to YOLO ONNX model.
            use_gpu: Whether to use GPU for detection.
            max_workers: Maximum number of worker threads.
        """
        self.template_matcher = TemplateMatcher(template_folder) if template_folder else None
        self.yolo_detector = YOLODetector(yolo_model_path) if yolo_model_path else None
        self.ocr_engine = PaddleOCREngine(use_gpu=use_gpu)
        
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
                
                if self.template_matcher:
                    future = self.executor.submit(self.template_matcher.match, frame, 0.8)
                    futures.append(('template', future))
                
                if self.yolo_detector:
                    future = self.executor.submit(self.yolo_detector.detect, frame)
                    futures.append(('yolo', future))
                
                # OCR runs separately (can be region-specific)
                ocr_future = self.executor.submit(self.ocr_engine.recognize, frame)
                futures.append(('ocr', ocr_future))
                
                # Collect results
                all_detections = []
                all_text = []
                
                for task_type, future in futures:
                    try:
                        result = future.result(timeout=1.0)
                        if task_type in ('template', 'yolo'):
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
    yolo_model_path: Optional[str] = None,
    use_gpu: bool = False
) -> VisionPipeline:
    """Get or create the global vision pipeline instance."""
    global _vision_pipeline
    if _vision_pipeline is None:
        _vision_pipeline = VisionPipeline(
            template_folder=template_folder,
            yolo_model_path=yolo_model_path,
            use_gpu=use_gpu
        )
    return _vision_pipeline
