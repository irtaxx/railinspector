"""
RailInspector - Client Raspberry Pi
Membaca GPS (NEO-6M), mengirim posisi lori secara berkala, dan menangkap
foto kerusakan lewat tombol push button untuk dikirim ke server backend.

Perangkat:
- Raspberry Pi 4
- GPS NEO-6M (serial, /dev/ttyAMA0 atau /dev/serial0)
- Pi Camera (picamera2)
- Push button (GPIO)
"""
import io
import time
import threading
from datetime import datetime

import requests
import serial
import pynmea2
import RPi.GPIO as GPIO
from picamera2 import Picamera2

# ---------- Konfigurasi ----------
SERVER_URL = "http://187.127.220.242"
GPS_PORT = "/dev/serial0"
GPS_BAUDRATE = 9600
BUTTON_PIN = 17
GPS_UPDATE_INTERVAL = 3  # detik

# ---------- State posisi GPS terkini ----------
current_position = {"lat": None, "lon": None}
position_lock = threading.Lock()


def gps_reader():
    """Membaca data GPS dari NEO-6M secara terus-menerus dan mengirim ke server."""
    ser = serial.Serial(GPS_PORT, baudrate=GPS_BAUDRATE, timeout=1)
    last_sent = 0

    while True:
        try:
            line = ser.readline().decode("ascii", errors="replace").strip()
            if line.startswith("$GPGGA") or line.startswith("$GNGGA"):
                msg = pynmea2.parse(line)
                if msg.latitude and msg.longitude:
                    with position_lock:
                        current_position["lat"] = msg.latitude
                        current_position["lon"] = msg.longitude

                    now = time.time()
                    if now - last_sent >= GPS_UPDATE_INTERVAL:
                        send_gps_update(msg.latitude, msg.longitude)
                        last_sent = now
        except (pynmea2.ParseError, UnicodeDecodeError):
            continue
        except Exception as e:
            print(f"[GPS] Error: {e}")
            time.sleep(1)


def send_gps_update(lat: float, lon: float):
    try:
        requests.post(
            f"{SERVER_URL}/api/gps",
            data={"lat": lat, "lon": lon},
            timeout=5,
        )
        print(f"[GPS] Posisi terkirim: {lat}, {lon}")
    except requests.RequestException as e:
        print(f"[GPS] Gagal mengirim posisi: {e}")


def capture_and_send_damage(camera: Picamera2):
    """Menangkap foto dari kamera lalu mengirimkannya sebagai laporan kerusakan."""
    with position_lock:
        lat, lon = current_position["lat"], current_position["lon"]

    if lat is None or lon is None:
        print("[Kerusakan] Posisi GPS belum tersedia, laporan dibatalkan.")
        return

    stream = io.BytesIO()
    camera.capture_file(stream, format="jpeg")
    stream.seek(0)

    filename = f"kerusakan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"

    try:
        response = requests.post(
            f"{SERVER_URL}/api/damage",
            data={"lat": lat, "lon": lon, "keterangan": "Kerusakan terdeteksi"},
            files={"image": (filename, stream, "image/jpeg")},
            timeout=15,
        )
        response.raise_for_status()
        print(f"[Kerusakan] Laporan terkirim: {lat}, {lon}")
    except requests.RequestException as e:
        print(f"[Kerusakan] Gagal mengirim laporan: {e}")


def button_listener(camera: Picamera2):
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    print("[Tombol] Menunggu penekanan tombol...")
    while True:
        GPIO.wait_for_edge(BUTTON_PIN, GPIO.FALLING)
        time.sleep(0.05)  # debounce
        if GPIO.input(BUTTON_PIN) == GPIO.LOW:
            print("[Tombol] Ditekan, menangkap gambar kerusakan...")
            capture_and_send_damage(camera)
            time.sleep(1)  # jeda agar tidak dobel-trigger


def main():
    camera = Picamera2()
    camera.configure(camera.create_still_configuration())
    camera.start()
    time.sleep(2)  # warm-up kamera

    gps_thread = threading.Thread(target=gps_reader, daemon=True)
    gps_thread.start()

    try:
        button_listener(camera)
    except KeyboardInterrupt:
        print("\nMenghentikan program...")
    finally:
        camera.stop()
        GPIO.cleanup()


if __name__ == "__main__":
    main()
