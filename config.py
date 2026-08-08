from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DEFECTS_DIR = DATA_DIR / "defects"
DB_PATH = DATA_DIR / "cnc_inspector.db"
MODELS_DIR = BASE_DIR / "models"
DEFAULT_YOLO_MODEL = "yolov8n-cls.pt"
CUSTOM_MODEL_PATH = MODELS_DIR / "best.pt"  # Eğitim sonrası üretilen özel model
DATASET_DIR = DATA_DIR / "dataset"  # Eğitim için dışa aktarılan veri seti

DEFAULT_DEFECT_TYPES = [
    "Yüzey çizigi",
    "Çatlak",
    "Burr (talaş)",
    "Eksik delik",
    "Yanlış ölçü",
    "Renk/kaplama hatası",
    "Kırık/kertik",
    "Diğer",
]

SIMILARITY_THRESHOLD = 0.75

# --- Eğitim Ayarları ---
TRAIN_SPLIT_RATIO = 0.8  # %80 eğitim, %20 doğrulama
MIN_IMAGES_FOR_TRAINING = 50  # Eğitim başlatmak için minimum toplam görsel sayısı
MIN_IMAGES_PER_CLASS = 5  # Her sınıfta en az bu kadar görsel olmalı
TRAINING_EPOCHS = 50  # Fine-tuning epoch sayısı
TRAINING_IMG_SIZE = 224  # YOLO-cls için görsel boyutu
AUTO_RETRAIN_THRESHOLD = 100  # Bu kadar yeni (eğitilmemiş) görsel birikince otomatik eğitim tetiklenir
