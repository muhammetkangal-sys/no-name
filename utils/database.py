import io
import sqlite3
from datetime import datetime
from pathlib import Path

import numpy as np

from config import DB_PATH, DEFECTS_DIR, DEFAULT_DEFECT_TYPES


def _ensure_dirs():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEFECTS_DIR.mkdir(parents=True, exist_ok=True)


def get_connection():
    _ensure_dirs()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        conn.executescript(
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
                status TEXT DEFAULT 'confirmed'
            );

            CREATE TABLE IF NOT EXISTS defect_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            );
            """
        )
        cols = [
            row[1]
            for row in conn.execute("PRAGMA table_info(defects)").fetchall()
        ]
        if "trained_at" not in cols:
            conn.execute("ALTER TABLE defects ADD COLUMN trained_at TEXT")
        for defect_type in DEFAULT_DEFECT_TYPES:
            conn.execute(
                "INSERT OR IGNORE INTO defect_types (name) VALUES (?)",
                (defect_type,),
            )
        conn.commit()


def _next_defect_code(conn) -> str:
    row = conn.execute(
        "SELECT defect_code FROM defects ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if row is None:
        return "HATA-0001"
    last_num = int(row["defect_code"].split("-")[1])
    return f"HATA-{last_num + 1:04d}"


def embedding_to_blob(embedding: np.ndarray) -> bytes:
    buffer = io.BytesIO()
    np.save(buffer, embedding.astype(np.float32))
    return buffer.getvalue()


def blob_to_embedding(blob: bytes) -> np.ndarray:
    buffer = io.BytesIO(blob)
    return np.load(buffer)


def save_defect(
    image_bytes: bytes,
    filename: str,
    defect_type: str,
    product_name: str = "",
    labeled_by: str = "",
    notes: str = "",
    embedding: np.ndarray | None = None,
) -> dict:
    timestamp = datetime.now()
    safe_name = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{Path(filename).name}"
    image_path = DEFECTS_DIR / safe_name
    image_path.write_bytes(image_bytes)

    embedding_blob = embedding_to_blob(embedding) if embedding is not None else None

    with get_connection() as conn:
        defect_code = _next_defect_code(conn)
        conn.execute(
            """
            INSERT INTO defects (
                defect_code, created_at, product_name, defect_type,
                labeled_by, notes, image_path, embedding
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                defect_code,
                timestamp.isoformat(timespec="seconds"),
                product_name.strip() or None,
                defect_type,
                labeled_by.strip() or None,
                notes.strip() or None,
                str(image_path),
                embedding_blob,
            ),
        )
        conn.execute(
            "INSERT OR IGNORE INTO defect_types (name) VALUES (?)",
            (defect_type,),
        )
        conn.commit()

    return {
        "defect_code": defect_code,
        "created_at": timestamp.isoformat(timespec="seconds"),
        "image_path": str(image_path),
        "defect_type": defect_type,
    }


def get_defect_types() -> list[str]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT name FROM defect_types ORDER BY name"
        ).fetchall()
    return [row["name"] for row in rows]


def get_all_defects(limit: int | None = None) -> list[dict]:
    query = "SELECT * FROM defects ORDER BY created_at DESC"
    if limit:
        query += f" LIMIT {int(limit)}"

    with get_connection() as conn:
        rows = conn.execute(query).fetchall()
    return [dict(row) for row in rows]


def get_defects_with_embeddings() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM defects WHERE embedding IS NOT NULL ORDER BY created_at DESC"
        ).fetchall()

    defects = []
    for row in rows:
        item = dict(row)
        item["embedding"] = blob_to_embedding(row["embedding"])
        defects.append(item)
    return defects


def get_defect_by_code(defect_code: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM defects WHERE defect_code = ?", (defect_code,)
        ).fetchone()
    return dict(row) if row else None


def get_stats() -> dict:
    with get_connection() as conn:
        total = conn.execute("SELECT COUNT(*) AS c FROM defects").fetchone()["c"]
        type_rows = conn.execute(
            """
            SELECT defect_type, COUNT(*) AS count
            FROM defects
            GROUP BY defect_type
            ORDER BY count DESC
            """
        ).fetchall()

    return {
        "total": total,
        "by_type": {row["defect_type"]: row["count"] for row in type_rows},
    }
