# Sistem Manajemen Keuangan Rental Mobil - Backend API

Repositori ini berisi *source code* untuk sisi *Backend* dari aplikasi Sistem Manajemen Keuangan Rental Mobil. API ini dirancang untuk mengelola data organisasi, autentikasi pengguna, pencatatan transaksi (pemasukan/pengeluaran), dan nantinya menyajikan data laporan keuangan.

Sistem ini dibangun menggunakan **FastAPI** dengan pendekatan arsitektur yang modular, menggunakan **PostgreSQL** sebagai basis data utama.

## Teknologi yang Digunakan
* **Bahasa:** Python 3.11+
* **Framework API:** FastAPI
* **Database:** PostgreSQL
* **ORM:** SQLAlchemy
* **Data Validation & Schemas:** Pydantic
* **Hashing:** Passlib (Bcrypt)
* **Server:** Uvicorn

## Struktur Direktori Proyek

```text
fin-management-for-car-rental/
├── app/
│   ├── core/
│   │   └── security.py        # Logika enkripsi dan hashing password
│   ├── db/
│   │   ├── database.py        # Konfigurasi koneksi engine SQLAlchemy
│   │   └── models.py          # Definisi skema tabel database
│   ├── main.py                # Entry point aplikasi dan routing endpoint
│   └── schemas.py             # Model Pydantic untuk validasi request/response
├── venv/                      # Virtual environment (diabaikan oleh git)
├── .env                       # Environment variables (kredensial database)
├── .gitignore                 # Daftar file/folder yang diabaikan Git
└── requirements.txt           # Daftar library Python beserta versinya
```
## Persiapan dan Instalasi
### 1. Clone Repository
```
git clone https://github.com/username/fin-management-for-car-rental.git
cd fin-management-for-car-rental
```
### 2. Setup venv
```
python -m venv venv
venv\Scripts\activate
```
### 3. Install Depedencies
```
pip install -r requirements.txt
```
### 4. .env Configuration
Buat file .env di root directory dan sesuaikan dengan database lokal
```
DATABASE_URL=postgresql://username:password@localhost:5432/rental_finance_db
```
### 5. Run Server
```
uvicorn app.main:app --reload
```
## Endpoints API (Current Progress)
### Organization
* **POST /organizations/**: Mendaftarkan organisasi atau tenant rental baru ke dalam sistem. Menghasilkan UUID unik yang diperlukan untuk pendaftaran user.

### Authentication & User
* **POST /register/**: Mendaftarkan akun pengguna baru yang terhubung ke organisasi tertentu. Menggunakan hashing Bcrypt untuk keamanan penyimpanan password.

## Progress Kerja
* Setup environment development dan koneksi PostgreSQL.
* Implementasi Base Models SQLAlchemy untuk entitas Organization, User, dan Transaction.
* Integrasi Pydantic untuk skema validasi data masuk dan keluar.
* Implementasi modul security (Bcrypt) untuk proteksi kredensial.
* Konfigurasi .gitignore standar industri untuk keamanan environment.

## Roadmap Selanjutnya
* Implementasi Authentication (Login & JWT Token).
* CRUD Transaksi Keuangan (In/Out).
* Dashboard Analytics & Reporting.
* Integrasi Predictive Model untuk estimasi pendapatan.

## Pengembangan Database
Tabel database di-generate secara otomatis melalui SQLAlchemy Base Metadata saat aplikasi dijalankan. Skema mengikuti relasi yang ditentukan di `app/db/models.py`.
