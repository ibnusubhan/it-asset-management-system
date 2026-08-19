# 💻 IT Asset Management System (Flask & SQLite)

Sistem Informasi Manajemen Aset IT berbasis web yang dirancang untuk mengelola inventaris perangkat IT (Laptop, PC, Monitor, Aksesoris) secara efisien, transparan, dan terorganisir. Dilengkapi dengan fitur penerimaan grosir (*Batch Receiving*), pencetakan QR Code, lacak riwayat (*Asset Logs*), serta export laporan ke Excel.

---

## ✨ Fitur Utama

- **📊 Dashboard Analytics & Categorization:**
  - Monitoring status aset (*In Use*, *Available*, *Repair*).
  - Breakdown statistik total aset berdasarkan kategori (*Executive Summary Modal*).
  
- **📦 Wholesale / Batch Receiving (Pengadaan Grosir):**
  - Mendaftarkan banyak unit perangkat sekaligus (misal: 10 unit Mouse/Monitor) dengan pembuatan *Asset Tag* otomatis (cth: `MNT-001`, `MNT-002`).

- **📱 QR Code Generator & Asset Detail:**
  - Pembuatan QR Code otomatis untuk setiap aset yang berisi detail spesifikasi & *Asset Tag*.

- **📜 Asset Audit & Logs Tracking:**
  - Mencatat riwayat riil setiap kali aset mengalami perubahan status, pendaftaran, atau perpindahan pengguna.

- **👥 Employee & Assignment Management:**
  - Penyerahan aset ke karyawan secara fleksibel.

- **📊 Export Reports:**
  - Export seluruh laporan aset IT ke format `.xlsx` (Microsoft Excel) dengan sekali klik.

- **🔒 Security & Session Timeout:**
  - Sistem autentikasi pengguna dengan enkripsi password (*pbkdf2:sha256*).
  - Auto-timeout sesi pengguna setelah 15 menit tanpa aktivitas untuk keamanan sistem internal.

---

## 🛠️ Tech Stack

- **Backend:** Python (Flask, Flask-Login)
- **Database:** SQLite3
- **Frontend:** HTML5, CSS3, Bootstrap 5, Jinja2
- **Data Processing & Export:** Pandas, OpenPyXL
- **QR Code Engine:** Python-qrcode

---

## 🚀 Cara Menjalankan Proyek di Lokal

1. **Clone Repositori ini:**
   ```bash
   git clone [https://github.com/ibnusubhan/it-asset-management-system.git](https://github.com/ibnusubhan/it-asset-management-system.git)
   cd it-asset-management



Buat Virtual Environment (Opsional tapi disarankan):

Bash
python -m venv venv
# Mengaktifkan venv:
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
Install Dependensi/Pustaka Python:

Bash
pip install -r requirements.txt
Jalankan Aplikasi:

Bash
python app.py
Akses via Browser:
Buka http://127.0.0.1:5000

Username Default: admin

Password Default: admin123