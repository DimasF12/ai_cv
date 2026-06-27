import uuid
import shutil
import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Job, Applicant, Employee
# from app.core.pipeline import process_cv_background  # ORIGINAL - push ke DB
from app.core.pipeline import process_cv_preview       # [DEV MODE] - tanpa DB

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.get("/jobs")
def get_public_jobs(db: Session = Depends(get_db)):
    jobs = db.query(Job).filter(Job.status == 'open', Job.deleted_at == None).all()
    results = []
    for job in jobs:
        results.append({
            "id": job.id,
            "title": job.title,
            "slug": job.slug,
            "location": job.location,
            "department": job.department,
            "experience_level": job.experience_level,
            "description": job.description
        })
    return results

# ============================================================
# [DEV MODE] /apply - Tidak push ke DB, langsung return hasil AI
# ORIGINAL endpoint ada di bawah dalam komentar
# ============================================================
@router.post("/{job_id}/apply")
async def apply_job(
    job_id: str,
    name: str,
    email: str,
    cv_file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # Cari lowongan
    job = db.query(Job).filter(Job.id == job_id, Job.status == 'open', Job.deleted_at == None).first()
    if not job:
        raise HTTPException(status_code=404, detail="Lowongan tidak ditemukan atau sudah ditutup")

    # Simpan file CV sementara (tetap perlu untuk dibaca AI)
    file_id = str(uuid.uuid4())
    file_extension = os.path.splitext(cv_file.filename)[1]
    safe_filename = f"{file_id}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(cv_file.file, buffer)

    # [DEV MODE] Jalankan AI langsung - TIDAK push ke DB
    result = await process_cv_preview(
        kriteria_perusahaan=job.requirements or job.description,
        threshold_skor=60,
        cv_file_path=file_path,
        cv_original_filename=cv_file.filename
    )

    # Hapus file sementara setelah AI selesai membacanya
    try:
        os.remove(file_path)
    except Exception:
        pass

    # Return hasil AI langsung ke FE
    if result.get("screening_status") == "error":
        return {
            "mode": "preview",
            "status": "error",
            "error": result.get("error_message", "Unknown error"),
            "applicant": {"name": name, "email": email},
        }

    return {
        "mode": "preview",
        "status": "success",
        "message": "CV berhasil dianalisis. Hasil ini TIDAK disimpan ke database.",
        "applicant": {
            "name": name,
            "email": email,
        },
        "ai_result": {
            "skor_kecocokan": result.get("skor_kecocokan"),
            "label": result.get("label"),
            "cv_summary": result.get("cv_summary"),
            "kelebihan_utama": result.get("kelebihan_utama", []),
            "kekurangan_utama": result.get("kekurangan_utama", []),
            "laporan_analisis_markdown": result.get("laporan_analisis_markdown"),
            "extracted_skills": result.get("extracted_skills"),
            "screening_status": result.get("screening_status"),
        }
    }

# ============================================================
# ORIGINAL endpoint (dengan DB push) - uncomment untuk restore
# ============================================================
# @router.post("/{job_id}/apply")
# async def apply_job(
#     job_id: str,
#     name: str,
#     email: str,
#     background_tasks: BackgroundTasks,
#     cv_file: UploadFile = File(...),
#     db: Session = Depends(get_db)
# ):
#     job = db.query(Job).filter(Job.id == job_id, Job.status == 'open', Job.deleted_at == None).first()
#     if not job:
#         raise HTTPException(status_code=404, detail="Lowongan tidak ditemukan atau sudah ditutup")
#
#     dummy_employee = db.query(Employee).first()
#     if not dummy_employee:
#         dummy_employee = Employee(
#             id=str(uuid.uuid4()), name="System Dummy", email="dummy@system.com", password="dummy"
#         )
#         db.add(dummy_employee)
#         db.commit()
#
#     existing = db.query(Applicant).filter(Applicant.job_id == job.id, Applicant.email == email).first()
#     if existing:
#         raise HTTPException(status_code=400, detail="Anda sudah melamar posisi ini")
#
#     file_id = str(uuid.uuid4())
#     file_extension = os.path.splitext(cv_file.filename)[1]
#     safe_filename = f"{file_id}{file_extension}"
#     file_path = os.path.join(UPLOAD_DIR, safe_filename)
#
#     with open(file_path, "wb") as buffer:
#         shutil.copyfileobj(cv_file.file, buffer)
#
#     new_applicant = Applicant(
#         id=str(uuid.uuid4()),
#         company_id=job.company_id,
#         job_id=job.id,
#         employee_id=dummy_employee.id,
#         name=name,
#         email=email,
#         status="pending_analysis",
#         cv_id=safe_filename
#     )
#     db.add(new_applicant)
#     job.applicant_count += 1
#     job.unseen_applicant_count += 1
#     db.commit()
#     db.refresh(new_applicant)
#
#     background_tasks.add_task(
#         process_cv_background,
#         company_id=job.company_id,
#         job_id=job.id,
#         applicant_id=new_applicant.id,
#         kriteria_perusahaan=job.requirements or job.description,
#         threshold_skor=60,
#         cv_file_path=file_path,
#         cv_original_filename=cv_file.filename
#     )
#
#     return {"message": "Berhasil melamar pekerjaan. CV Anda sedang dianalisis oleh AI."}

