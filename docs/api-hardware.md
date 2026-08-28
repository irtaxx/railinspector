# Dokumentasi API — Untuk Programmer ESP32 & Raspberry Pi

Base URL: `http://187.127.220.242` (ganti sesuai IP/domain server)

---

## 1. ESP32 — Kirim Posisi GPS

Kirim posisi lori secara berkala (misal tiap 3–5 detik).

**Endpoint:** `POST /api/gps`
**Content-Type:** `application/x-www-form-urlencoded`

| Field | Tipe  | Wajib | Keterangan            |
|-------|-------|-------|------------------------|
| lat   | float | Ya    | Latitude posisi lori   |
| lon   | float | Ya    | Longitude posisi lori  |

**Contoh (curl):**
```bash
curl -X POST http://187.127.220.242/api/gps \
  -d "lat=-7.9553" -d "lon=112.6146"
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
**Content-Type:** `multipart/form-data`

| Field      | Tipe   | Wajib | Keterangan                          |
|------------|--------|-------|--------------------------------------|
| lat        | float  | Ya    | Latitude lokasi kerusakan            |
| lon        | float  | Ya    | Longitude lokasi kerusakan           |
| keterangan | string | Tidak | Catatan singkat (boleh kosong)       |
| image      | file   | Ya    | Foto kerusakan (jpg/png)             |

**Contoh (curl):**
```bash
curl -X POST http://187.127.220.242/api/damage \
  -F "lat=-7.9550" -F "lon=112.6140" \
  -F "keterangan=Retak pada sambungan rel" \
  -F "image=@foto.jpg;type=image/jpeg"
```

**Contoh (Python requests, dipakai di `raspi/damage_reporter.py`):**
```python
requests.post(
    f"{SERVER_URL}/api/damage",
    data={"lat": lat, "lon": lon, "keterangan": "..."},
    files={"image": ("kerusakan.jpg", foto_bytes, "image/jpeg")},
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
- Kalau request gagal (server tidak bisa dihubungi / timeout), coba lagi — tidak ada efek samping kalau dikirim ulang.
- Endpoint lain yang tersedia untuk dicek manual: `GET /api/gps/current`, `GET /api/damages` (lihat data yang sudah masuk).
- Dashboard hasilnya bisa dilihat langsung di `http://187.127.220.242/`.
