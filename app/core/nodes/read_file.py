import fitz  # PyMuPDF
import os
from app.core.state import CVScreeningState

def read_file_node(state: CVScreeningState) -> CVScreeningState:
    file_path = state.get("cv_file_path")
    if not file_path or not os.path.exists(file_path):
        state["screening_status"] = "error"
        state["error_message"] = f"File {file_path} not found."
        return state
        
    try:
        text = ""
        # Cek ekstensi file (asumsi pdf dulu)
        if file_path.endswith('.pdf'):
            doc = fitz.open(file_path)
            for page in doc:
                text += page.get_text()
            doc.close()
        else:
            # Fallback untuk txt atau ekstensi lain jika ada
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
                
        state["cv_text"] = text
        state["screening_status"] = "processing"
    except Exception as e:
        state["screening_status"] = "error"
        state["error_message"] = str(e)
        
    return state
