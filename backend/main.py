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
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = BASE_DIR / "uploads"
DATABASE_FILE = BASE_DIR / "database.json"
GPS_HISTORY_FILE = BASE_DIR / "gps_history.json"
TRIPS_FILE = BASE_DIR / "trips.json"
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
    speed: Optional[float] = None  # km/jam
    battery: Optional[float] = Field(default=None, ge=0, le=100)  # persentase baterai perangkat GPS


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


def load_trips() -> dict:
    return _read_json(TRIPS_FILE, {"current_trip_id": None, "trips": []})


def save_trips(data: dict) -> None:
    _write_json(TRIPS_FILE, data)


def get_current_trip_id() -> str:
    """Ambil id perjalanan (trip) yang sedang aktif; buat trip pertama kalau belum ada sama sekali."""
    trips = load_trips()
    if trips["current_trip_id"] is None:
        trip = {
            "id": uuid.uuid4().hex,
            "waktu_mulai": datetime.now().isoformat(),
            "waktu_selesai": None,
        }
        trips["trips"].append(trip)
        trips["current_trip_id"] = trip["id"]
        save_trips(trips)
    return trips["current_trip_id"]


def find_trip(trips: dict, trip_id: str) -> Optional[dict]:
    return next((t for t in trips["trips"] if t["id"] == trip_id), None)


def trip_summary(trip: dict, gps_points: list, damages: list) -> dict:
    """Ringkasan satu trip: jumlah titik jalur yang dilalui + jumlah kerusakan yang ditemukan."""
    trip_gps = [p for p in gps_points if p.get("trip_id") == trip["id"]]
    trip_damages = [d for d in damages if d.get("trip_id") == trip["id"]]
    return {
        "id": trip["id"],
        "waktu_mulai": trip["waktu_mulai"],
        "waktu_selesai": trip["waktu_selesai"],
        "status": "selesai" if trip["waktu_selesai"] else "aktif",
        "jumlah_titik_gps": len(trip_gps),
        "jumlah_kerusakan": len(trip_damages),
    }


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
        "trip_id": get_current_trip_id(),
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
    point = {
        "lat": payload.lat,
        "lon": payload.lon,
        "speed": payload.speed,
        "battery": payload.battery,
        "waktu": datetime.now().isoformat(),
        "trip_id": get_current_trip_id(),
    }
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
    """Riwayat seluruh posisi lori (semua trip)."""
    return load_gps()["history"]


# ---------- Endpoint: Log Perjalanan (Trip) ----------
#
# Satu "trip" adalah satu siklus perjalanan lori, dari terakhir kali di-reset
# sampai reset berikutnya. Dipakai untuk mengecek jalur yang sudah dilalui dan
# jumlah kerusakan yang ditemukan pada satu siklus, tanpa tercampur data trip lain.

@app.post("/api/trip/reset")
def reset_trip():
    """Tutup trip yang sedang berjalan dan mulai trip baru dari awal."""
    trips = load_trips()
    current = find_trip(trips, trips["current_trip_id"]) if trips["current_trip_id"] else None
    if current is not None and current["waktu_selesai"] is None:
        current["waktu_selesai"] = datetime.now().isoformat()

    new_trip = {
        "id": uuid.uuid4().hex,
        "waktu_mulai": datetime.now().isoformat(),
        "waktu_selesai": None,
    }
    trips["trips"].append(new_trip)
    trips["current_trip_id"] = new_trip["id"]
    save_trips(trips)

    return {"status": "ok", "data": new_trip}


@app.get("/api/trips")
def list_trips():
    """Daftar seluruh trip beserta ringkasannya (jumlah titik jalur & kerusakan)."""
    trips = load_trips()
    gps_points = load_gps()["history"]
    damages = load_database()["damages"]
    return [trip_summary(t, gps_points, damages) for t in trips["trips"]]


@app.get("/api/trip/current")
def current_trip():
    """Ringkasan trip yang sedang berjalan saat ini."""
    trip_id = get_current_trip_id()
    trip = find_trip(load_trips(), trip_id)
    gps_points = load_gps()["history"]
    damages = load_database()["damages"]
    return trip_summary(trip, gps_points, damages)


@app.get("/api/trip/{trip_id}")
def trip_detail(trip_id: str):
    """Detail satu trip: ringkasan + jalur GPS yang dilalui + daftar kerusakan yang ditemukan."""
    trips = load_trips()
    trip = find_trip(trips, trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip tidak ditemukan")

    gps_points = load_gps()["history"]
    damages = load_database()["damages"]
    summary = trip_summary(trip, gps_points, damages)
    summary["jalur"] = [p for p in gps_points if p.get("trip_id") == trip_id]
    summary["kerusakan"] = [d for d in damages if d.get("trip_id") == trip_id]
    return summary


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
