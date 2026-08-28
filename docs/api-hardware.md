# Dokumentasi API — Untuk Programmer ESP32 & Raspberry Pi

Base URL: `http://187.127.220.242` (ganti sesuai IP/domain server)

Semua endpoint di bawah menerima **JSON** (`Content-Type: application/json`).

---

## 1. ESP32 — Kirim Posisi GPS

Kirim posisi lori secara berkala (misal tiap 3–5 detik).

**Endpoint:** `POST /api/gps`

**Body (JSON):**
```json
{
  "lat": -7.9553,
  "lon": 112.6146
}
```

| Field | Tipe  | Wajib | Keterangan            |
|-------|-------|-------|------------------------|
| lat   | float | Ya    | Latitude posisi lori   |
| lon   | float | Ya    | Longitude posisi lori  |

**Contoh (curl):**
```bash
curl -X POST http://187.127.220.242/api/gps \
  -H "Content-Type: application/json" \
  -d '{"lat": -7.9553, "lon": 112.6146}'
```

**Response 200:**
```json
{
  "status": "ok",
  "data": { "lat": -7.9553, "lon": 112.6146, "waktu": "2026-08-28T10:00:00" }
}
```

Tidak perlu kirim timestamp — server yang mencatat waktu terima.

---

## 2. Raspberry Pi — Kirim Laporan Kerusakan (foto)

Dikirim sekali setiap tombol inspektor ditekan.

**Endpoint:** `POST /api/damage`

**Body (JSON):**
```json
{
  "lat": -7.9550,
  "lon": 112.6140,
  "keterangan": "Retak pada sambungan rel",
  "image_base64": "/9j/4AAQSkZJRgABAQAAAQABAAD...",
  "filename": "kerusakan.jpg"
}
```

| Field         | Tipe   | Wajib | Keterangan                                              |
|---------------|--------|-------|-----------------------------------------------------------|
| lat           | float  | Ya    | Latitude lokasi kerusakan                                  |
| lon           | float  | Ya    | Longitude lokasi kerusakan                                 |
| keterangan    | string | Tidak | Catatan singkat (boleh kosong)                             |
| image_base64  | string | Ya    | Isi foto di-encode **base64** (tanpa prefix `data:image/...;base64,`) |
| filename      | string | Tidak | Nama file asli, dipakai server hanya untuk ambil ekstensi (default `.jpg`) |

**Contoh (curl):**
```bash
curl -X POST http://187.127.220.242/api/damage \
  -H "Content-Type: application/json" \
  -d "{\"lat\": -7.9550, \"lon\": 112.6140, \"keterangan\": \"Retak pada sambungan rel\", \"image_base64\": \"$(base64 -w0 foto.jpg)\", \"filename\": \"foto.jpg\"}"
```

**Contoh (Python requests, dipakai di `raspi/damage_reporter.py`):**
```python
import base64, requests

image_base64 = base64.b64encode(foto_bytes).decode("ascii")

requests.post(
    f"{SERVER_URL}/api/damage",
    json={
        "lat": lat,
        "lon": lon,
        "keterangan": "...",
        "image_base64": image_base64,
        "filename": "kerusakan.jpg",
    },
)
```

**Response 200:**
```json
{
  "status": "ok",
  "data": {
    "id": "8fc81f11b9ff49b89f389a058020df3b",
    "lat": -7.955, "lon": 112.614,
    "keterangan": "Retak pada sambungan rel",
    "image": "763addf1ff764d39b9c94c7565c2fa0d.jpg",
    "waktu": "2026-08-28T10:00:00"
  }
}
```

---

## Catatan Umum

- Semua koordinat pakai format desimal (WGS84), contoh: `-7.9553, 112.6146`.
- Foto wajib di-encode base64 dulu sebelum dikirim — jangan kirim sebagai file/multipart, dan jangan sertakan prefix `data:image/jpeg;base64,`.
- Kalau request gagal (server tidak bisa dihubungi / timeout), coba lagi — tidak ada efek samping kalau dikirim ulang.
- Endpoint lain yang tersedia untuk dicek manual: `GET /api/gps/current`, `GET /api/damages` (lihat data yang sudah masuk).
- Dashboard hasilnya bisa dilihat langsung di `http://187.127.220.242/`.
