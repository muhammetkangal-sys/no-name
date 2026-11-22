"""
import_and_train_neu.py
NEU Surface Defect veri setini sisteme aktarır:
1. Görselleri data/dataset/train ve data/dataset/val klasörlerine Türkçe etiketlerle yerleştirir.
2. Görselleri data/defects klasörüne kopyalayıp ResNet-18 embedding'leri ile SQLite veritabanına kaydeder.
3. YOLOv8 Classification modelini bu veri setiyle (Apple M2 MPS desteğiyle) eğitir.
"""

import io
import shutil
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from PIL import Image
import numpy as np
import torch
from torchvision.models import resnet18, ResNet18_Weights

from config import (
    BASE_DIR,
    CUSTOM_MODEL_PATH,
    DATA_DIR,
    DATASET_DIR,
    DB_PATH,
    DEFECTS_DIR,
    MODELS_DIR,
)
from train_model import train

KAGGLE_NEU_DIR = Path(
    "/Users/kangal/.cache/kagglehub/datasets/kaustubhdikshit/neu-surface-defect-database/versions/1/NEU-DET"
)

CLASS_MAPPING = {
    "crazing": {
        "tr_label": "Kılcal Çatlak",
        "dir_name": "kilcal_catlak",
    },
    "scratches": {
        "tr_label": "Yüzey Çiziği",
        "dir_name": "yuzey_cizigi",
    },
    "inclusion": {
        "tr_label": "İnklüzyon",
        "dir_name": "inkluzyon",
    },
    "patches": {
        "tr_label": "Yama",
        "dir_name": "yama",
    },
    "pitted_surface": {
        "tr_label": "Çukurlaşma",
        "dir_name": "cukurlasma",
    },
    "rolled-in_scale": {
        "tr_label": "Hadde Tufalı",
        "dir_name": "hadde_tufali",
    },
}


def embedding_to_blob(embedding: np.ndarray) -> bytes:
    buffer = io.BytesIO()
    np.save(buffer, embedding.astype(np.float32))
    return buffer.getvalue()


def get_embedding_model():
    weights = ResNet18_Weights.DEFAULT
    model = resnet18(weights=weights)
    model.fc = torch.nn.Identity()
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    model = model.to(device)
    model.eval()
    transform = weights.transforms()
    return model, transform, device


def setup_yolo_dataset():
    print("\n📂 [1/3] YOLO veri seti klasörleri hazırlanıyor...")
    train_dest = DATASET_DIR / "train"
    val_dest = DATASET_DIR / "val"

    if DATASET_DIR.exists():
        shutil.rmtree(DATASET_DIR)

    train_dest.mkdir(parents=True, exist_ok=True)
    val_dest.mkdir(parents=True, exist_ok=True)

    counts = {"train": 0, "val": 0}

    # Train kopyalama
    for src_cls, info in CLASS_MAPPING.items():
        src_folder = KAGGLE_NEU_DIR / "train" / "images" / src_cls
        dst_folder = train_dest / info["dir_name"]
        dst_folder.mkdir(parents=True, exist_ok=True)
        for img_path in src_folder.glob("*.jpg"):
            shutil.copy2(img_path, dst_folder / img_path.name)
            counts["train"] += 1

    # Validation kopyalama
    for src_cls, info in CLASS_MAPPING.items():
        src_folder = KAGGLE_NEU_DIR / "validation" / "images" / src_cls
        dst_folder = val_dest / info["dir_name"]
        dst_folder.mkdir(parents=True, exist_ok=True)
        for img_path in src_folder.glob("*.jpg"):
            shutil.copy2(img_path, dst_folder / img_path.name)
            counts["val"] += 1

    print(
        f"✅ YOLO Veri seti hazırlandı: {counts['train']} train, {counts['val']} val görsel."
    )
    return counts


