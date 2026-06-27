import json
import re
from openai import AsyncOpenAI
from app.core.state import CVScreeningState
from app.core.config import settings


async def extractor_node(state: CVScreeningState) -> CVScreeningState:
    """
    Agent 1: Extractor
    Membaca teks CV mentah dan mengekstrak informasi terstruktur (skill, pengalaman, pendidikan).
    Menggunakan model deepseek-chat yang stabil untuk JSON parsing.
    """
    if state.get("screening_status") == "error":
        return state

    cv_text = state.get("cv_text", "")
    if not cv_text.strip():
        state["screening_status"] = "error"
        state["error_message"] = "CV text is empty, cannot extract."
        return state

    # Format prompt dari .env, mengganti placeholder {cv_text}
    prompt = settings.PROMPT_EXTRACTOR.replace("{cv_text}", cv_text)

    try:
        client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_API_BASE
        )
        response = await client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL_CHAT,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.1,  # Rendah agar ekstraksi konsisten dan faktual
        )

        raw_content = response.choices[0].message.content.strip()
        # Bersihkan markdown fence jika ada
        clean_json = re.sub(r"```json|```", "", raw_content).strip()
        # Validasi JSON
        json.loads(clean_json)

        state["extracted_skills"] = clean_json
        state["screening_status"] = "extracted"

    except json.JSONDecodeError as e:
        state["screening_status"] = "error"
        state["error_message"] = f"Extractor JSON Parsing Error: {str(e)}"
    except Exception as e:
        state["screening_status"] = "error"
        state["error_message"] = f"Extractor LLM Error: {str(e)}"

    return state
