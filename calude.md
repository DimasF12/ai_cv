# CLAUDE.md — CV Screening AI Agent

> Dokumen ini adalah panduan lengkap bagi AI Agent untuk memahami, membangun, dan mengembangkan sistem **CV Screening AI** berbasis FastAPI + LangChain/LangGraph. Baca seluruh dokumen ini sebelum menulis satu baris kode pun.

---

## 1. GAMBARAN BESAR SISTEM

Sistem ini adalah pipeline otomatis untuk membantu HR melakukan **screening CV kandidat secara individual**. Setiap kandidat dievaluasi sendiri-sendiri — bukan dibandingkan satu sama lain dalam batch.

### Dua Aktor Utama

| Aktor | Peran |
|-------|-------|
| **HR** | Membuka lowongan, set kriteria, melihat dashboard hasil screening, membuat keputusan |
| **Kandidat** | Upload CV ke halaman lowongan yang sudah dibuka HR |

### Alur Besar Sistem
```
[HR Buka Lowongan + Set Kriteria + Set Threshold Skor]
                    │
                    ▼
        [Kandidat Upload CV ke Lowongan]
                    │
                    ▼
  [AI Screening Jalan di Background per Kandidat]
                    │
                    ▼
  [HR Buka Dashboard → Lihat Kandidat yang Lolos Threshold]
                    │
                    ▼
     [HR Buat Keputusan: Next Step / Tidak Lolos]
                    │
                    ▼
        [Next Step → Tahap Soal]  ← dikerjakan nanti
```

---

## 2. FLOW DETAIL PER AKTOR

### 2.1 Flow HR — Membuka Lowongan

1. HR login ke dashboard
2. HR membuat **Job Posting** baru:
   - Judul posisi
   - Deskripsi pekerjaan
   - **Kriteria screening** → diisi manual, ini yang masuk ke prompt AI
   - **Threshold skor minimum** → default 60, HR bisa ubah (misal: 70, 80)
3. Sistem generate **link lowongan unik** untuk kandidat
4. HR share link ke kandidat

### 2.2 Flow Kandidat — Upload CV

1. Kandidat buka link lowongan dari HR
2. Kandidat upload file CV (PDF/DOCX)
3. Sistem otomatis menjalankan **AI Screening Pipeline**
4. Kandidat melihat halaman konfirmasi "CV berhasil dikirim"

### 2.3 Flow HR — Dashboard Screening

Setelah CV masuk dan diproses di background, HR membuka dashboard:

- **Default view:** hanya tampilkan kandidat dengan `skor_kecocokan >= threshold`
- HR bisa toggle untuk lihat semua kandidat (termasuk yang di bawah threshold)
- Per kandidat, HR bisa lihat:
  - Skor kecocokan (1–100) + label
  - Laporan & Key Insight (Markdown)
- Per kandidat, HR bisa klik:
  - ✅ **Next Step** → kandidat lanjut ke tahap soal *(dikerjakan nanti)*
  - ❌ **Tidak Lolos** → trigger saran AI untuk HR
  - 💡 **Saran Pertanyaan** → AI generate pertanyaan interview *(dikerjakan nanti)*

---

## 3. ARSITEKTUR PIPELINE AI (Per Kandidat)

> ⚠️ Pipeline ini dijalankan **satu kali per kandidat** saat mereka upload CV, berjalan di background. Bukan batch semua kandidat sekaligus.

```
[Kandidat Upload CV]
        │
        ▼
┌─────────────────┐
│   Read File     │  → Baca file CV (PDF/DOCX)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Parser        │  → Ekstraksi teks bersih dari CV kandidat ini
└────────┬────────┘
         │  + kriteria_perusahaan (dari Job Posting HR)
         ▼
┌──────────────────────┐
│  CV Evaluator        │  → Evaluasi 1 kandidat vs kriteria perusahaan
│  (LLM #1)            │    Model: deepseek-reasoner
│                      │    Output: skor + laporan + ringkasan (JSON)
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  JSON Parser &       │  → Parse output JSON dari LLM
│  DB Writer           │    Simpan hasil ke database
└──────────────────────┘
           │
           ▼
  [Hasil tersimpan di DB]
  [HR lihat di dashboard — hanya yang lolos threshold]
```

---

## 4. DETAIL SETIAP NODE / KOMPONEN

