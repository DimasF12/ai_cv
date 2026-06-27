import json
import re
from openai import AsyncOpenAI
from app.core.state import CVScreeningState
from app.core.config import settings

MAX_REVIEW_RETRIES = 2


async def reviewer_node(state: CVScreeningState) -> CVScreeningState:
    """
    Agent 4: Reviewer (Critic)
    Memvalidasi kualitas 20 soal yang dibuat oleh Test Generator.
    Jika FAIL dan retry_count < MAX_REVIEW_RETRIES (2), kembalikan ke generator.
    Jika sudah max retry atau PASS, lanjut ke db_writer_questions.
    """
    if state.get("screening_status") == "error":
        return state

    soal_list = state.get("soal_list", [])
    cv_summary = state.get("cv_summary", "")

    soal_json_str = json.dumps(soal_list, ensure_ascii=False, indent=2)

    # Format prompt dari .env
    prompt = (
        settings.PROMPT_REVIEWER
        .replace("{soal_json}", soal_json_str)
        .replace("{cv_summary}", cv_summary)
    )

    # Inisialisasi retry_count jika belum ada
    current_retry = state.get("retry_count") or 0

    try:
        client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_API_BASE
        )
        response = await client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL_CHAT,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.1,  # Rendah agar penilaian konsisten
        )

        raw_content = response.choices[0].message.content.strip()
        clean_json = re.sub(r"```json|```", "", raw_content).strip()
        parsed_data = json.loads(clean_json)

        review_status = parsed_data.get("status", "FAIL").upper()
        feedback = parsed_data.get("feedback", "")
        skor_kualitas = parsed_data.get("skor_kualitas", 0)

        state["reviewer_status"] = review_status
        state["reviewer_feedback"] = feedback if review_status == "FAIL" else ""
        state["reviewer_skor"] = skor_kualitas
        state["retry_count"] = current_retry + 1

    except json.JSONDecodeError as e:
        # Jika reviewer sendiri error parsing, anggap PASS agar pipeline tidak infinite loop
        state["reviewer_status"] = "PASS"
        state["reviewer_feedback"] = ""
        state["retry_count"] = MAX_REVIEW_RETRIES  # Force stop loop
    except Exception as e:
        state["screening_status"] = "error"
        state["error_message"] = f"Reviewer LLM Error: {str(e)}"

    return state
