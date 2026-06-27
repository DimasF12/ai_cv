# Dokumentasi Teknis - CV AI Screener

Dokumen ini berisi panduan teknis dan arsitektur untuk proyek **CV AI Screener & Exam Generator**.

## 1. Stack Teknologi

- **Backend**: Python 3.x, FastAPI
- **Database**: PostgreSQL (SQLAlchemy ORM)
- **AI / LLM Orchestration**: LangGraph (untuk multi-agent workflow)
- **Model AI**: DeepSeek Chat (`deepseek-chat`) via OpenAI API format
- **Frontend**: Vanilla HTML, CSS, JavaScript (terletak di folder `/static`)

## 2. Arsitektur Multi-Agent AI (LangGraph)

Proses inti dari aplikasi ini berjalan secara asinkron di belakang layar (background task) menggunakan graf aliran kerja (workflow graph) yang terdiri dari beberapa agen AI:

### A. Alur Screening CV (Saat Kandidat Apply)
1. **Node `read_file`**: Membaca file PDF CV dan mengubahnya menjadi teks mentah.
2. **Node `extractor`**: Agen yang bertugas mengekstrak teks mentah menjadi data terstruktur (JSON) seperti *skills, work experience*, dan *education*.
3. **Node `evaluator`**: Agen HR Evaluator yang membandingkan hasil ekstraksi dengan **Kriteria Lowongan (Job Requirements)**. Menghasilkan skor kecocokan (1-100), label, ringkasan, serta analisis kelebihan & kekurangan.
4. **Node `db_writer`**: Menyimpan hasil evaluasi ke tabel `applicants` di database. Jika skor terlalu rendah, status pelamar otomatis menjadi `rejected`.

### B. Alur Question Generation (Trigger Manual oleh HR)
Jika skor kandidat memenuhi kriteria (≥ 60), HR dapat memicu pembuatan soal ujian khusus:
1. **Node `test_generator`**: Membuat 20 soal ujian (14 Pilihan Ganda, 6 Esai) yang sangat spesifik dan *personalized* berdasarkan pengalaman di CV kandidat.
2. **Node `reviewer`**: Agen penguji kualitas yang memvalidasi keakuratan dan relevansi soal. 
   - Jika *FAIL*, agen akan me-loop kembali ke `test_generator` (maksimal 2 kali pengulangan) untuk memperbaiki soal.
   - Jika *PASS*, lanjut ke tahap berikutnya.
3. **Node `db_writer_questions`**: Menyimpan ke-20 soal ke dalam tabel `exam_questions` dan membuat sesi `Exam` baru yang dikaitkan langsung dengan kandidat tersebut.

## 3. Struktur Direktori Utama

```text
cv_ai/
├── app/
│   ├── api/
│   │   ├── routes/          # Endpoint API (auth.py, jobs.py, apply.py)
│   │   ├── deps.py          # Dependency injection (Cek Token Auth)
│   │   └── schemas.py       # Pydantic schemas untuk validasi request/response
│   ├── core/
│   │   ├── nodes/           # File fungsi agen LangGraph (extractor, evaluator, dll)
│   │   ├── config.py        # Pengaturan .env (Pydantic BaseSettings)
│   │   ├── pipeline.py      # Definisi alur graf LangGraph
│   │   └── state.py         # Definisi schema state (memori) antar agen
│   ├── db/
│   │   ├── database.py      # Koneksi database SQLAlchemy
│   │   └── models.py        # Definisi tabel DB (Job, Applicant, Exam, dll)
│   └── main.py              # Entry point aplikasi FastAPI
├── static/                  # File UI Frontend
│   ├── hr.html              # Dashboard HR (Manajemen job, pelamar, dan trigger soal)
│   ├── candidate.html       # Portal karir kandidat (Mendaftar & upload CV)
│   ├── simulator.html       # Dashboard simulasi visual untuk alur LangGraph
│   └── style.css            # Styling utama aplikasi
└── .env                     # File konfigurasi rahasia (DB URL, API Key, System Prompts)
```

## 4. Manajemen Prompt & Konfigurasi (.env)

Semua prompt AI tidak di-*hardcode* di dalam kode Python, melainkan disimpan di file `.env` agar mudah disesuaikan tanpa perlu *re-deploy* kode.
Prompt utama meliputi:
- `PROMPT_EXTRACTOR`
- `PROMPT_EVALUATOR`
- `PROMPT_TEST_GENERATOR`
- `PROMPT_REVIEWER`

Aturan penulisan `.env`: Hindari penggunaan tanda kutip tunggal (`'`) di dalam teks prompt untuk menghindari *error parsing*. Gunakan format *JSON valid* untuk ekspektasi output LLM.

## 5. Endpoints API Utama

### Autentikasi
- `POST /api/v1/auth/register` - Mendaftarkan akun HR & Company baru.
- `POST /api/v1/auth/login` - Mendapatkan JWT *access token*.

### Kandidat (Public)
- `GET /api/v1/public/jobs` - Mengambil daftar lowongan aktif.
- `POST /api/v1/public/{job_id}/apply` - Mengirim CV (File Upload) dan memicu background task *Screening CV*.

### HR (Protected - Butuh JWT)
- `POST /api/v1/jobs/` - Membuat lowongan baru beserta kriteria AI.
- `GET /api/v1/jobs/{job_id}/applicants` - Melihat daftar kandidat, skor, dan statusnya.
- `POST /api/v1/jobs/{job_id}/applicants/{applicant_id}/generate-questions` - Memicu background task untuk membuat soal *personalized*.
- `GET /api/v1/jobs/{job_id}/applicants/{applicant_id}/questions` - Mengambil soal yang sudah berhasil di-*generate* dari database.

## 6. Diagram Logika Frontend HR (hr.html)

Saat HR melihat soal kandidat (Fungsi `generateAndViewQuestions`):
1. UI memanggil `GET /questions`.
2. Jika respons `200 OK` (soal sudah ada di database), soal langsung di-*render* ke layar.
3. Jika respons `404 Not Found` (soal belum pernah dibuat), UI akan memanggil `POST /generate-questions`.
4. UI akan masuk ke fase *polling* (mengecek `GET /questions` setiap 4 detik, maksimal 15 kali).
5. Jika ada hasil, tampilkan soal. Jika gagal, tampilkan *error message*.
6. Terdapat tombol **Regenerate** untuk memaksa AI menghapus soal lama dan membuat ulang dari awal (Loop langkah 3).
