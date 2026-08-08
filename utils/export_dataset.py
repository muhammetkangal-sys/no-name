"""
export_dataset.py — Veritabanındaki etiketlenmiş görselleri YOLO Classification
veri seti formatına dönüştürür.

Çıktı yapısı:
    data/dataset/
    ├── train/
    │   ├── cizik/
    │   │   ├── img001.jpg
    │   │   └── ...
    │   └── catlak/
    │       └── ...
    └── val/
        ├── cizik/
        └── catlak/

Her sınıf kendi klasörüne ayrılır, görseller train/val olarak bölünür.
"""

import random
import re
import shutil
from pathlib import Path

from config import (
    DATASET_DIR,
    MIN_IMAGES_FOR_TRAINING,
    MIN_IMAGES_PER_CLASS,
    TRAIN_SPLIT_RATIO,
)
from utils.database import get_all_defects, get_connection


def _sanitize_class_name(name: str) -> str:
    """Hata tipi adını dosya sistemi için güvenli klasör adına çevirir."""
    # Türkçe karakter dönüşümü
    tr_map = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
    name = name.translate(tr_map)
    # Boşluk ve özel karakterleri alt çizgiye çevir
    name = re.sub(r"[^a-zA-Z0-9]", "_", name.strip().lower())
    # Ardışık alt çizgileri teke düşür
    name = re.sub(r"_+", "_", name).strip("_")
    return name or "diger"


def _get_untrained_count() -> int:
    """Henüz eğitimde kullanılmamış (trained_at IS NULL) görsel sayısını döndürür.
    Eğer tablo henüz 'trained_at' sütununa sahip değilse toplam sayıyı döndürür."""
    with get_connection() as conn:
        # trained_at sütunu var mı kontrol et
        cols = [
            row[1]
            for row in conn.execute("PRAGMA table_info(defects)").fetchall()
        ]
        if "trained_at" in cols:
            row = conn.execute(
                "SELECT COUNT(*) AS c FROM defects WHERE trained_at IS NULL"
            ).fetchone()
        else:
            row = conn.execute("SELECT COUNT(*) AS c FROM defects").fetchone()
    return row["c"]


def _mark_as_trained(defect_ids: list[int]) -> None:
    """Eğitimde kullanılan kayıtları 'trained_at' ile işaretler."""
    if not defect_ids:
        return
    with get_connection() as conn:
        # trained_at sütunu yoksa ekle
        cols = [
            row[1]
            for row in conn.execute("PRAGMA table_info(defects)").fetchall()
        ]
        if "trained_at" not in cols:
            conn.execute(
                "ALTER TABLE defects ADD COLUMN trained_at TEXT"
            )

        from datetime import datetime

        now = datetime.now().isoformat(timespec="seconds")
        placeholders = ",".join("?" for _ in defect_ids)
        conn.execute(
            f"UPDATE defects SET trained_at = ? WHERE id IN ({placeholders})",
            [now, *defect_ids],
        )
        conn.commit()


