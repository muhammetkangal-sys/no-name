from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from ultralytics import YOLO

from config import CUSTOM_MODEL_PATH, DEFAULT_YOLO_MODEL, MODELS_DIR

_model = None

def _get_model():
    global _model
    if _model is None:
        MODELS_DIR.mkdir(parents=True, exist_ok=True)

        # Özel eğitilmiş model varsa onu tercih et
        if CUSTOM_MODEL_PATH.exists():
            try:
                _model = YOLO(str(CUSTOM_MODEL_PATH))
                return _model
            except Exception:
                pass  # Özel model yüklenemezse base modele düş

        model_path = MODELS_DIR / DEFAULT_YOLO_MODEL
        try:
            if model_path.exists():
                _model = YOLO(str(model_path))
            else:
                # Ultralytics standart modeli otomatik indirir
                _model = YOLO(DEFAULT_YOLO_MODEL)
        except Exception as e:
            raise RuntimeError(f"YOLO modeli yüklenemedi: {e}")
    return _model


def reload_model():
    """Eğitim sonrası yeni modeli yüklemek için mevcut modeli sıfırlar."""
    global _model
    _model = None


def run_yolo_classification(image_source) -> tuple[Image.Image, str, float]:
    """
    Runs YOLO image classification on the provided image.
    Returns:
    - Original PIL Image (no bounding boxes needed for classification)
    - Top predicted class name
    - Confidence score of the top prediction
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
    
    # Extract classification info
    # YOLO classification results have `probs` attribute
    if hasattr(results[0], 'probs') and results[0].probs is not None:
        top1_idx = int(results[0].probs.top1)
        top1_score = float(results[0].probs.top1conf)
        top_class_name = model.names[top1_idx]
    else:
        # Fallback if model is not classification or something fails
        top_class_name = "Bilinmiyor"
        top1_score = 0.0
            
    return image, top_class_name, top1_score
