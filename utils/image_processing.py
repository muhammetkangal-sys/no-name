import cv2


def preprocess_image(image_path):
    # Görüntüyü oku
    image = cv2.imread(image_path)

    if image is None:
        raise FileNotFoundError(f"Görüntü bulunamadı: {image_path}")

    # Gri ton
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Gürültü azaltma
    blur = cv2.GaussianBlur(gray, (5, 5), 0)

    # Kenar bulma
    edges = cv2.Canny(blur, 50, 150)

    return image, gray, blur, edges