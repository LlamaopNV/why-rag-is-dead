from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # API keys
    anthropic_api_key: str = ""

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    worker_model: str = "qwen2.5:1.5b"
    manager_model: str = "qwen2.5:7b"

    # Claude models
    planner_model: str = "claude-sonnet-4-6"
    main_model: str = "claude-sonnet-4-6"

    # Codebase
    codebase_path: str = "./codebase"

    # Agent tuning
    worker_timeout: int = 60
    worker_max_failures: int = 3

    # Database (stretch goal)
    database_url: str = "postgresql://nexus:nexus@localhost:5432/nexus"


settings = Settings()
