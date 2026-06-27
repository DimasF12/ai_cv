import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Job, User, Applicant, ExamQuestion
from app.api.schemas import JobCreate, JobResponse
from app.api.deps import get_current_user
from app.core.nodes.test_generator import test_generator_node
from app.core.nodes.reviewer import reviewer_node
from app.core.nodes.db_writer_questions import db_writer_questions_node

router = APIRouter()

@router.post("/", response_model=JobResponse)
def create_job(job_in: JobCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    new_job_id = str(uuid.uuid4())
    new_job = Job(
        id=new_job_id,
        company_id=current_user.company_id,
        created_by=current_user.id,
        title=job_in.title,
        slug=job_in.slug,
        location=job_in.location,
        department=job_in.department,
        type=job_in.experience_level, # map temp
        experience_level=job_in.experience_level,
        description=job_in.description,
        requirements=job_in.requirements,
        salary_min=job_in.salary_min,
        salary_max=job_in.salary_max,
        currency=job_in.currency,
        openings=job_in.openings,
        status="open"
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    return new_job

@router.get("/", response_model=List[JobResponse])
def get_jobs(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    jobs = db.query(Job).filter(Job.company_id == current_user.company_id, Job.deleted_at == None).all()
    return jobs

@router.get("/{job_id}/applicants")
def get_job_applicants(job_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Pastikan lowongan ini milik company HR tersebut
    job = db.query(Job).filter(Job.id == job_id, Job.company_id == current_user.company_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    applicants = db.query(Applicant).filter(Applicant.job_id == job_id).all()
    
    results = []
    for app in applicants:
        results.append({
            "id": app.id,
            "name": app.name,
            "email": app.email,
            "status": app.status,
            "overall_score": app.overall_score,
            "cv_summary": app.cv_summary,
            "strengths": app.strengths,
            "weaknesses": app.weaknesses
        })
    return results


async def _run_question_generation(state: dict):
    """Background task: run test_generator -> reviewer (max 2x) -> db_writer_questions"""
    from app.core.nodes.reviewer import MAX_REVIEW_RETRIES
    state["retry_count"] = 0

    state = await test_generator_node(state)
    if state.get("screening_status") == "error":
        return

    state = await reviewer_node(state)

    # Loop max 2x jika reviewer FAIL
    while (
        state.get("reviewer_status") == "FAIL"
        and (state.get("retry_count") or 0) < MAX_REVIEW_RETRIES
    ):
        state = await test_generator_node(state)
        if state.get("screening_status") == "error":
            return
        state = await reviewer_node(state)

    db_writer_questions_node(state)


@router.post("/{job_id}/applicants/{applicant_id}/generate-questions")
async def generate_questions(
    job_id: str,
    applicant_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Trigger AI question generation untuk satu kandidat yang sudah lolos screening.
    Hanya bisa dipanggil jika kandidat memiliki status 'analysis_completed'.
    """
    # Validasi job milik company HR
    job = db.query(Job).filter(Job.id == job_id, Job.company_id == current_user.company_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Validasi applicant
    applicant = db.query(Applicant).filter(
        Applicant.id == applicant_id,
        Applicant.job_id == job_id
    ).first()
    if not applicant:
        raise HTTPException(status_code=404, detail="Applicant not found")

    if not applicant.overall_score or applicant.overall_score < 60:
        raise HTTPException(
            status_code=400,
            detail=f"Candidate score ({applicant.overall_score or 0}) is too low to generate questions."
        )

    # Bangun state untuk pipeline test generation
    state = {
        "company_id": current_user.company_id,
        "job_id": job_id,
        "applicant_id": applicant_id,
        "kriteria_perusahaan": job.requirements or job.description or "",
        "cv_summary": applicant.cv_summary or "",
        "extracted_skills": applicant.cv_summary or "",  # fallback
        "screening_status": "evaluated",
        "soal_list": None,
        "reviewer_status": None,
        "reviewer_feedback": None,
        "reviewer_skor": None,
        "retry_count": 0,
        "error_message": None,
    }

    # Jalankan di background agar response cepat
    background_tasks.add_task(_run_question_generation, state)

    return {
        "message": f"Question generation started for {applicant.name}. Please wait ~30-60 seconds then refresh.",
        "applicant_id": applicant_id
    }


from app.db.models import Job, User, Applicant, ExamQuestion, Exam

@router.get("/{job_id}/applicants/{applicant_id}/questions")
def get_applicant_questions(
    job_id: str,
    applicant_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Ambil soal-soal yang sudah di-generate untuk kandidat tertentu dari tabel exam_questions
    melalui tabel exams.
    """
    job = db.query(Job).filter(Job.id == job_id, Job.company_id == current_user.company_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Cari record Exam untuk applicant ini
    exam = db.query(Exam).filter(Exam.applicant_id == applicant_id, Exam.job_id == job_id).first()
    if not exam or not exam.question_ids:
        raise HTTPException(status_code=404, detail="No questions generated yet. Please wait or trigger generation first.")

    # Ambil soal berdasarkan question_ids dari Exam
    questions = db.query(ExamQuestion).filter(ExamQuestion.id.in_(exam.question_ids)).all()
    
    # Sortir sesuai urutan question_ids
    q_dict = {q.id: q for q in questions}
    sorted_questions = [q_dict[q_id] for q_id in exam.question_ids if q_id in q_dict]

    results = []
    for q in sorted_questions:
        results.append({
            "id": q.id,
            "tipe": "mcq" if q.options else "essay",
            "kategori": q.category,
            "pertanyaan": q.question,
            "opsi": q.options,
            "kunci_jawaban": q.correct_answer or None,
            "difficulty": q.difficulty,
        })
    return results
