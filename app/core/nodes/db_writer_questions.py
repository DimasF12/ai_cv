import uuid
import json
from app.core.state import CVScreeningState
from app.db.database import SessionLocal
from app.db.models import ExamQuestion, Exam, Applicant


def db_writer_questions_node(state: CVScreeningState) -> CVScreeningState:
    """
    Menyimpan setiap soal dari soal_list ke tabel exam_questions satu per satu,
    lalu membuat record Exam untuk mengaitkannya dengan kandidat.
    """
    if state.get("screening_status") == "error":
        return state

    soal_list = state.get("soal_list", [])
    company_id = state.get("company_id")
    applicant_id = state.get("applicant_id")
    job_id = state.get("job_id")

    if not soal_list:
        return state

    db = SessionLocal()
    try:
        # Get employee_id from Applicant
        applicant = db.query(Applicant).filter(Applicant.id == applicant_id).first()
        if not applicant:
            raise Exception("Applicant not found")

        # Delete existing Exam and ExamQuestions if they already exist (Regenerate flow)
        existing_exam = db.query(Exam).filter(Exam.applicant_id == applicant_id).first()
        if existing_exam:
            if existing_exam.question_ids:
                q_ids = existing_exam.question_ids
                db.query(ExamQuestion).filter(ExamQuestion.id.in_(q_ids)).delete(synchronize_session=False)
            db.delete(existing_exam)
            db.commit()

        inserted_question_ids = []
        for soal in soal_list:
            tipe = soal.get("tipe", "essay")
            pertanyaan = soal.get("pertanyaan", "")
            kategori = soal.get("kategori", "General")
            kunci = soal.get("kunci_jawaban")

            if tipe == "mcq":
                opsi_dict = soal.get("opsi", {})
                opsi_json = opsi_dict if isinstance(opsi_dict, dict) else {}
            else:
                opsi_json = {}
                kunci = None

            q_id = str(uuid.uuid4())
            new_question = ExamQuestion(
                id=q_id,
                company_id=company_id,
                category=kategori,
                question=pertanyaan,
                options=opsi_json,
                correct_answer=kunci or "",
                difficulty="medium",
            )
            db.add(new_question)
            inserted_question_ids.append(q_id)

        # Create new Exam record
        new_exam = Exam(
            id=str(uuid.uuid4()),
            company_id=company_id,
            applicant_id=applicant_id,
            job_id=job_id,
            employee_id=applicant.employee_id,
            question_ids=inserted_question_ids,
            total_questions=len(inserted_question_ids),
            status="pending"
        )
        db.add(new_exam)
        
        # Update applicant status
        applicant.exam_status = "generated"

        db.commit()
        state["screening_status"] = "completed"

    except Exception as e:
        db.rollback()
        state["screening_status"] = "error"
        state["error_message"] = f"DB Questions Write Error: {str(e)}"
    finally:
        db.close()

    return state
