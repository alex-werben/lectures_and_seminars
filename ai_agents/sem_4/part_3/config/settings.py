"""Configuration settings for AutoGen Multi-Agent System."""

try:
    from pydantic_settings import BaseSettings
except ImportError as e:
    raise ImportError(f"Pydantic не установлен. Установите: pip install pydantic pydantic-settings. Ошибка: {e}")


class Config(BaseSettings):
    """Гибкая конфигурация через переменные окружения."""
    
    OLLAMA_BASE_URL: str = "http://localhost:11434/v1"
    OLLAMA_API_KEY: str = "ollama"
    CODE_LLM_MODEL: str = "qwen2.5-coder:32b"
    GENERAL_LLM_MODEL: str = "qwen2.5:32b"  # Лучше следует инструкциям, без <think>
    DATA_EXTRACTION_MODEL: str = "qwen2.5:32b"  # Специализированная модель для извлечения данных
    WORKSPACE_DIR: str = "test_example"
    SCRIPT_NAME: str = "generated_script.py"
    TESTS_NAME: str = "test_generated_script.py"
    MAX_IMPROVEMENT_LOOPS: int = 15
    USE_DOCKER: bool = True
    DOCKER_IMAGE: str = "python:3.11"
    
    # Стоимость токенов в рублях (примерные значения)
    TOKEN_INPUT_COST: float = 0.0002  # Стоимость входящего токена в рублях
    TOKEN_OUTPUT_COST: float = 0.0002  # Стоимость исходящего токена в рублях

    class Config:
        env_file = ".env"  # Позволяет переопределять переменные через .env файл
        env_file_encoding = "utf-8" 