"""
RailInspector - Backend API
Sistem monitoring kerusakan rel kereta api.

Menerima laporan kerusakan (gambar + lokasi GPS) dari lori inspeksi,
serta menyimpan dan menyajikan data posisi lori secara real-time
untuk ditampilkan di dashboard GIS.
"""
import base64
import binascii
import json
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = BASE_DIR / "uploads"
DATABASE_FILE = BASE_DIR / "database.json"
GPS_HISTORY_FILE = BASE_DIR / "gps_history.json"
STATIC_DIR = BASE_DIR / "static"

UPLOADS_DIR.mkdir(exist_ok=True)

app = FastAPI(title="RailInspector API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ---------- Skema request (JSON) ----------

class GpsUpdate(BaseModel):
    lat: float
    lon: float


class DamageReport(BaseModel):
    lat: float
    lon: float
    keterangan: str = ""
    image_base64: str  # isi gambar di-encode base64 (tanpa prefix "data:image/...;base64,")
    filename: str = "kerusakan.jpg"  # dipakai untuk menentukan ekstensi file


# ---------- Helper penyimpanan JSON ----------

def _read_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_database() -> dict:
    return _read_json(DATABASE_FILE, {"damages": []})


def save_database(data: dict) -> None:
    _write_json(DATABASE_FILE, data)


def load_gps() -> dict:
    return _read_json(GPS_HISTORY_FILE, {"current": None, "history": []})


def save_gps(data: dict) -> None:
    _write_json(GPS_HISTORY_FILE, data)


# ---------- Endpoint: Dashboard ----------

@app.get("/")
def dashboard():
    return FileResponse(STATIC_DIR / "dashboard.html")


# ---------- Endpoint: Laporan Kerusakan ----------

@app.post("/api/damage")
def report_damage(payload: DamageReport):
    """Menerima laporan kerusakan dari lori: gambar (base64) + lokasi GPS."""
    try:
        image_bytes = base64.b64decode(payload.image_base64, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(status_code=400, detail="image_base64 tidak valid")

    ext = Path(payload.filename).suffix or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = UPLOADS_DIR / filename

    with open(filepath, "wb") as f:
        f.write(image_bytes)

    db = load_database()
    entry = {
        "id": uuid.uuid4().hex,
        "lat": payload.lat,
        "lon": payload.lon,
        "keterangan": payload.keterangan,
        "image": filename,
        "waktu": datetime.now().isoformat(),
    }
    db["damages"].append(entry)
    save_database(db)

    return {"status": "ok", "data": entry}


@app.get("/api/damages")
def list_damages():
    """Daftar seluruh titik kerusakan yang tercatat."""
    return load_database()["damages"]


@app.delete("/api/damage/{damage_id}")
def delete_damage(damage_id: str):
    db = load_database()
    before = len(db["damages"])
    db["damages"] = [d for d in db["damages"] if d["id"] != damage_id]
    if len(db["damages"]) == before:
        raise HTTPException(status_code=404, detail="Data kerusakan tidak ditemukan")
    save_database(db)
    return {"status": "ok"}


# ---------- Endpoint: Posisi GPS Lori ----------

@app.post("/api/gps")
def update_gps(payload: GpsUpdate):
    """Menerima update posisi lori terkini dari perangkat GPS."""
    gps = load_gps()
    point = {"lat": payload.lat, "lon": payload.lon, "waktu": datetime.now().isoformat()}
    gps["current"] = point
    gps["history"].append(point)
    save_gps(gps)
    return {"status": "ok", "data": point}


@app.get("/api/gps/current")
def current_gps():
    """Posisi lori saat ini."""
    return load_gps()["current"]


@app.get("/api/gps/history")
def gps_history():
    """Riwayat perjalanan lori."""
    return load_gps()["history"]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