### 4.1 `ReadFileNode`
- **Fungsi:** Membaca file CV kandidat yang diupload
- **Input:** File CV (PDF/DOCX), `job_id`, `kandidat_id`
- **Output:** Raw content + `nama_file`

### 4.2 `ParserNode`
- **Fungsi:** Ekstraksi teks bersih dari CV kandidat ini saja
- **Mode:** `Parser` (terstruktur) atau `Stringify` (plain text)
- **Output:** `cv_text` — string teks CV 1 kandidat, siap dikirim ke LLM

### 4.3 `CVEvaluatorNode` ← CORE NODE
- **Fungsi:** Evaluasi 1 kandidat berdasarkan kriteria perusahaan
- **Model:** `deepseek-reasoner`
- **Input:**
  - `kriteria_perusahaan` → dari Job Posting HR
  - `cv_text` → hasil ParserNode (hanya CV kandidat ini, bukan batch)

**Full Prompt Template:**
```python
prompt = f"""Anda adalah Head of HR & Senior AI Analyst.
Tugas Anda adalah mengevaluasi CV kandidat berikut berdasarkan Kriteria Perusahaan
dan memberikan penilaian yang objektif dan komprehensif.

--- KRITERIA PERUSAHAAN ---
{kriteria_perusahaan}

--- CV KANDIDAT ---
{cv_text}

INSTRUKSI EVALUASI:
1. Analisis kesesuaian kandidat ini dengan kriteria perusahaan secara mendalam.
2. Buat laporan evaluasi lengkap dalam format Markdown (gunakan emoji ✅, ❌, ⚠️).
3. Berikan skor kecocokan dari 1-100 berdasarkan seberapa cocok kandidat dengan kriteria.

Output HARUS murni dalam format JSON. DILARANG menggunakan markdown code block (seperti ```json).

Struktur JSON Wajib:
{{
    "skor_kecocokan": <angka 1-100>,
    "laporan_analisis_markdown": "<Laporan markdown lengkap, gunakan \\n untuk baris baru>",
    "ringkasan_pengalaman": "<Rangkuman padat 2-3 kalimat pengalaman teknis utama kandidat>",
    "kelebihan_utama": ["<poin 1>", "<poin 2>", "<poin 3>"],
    "kekurangan_utama": ["<poin 1>", "<poin 2>"]
}}"""
```

### 4.4 `JSONParserAndDBWriterNode`
- **Fungsi:** Parse JSON output LLM, simpan ke database
```python
import json, re

def parse_evaluator_output(raw: str) -> dict:
    clean = re.sub(r"```json|```", "", raw).strip()
    return json.loads(clean)

result = parse_evaluator_output(raw_output)
# Simpan result ke tabel screening_results
```

### 4.5 `SaranGagalNode` ← ON-DEMAND
- **Fungsi:** Generate saran AI saat HR klik tombol ❌ Tidak Lolos
- **Model:** `deepseek-chat`
- **Trigger:** HR action, bukan bagian pipeline awal
```python
prompt = f"""HR memutuskan kandidat ini tidak lolos seleksi.

Ringkasan kandidat: {ringkasan_pengalaman}
Kriteria perusahaan: {kriteria_perusahaan}

Berikan saran konstruktif dalam Markdown:
1. Apa kelemahan utama kandidat ini dibanding kriteria?
2. Skill apa yang perlu mereka kembangkan?
3. Posisi lain yang mungkin lebih cocok untuk mereka?"""
```

### 4.6 `SaranPertanyaanNode` ← ON-DEMAND, DIKERJAKAN NANTI
- **Fungsi:** Generate pertanyaan interview berdasarkan CV kandidat ini
- **Model:** `deepseek-chat`
- **Dua tipe pertanyaan:**

| Tipe | Sumber |
|------|--------|
| `soal_resmi_hr` | Template soal standar dari HR (diisi HR di Job Posting) |
| `saran_pertanyaan_ai` | AI generate berdasarkan pengalaman spesifik di CV kandidat ini |

---

## 5. OUTPUT SISTEM

### Output 1 — Skor Kecocokan (Ditampilkan di Dashboard HR)
```json
{
  "nama_file": "CV_Budi_Santoso.pdf",
  "skor_kecocokan": 87,
  "label": "Sangat Cocok"
}
```
Label mapping:
- 80–100 → `"Sangat Cocok"` ✅
- 60–79 → `"Cukup Cocok"` ⚠️
- 0–59 → `"Kurang Cocok"` ❌

### Output 2 — Laporan & Key Insight HR
- Format: **Markdown** (render di dashboard)
- Isi: analisis per kandidat + tabel rekomendasi akhir
- Gunakan emoji ✅ ❌ ⚠️

### Output 3 — Saran AI saat HR Tekan Tombol "Tidak Lolos"
**Trigger:** HR klik ❌ pada kandidat tertentu → panggil LLM on-demand

```python
async def generate_saran_gagal(nama_file: str, ringkasan: str, kriteria: str) -> str:
    prompt = f"""HR memutuskan kandidat '{nama_file}' tidak lolos seleksi.

