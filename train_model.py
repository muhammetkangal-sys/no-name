"""
train_model.py — Dışa aktarılmış veri seti üzerinden YOLOv8 Classification
modelini fine-tune eder.

Kullanım:
    python train_model.py              # Varsayılan ayarlarla eğitim
    python train_model.py --epochs 100 # Özel epoch sayısı ile eğitim
    python train_model.py --force      # Minimum görsel kontrolünü atla

Eğitim sonrası en iyi ağırlıklar models/best.pt olarak kaydedilir.
"""

import argparse
import shutil
from datetime import datetime
from pathlib import Path

from ultralytics import YOLO

from config import (
    CUSTOM_MODEL_PATH,
    DATASET_DIR,
    DEFAULT_YOLO_MODEL,
    MODELS_DIR,
    TRAINING_EPOCHS,
    TRAINING_IMG_SIZE,
)
from utils.export_dataset import export_dataset, get_dataset_status


def _backup_existing_model() -> Path | None:
    """Mevcut özel modeli yedekler, yoksa None döner."""
    if CUSTOM_MODEL_PATH.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = MODELS_DIR / f"best_backup_{timestamp}.pt"
        shutil.copy2(CUSTOM_MODEL_PATH, backup_path)
        return backup_path
    return None


def train(
    epochs: int | None = None,
    force_export: bool = False,
    skip_export: bool = False,
) -> dict:
    """
    Eğitim pipeline'ını baştan sona çalıştırır:
    1. Veri setini dışa aktar (export_dataset)
    2. Mevcut modeli yedekle
    3. YOLOv8-cls fine-tuning başlat
    4. En iyi ağırlıkları models/best.pt'ye kopyala

    Args:
        epochs: Epoch sayısı (None ise config'den alır).
        force_export: True ise minimum görsel kontrolünü atlar.
        skip_export: True ise veri setini yeniden oluşturmaz (zaten mevcut ise).

    Returns:
        Eğitim sonuç bilgilerini içeren dict.
    """
    epochs = epochs or TRAINING_EPOCHS

    # --- 1. Veri seti dışa aktarımı ---
    if not skip_export:
        export_result = export_dataset(force=force_export)
        if not export_result["success"]:
            return {
                "success": False,
                "stage": "export",
                "message": export_result["message"],
            }
    else:
        # Zaten mevcut veri setini kontrol et
        if not DATASET_DIR.exists() or not (DATASET_DIR / "train").exists():
            return {
                "success": False,
                "stage": "export",
                "message": "Veri seti bulunamadı. --skip-export'u kaldırın.",
            }

    # Train klasöründeki sınıf sayısını kontrol et
    train_dir = DATASET_DIR / "train"
    class_dirs = [d for d in train_dir.iterdir() if d.is_dir()]
    num_classes = len(class_dirs)

    if num_classes < 2:
        return {
            "success": False,
            "stage": "validation",
            "message": (
                f"Eğitim için en az 2 farklı sınıf gerekiyor. "
                f"Şu an {num_classes} sınıf var."
            ),
        }

    # Her sınıfta en az 1 görsel olduğunu doğrula
    empty_classes = [
        d.name for d in class_dirs if not list(d.glob("*"))
    ]
    if empty_classes:
        return {
            "success": False,
            "stage": "validation",
            "message": f"Şu sınıflar boş: {', '.join(empty_classes)}",
        }

    # --- 2. Mevcut modeli yedekle ---
    backup = _backup_existing_model()

    # --- 3. Modeli yükle ve eğit ---
    # Önceden eğitilmiş özel model varsa onu kullan, yoksa base modeli al
    if CUSTOM_MODEL_PATH.exists():
        base_model = str(CUSTOM_MODEL_PATH)
        print(f"Önceki özel model üzerinden devam ediliyor: {base_model}")
    else:
        base_model = DEFAULT_YOLO_MODEL
        print(f"Temel model ile başlanıyor: {base_model}")

    model = YOLO(base_model)

    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    try:
        results = model.train(
            data=str(DATASET_DIR),
            epochs=epochs,
            imgsz=TRAINING_IMG_SIZE,
            batch=-1,  # AutoBatch — GPU/CPU'ya göre otomatik batch boyutu
            patience=10,  # 10 epoch iyileşme olmazsa erken durdur
            project=str(MODELS_DIR / "runs"),
            name="cls_training",
            exist_ok=True,
            verbose=True,
        )
    except Exception as e:
        # Eğitim başarısız olursa yedekten geri yükle
        if backup and backup.exists():
            shutil.copy2(backup, CUSTOM_MODEL_PATH)
            print(f"Hata nedeniyle yedek geri yüklendi: {backup}")
        return {
            "success": False,
            "stage": "training",
            "message": f"Eğitim sırasında hata: {e}",
        }

    # --- 4. En iyi modeli kopyala ---
    best_weights = MODELS_DIR / "runs" / "cls_training" / "weights" / "best.pt"
    if best_weights.exists():
        shutil.copy2(best_weights, CUSTOM_MODEL_PATH)
        print(f"En iyi model kaydedildi: {CUSTOM_MODEL_PATH}")
    else:
        # best yoksa last'ı dene
        last_weights = (
            MODELS_DIR / "runs" / "cls_training" / "weights" / "last.pt"
        )
        if last_weights.exists():
            shutil.copy2(last_weights, CUSTOM_MODEL_PATH)
            print(f"Son model kaydedildi (best bulunamadı): {CUSTOM_MODEL_PATH}")
        else:
            return {
                "success": False,
                "stage": "save",
                "message": "Eğitim tamamlandı ancak ağırlık dosyası bulunamadı.",
            }

    return {
        "success": True,
        "stage": "complete",
        "message": (
            f"Eğitim başarıyla tamamlandı! {epochs} epoch, "
            f"{num_classes} sınıf. Model: {CUSTOM_MODEL_PATH}"
        ),
        "model_path": str(CUSTOM_MODEL_PATH),
        "backup_path": str(backup) if backup else None,
        "num_classes": num_classes,
        "epochs": epochs,
    }


def check_auto_retrain_needed() -> bool:
    """Otomatik yeniden eğitim gerekip gerekmediğini kontrol eder."""
    from config import AUTO_RETRAIN_THRESHOLD

    status = get_dataset_status()
    return (
        status["ready_for_training"]
        and status["untrained_images"] >= AUTO_RETRAIN_THRESHOLD
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="YOLOv8 Classification modeli eğitimi"
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=None,
        help=f"Epoch sayısı (varsayılan: {TRAINING_EPOCHS})",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Minimum görsel kontrolünü atla",
    )
    parser.add_argument(
        "--skip-export",
        action="store_true",
        help="Veri setini yeniden oluşturma, mevcut olanı kullan",
    )

    args = parser.parse_args()

    result = train(
        epochs=args.epochs,
        force_export=args.force,
        skip_export=args.skip_export,
    )

    if result["success"]:
        print(f"\n✅ {result['message']}")
    else:
        print(f"\n❌ [{result['stage']}] {result['message']}")
