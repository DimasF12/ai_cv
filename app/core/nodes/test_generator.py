import json
import re
from openai import AsyncOpenAI
from app.core.state import CVScreeningState
from app.core.config import settings


async def test_generator_node(state: CVScreeningState) -> CVScreeningState:
    """
    Agent 3: Test Generator
    Membuat 20 soal ujian kustom (14 MCQ + 6 Essay) berdasarkan profil kandidat.
    Hanya berjalan jika skor_kecocokan >= threshold (default: 80).
    Jika ada feedback dari Reviewer, prompt akan disertakan untuk perbaikan.
    """
    if state.get("screening_status") == "error":
        return state

    cv_summary = state.get("cv_summary", "")
    extracted_skills = state.get("extracted_skills", "")
    kriteria = state.get("kriteria_perusahaan", "")
    reviewer_feedback = state.get("reviewer_feedback", "")

    # Format prompt dari .env
    prompt = (
        settings.PROMPT_TEST_GENERATOR
        .replace("{cv_summary}", cv_summary)
        .replace("{extracted_skills}", extracted_skills)
        .replace("{kriteria_perusahaan}", kriteria)
    )

    # Jika ada feedback dari Reviewer (iterasi ke-2), tambahkan konteks perbaikan
    if reviewer_feedback:
        prompt += f"\n\n--- FEEDBACK DARI REVIEWER (WAJIB DIPERBAIKI) ---\n{reviewer_feedback}"

    try:
        client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_API_BASE
        )
        response = await client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL_CHAT,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.5,  # Sedikit lebih tinggi agar soal bervariasi
        )

        raw_content = response.choices[0].message.content.strip()
        clean_json = re.sub(r"```json|```", "", raw_content).strip()
        parsed_data = json.loads(clean_json)

        soal_list = parsed_data.get("soal", [])
        if len(soal_list) == 0:
            raise ValueError("Generator menghasilkan 0 soal, response tidak valid.")

        state["soal_list"] = soal_list
        # Reset reviewer state untuk iterasi baru
        state["reviewer_status"] = None
        state["reviewer_feedback"] = None

    except json.JSONDecodeError as e:
        state["screening_status"] = "error"
        state["error_message"] = f"Test Generator JSON Parsing Error: {str(e)}"
    except Exception as e:
        state["screening_status"] = "error"
        state["error_message"] = f"Test Generator LLM Error: {str(e)}"

    return state
