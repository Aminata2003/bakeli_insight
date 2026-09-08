from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

    # =========================
    # Base de données
    # =========================
    database_url: str

    # =========================
    # API Keys
    # =========================
    api_keys: str = (
        "admin-secret:admin,"
        "analyst-secret:analyst,"
        "collaborator-secret:collaborator"
    )

    # =========================
    # JWT
    # =========================
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60

    # =========================
    # Hugging Face
    # =========================
    hf_api_token: str | None = None

    hf_sentiment_model: str = (
        "cardiffnlp/twitter-xlm-roberta-base-sentiment"
    )

    hf_inference_url: str = (
        "https://router.huggingface.co/hf-inference/models/"
        "cardiffnlp/twitter-xlm-roberta-base-sentiment"
    )

    # =========================
    # Google Sheets (ingestion Google Forms)
    # =========================
    google_service_account_file: str | None = None
    google_sheets_id_disponibilite: str | None = None
    google_sheets_plage_disponibilite: str = "Form_Responses"
    typeform_api_token: str | None = None
    typeform_form_id: str | None = None

settings = Settings()