import os
from dotenv import load_dotenv

# Load .env file for local development
# In production (Container App), these come from app settings
load_dotenv()

class Config:
    # App
    APP_NAME: str = os.getenv("APP_NAME", "slo-demo-service")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # Azure
    AZURE_SUBSCRIPTION_ID: str = os.getenv("AZURE_SUBSCRIPTION_ID", "")
    AZURE_RESOURCE_GROUP: str = os.getenv("AZURE_RESOURCE_GROUP", "rg-slo-dashboard")

    # Application Insights — get this from terraform output
    APPLICATIONINSIGHTS_CONNECTION_STRING: str = os.getenv(
        "APPLICATIONINSIGHTS_CONNECTION_STRING", ""
    )

    # OpenRouter AI
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL: str = os.getenv(
        "OPENROUTER_MODEL", "anthropic/claude-haiku-4-5"
    )

    # SLO Targets
    SLO_AVAILABILITY_TARGET: float = float(
        os.getenv("SLO_AVAILABILITY_TARGET", "0.999")  # 99.9%
    )
    SLO_LATENCY_TARGET_MS: int = int(
        os.getenv("SLO_LATENCY_TARGET_MS", "200")
    )

config = Config()