Ringkasan kandidat: {ringkasan}
Kriteria perusahaan: {kriteria}

Berikan saran konstruktif dalam Markdown:
1. Apa kelemahan utama kandidat ini dibanding kriteria?
2. Skill apa yang perlu mereka kembangkan?
3. Posisi lain yang mungkin lebih cocok untuk mereka?"""
```

### Output 4 — Saran Pertanyaan saat HR Tekan Tombol "Saran"
**Trigger:** HR klik 💡 pada kandidat tertentu
- Ambil dari hasil `AITestGeneratorNode` yang sudah tersimpan di DB
- Return: `soal_resmi_hr` + `saran_pertanyaan_ai`
- ⏳ *Implementasi lengkap dikerjakan nanti*

---

## 6. DATABASE SCHEMA — PostgreSQL (Multi-Tenant)

### Desain Prinsip
- **Multi-tenant by `company_id`** — semua tabel utama punya kolom `company_id`
- **Row-level isolation** — query selalu filter by `company_id` dari JWT token HR
- **UUID sebagai primary key** — pakai `gen_random_uuid()` bawaan PostgreSQL
- **Soft delete** — pakai `deleted_at` bukan `DELETE` untuk audit trail

### ERD Singkat
```
companies ──< hr_users ──< jobs ──< candidates ──< screening_results
                                         │
                                    (cv file di storage)
```

### DDL Lengkap

```sql
-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ================================================================
-- TABEL 1: companies
-- Satu row per perusahaan (tenant)
-- ================================================================
CREATE TABLE companies (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    slug            TEXT UNIQUE NOT NULL,       -- untuk URL: app.com/acme-corp
    logo_url        TEXT,
    created_at      TIMESTAMPTZ DEFAULT now(),
    deleted_at      TIMESTAMPTZ                 -- soft delete
);

-- ================================================================
-- TABEL 2: hr_users
-- User HR yang login ke dashboard
-- Auth: JWT dengan payload {user_id, company_id, role}
-- ================================================================
CREATE TABLE hr_users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id      UUID NOT NULL REFERENCES companies(id),
    email           TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,              -- bcrypt
    full_name       TEXT NOT NULL,
    role            TEXT NOT NULL DEFAULT 'hr', -- 'hr' | 'admin'
    is_active       BOOLEAN DEFAULT true,
    created_at      TIMESTAMPTZ DEFAULT now(),
    deleted_at      TIMESTAMPTZ
);
CREATE INDEX idx_hr_users_company ON hr_users(company_id);

-- ================================================================
-- TABEL 3: jobs
-- Lowongan yang dibuka HR
-- ================================================================
CREATE TABLE jobs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id          UUID NOT NULL REFERENCES companies(id),
    created_by          UUID NOT NULL REFERENCES hr_users(id),

    title               TEXT NOT NULL,
    description         TEXT,
    kriteria_perusahaan TEXT NOT NULL,          -- masuk ke prompt AI evaluator
    soal_template_hr    TEXT,                   -- template soal resmi HR (nanti)
    threshold_skor      INTEGER DEFAULT 60      -- kandidat tampil di dashboard jika >= ini
                            CHECK (threshold_skor BETWEEN 1 AND 100),

    apply_link_token    TEXT UNIQUE NOT NULL,   -- token unik untuk link kandidat
    status              TEXT DEFAULT 'open'
                            CHECK (status IN ('open', 'closed', 'draft')),

    created_at          TIMESTAMPTZ DEFAULT now(),
    closed_at           TIMESTAMPTZ,
    deleted_at          TIMESTAMPTZ
);
CREATE INDEX idx_jobs_company ON jobs(company_id);
CREATE INDEX idx_jobs_token   ON jobs(apply_link_token);

-- ================================================================
-- TABEL 4: candidates
-- Kandidat yang apply ke suatu job
-- Kandidat tidak punya akun — diidentifikasi by email + job
-- ================================================================
CREATE TABLE candidates (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id          UUID NOT NULL REFERENCES jobs(id),
    company_id      UUID NOT NULL REFERENCES companies(id), -- denormalized untuk query cepat

    full_name       TEXT NOT NULL,
    email           TEXT NOT NULL,
    phone           TEXT,

    cv_original_filename    TEXT NOT NULL,      -- nama file asli dari kandidat
    cv_storage_path         TEXT NOT NULL,      -- path di storage (S3/Supabase/lokal)
    cv_mime_type            TEXT NOT NULL,      -- 'application/pdf' | 'application/vnd...'

    applied_at      TIMESTAMPTZ DEFAULT now(),

    UNIQUE (job_id, email)                      -- 1 kandidat tidak bisa apply 2x ke job yang sama
);
CREATE INDEX idx_candidates_job     ON candidates(job_id);
CREATE INDEX idx_candidates_company ON candidates(company_id);
CREATE INDEX idx_candidates_email   ON candidates(job_id, email);

-- ================================================================
-- TABEL 5: screening_results
-- Hasil AI screening per kandidat — 1 kandidat : 1 result
-- ================================================================
CREATE TABLE screening_results (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id    UUID UNIQUE NOT NULL REFERENCES candidates(id), -- 1-to-1
    job_id          UUID NOT NULL REFERENCES jobs(id),
    company_id      UUID NOT NULL REFERENCES companies(id),         -- denormalized

    -- Hasil dari LLM (CVEvaluatorNode)
    skor_kecocokan          SMALLINT CHECK (skor_kecocokan BETWEEN 1 AND 100),
    label                   TEXT CHECK (label IN ('Sangat Cocok', 'Cukup Cocok', 'Kurang Cocok')),
    ringkasan_pengalaman    TEXT,
    kelebihan_utama         JSONB,              -- ["poin 1", "poin 2"]
    kekurangan_utama        JSONB,              -- ["poin 1", "poin 2"]
    laporan_markdown        TEXT,               -- laporan lengkap untuk HR

    -- Soal & saran (diisi nanti oleh SaranPertanyaanNode)
    soal_resmi_hr           JSONB,              -- ["pertanyaan 1", "pertanyaan 2"]
    saran_pertanyaan_ai     JSONB,              -- ["saran 1", "saran 2"]

    -- Keputusan HR
    hr_decision             TEXT DEFAULT 'pending'
                                CHECK (hr_decision IN ('pending', 'next_step', 'rejected')),
    hr_decision_by          UUID REFERENCES hr_users(id),
    hr_decision_at          TIMESTAMPTZ,
    saran_gagal_markdown    TEXT,               -- diisi on-demand saat HR reject

    -- Status pipeline
    screening_status        TEXT DEFAULT 'pending'
                                CHECK (screening_status IN ('pending', 'processing', 'completed', 'error')),
    error_message           TEXT,
    screened_at             TIMESTAMPTZ,

    created_at              TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_screening_job      ON screening_results(job_id);
CREATE INDEX idx_screening_company  ON screening_results(company_id);
CREATE INDEX idx_screening_skor     ON screening_results(job_id, skor_kecocokan DESC);
CREATE INDEX idx_screening_status   ON screening_results(screening_status);
CREATE INDEX idx_screening_decision ON screening_results(job_id, hr_decision);
```

### Catatan Penting untuk Query

```sql
-- ✅ SELALU filter by company_id (ambil dari JWT token) untuk isolasi tenant
SELECT * FROM jobs
WHERE company_id = :company_id_from_jwt
  AND deleted_at IS NULL;

-- ✅ Dashboard HR — hanya tampilkan kandidat lolos threshold
SELECT c.*, sr.*
FROM candidates c
JOIN screening_results sr ON sr.candidate_id = c.id
JOIN jobs j ON j.id = c.job_id
WHERE c.job_id = :job_id
  AND c.company_id = :company_id_from_jwt
  AND sr.screening_status = 'completed'
  AND sr.skor_kecocokan >= j.threshold_skor   -- filter threshold otomatis
ORDER BY sr.skor_kecocokan DESC;

-- ✅ Toggle "lihat semua" — hapus filter threshold
SELECT c.*, sr.*
FROM candidates c
JOIN screening_results sr ON sr.candidate_id = c.id
WHERE c.job_id = :job_id
  AND c.company_id = :company_id_from_jwt
  AND sr.screening_status = 'completed'
ORDER BY sr.skor_kecocokan DESC;
```

### JWT Payload Struktur
```json
{
  "sub": "hr_user_uuid",
  "company_id": "company_uuid",
  "role": "hr",
  "exp": 1234567890
}
```
> Setiap request dari HR, extract `company_id` dari JWT dan inject ke semua query sebagai filter tenant.

---

## 7. API ENDPOINTS (FastAPI)

```
# Auth (Public)
POST   /auth/register             → Daftar perusahaan + HR admin pertama
POST   /auth/login                → Login HR → return JWT token

# HR — Job Management  [requires JWT]
POST   /jobs                      → Buat lowongan + set kriteria + threshold
GET    /jobs                      → List semua lowongan milik company ini
GET    /jobs/{job_id}             → Detail lowongan
PATCH  /jobs/{job_id}             → Update kriteria / threshold / status
DELETE /jobs/{job_id}             → Soft delete lowongan

# Kandidat — Apply  [PUBLIC — no auth, pakai apply_link_token]
GET    /apply/{token}             → Info lowongan (judul, deskripsi) untuk halaman apply
POST   /apply/{token}             → Upload CV → simpan kandidat → trigger AI pipeline background

# HR — Dashboard Screening  [requires JWT]
GET    /jobs/{job_id}/candidates              → List kandidat lolos threshold (default)
GET    /jobs/{job_id}/candidates?show_all=true → List semua kandidat termasuk di bawah threshold
GET    /candidates/{candidate_id}             → Detail kandidat + laporan markdown lengkap
POST   /candidates/{candidate_id}/decision    → Set keputusan: {decision: "next_step" | "rejected"}
GET    /candidates/{candidate_id}/saran-gagal → Saran AI on-demand saat HR reject
GET    /candidates/{candidate_id}/saran-soal  → Saran pertanyaan interview (nanti)
```

> **Security note:** Endpoint `/apply/{token}` adalah satu-satunya endpoint publik tanpa JWT. Token ini unik per job dan di-generate saat HR buat lowongan.

---

## 8. STRUKTUR PROJECT

```
cv-screening-ai/
├── main.py
├── CLAUDE.md
├── alembic/                       # Database migrations
│   └── versions/
│
├── core/
│   ├── pipeline.py                # LangGraph orchestrator (per kandidat)
│   ├── state.py                   # CVScreeningState TypedDict
│   └── nodes/
│       ├── read_file.py           # ReadFileNode
│       ├── parser.py              # ParserNode
│       ├── evaluator.py           # CVEvaluatorNode (deepseek-reasoner)
│       ├── db_writer.py           # JSONParserAndDBWriterNode
│       ├── saran_gagal.py         # SaranGagalNode (on-demand)
│       └── saran_soal.py          # SaranPertanyaanNode (nanti)
│
├── api/
│   ├── deps.py                    # JWT auth dependency, get_current_hr_user()
│   ├── routes/
│   │   ├── auth.py                # POST /auth/login, POST /auth/register
│   │   ├── jobs.py                # /jobs endpoints (HR)
│   │   ├── apply.py               # /jobs/{token}/apply (Kandidat, no auth)
│   │   └── screening.py           # Dashboard HR + keputusan
│   └── schemas.py                 # Pydantic models request/response
│
├── db/
│   ├── session.py                 # PostgreSQL async session (SQLAlchemy)
│   ├── models.py                  # ORM models (Company, HRUser, Job, Candidate, ScreeningResult)
│   └── queries/
│       ├── jobs.py
│       ├── candidates.py
│       └── screening.py
│
├── services/
│   ├── auth.py                    # JWT encode/decode, password hash
│   ├── file_reader.py             # Baca PDF/DOCX → text
│   ├── llm_client.py              # DeepSeek API wrapper
│   ├── storage.py                 # Upload/download file CV (S3/lokal)
│   └── background_tasks.py        # Handler background screening pipeline
│
└── prompts/
    ├── evaluator.txt              # Prompt template evaluasi per kandidat
    └── saran_soal.txt             # (nanti)
```

---

## 9. LANGGRAPH STATE SCHEMA

```python
from typing import TypedDict, List, Optional

class CVScreeningState(TypedDict):
    # Dari Job Posting HR
    job_id: str
    company_id: str                       # Dari JWT token HR
    kriteria_perusahaan: str
    threshold_skor: int                   # Default 60

    # Dari upload kandidat
    candidate_id: str
    cv_original_filename: str
    cv_raw_content: bytes

    # Setelah Parser
    cv_text: str                          # Teks bersih CV 1 kandidat

    # Setelah CVEvaluatorNode
    raw_evaluator_output: str
    skor_kecocokan: Optional[int]         # 1–100
    label: Optional[str]                  # Sangat Cocok | Cukup Cocok | Kurang Cocok
    laporan_analisis_markdown: Optional[str]
    ringkasan_pengalaman: Optional[str]
    kelebihan_utama: Optional[List[str]]
    kekurangan_utama: Optional[List[str]]

    # Metadata pipeline
    screening_status: str                 # "pending" | "processing" | "completed" | "error"
    error_message: Optional[str]
```

---

## 10. MODEL LLM & KONFIGURASI

| Node | Model | Alasan |
|------|-------|--------|
| CVEvaluator | `deepseek-reasoner` | Reasoning mendalam evaluasi CV vs kriteria |
| SaranGagal (on-demand) | `deepseek-chat` | Saran konstruktif ringan |
| SaranSoal (nanti) | `deepseek-chat` | Generate pertanyaan interview |

```python
DEEPSEEK_CONFIG = {
    "reasoner": {
        "model": "deepseek-reasoner",
        "temperature": 0.2,
        "max_tokens": 4000,
    },
    "chat": {
        "model": "deepseek-chat",
        "temperature": 0.2,
        "max_tokens": 2000,
    }
}
```

---

## 11. ATURAN PENTING UNTUK AI AGENT

1. **Evaluasi per kandidat, bukan batch** — pipeline dijalankan satu kali per kandidat saat upload, berjalan di background
2. **Kandidat upload CV, bukan HR** — HR hanya melihat hasil di dashboard
3. **Selalu filter `company_id` dari JWT** — wajib di setiap query DB untuk isolasi tenant
4. **Kriteria perusahaan dari Job Posting** — diisi HR saat buka lowongan, bukan hardcoded
5. **Threshold filter di dashboard** — default 60, HR bisa ubah per job, HR bisa toggle lihat semua
6. **JSON parsing wajib robust** — selalu strip markdown fences sebelum `json.loads()`
7. **Saran Gagal = on-demand** — hanya dipanggil saat HR klik ❌, simpan hasilnya ke kolom `saran_gagal_markdown`
8. **Soal & Saran Pertanyaan = dikerjakan nanti** — siapkan kolom di DB dan endpoint placeholder saja
9. **`candidate_id` adalah identifier utama** — gunakan UUID, bukan nama file

---

## 12. NEXT STEPS (Prioritas Pengerjaan)

- [x] Arsitektur & dokumentasi flow
- [x] Database schema PostgreSQL (multi-tenant)
- [ ] **Fase 1:** Setup project — FastAPI boilerplate, koneksi PostgreSQL, Alembic migrations
- [ ] **Fase 2:** Auth — register perusahaan, login HR, JWT middleware
- [ ] **Fase 3:** Job Posting — HR buat lowongan, generate apply link token
- [ ] **Fase 4:** Kandidat apply — upload CV, trigger AI pipeline di background
- [ ] **Fase 5:** Dashboard HR — list kandidat, filter threshold, laporan, tombol keputusan
- [ ] **Fase 6:** Saran Gagal — on-demand saat HR reject kandidat
- [ ] **Fase 7:** Soal & Saran Pertanyaan Interview ← *dikerjakan nanti*

---

*Dokumen ini di-generate dari rancangan Langflow dan spesifikasi sistem CV Screening AI. Update dokumen ini setiap kali ada perubahan flow atau penambahan fitur.*