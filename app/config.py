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
    discord_bot_token: str | None = None
    discord_channel_id_entraide: str | None = None
    mongodb_url: str | None = None
    mongodb_database: str = "bakeli_insights"
    google_business_account_id: str | None = None
    google_business_location_id: str | None = None
    meta_page_access_token: str | None = None
    instagram_media_ids: str | None = None  # liste séparée par des virgules
    facebook_post_ids: str | None = None    # liste séparée par des virgules
    telegram_bot_token: str | None = None
settings = Settings()