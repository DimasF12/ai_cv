from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Portal Backend"

    # Database
    DATABASE_URL: str

    # Keamanan
    SECURE_API_HEADER_TOKEN: str = "ganti-dengan-token-rahasia-anda"

    # API Keys & Model DeepSeek
    DEEPSEEK_API_KEY: str
    DEEPSEEK_API_BASE: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL_CHAT: str = "deepseek-chat"
    DEEPSEEK_MODEL_REASONER: str = "deepseek-reasoner"

    # Prompt AI (dimuat dari .env)
    PROMPT_EXTRACTOR: str
    PROMPT_EVALUATOR: str
    PROMPT_TEST_GENERATOR: str
    PROMPT_REVIEWER: str

    # Konfigurasi Pydantic untuk membaca file .env
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

# Instansiasi objek settings agar bisa di-import di file lain
settings = Settings()