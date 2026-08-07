from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from ultralytics import YOLO

from config import DEFAULT_YOLO_MODEL, MODELS_DIR

_model = None

def _get_model():
    global _model
    if _model is None:
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        model_path = MODELS_DIR / DEFAULT_YOLO_MODEL
        # Ultralytics can download the model automatically if it's a standard one like yolov8n.pt
        try:
            if model_path.exists():
                _model = YOLO(str(model_path))
            else:
                # This will download yolov8n.pt if DEFAULT_YOLO_MODEL is a standard YOLO model
                _model = YOLO(DEFAULT_YOLO_MODEL) 
                
        except Exception as e:
            raise RuntimeError(f"YOLO modeli yüklenemedi: {e}")
    return _model


def run_yolo_detection(image_source) -> tuple[Image.Image, int, list[str]]:
    """
    Runs YOLO object detection on the provided image.
    Returns:
    - Annotated PIL Image (with bounding boxes)
    - Total number of detections
    - List of class names detected
    """
    if isinstance(image_source, (str, Path)):
        image = Image.open(image_source).convert("RGB")
    elif isinstance(image_source, Image.Image):
        image = image_source.convert("RGB")
    else:
        raise TypeError("image_source must be a path or PIL Image")

    model = _get_model()
    
    # Run inference
    results = model(image, verbose=False)
    
    # Get annotated image array (BGR)
    annotated_bgr = results[0].plot()
    
    # Convert BGR to RGB for PIL
    annotated_rgb = cv2.cvtColor(annotated_bgr, cv2.COLOR_BGR2RGB)
    annotated_image = Image.fromarray(annotated_rgb)
    
    # Extract detection info
    boxes = results[0].boxes
    num_detections = len(boxes)
    
    detected_classes = []
    if num_detections > 0:
        for cls_id in boxes.cls.tolist():
            detected_classes.append(model.names[int(cls_id)])
            
    return annotated_image, num_detections, detected_classes