def populate_database_and_embeddings():
    print("\n🗄️ [2/3] Veritabanı ve benzerlik hafızası (ResNet-18) oluşturuluyor...")
    DEFECTS_DIR.mkdir(parents=True, exist_ok=True)

    # Veritabanı tablosunu hazırla
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS defects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            defect_code TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL,
            product_name TEXT,
            defect_type TEXT NOT NULL,
            labeled_by TEXT,
            notes TEXT,
            image_path TEXT NOT NULL,
            embedding BLOB,
            status TEXT DEFAULT 'confirmed',
            trained_at TEXT
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS defect_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        );
        """
    )
    cols = [r[1] for r in conn.execute("PRAGMA table_info(defects)").fetchall()]
    if "trained_at" not in cols:
        conn.execute("ALTER TABLE defects ADD COLUMN trained_at TEXT")

    for info in CLASS_MAPPING.values():
        conn.execute(
            "INSERT OR IGNORE INTO defect_types (name) VALUES (?)",
            (info["tr_label"],),
        )
    conn.commit()

    # Mevcut kayıt sayısını kontrol et
    row = conn.execute("SELECT COUNT(*) AS c FROM defects").fetchone()
    current_count = row[0]
    print(f"Mevcut veritabanı kayıt sayısı: {current_count}")

    # Toplanacak tüm görseller
    all_items = []
    # Train ve validation setlerinden topla
    for split_dir in ["train", "validation"]:
        for src_cls, info in CLASS_MAPPING.items():
            folder = KAGGLE_NEU_DIR / split_dir / "images" / src_cls
            for p in sorted(folder.glob("*.jpg")):
                all_items.append((p, info["tr_label"]))

    print(f"İşlenecek toplam görsel sayısı: {len(all_items)}")

    model, transform, device = get_embedding_model()
    print(f"Embedding modeli hazır (Cihaz: {device.upper()}).")

    batch_size = 64
    db_rows = []
    now_str = datetime.now().isoformat(timespec="seconds")
    start_time = time.time()

    for i in range(0, len(all_items), batch_size):
        batch = all_items[i : i + batch_size]
        pil_images = []
        metadata_list = []

        for idx, (img_path, tr_label) in enumerate(batch):
            code_num = current_count + i + idx + 1
            defect_code = f"HATA-{code_num:04d}"
            dest_name = f"neu_{img_path.name}"
            dest_path = DEFECTS_DIR / dest_name
            if not dest_path.exists():
                shutil.copy2(img_path, dest_path)

            img = Image.open(img_path).convert("RGB")
            pil_images.append(img)
            metadata_list.append((defect_code, str(dest_path), tr_label))

        # Batch embedding çıkarımı
        tensors = torch.stack([transform(img) for img in pil_images]).to(device)
        with torch.no_grad():
            features = model(tensors)
            features = features.cpu().numpy()

        for (defect_code, dest_path_str, tr_label), feat in zip(
            metadata_list, features
        ):
            norm = np.linalg.norm(feat)
            if norm > 0:
                feat = feat / norm
            emb_blob = embedding_to_blob(feat)
            db_rows.append(
                (
                    defect_code,
                    now_str,
                    "NEU Çelik Levha",
                    tr_label,
                    "NEU Benchmark",
                    "NEU Surface Defect Database örneği",
                    dest_path_str,
                    emb_blob,
                    "confirmed",
                    now_str,
                )
            )

        print(
            f"  İşlendi: {min(i + batch_size, len(all_items))}/{len(all_items)} görsel...",
            end="\r",
        )

    print()
    # Veritabanına toplu ekle
    conn.executemany(
        """
        INSERT OR IGNORE INTO defects (
            defect_code, created_at, product_name, defect_type,
            labeled_by, notes, image_path, embedding, status, trained_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        db_rows,
    )
    conn.commit()
    conn.close()

    elapsed = time.time() - start_time
    print(
        f"✅ {len(db_rows)} görsel başarıyla veritabanına ve benzerlik hafızasına kaydedildi ({elapsed:.1f} sn)."
    )


def run_training(epochs: int = 25):
    print(f"\n🚀 [3/3] YOLOv8 Classification modeli eğitiliyor ({epochs} epoch)...")
    result = train(epochs=epochs, skip_export=True)
    if result["success"]:
        print(f"\n🎉 {result['message']}")
    else:
        print(f"\n❌ [{result['stage']}] {result['message']}")
    return result


if __name__ == "__main__":
    epochs = int(sys.argv[1]) if len(sys.argv) > 1 else 25
    setup_yolo_dataset()
    populate_database_and_embeddings()
    run_training(epochs=epochs)
