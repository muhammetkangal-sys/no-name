from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torchvision.models import ResNet18_Weights, resnet18

_model = None
_transform = None


def _get_model():
    global _model, _transform
    if _model is None:
        weights = ResNet18_Weights.DEFAULT
        model = resnet18(weights=weights)
        model.fc = torch.nn.Identity()
        model.eval()
        _model = model
        _transform = weights.transforms()
    return _model, _transform


def extract_embedding(image_source) -> np.ndarray:
    if isinstance(image_source, (str, Path)):
        image = Image.open(image_source).convert("RGB")
    elif isinstance(image_source, Image.Image):
        image = image_source.convert("RGB")
    else:
        raise TypeError("image_source must be a path or PIL Image")

    model, transform = _get_model()
    tensor = transform(image).unsqueeze(0)

    with torch.no_grad():
        features = model(tensor)

    embedding = features.squeeze(0).numpy().astype(np.float32)
    norm = np.linalg.norm(embedding)
    if norm > 0:
        embedding = embedding / norm
    return embedding


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b))


def find_similar_defects(
    query_embedding: np.ndarray,
    known_defects: list[dict],
    top_k: int = 3,
    threshold: float = 0.0,
) -> list[dict]:
    results = []
    for defect in known_defects:
        score = cosine_similarity(query_embedding, defect["embedding"])
        if score >= threshold:
            results.append({**defect, "similarity": score})

    results.sort(key=lambda item: item["similarity"], reverse=True)
    return results[:top_k]
