# RailInspector

Sistem monitoring kerusakan rel kereta api untuk Politeknik Negeri Malang.

Lori yang mengangkut inspektor rel dilengkapi GPS dan kamera. Saat inspektor menemukan
kerusakan, ia menekan tombol untuk menangkap gambar dan mengirimkannya ke server lewat API.
Data kemudian ditampilkan di dashboard berupa peta GIS dengan pin lokasi kerusakan dan
posisi lori saat ini.

## Stack

- Backend: Python 3.14, FastAPI, Uvicorn
- Frontend: HTML, Leaflet.js, Montserrat font
- Hardware: Raspberry Pi 4, GPS NEO-6M, Pi Camera, push button
- Client: Python (requests, RPi.GPIO, picamera2)

## Struktur

- `backend/` — FastAPI server (main.py), dashboard HTML, tile offline
- `raspi/` — Script Raspberry Pi (damage_reporter.py)
- `docs/` — Panduan setup

Lihat [docs/setup.md](docs/setup.md) untuk panduan instalasi lengkap.

## Konvensi

- Bahasa komentar dan UI: Indonesia
- API endpoint prefix: `/api/`
- Database: JSON file (`database.json`, `gps_history.json`)
- Image uploads: folder `uploads/`
