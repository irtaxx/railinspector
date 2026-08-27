# Panduan Setup RailInspector

## 1. Backend (Server)

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
python main.py
```

Server berjalan di `http://0.0.0.0:8000`. Dashboard dapat diakses lewat browser di `http://localhost:8000`.

## 2. Raspberry Pi (Client Lori)

1. Pasang GPS NEO-6M ke pin UART (RX/TX) dan aktifkan serial di `raspi-config`.
2. Pasang Pi Camera ke port CSI.
3. Pasang push button ke GPIO 17 dan GND.
4. Install dependencies:

   ```bash
   cd raspi
   pip install -r requirements.txt
   ```

5. Ubah `SERVER_URL` di `damage_reporter.py` sesuai alamat IP server backend.
6. Jalankan:

   ```bash
   python damage_reporter.py
   ```

## 3. Alur Kerja

1. Raspberry Pi membaca posisi GPS secara berkala dan mengirim ke `POST /api/gps`.
2. Saat inspektor menemukan kerusakan, ia menekan tombol → kamera menangkap gambar → dikirim ke `POST /api/damage` beserta koordinat GPS saat itu.
3. Dashboard (`/`) melakukan polling ke `GET /api/gps/current` dan `GET /api/damages` setiap 5 detik untuk memperbarui peta.
