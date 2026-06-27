from typing import TypedDict, List, Optional, Any

class CVScreeningState(TypedDict):
    # Identifiers
    company_id: str
    job_id: str
    applicant_id: str

    # Context
    kriteria_perusahaan: str
    threshold_skor: int

    # File Info
    cv_file_path: str
    cv_original_filename: str

    # Node 1: read_file output
    cv_text: str

    # Node 2: extractor output (struktur skill terorganisir)
    extracted_skills: Optional[str]   # JSON string hasil ekstraksi

    # Node 3: evaluator output
    raw_evaluator_output: Optional[str]
    skor_kecocokan: Optional[int]
    label: Optional[str]
    laporan_analisis_markdown: Optional[str]
    cv_summary: Optional[str]
    kelebihan_utama: Optional[List[str]]
    kekurangan_utama: Optional[List[str]]

    # Node 4: test_generator output
    soal_list: Optional[Any]          # List of dict soal mentah dari LLM

    # Node 5: reviewer output
    reviewer_status: Optional[str]    # "PASS" atau "FAIL"
    reviewer_feedback: Optional[str]  # Feedback jika FAIL
    reviewer_skor: Optional[int]      # Skor kualitas 1-100
    retry_count: Optional[int]        # Jumlah iterasi reviewer (max 2)

    # Metadata
    screening_status: str
    error_message: Optional[str]
