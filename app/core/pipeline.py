from langgraph.graph import StateGraph, END
from app.core.state import CVScreeningState
from app.core.nodes.read_file import read_file_node
from app.core.nodes.extractor import extractor_node
from app.core.nodes.evaluator import evaluate_node
from app.core.nodes.test_generator import test_generator_node
from app.core.nodes.reviewer import reviewer_node, MAX_REVIEW_RETRIES
from app.core.nodes.db_writer import db_writer_node
from app.core.nodes.db_writer_questions import db_writer_questions_node

# ==========================================
# Inisialisasi Graph
# ==========================================
workflow = StateGraph(CVScreeningState)

# ==========================================
# Daftarkan semua Nodes (Agents)
# ==========================================
workflow.add_node("read_file", read_file_node)
workflow.add_node("extractor", extractor_node)
workflow.add_node("evaluator", evaluate_node)
workflow.add_node("db_writer", db_writer_node)           # Simpan hasil screening
workflow.add_node("test_generator", test_generator_node) # Buat 20 soal
workflow.add_node("reviewer", reviewer_node)             # Validasi soal (max 2x)
workflow.add_node("db_writer_questions", db_writer_questions_node)  # Simpan soal

# ==========================================
# Entry Point
# ==========================================
workflow.set_entry_point("read_file")

# ==========================================
# Edge Routing Functions
# ==========================================

def route_after_read(state: CVScreeningState) -> str:
    """Jika gagal baca file, stop. Jika sukses, lanjut ke Extractor."""
    if state.get("screening_status") == "error":
        return END
    return "extractor"

def route_after_extractor(state: CVScreeningState) -> str:
    """Jika Extractor gagal, stop. Jika sukses, lanjut ke Evaluator."""
    if state.get("screening_status") == "error":
        return END
    return "evaluator"

def route_after_evaluator(state: CVScreeningState) -> str:
    """
    Setelah Evaluator:
    - Jika error → stop
    - Selalu simpan hasil ke DB dulu (skor & status)
    """
    if state.get("screening_status") == "error":
        return END
    return "db_writer"

def route_after_db_writer(state: CVScreeningState) -> str:
    """
    Setelah hasil screening tersimpan:
    - Jika skor >= threshold → generate soal
    - Jika skor < threshold → selesai (kandidat ditolak)
    """
    if state.get("screening_status") == "error":
        return END
    skor = state.get("skor_kecocokan") or 0
    threshold = state.get("threshold_skor") or 80
    if skor >= threshold:
        return "test_generator"
    return END

def route_after_reviewer(state: CVScreeningState) -> str:
    """
    Loop Reviewer <-> Test Generator (max 2 iterasi):
    - Jika PASS → simpan soal ke DB
    - Jika FAIL dan masih bisa retry → kembali ke test_generator
    - Jika FAIL tapi sudah max retry → tetap simpan soal terbaik yang ada
    """
    if state.get("screening_status") == "error":
        return END

    reviewer_status = state.get("reviewer_status", "FAIL")
    retry_count = state.get("retry_count") or 0

    if reviewer_status == "PASS":
        return "db_writer_questions"

    # FAIL: cek apakah masih bisa retry
    if retry_count < MAX_REVIEW_RETRIES:
        return "test_generator"   # Kembali ke Generator dengan feedback

    # Max retry tercapai, simpan apa yang ada
    return "db_writer_questions"

# ==========================================
# Definisikan Semua Edges
# ==========================================
workflow.add_conditional_edges("read_file", route_after_read)
workflow.add_conditional_edges("extractor", route_after_extractor)
workflow.add_conditional_edges("evaluator", route_after_evaluator)
workflow.add_conditional_edges("db_writer", route_after_db_writer)
workflow.add_edge("test_generator", "reviewer")
workflow.add_conditional_edges("reviewer", route_after_reviewer)
workflow.add_edge("db_writer_questions", END)

# ==========================================
# Compile Pipeline
# ==========================================
cv_screening_pipeline = workflow.compile()


# ==========================================
# Helper: Background Task untuk FastAPI
# ==========================================
async def process_cv_background(
    company_id: str,
    job_id: str,
    applicant_id: str,
    kriteria_perusahaan: str,
    threshold_skor: int,
    cv_file_path: str,
    cv_original_filename: str
):
    """
    Fungsi helper untuk dipanggil sebagai FastAPI BackgroundTask.
    Menginisialisasi state awal dan menjalankan pipeline multi-agent.
    """
    initial_state = {
        "company_id": company_id,
        "job_id": job_id,
        "applicant_id": applicant_id,
        "kriteria_perusahaan": kriteria_perusahaan,
        "threshold_skor": threshold_skor,
        "cv_file_path": cv_file_path,
        "cv_original_filename": cv_original_filename,
        "screening_status": "pending",
        "retry_count": 0,
        # Field opsional diinisialisasi None
        "extracted_skills": None,
        "raw_evaluator_output": None,
        "skor_kecocokan": None,
        "label": None,
        "laporan_analisis_markdown": None,
        "cv_summary": None,
        "kelebihan_utama": None,
        "kekurangan_utama": None,
        "soal_list": None,
        "reviewer_status": None,
        "reviewer_feedback": None,
        "reviewer_skor": None,
        "error_message": None,
    }

    result = await cv_screening_pipeline.ainvoke(initial_state)
    return result
