import cv2
import numpy as np


from pathlib import Path
from PIL import Image

def preprocess_image(image_source):
    if isinstance(image_source, (str, Path)):
        image = cv2.imread(str(image_source))
        if image is None:
            raise FileNotFoundError(f"Görüntü bulunamadı: {image_source}")
    elif isinstance(image_source, Image.Image):
        # PIL RGB to OpenCV BGR
        image = cv2.cvtColor(np.array(image_source), cv2.COLOR_RGB2BGR)
    else:
        raise TypeError("image_source must be a path or PIL Image")

    # Gri ton
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Gürültü azaltma
    blur = cv2.GaussianBlur(gray, (5, 5), 0)

    # Kenar bulma
    edges = cv2.Canny(blur, 50, 150)

    # Streamlit'te göstermek için OpenCV BGR görüntüsünü RGB'ye çevir (orijinal ve blur için)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    blur_rgb = cv2.cvtColor(blur, cv2.COLOR_GRAY2RGB)
    
    return image_rgb, gray, blur_rgb, edges