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

**Backend (`backend/main.py`)** is a single-file FastAPI app with three independent data streams,
each persisted to its own flat JSON file (no database engine):

- `database.json` — list of damage reports (`{id, lat, lon, keterangan, image, waktu, trip_id}`).
  Images themselves are saved as files under `uploads/` (mounted at `/uploads`), referenced by
  filename only.
- `gps_history.json` — `{current, history}`: `current` is the lori's latest position, overwritten
  on every GPS update; `history` accumulates every point ever received (`{lat, lon, speed, battery,
  waktu, trip_id}` — `speed`/`battery` are optional, sent by the GPS client if available).
- `trips.json` — `{current_trip_id, trips: [{id, waktu_mulai, waktu_selesai}]}`. A "trip" is one
  journey cycle of the lori, from the last reset to the next. `get_current_trip_id()` lazily creates
  the first trip on first use. Every GPS point and damage report gets stamped with the active
  `trip_id` at write time — trip membership is derived by filtering `gps_history.json`/`database.json`
  on that field (`trip_summary()`), not by duplicating the data into `trips.json`.

Requests are all JSON (Pydantic models `GpsUpdate`/`DamageReport`), not multipart — photos are sent
as base64 (`image_base64`) and decoded server-side before being written to `uploads/`.

Read/write to these files goes through `_read_json`/`_write_json` helpers — full read-modify-write
of the whole file on every request, no locking. This is fine at the current scale (one lori, low
request rate) but means concurrent writes could race; keep that in mind before adding multi-device
support.

Endpoints (prefix `/api/`):
- `POST /api/damage` (JSON: lat, lon, keterangan, image_base64, filename) — client (Raspberry Pi)
  reports a new damage point with photo.
- `GET /api/damages` / `DELETE /api/damage/{id}` — list/remove damage reports (all trips).
- `POST /api/gps` (JSON: lat, lon, speed?, battery?) — client reports current lori position; appends
  to history and overwrites `current`.
- `GET /api/gps/current` / `GET /api/gps/history` — read lori position state (all trips).
- `POST /api/trip/reset` — close the current trip, open a new one; subsequent GPS/damage writes
  attach to the new trip.
- `GET /api/trips` / `GET /api/trip/current` / `GET /api/trip/{id}` — trip summaries (`jumlah_titik_gps`,
  `jumlah_kerusakan`); `GET /api/trip/{id}` additionally returns the full `jalur` (path) and
  `kerusakan` (damages) for that one trip.
- `GET /` — serves `backend/static/dashboard.html`; `/static` is also mounted for assets (logos).

**Dashboard (`backend/static/dashboard.html`)** is a single static HTML file (no build step, no
framework) using Leaflet.js + Font Awesome from CDNs, Montserrat font, and a navy/orange color
scheme matching the KAI/Polinema branding. It polls `/api/gps/current`, `/api/gps/history`, and
`/api/damages` every 5 seconds (see `poll()` at the bottom of the file). The lori's latest position
is a single mutable `L.marker` (train icon) moved via `setLatLng`; earlier positions from
`/api/gps/history` are drawn as small `L.circleMarker` dots and tracked in a `trailDots` set (keyed
by `waktu`) so they're only drawn once. Damage pins are diffed against `damageMarkers` (keyed by
damage id) the same way. The lori popup shows lat/lon plus **dummy** battery/speed generated
client-side (`dummyTelemetry()`) — real `speed`/`battery` values now exist in the GPS API response
but the dashboard doesn't consume them yet; wire that up instead of the dummy generator if asked to
make it real. The dashboard does not currently expose trip history/reset UI — that's API-only for now.

**Raspberry Pi client (`raspi/damage_reporter.py`)** runs two concurrent loops in one process:
- A background thread (`gps_reader`) continuously reads NMEA sentences off the serial GPS, updates
  a shared `current_position` dict (guarded by `position_lock`), and POSTs to `/api/gps` on a
  throttled interval (`GPS_UPDATE_INTERVAL`).
- The main thread (`button_listener`) blocks on a GPIO falling-edge interrupt; on press it captures
  a still frame from `picamera2` in memory (no temp file), base64-encodes it, and POSTs it to
  `/api/damage` along with whatever GPS position was most recently read.

GPS reporting duties are moving to a separate ESP32 device (see `docs/api-hardware.md`) — the raspi
script's own `gps_reader` thread may become redundant/removed once that transition is complete; don't
assume both are meant to run long-term without checking current intent.

Because the damage report reuses `current_position` from the GPS thread rather than reading the GPS
fresh, a damage report sent right after startup (before the first GPS fix arrives) is dropped with a
console message — this is intentional, not a bug to "fix" by blocking for a fix.

## Conventions

- All UI text and code comments are written in Indonesian (Bahasa Indonesia) — follow this for any
  new endpoints, dashboard copy, or client script changes.
- API routes live under `/api/` prefix; the dashboard route (`/`), `/uploads`, and `/static` mounts
  are the only exceptions.
- Persistence is flat JSON files, not a real database — `database.json` for damages, `gps_history.json`
  for GPS, `trips.json` for trip metadata. Don't introduce a database dependency without discussing it
  first; the project intentionally keeps deployment simple for a Raspberry Pi + single-server setup.
- Uploaded images go in `backend/uploads/`, served statically at `/uploads/<filename>`.
- Hardware-facing API contract (what ESP32/Raspi programmers integrate against) is documented in
  `docs/api-hardware.md` — keep it in sync when changing request/response shapes.
- VPS deployment configs (systemd unit, nginx reverse proxy) live in `deploy/`; see `docs/setup.md`.
