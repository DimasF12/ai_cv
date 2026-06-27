import json
from app.core.state import CVScreeningState
from app.db.database import SessionLocal
from app.db.models import Applicant


def db_writer_node(state: CVScreeningState) -> CVScreeningState:
    """
    Menyimpan hasil evaluasi (skor, summary, kelebihan, kekurangan) ke tabel applicants.
    Status dikunci menjadi 'analysis_completed' jika sukses.
    Jika kandidat tidak lolos threshold, status disetel ke 'rejected'.
    """
    if state.get("screening_status") == "error":
        return state

    db = SessionLocal()
    try:
        applicant = db.query(Applicant).filter(Applicant.id == state["applicant_id"]).first()
        if applicant:
            skor = state.get("skor_kecocokan") or 0
            threshold = state.get("threshold_skor") or 80

            applicant.overall_score = skor
            applicant.cv_summary = state.get("cv_summary")
            applicant.strengths = json.dumps(state.get("kelebihan_utama", []), ensure_ascii=False)
            applicant.weaknesses = json.dumps(state.get("kekurangan_utama", []), ensure_ascii=False)

            # Tentukan status berdasarkan skor
            if skor >= threshold:
                applicant.status = "analysis_completed"   # Lolos, soal sedang/sudah dibuat
            else:
                applicant.status = "rejected"              # Tidak lolos threshold

            db.commit()
        else:
            state["screening_status"] = "error"
            state["error_message"] = "Applicant ID not found in DB."

    except Exception as e:
        db.rollback()
        state["screening_status"] = "error"
        state["error_message"] = f"DB Writer Error: {str(e)}"
    finally:
        db.close()

    return state