def export_dataset(
    force: bool = False,
) -> dict:
    """
    Veritabanından görselleri okuyup YOLO Classification formatında dışa aktarır.

    Args:
        force: True ise minimum kontrolleri atlar.

    Returns:
        Sonuç istatistiklerini içeren dict:
        {
            "success": bool,
            "message": str,
            "total_images": int,
            "classes": dict[str, int],
            "train_count": int,
            "val_count": int,
            "dataset_path": str,
        }
    """
    defects = get_all_defects()

    if not defects:
        return {
            "success": False,
            "message": "Veritabanında hiç hata kaydı bulunamadı.",
            "total_images": 0,
            "classes": {},
            "train_count": 0,
            "val_count": 0,
            "dataset_path": "",
        }

    # Sınıf bazında gruplama
    class_groups: dict[str, list[dict]] = {}
    for defect in defects:
        cls_name = _sanitize_class_name(defect["defect_type"])
        class_groups.setdefault(cls_name, []).append(defect)

    total_images = sum(len(v) for v in class_groups.values())

    # Minimum kontroller
    if not force:
        if total_images < MIN_IMAGES_FOR_TRAINING:
            return {
                "success": False,
                "message": (
                    f"Eğitim için en az {MIN_IMAGES_FOR_TRAINING} görsel gerekiyor. "
                    f"Şu an {total_images} görsel var."
                ),
                "total_images": total_images,
                "classes": {k: len(v) for k, v in class_groups.items()},
                "train_count": 0,
                "val_count": 0,
                "dataset_path": "",
            }

        small_classes = [
            name
            for name, items in class_groups.items()
            if len(items) < MIN_IMAGES_PER_CLASS
        ]
        if small_classes:
            return {
                "success": False,
                "message": (
                    f"Şu sınıflarda yeterli görsel yok (en az {MIN_IMAGES_PER_CLASS} gerekli): "
                    f"{', '.join(small_classes)}"
                ),
                "total_images": total_images,
                "classes": {k: len(v) for k, v in class_groups.items()},
                "train_count": 0,
                "val_count": 0,
                "dataset_path": "",
            }

    # Eski veri setini temizle ve yeniden oluştur
    if DATASET_DIR.exists():
        shutil.rmtree(DATASET_DIR)

    train_dir = DATASET_DIR / "train"
    val_dir = DATASET_DIR / "val"
    train_dir.mkdir(parents=True, exist_ok=True)
    val_dir.mkdir(parents=True, exist_ok=True)

    train_count = 0
    val_count = 0
    all_exported_ids = []

    for cls_name, items in class_groups.items():
        # Sınıf klasörlerini oluştur
        (train_dir / cls_name).mkdir(exist_ok=True)
        (val_dir / cls_name).mkdir(exist_ok=True)

        # Karıştır ve böl
        random.shuffle(items)
        split_idx = max(1, int(len(items) * TRAIN_SPLIT_RATIO))

        train_items = items[:split_idx]
        val_items = items[split_idx:] if len(items) > 1 else []

        # Eğer sadece 1 görsel varsa train'e koy, val boş kalsın
        if not val_items and len(items) > 1:
            val_items = [train_items.pop()]

        for i, item in enumerate(train_items):
            src = Path(item["image_path"])
            if src.exists():
                dst = train_dir / cls_name / f"{cls_name}_{i:04d}{src.suffix}"
                shutil.copy2(src, dst)
                train_count += 1
                all_exported_ids.append(item["id"])

        for i, item in enumerate(val_items):
            src = Path(item["image_path"])
            if src.exists():
                dst = val_dir / cls_name / f"{cls_name}_{i:04d}{src.suffix}"
                shutil.copy2(src, dst)
                val_count += 1
                all_exported_ids.append(item["id"])

    # Eğitimde kullanılan görselleri işaretle
    _mark_as_trained(all_exported_ids)

    return {
        "success": True,
        "message": (
            f"Veri seti başarıyla oluşturuldu! "
            f"{train_count} train, {val_count} val görsel."
        ),
        "total_images": train_count + val_count,
        "classes": {k: len(v) for k, v in class_groups.items()},
        "train_count": train_count,
        "val_count": val_count,
        "dataset_path": str(DATASET_DIR),
    }


def get_dataset_status() -> dict:
    """Mevcut veri durumunu özetler (UI'da göstermek için)."""
    defects = get_all_defects()
    total = len(defects)
    untrained = _get_untrained_count()

    class_counts: dict[str, int] = {}
    for d in defects:
        cls = _sanitize_class_name(d["defect_type"])
        class_counts[cls] = class_counts.get(cls, 0) + 1

    ready = total >= MIN_IMAGES_FOR_TRAINING and all(
        c >= MIN_IMAGES_PER_CLASS for c in class_counts.values()
    )

    return {
        "total_images": total,
        "untrained_images": untrained,
        "class_counts": class_counts,
        "ready_for_training": ready,
        "min_required": MIN_IMAGES_FOR_TRAINING,
        "min_per_class": MIN_IMAGES_PER_CLASS,
    }


if __name__ == "__main__":
    print("Veri seti dışa aktarılıyor...")
    result = export_dataset(force=True)
    print(f"Sonuç: {result['message']}")
    if result["classes"]:
        print("Sınıf dağılımı:")
        for cls, count in result["classes"].items():
            print(f"  {cls}: {count}")
"""
Veritabanındaki etiketlenmiş görselleri YOLO Classification veri seti formatına
dönüştüren modül. Train/Val ayrımı yapar, sınıf bazında klasörler oluşturur ve
eğitimde kullanılan görselleri 'trained_at' ile işaretler.
"""
