import json
import re
from openai import AsyncOpenAI
from app.core.state import CVScreeningState
from app.core.config import settings


async def evaluate_node(state: CVScreeningState) -> CVScreeningState:
    """
    Agent 2: Evaluator
    Menilai kecocokan kandidat (skor 1-100) berdasarkan hasil Extractor Agent
    dibandingkan dengan kriteria/job description dari HR.
    Menggunakan deepseek-chat (bukan reasoner) agar output JSON stabil.
    """
    if state.get("screening_status") == "error":
        return state

    extracted_skills = state.get("extracted_skills", "")
    kriteria = state.get("kriteria_perusahaan", "")

    # Format prompt dari .env
    prompt = (
        settings.PROMPT_EVALUATOR
        .replace("{kriteria_perusahaan}", kriteria)
        .replace("{extracted_skills}", extracted_skills)
    )

    try:
        client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_API_BASE
        )
        response = await client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL_CHAT,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.2,
        )

        raw_content = response.choices[0].message.content.strip()
        state["raw_evaluator_output"] = raw_content

        clean_json = re.sub(r"```json|```", "", raw_content).strip()
        parsed_data = json.loads(clean_json)

        state["skor_kecocokan"] = parsed_data.get("skor_kecocokan")
        state["label"] = parsed_data.get("label")
        state["laporan_analisis_markdown"] = parsed_data.get("laporan_analisis_markdown")
        state["cv_summary"] = parsed_data.get("cv_summary")
        state["kelebihan_utama"] = parsed_data.get("kelebihan_utama", [])
        state["kekurangan_utama"] = parsed_data.get("kekurangan_utama", [])
        state["screening_status"] = "evaluated"

    except json.JSONDecodeError as e:
        state["screening_status"] = "error"
        state["error_message"] = f"Evaluator JSON Parsing Error: {str(e)}"
    except Exception as e:
        state["screening_status"] = "error"
        state["error_message"] = f"Evaluator LLM Error: {str(e)}"

    return state
