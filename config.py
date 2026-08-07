from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DEFECTS_DIR = DATA_DIR / "defects"
DB_PATH = DATA_DIR / "cnc_inspector.db"
MODELS_DIR = BASE_DIR / "models"
DEFAULT_YOLO_MODEL = "yolov8n.pt"

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
