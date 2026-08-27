# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

RailInspector: sistem monitoring kerusakan rel kereta api untuk Politeknik Negeri Malang. Sebuah
lori mengangkut inspektor rel yang dilengkapi GPS (NEO-6M) dan kamera. Saat menemukan kerusakan,
inspektor menekan push button untuk menangkap foto dan mengirimkannya ke backend lewat API. Dashboard
menampilkan peta GIS (Leaflet) dengan posisi lori saat ini dan pin lokasi tiap kerusakan yang ditemukan.

## Commands

Backend (from `backend/`):

```bash
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
python main.py                 # runs uvicorn with reload on :8000
```

Or directly: `uvicorn main:app --host 0.0.0.0 --port 8000 --reload`

Raspberry Pi client (from `raspi/`):

```bash
pip install -r requirements.txt
python damage_reporter.py      # set SERVER_URL inside the file first
```

There is no test suite, linter, or build step configured yet.

## Architecture

**Backend (`backend/main.py`)** is a single-file FastAPI app with two independent data streams,
each persisted to its own flat JSON file (no database engine):

- `database.json` — list of damage reports (`{id, lat, lon, keterangan, image, waktu}`). Images
  themselves are saved as files under `uploads/` (mounted at `/uploads`), referenced by filename only.
- `gps_history.json` — `{current, history}`: `current` is the lori's latest position, overwritten
  on every GPS update; `history` accumulates every point ever received.

Read/write to these files goes through `_read_json`/`_write_json` helpers — full read-modify-write
of the whole file on every request, no locking. This is fine at the current scale (one lori, low
request rate) but means concurrent writes could race; keep that in mind before adding multi-device
support.

Endpoints (prefix `/api/`):
- `POST /api/damage` (multipart: lat, lon, keterangan, image) — client (Raspberry Pi) reports a
  new damage point with photo.
- `GET /api/damages` / `DELETE /api/damage/{id}` — list/remove damage reports.
- `POST /api/gps` (form: lat, lon) — client reports current lori position; appends to history and
  overwrites `current`.
- `GET /api/gps/current` / `GET /api/gps/history` — read lori position state.
- `GET /` — serves `backend/static/dashboard.html`.

**Dashboard (`backend/static/dashboard.html`)** is a single static HTML file (no build step, no
framework) using Leaflet.js loaded from a CDN. It polls `/api/gps/current` and `/api/damages` every
5 seconds (see `poll()` at the bottom of the file) and diffs against in-memory marker maps
(`damageMarkers` keyed by damage id) to avoid re-adding existing pins. The lori marker is a single
mutable `L.marker` moved via `setLatLng`. There's no websocket/SSE — everything is poll-based.

**Raspberry Pi client (`raspi/damage_reporter.py`)** runs two concurrent loops in one process:
- A background thread (`gps_reader`) continuously reads NMEA sentences off the serial GPS, updates
  a shared `current_position` dict (guarded by `position_lock`), and POSTs to `/api/gps` on a
  throttled interval (`GPS_UPDATE_INTERVAL`).
- The main thread (`button_listener`) blocks on a GPIO falling-edge interrupt; on press it captures
  a still frame from `picamera2` in memory (no temp file) and POSTs it to `/api/damage` along with
  whatever GPS position was most recently read.

Because the damage report reuses `current_position` from the GPS thread rather than reading the GPS
fresh, a damage report sent right after startup (before the first GPS fix arrives) is dropped with a
console message — this is intentional, not a bug to "fix" by blocking for a fix.

## Conventions

- All UI text and code comments are written in Indonesian (Bahasa Indonesia) — follow this for any
  new endpoints, dashboard copy, or client script changes.
- API routes live under `/api/` prefix; the dashboard route (`/`) and `/uploads` static mount are
  the only exceptions.
- Persistence is flat JSON files, not a real database — `database.json` for damages, `gps_history.json`
  for GPS. Don't introduce a database dependency without discussing it first; the project intentionally
  keeps deployment simple for a Raspberry Pi + single-server setup.
- Uploaded images go in `backend/uploads/`, served statically at `/uploads/<filename>`.
